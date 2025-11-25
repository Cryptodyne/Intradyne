from abc import ABC, abstractmethod

class BaseEngine(ABC):
    """
    Abstract base class for all 7 engines in the Hybrid Ensemble.
    """
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def analyze(self, data: dict) -> dict:
        """
        Must return:
        {
            "direction": "LONG" | "SHORT" | "NEUTRAL",
            "confidence": float (0.0 - 1.0),
            "risk_flags": List[str],
            "reason_code": str
        }
        """
        pass

class ComplianceEngine(BaseEngine):
    """
    Layer 1 & 6: Ultra-Strict Shariah Compliance (AAOIFI).
    """
    def __init__(self):
        super().__init__("ComplianceEngine")
        self.forbidden_assets = ["USDT", "USDC"] # Example placeholder

    def analyze(self, data: dict) -> dict:
        asset = data.get("symbol", "")
        # Basic screening logic
        if asset in self.forbidden_assets:
            return {
                "direction": "NEUTRAL",
                "confidence": 0.0,
                "risk_flags": ["HARAM_ASSET"],
                "reason_code": "COMPLIANCE_FAIL"
            }
        
        return {
            "direction": "NEUTRAL", # Compliance doesn't dictate direction, only permission
            "confidence": 1.0,
            "risk_flags": [],
            "reason_code": "COMPLIANCE_PASS"
        }
