"""
Ensemble Orchestrator
Coordinates multiple trading strategies and combines their signals
"""

from typing import Dict, List, Callable, Optional, Any
from datetime import datetime
import numpy as np
import logging

class StrategyWrapper:
    """Wrapper for individual strategy with metadata"""
    
    def __init__(self, name: str, strategy_func: Callable, 
                 weight: float = 1.0, enabled: bool = True):
        self.name = name
        self.strategy_func = strategy_func
        self.weight = weight
        self.enabled = enabled
        
        # Performance tracking
        self.signals_generated = 0
        self.correct_signals = 0
        self.accuracy = 0.0
        self.recent_performance = []
    
    def generate_signal(self, data, index: int, **kwargs) -> str:
        """Generate signal from strategy"""
        if not self.enabled:
            return 'HOLD'
        
        try:
            signal = self.strategy_func(data, index, **kwargs)
            self.signals_generated += 1
            return signal
        except Exception as e:
            logging.error(f"Strategy {self.name} error: {e}")
            return 'HOLD'
    
    def update_performance(self, was_correct: bool):
        """Update strategy performance"""
        if was_correct:
            self.correct_signals += 1
        
        self.recent_performance.append(1 if was_correct else 0)
        if len(self.recent_performance) > 20:
            self.recent_performance.pop(0)
        
        # Calculate accuracy
        if self.signals_generated > 0:
            self.accuracy = self.correct_signals / self.signals_generated


