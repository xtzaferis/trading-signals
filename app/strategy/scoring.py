from dataclasses import dataclass, field


@dataclass
class SignalResult:
    symbol: str
    score: int = 0
    action: str = "HOLD"
    confidence: float = 0.0
    reasons: list[str] = field(default_factory=list)