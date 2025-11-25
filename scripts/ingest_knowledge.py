import os
import glob
from src.core.rag_engine import RAGEngine

def ingest_all():
    rag = RAGEngine()
    
    # Ingest Rules
    rule_files = glob.glob("config/rulebook/*.md")
    for file_path in rule_files:
        with open(file_path, "r") as f:
            content = f.read()
            rag.ingest_document(
                doc_id=os.path.basename(file_path),
                text=content,
                metadata={"type": "rulebook", "source": file_path}
            )
            print(f"Ingested {file_path}")

    # Ingest Instructions
    sop_files = glob.glob("config/instructions/*.md")
    for file_path in sop_files:
        with open(file_path, "r") as f:
            content = f.read()
            rag.ingest_document(
                doc_id=os.path.basename(file_path),
                text=content,
                metadata={"type": "instruction", "source": file_path}
            )
            print(f"Ingested {file_path}")

if __name__ == "__main__":
    ingest_all()