class EnsembleOrchestrator:
    """
    Orchestrates multiple trading strategies.
    Combines signals using various methods.
    """
    
    def __init__(self, combination_method: str = 'weighted_vote'):
        """
        Initialize ensemble orchestrator.
        
        Args:
            combination_method: 'weighted_vote', 'majority_vote', 'unanimous', 
                              'confidence_weighted', 'performance_weighted'
        """
        self.strategies: List[StrategyWrapper] = []
        self.combination_method = combination_method
        self.logger = logging.getLogger("EnsembleOrchestrator")
        
        # Ensemble performance
        self.ensemble_signals = 0
        self.ensemble_correct = 0
        self.ensemble_accuracy = 0.0
    
    def add_strategy(self, name: str, strategy_func: Callable, 
                    weight: float = 1.0, enabled: bool = True):
        """Add strategy to ensemble"""
        wrapper = StrategyWrapper(name, strategy_func, weight, enabled)
        self.strategies.append(wrapper)
        self.logger.info(f"Added strategy: {name} (weight: {weight})")
    
    def remove_strategy(self, name: str):
        """Remove strategy from ensemble"""
        self.strategies = [s for s in self.strategies if s.name != name]
        self.logger.info(f"Removed strategy: {name}")
    
    def enable_strategy(self, name: str):
        """Enable a strategy"""
        for strategy in self.strategies:
            if strategy.name == name:
                strategy.enabled = True
                self.logger.info(f"Enabled strategy: {name}")
    
    def disable_strategy(self, name: str):
        """Disable a strategy"""
        for strategy in self.strategies:
            if strategy.name == name:
                strategy.enabled = False
                self.logger.info(f"Disabled strategy: {name}")
    
    def generate_ensemble_signal(self, data, index: int, **kwargs) -> Dict[str, Any]:
        """
        Generate ensemble signal from all strategies.
        
        Returns:
            Dictionary with signal, confidence, and breakdown
        """
        # Collect signals from all strategies
        signals = {}
        for strategy in self.strategies:
            if strategy.enabled:
                signal = strategy.generate_signal(data, index, **kwargs)
                signals[strategy.name] = {
                    'signal': signal,
                    'weight': strategy.weight,
                    'accuracy': strategy.accuracy
                }
        
        if not signals:
            return {
                'signal': 'HOLD',
                'confidence': 0.0,
                'breakdown': {},
                'method': self.combination_method
            }
        
        # Combine signals based on method
        if self.combination_method == 'weighted_vote':
            final_signal, confidence = self._weighted_vote(signals)
        elif self.combination_method == 'majority_vote':
            final_signal, confidence = self._majority_vote(signals)
        elif self.combination_method == 'unanimous':
            final_signal, confidence = self._unanimous(signals)
        elif self.combination_method == 'confidence_weighted':
            final_signal, confidence = self._confidence_weighted(signals)
        elif self.combination_method == 'performance_weighted':
            final_signal, confidence = self._performance_weighted(signals)
        else:
            final_signal, confidence = self._weighted_vote(signals)
        
        self.ensemble_signals += 1
        
        return {
            'signal': final_signal,
            'confidence': confidence,
            'breakdown': signals,
            'method': self.combination_method,
            'num_strategies': len(signals)
        }
    
    def _weighted_vote(self, signals: Dict) -> tuple[str, float]:
        """Combine using weighted voting"""
        votes = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        
        for strategy_name, data in signals.items():
            signal = data['signal']
            weight = data['weight']
            votes[signal] += weight
        
        # Get winner
        max_vote = max(votes.values())
        if max_vote == 0:
            return 'HOLD', 0.0
        
        winner = max(votes, key=votes.get)
        confidence = max_vote / sum(votes.values())
        
        return winner, confidence
    
    def _majority_vote(self, signals: Dict) -> tuple[str, float]:
        """Simple majority voting (equal weights)"""
        votes = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        
        for strategy_name, data in signals.items():
            signal = data['signal']
            votes[signal] += 1
        
        winner = max(votes, key=votes.get)
        confidence = votes[winner] / len(signals)
        
        return winner, confidence
    
    def _unanimous(self, signals: Dict) -> tuple[str, float]:
        """Require unanimous agreement"""
        signal_list = [data['signal'] for data in signals.values()]
        
        if len(set(signal_list)) == 1:
            # All agree
            return signal_list[0], 1.0
        else:
            # No agreement
            return 'HOLD', 0.0
    
    def _confidence_weighted(self, signals: Dict) -> tuple[str, float]:
        """Weight by signal confidence (if available)"""
        # Similar to weighted vote but could use confidence scores
        # For now, use accuracy as proxy for confidence
        return self._performance_weighted(signals)
    
    def _performance_weighted(self, signals: Dict) -> tuple[str, float]:
        """Weight by historical performance"""
        votes = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        
        for strategy_name, data in signals.items():
            signal = data['signal']
            accuracy = data.get('accuracy', 0.5)
            
            # Weight by accuracy
            weight = max(accuracy, 0.1)  # Minimum weight 0.1
            votes[signal] += weight
        
        max_vote = max(votes.values())
        if max_vote == 0:
            return 'HOLD', 0.0
        
        winner = max(votes, key=votes.get)
        confidence = max_vote / sum(votes.values())
        
        return winner, confidence
    
    def update_ensemble_performance(self, was_correct: bool):
        """Update ensemble performance"""
        if was_correct:
            self.ensemble_correct += 1
        
        if self.ensemble_signals > 0:
            self.ensemble_accuracy = self.ensemble_correct / self.ensemble_signals
    
    def get_strategy_rankings(self) -> List[Dict]:
        """Get strategies ranked by performance"""
        rankings = []
        
        for strategy in self.strategies:
            rankings.append({
                'name': strategy.name,
                'accuracy': strategy.accuracy,
                'signals': strategy.signals_generated,
                'weight': strategy.weight,
                'enabled': strategy.enabled
            })
        
        # Sort by accuracy
        rankings.sort(key=lambda x: x['accuracy'], reverse=True)
        
        return rankings
    
    def auto_adjust_weights(self, method: str = 'accuracy'):
        """Automatically adjust strategy weights based on performance"""
        if method == 'accuracy':
            # Adjust weights based on accuracy
            for strategy in self.strategies:
                if strategy.signals_generated >= 10:
                    # Scale weight by accuracy
                    strategy.weight = max(0.1, strategy.accuracy)
                    self.logger.info(f"Adjusted {strategy.name} weight to {strategy.weight:.2f}")
        
        elif method == 'recent':
            # Adjust based on recent performance
            for strategy in self.strategies:
                if len(strategy.recent_performance) >= 10:
                    recent_accuracy = np.mean(strategy.recent_performance)
                    strategy.weight = max(0.1, recent_accuracy)
                    self.logger.info(f"Adjusted {strategy.name} weight to {strategy.weight:.2f}")
    
    def get_status(self) -> Dict:
        """Get ensemble status"""
        return {
            'num_strategies': len(self.strategies),
            'enabled_strategies': sum(1 for s in self.strategies if s.enabled),
            'combination_method': self.combination_method,
            'ensemble_signals': self.ensemble_signals,
            'ensemble_accuracy': self.ensemble_accuracy,
            'strategies': self.get_strategy_rankings()
        }
    
    def print_status(self):
        """Print ensemble status"""
        status = self.get_status()
        
        print("\n" + "="*70)
        print("ENSEMBLE ORCHESTRATOR STATUS")
        print("="*70)
        
        print(f"\nStrategies: {status['enabled_strategies']}/{status['num_strategies']} enabled")
        print(f"Method: {status['combination_method']}")
        print(f"Ensemble Accuracy: {status['ensemble_accuracy']*100:.1f}% ({status['ensemble_signals']} signals)")
        
        print("\nStrategy Rankings:")
        for i, strat in enumerate(status['strategies'], 1):
            enabled = "✅" if strat['enabled'] else "❌"
            print(f"  {i}. {enabled} {strat['name']:<20} "
                  f"Accuracy: {strat['accuracy']*100:>5.1f}% "
                  f"Weight: {strat['weight']:.2f} "
                  f"Signals: {strat['signals']}")
        
        print("="*70)
