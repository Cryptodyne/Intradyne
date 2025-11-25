import os
import re
import hashlib
from typing import List, Optional, Dict, Any
from collections import OrderedDict
import chromadb
from chromadb.utils import embedding_functions

class RAGEngine:
    """
    Layer 5 Component: Zero Hallucination Tolerance.
    Indexes Rulebook, Instructions, and Chronicles to provide
    grounded context for the Hybrid Ensemble.
    """
    def __init__(self, persistence_path: str = "data/vector_store"):
        self.client = chromadb.PersistentClient(path=persistence_path)
        # Use faster embedding model
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        self.collection = self.client.get_or_create_collection(
            name="intradyne_knowledge_base",
            embedding_function=self.embedding_fn
        )
        
        # Semantic cache with similarity matching
        self._query_cache = OrderedDict()
        self._cache_max_size = 100
        self._cache_ttl = 300  # 5 minutes
        self._similarity_threshold = 0.85  # 85% similarity to match
        
        # Query expansion synonyms
        self._synonyms = {
            "stop loss": ["stop loss", "SL", "exit point", "stop order"],
            "capital": ["capital", "equity", "funds", "balance"],
            "risk": ["risk", "exposure", "drawdown"],
            "forbidden": ["forbidden", "prohibited", "not allowed", "banned"],
        }

    def _clean_text(self, text: str) -> str:
        """Normalize whitespace and formatting."""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove leading/trailing whitespace
        text = text.strip()
        return text

    def _extract_rule_number(self, text: str) -> Optional[str]:
        """Extract rule number from text (e.g., '1.', '10.', 'SOP-01')."""
        # Match patterns like "1.", "10.", "SOP-01"
        match = re.search(r'(?:^|\s)(\d+\.|\w+-\d+)', text)
        return match.group(1).rstrip('.') if match else None

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text."""
        # Simple keyword extraction - lowercase words > 4 chars
        words = re.findall(r'\b\w{5,}\b', text.lower())
        # Remove common words
        stopwords = {'should', 'would', 'could', 'there', 'their', 'which', 'where'}
        return [w for w in set(words) if w not in stopwords][:10]

    def _categorize_content(self, text: str, metadata: dict) -> str:
        """Categorize content based on keywords."""
        text_lower = text.lower()
        if metadata.get('type') == 'rule':
            if any(word in text_lower for word in ['risk', 'drawdown', 'loss', 'leverage']):
                return 'risk'
            elif any(word in text_lower for word in ['shariah', 'halal', 'forbidden', 'compliance']):
                return 'compliance'
            elif any(word in text_lower for word in ['capital', 'preservation', 'equity']):
                return 'capital'
        elif metadata.get('type') == 'instruction':
            return 'execution'
        return 'general'

    def _assign_priority(self, text: str, rule_number: Optional[str]) -> str:
        """Assign priority level based on content."""
        text_lower = text.lower()
        # Critical keywords
        if any(word in text_lower for word in ['never', 'must', 'forbidden', 'halt']):
            return 'critical'
        # High priority for early rules
        if rule_number and int(re.search(r'\d+', rule_number).group()) <= 5:
            return 'high'
        # Medium for risk-related
        if any(word in text_lower for word in ['risk', 'limit', 'check']):
            return 'medium'
        return 'low'

    def _chunk_document(self, text: str, source_file: str, doc_type: str) -> List[Dict[str, Any]]:
        """Split document into semantic chunks by headers."""
        chunks = []
        
        # Split by markdown headers (## or ###)
        sections = re.split(r'\n(#{2,3}\s+.+)', text)
        
        current_section = "Introduction"
        current_text = ""
        
        for i, part in enumerate(sections):
            if re.match(r'^#{2,3}\s+', part):
                # This is a header
                if current_text.strip():
                    # Save previous chunk
                    chunk_data = self._create_chunk(
                        current_text, source_file, doc_type, current_section, len(chunks)
                    )
                    chunks.append(chunk_data)
                
                current_section = part.strip('#').strip()
                current_text = ""
            else:
                current_text += part
        
        # Add last chunk
        if current_text.strip():
            chunk_data = self._create_chunk(
                current_text, source_file, doc_type, current_section, len(chunks)
            )
            chunks.append(chunk_data)
        
        return chunks

    def _create_chunk(self, text: str, source_file: str, doc_type: str, 
                     section: str, chunk_index: int) -> Dict[str, Any]:
        """Create a chunk with metadata."""
        cleaned_text = self._clean_text(text)
        rule_number = self._extract_rule_number(cleaned_text)
        keywords = self._extract_keywords(cleaned_text)
        
        metadata = {
            "type": doc_type,
            "source_file": source_file,
            "section": section,
            "chunk_index": chunk_index,
            "keywords": ",".join(keywords),  # ChromaDB requires string values
        }
        
        category = self._categorize_content(cleaned_text, metadata)
        priority = self._assign_priority(cleaned_text, rule_number)
        
        metadata["category"] = category
        metadata["priority"] = priority
        
        if rule_number:
            metadata["rule_number"] = rule_number
        
        return {
            "text": cleaned_text,
            "metadata": metadata,
            "id": f"{source_file}_{chunk_index}"
        }

    def ingest_document(self, doc_id: str, text: str, metadata: dict):
        """Ingests a document (Rule, Instruction, Chronicle) into the vector store."""
        self.collection.add(
            documents=[text],
            metadatas=[metadata],
            ids=[doc_id]
        )

    def load_knowledge_base(self, config_path: str = "config"):
        """Scans config directory and ingests markdown files with chunking."""
        all_chunks = []
        
        # Ingest Rules
        rule_path = os.path.join(config_path, "rulebook")
        if os.path.exists(rule_path):
            for f in os.listdir(rule_path):
                if f.endswith(".md"):
                    with open(os.path.join(rule_path, f), 'r', encoding='utf-8') as file:
                        text = file.read()
                        chunks = self._chunk_document(text, f, "rule")
                        all_chunks.extend(chunks)

        # Ingest Instructions
        inst_path = os.path.join(config_path, "instructions")
        if os.path.exists(inst_path):
            for f in os.listdir(inst_path):
                if f.endswith(".md"):
                    with open(os.path.join(inst_path, f), 'r', encoding='utf-8') as file:
                        text = file.read()
                        chunks = self._chunk_document(text, f, "instruction")
                        all_chunks.extend(chunks)
        
        # Batch ingest all chunks
        if all_chunks:
            self.collection.add(
                documents=[c["text"] for c in all_chunks],
                metadatas=[c["metadata"] for c in all_chunks],
                ids=[c["id"] for c in all_chunks]
            )

    def _get_cache_key(self, query: str, **kwargs) -> str:
        """Generate cache key from query and parameters."""
        import hashlib
        import json
        key_str = json.dumps({'query': query, **kwargs}, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _add_to_semantic_cache(self, query: str, results: List[Dict[str, Any]], **kwargs):
        """Add query results to semantic cache."""
        import time
        
        cache_key = self._get_cache_key(query, **kwargs)
        
        # Add to cache
        self._query_cache[cache_key] = (results, time.time())
        
        # LRU eviction
        if len(self._query_cache) > self._cache_max_size:
            # Remove oldest (first) item
            self._query_cache.popitem(last=False)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get semantic cache statistics."""
        import time
        
        # Count valid entries
        valid_entries = sum(
            1 for _, (_, timestamp) in self._query_cache.items()
            if time.time() - timestamp < self._cache_ttl
        )
        
        return {
            'total_entries': len(self._query_cache),
            'valid_entries': valid_entries,
            'max_size': self._cache_max_size,
            'ttl_seconds': self._cache_ttl,
            'similarity_threshold': self._similarity_threshold
        }

    def _expand_query(self, query: str) -> List[str]:
        """Expand query with synonyms."""
        expanded = [query]
        query_lower = query.lower()
        
        for term, synonyms in self._synonyms.items():
            if term in query_lower:
                for syn in synonyms:
                    if syn != term:
                        expanded.append(query_lower.replace(term, syn))
        
        return expanded[:3]  # Limit to 3 variations

    def query_context(self, query_text: str, n_results: int = 3) -> List[str]:
        """Retrieves relevant context to validate decisions."""
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        return results['documents'][0] if results['documents'] else []

    def query_rules(self, query: str, category: Optional[str] = None, 
                   priority: Optional[str] = None, n: int = 3) -> List[Dict[str, Any]]:
        """Query only rules with optional filters."""
        where_filter = {"type": "rule"}
        
        if category:
            where_filter["category"] = category
        if priority:
            where_filter["priority"] = priority
        
        results = self.collection.query(
            query_texts=[query],
            n_results=n,
            where=where_filter
        )
        
        return self._format_results(results)

    def query_instructions(self, query: str, sop_id: Optional[str] = None, n: int = 3) -> List[Dict[str, Any]]:
        """Query only SOPs."""
        where_filter = {"type": "instruction"}
        
        if sop_id:
            where_filter["rule_number"] = sop_id
        
        results = self.collection.query(
            query_texts=[query],
            n_results=n,
            where=where_filter
        )
        
        return self._format_results(results)

    def query_by_keyword(self, keywords: List[str], n: int = 5) -> List[Dict[str, Any]]:
        """Exact keyword matching."""
        # Query with combined keywords
        query = " ".join(keywords)
        results = self.collection.query(
            query_texts=[query],
            n_results=n
        )
        
        # Filter results that contain at least one keyword
        formatted = self._format_results(results)
        filtered = []
        for result in formatted:
            result_keywords = result['metadata'].get('keywords', '').split(',')
            if any(kw in result_keywords for kw in keywords):
                filtered.append(result)
        
        return filtered[:n]

    def hybrid_search(self, query: str, keywords: Optional[List[str]] = None, 
                     filters: Optional[dict] = None, n: int = 5) -> List[Dict[str, Any]]:
        """Combined semantic + keyword search with re-ranking."""
        # Expand query
        expanded_queries = self._expand_query(query)
        
        all_results = []
        for q in expanded_queries:
            results = self.collection.query(
                query_texts=[q],
                n_results=n * 2,  # Get more for re-ranking
                where=filters
            )
            all_results.extend(self._format_results(results))
        
        # Re-rank by multiple factors
        scored_results = []
        for result in all_results:
            score = 0.0
            
            # Semantic similarity (already in distance, lower is better)
            # Convert to score (higher is better)
            score += (1.0 - result.get('distance', 0.5)) * 0.4
            
            # Keyword overlap
            if keywords:
                result_keywords = result['metadata'].get('keywords', '').split(',')
                overlap = len(set(keywords) & set(result_keywords))
                score += (overlap / len(keywords)) * 0.3
            
            # Priority boost
            priority_scores = {'critical': 1.0, 'high': 0.7, 'medium': 0.4, 'low': 0.2}
            score += priority_scores.get(result['metadata'].get('priority', 'low'), 0.2) * 0.3
            
            result['rerank_score'] = score
            scored_results.append(result)
        
        # Sort by score and deduplicate
        scored_results.sort(key=lambda x: x['rerank_score'], reverse=True)
        seen_ids = set()
        unique_results = []
        for r in scored_results:
            if r['id'] not in seen_ids:
                seen_ids.add(r['id'])
                unique_results.append(r)
        
        return unique_results[:n]

    def _format_results(self, results: dict) -> List[Dict[str, Any]]:
        """Format ChromaDB results into structured dicts."""
        formatted = []
        if not results['documents'] or not results['documents'][0]:
            return formatted
        
        for i, doc in enumerate(results['documents'][0]):
            formatted.append({
                'text': doc,
                'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                'distance': results['distances'][0][i] if results.get('distances') else 0.0,
                'id': results['ids'][0][i] if results['ids'] else f"result_{i}"
            })
        
        return formatted

    def validate_compliance(self, proposed_action: str, asset: str = None, 
                          position_size: float = None) -> Dict[str, Any]:
        """
        Multi-stage compliance validation.
        Returns detailed compliance report.
        """
        violations = []
        warnings = []
        matched_rules = []
        
        # Stage 1: Asset screening
        if asset:
            asset_rules = self.query_rules(f"forbidden assets {asset}", category="compliance", n=5)
            for rule in asset_rules:
                if any(word in rule['text'].lower() for word in ['forbidden', 'prohibited', 'not allowed']):
                    if asset.upper() in rule['text'].upper():
                        violations.append(f"Asset {asset} may be forbidden: {rule['text'][:100]}")
                        matched_rules.append(rule)
        
        # Stage 2: Risk limits
        risk_rules = self.query_rules("risk management limits", category="risk", n=5)
        matched_rules.extend(risk_rules)
        
        # Stage 3: Capital preservation
        if position_size:
            capital_rules = self.query_rules("capital preservation position size", n=3)
            for rule in capital_rules:
                # Check for percentage limits
                if '2%' in rule['text'] and position_size > 0.02:
                    warnings.append(f"Position size may exceed 2% limit: {rule['text'][:100]}")
                    matched_rules.append(rule)
        
        # Stage 4: Action-specific rules
        action_rules = self.hybrid_search(proposed_action, n=5)
        matched_rules.extend(action_rules)
        
        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "warnings": warnings,
            "matched_rules": matched_rules[:10],  # Limit to top 10
            "total_rules_checked": len(matched_rules)
        }

