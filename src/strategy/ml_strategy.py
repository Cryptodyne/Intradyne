import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
import logging

class MLStrategy:
    """
    Machine Learning-based trading strategy.
    Uses technical indicators as features to predict price movements.
    """
    
    def __init__(self, model_type: str = 'random_forest'):
        """
        Initialize ML strategy.
        
        Args:
            model_type: 'random_forest' or 'xgboost'
        """
        self.model_type = model_type
        self.model = None
        self.feature_names = []
        self.logger = logging.getLogger("MLStrategy")
        
        # Try to import ML libraries
        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import accuracy_score, classification_report
            self.sklearn_available = True
        except ImportError:
            self.logger.warning("scikit-learn not available. Install with: pip install scikit-learn")
            self.sklearn_available = False
    
    def prepare_features(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare features from OHLCV data.
        
        Args:
            data: DataFrame with OHLCV columns
            
        Returns:
            Tuple of (features, labels)
        """
        df = data.copy()
        
        # Calculate technical indicators as features
        df['sma_9'] = df['close'].rolling(window=9).mean()
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        
        # EMA
        df['ema_12'] = df['close'].ewm(span=12).mean()
        df['ema_26'] = df['close'].ewm(span=26).mean()
        
        # MACD
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (2 * bb_std)
        df['bb_lower'] = df['bb_middle'] - (2 * bb_std)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        # Volume indicators
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # Price momentum
        df['momentum_1'] = df['close'].pct_change(1)
        df['momentum_5'] = df['close'].pct_change(5)
        df['momentum_10'] = df['close'].pct_change(10)
        
        # Volatility
        df['volatility'] = df['close'].rolling(window=20).std() / df['close'].rolling(window=20).mean()
        
        # Create labels (1 = price up, 0 = price down)
        df['future_return'] = df['close'].shift(-1) / df['close'] - 1
        df['label'] = (df['future_return'] > 0).astype(int)
        
        # Select features
        self.feature_names = [
            'sma_9', 'sma_20', 'sma_50',
            'ema_12', 'ema_26',
            'macd', 'macd_signal',
            'rsi',
            'bb_width',
            'volume_ratio',
            'momentum_1', 'momentum_5', 'momentum_10',
            'volatility'
        ]
        
        # Drop NaN values
        df = df.dropna()
        
        X = df[self.feature_names].values
        y = df['label'].values
        
        return X, y
    
    def train_model(self, X: np.ndarray, y: np.ndarray,
                   test_size: float = 0.2) -> Dict[str, Any]:
        """
        Train ML model.
        
        Args:
            X: Feature matrix
            y: Labels
            test_size: Test set size
            
        Returns:
            Training results
        """
        if not self.sklearn_available:
            return {'error': 'scikit-learn not available'}
        
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score, classification_report
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, shuffle=False  # Don't shuffle time series
        )
        
        self.logger.info(f"Training {self.model_type} model...")
        self.logger.info(f"Train size: {len(X_train)}, Test size: {len(X_test)}")
        
        # Train model
        if self.model_type == 'random_forest':
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
        else:
            # Try XGBoost
            try:
                import xgboost as xgb
                self.model = xgb.XGBClassifier(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42
                )
            except ImportError:
                self.logger.warning("XGBoost not available, using Random Forest")
                self.model = RandomForestClassifier(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42,
                    n_jobs=-1
                )
        
        # Fit model
        self.model.fit(X_train, y_train)
        
        # Evaluate
        y_pred_train = self.model.predict(X_train)
        y_pred_test = self.model.predict(X_test)
        
        train_accuracy = accuracy_score(y_train, y_pred_train)
        test_accuracy = accuracy_score(y_test, y_pred_test)
        
        self.logger.info(f"Train accuracy: {train_accuracy:.4f}")
        self.logger.info(f"Test accuracy: {test_accuracy:.4f}")
        
        # Feature importance
        if hasattr(self.model, 'feature_importances_'):
            feature_importance = dict(zip(
                self.feature_names,
                self.model.feature_importances_
            ))
            
            # Sort by importance
            sorted_features = sorted(
                feature_importance.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            self.logger.info("Top 5 features:")
            for feat, imp in sorted_features[:5]:
                self.logger.info(f"  {feat}: {imp:.4f}")
        
        return {
            'train_accuracy': train_accuracy,
            'test_accuracy': test_accuracy,
            'train_size': len(X_train),
            'test_size': len(X_test),
            'feature_importance': feature_importance if hasattr(self.model, 'feature_importances_') else None
        }
    
    def predict_signal(self, data: pd.DataFrame, index: int) -> str:
        """
        Predict trading signal for current candle.
        
        Args:
            data: OHLCV DataFrame
            index: Current candle index
            
        Returns:
            'BUY', 'SELL', or 'HOLD'
        """
        if self.model is None:
            return 'HOLD'
        
        # Need enough data for features
        if index < 50:
            return 'HOLD'
        
        # Prepare features for current candle
        current_data = data.iloc[:index+1]
        
        try:
            X, _ = self.prepare_features(current_data)
            
            if len(X) == 0:
                return 'HOLD'
            
            # Get last row (current candle)
            current_features = X[-1:, :]
            
            # Predict
            prediction = self.model.predict(current_features)[0]
            probability = self.model.predict_proba(current_features)[0]
            
            # Convert to signal
            if prediction == 1 and probability[1] > 0.6:  # High confidence up
                return 'BUY'
            elif prediction == 0 and probability[0] > 0.6:  # High confidence down
                return 'SELL'
            else:
                return 'HOLD'
        
        except Exception as e:
            self.logger.warning(f"Prediction failed: {e}")
            return 'HOLD'
    
    def evaluate_model(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, Any]:
        """
        Evaluate model performance.
        
        Args:
            X_test: Test features
            y_test: Test labels
            
        Returns:
            Evaluation metrics
        """
        if self.model is None or not self.sklearn_available:
            return {'error': 'Model not trained'}
        
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
        
        y_pred = self.model.predict(X_test)
        
        return {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, zero_division=0),
            'recall': recall_score(y_test, y_pred, zero_division=0),
            'f1_score': f1_score(y_test, y_pred, zero_division=0)
        }
    
    def save_model(self, filepath: str):
        """Save trained model to file."""
        if self.model is None:
            self.logger.warning("No model to save")
            return
        
        try:
            import joblib
            joblib.dump({
                'model': self.model,
                'feature_names': self.feature_names,
                'model_type': self.model_type
            }, filepath)
            self.logger.info(f"Model saved to {filepath}")
        except ImportError:
            self.logger.warning("joblib not available. Install with: pip install joblib")
    
    def load_model(self, filepath: str):
        """Load trained model from file."""
        try:
            import joblib
            data = joblib.load(filepath)
            self.model = data['model']
            self.feature_names = data['feature_names']
            self.model_type = data['model_type']
            self.logger.info(f"Model loaded from {filepath}")
        except ImportError:
            self.logger.warning("joblib not available. Install with: pip install joblib")
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")


# Helper function to create ML-based strategy function
def create_ml_strategy(ml_model: MLStrategy):
    """
    Create a strategy function that uses ML predictions.
    
    Args:
        ml_model: Trained MLStrategy instance
        
    Returns:
        Strategy function compatible with backtester
    """
    def ml_strategy_func(data: pd.DataFrame, index: int) -> str:
        return ml_model.predict_signal(data, index)
    
    return ml_strategy_func
