from pydantic import BaseModel, field_validator

SUPPORTED_LANGUAGES = {
    "python",
    "java",
    "c",
    "c++",
    "javascript",
}


class CodeRequest(BaseModel):
    code: str
    language: str = "python"

    @field_validator("code")
    @classmethod
    def validate_code(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Code cannot be empty")
        if len(v) > 50_000:
            raise ValueError("Code too large (max 50KB)")
        return v

    @field_validator("language")
    @classmethod
    def validate_language(cls, v):
        value = (v or "python").strip().lower()
        if value not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {value}")
        return value


class LineBug(BaseModel):
    line: int
    code: str
    issue: str


class AnalysisResponse(BaseModel):
    syntax_error: str
    bug_probability: float
    confidence: str           # Low / Medium / High
    issues: list[str]
    line_bugs: list[LineBug]
    fixed_code: str
    explanation: str
    features: dict


class HistoryItem(BaseModel):
    id: int
    bug_probability: float
    confidence: str
    issues: list[str]
    created_at: str


class MetricsResponse(BaseModel):
    trained: bool = False
    accuracy: float
    f1: float
    precision: float
    recall: float
    training_samples: int
    model_version: str
