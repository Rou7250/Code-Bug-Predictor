from sqlalchemy import create_engine, Column, Integer, Float, String, Text, DateTime
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from datetime import datetime, timezone
import json

import os
db_path = os.getenv("DB_PATH", "./bug_predictor.db")
DB_URL = f"sqlite:///{db_path}"
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class AnalysisRecord(Base):
    __tablename__ = "analyses"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    code          = Column(Text, nullable=False)
    syntax_error  = Column(String(500), default="")
    bug_probability = Column(Float, default=0.0)
    confidence    = Column(String(20), default="Low")
    issues        = Column(Text, default="[]")   # JSON list
    line_bugs     = Column(Text, default="[]")   # JSON list
    fixed_code    = Column(Text, default="")
    explanation   = Column(Text, default="")
    created_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_db():
    Base.metadata.create_all(engine)


def save_analysis(code: str, result: dict) -> int:
    with Session() as s:
        rec = AnalysisRecord(
            code=code,
            syntax_error=result.get("syntax_error", ""),
            bug_probability=result.get("bug_probability", 0.0),
            confidence=result.get("confidence", "Low"),
            issues=json.dumps(result.get("issues", [])),
            line_bugs=json.dumps([lb.model_dump() if hasattr(lb, "model_dump") else lb
                                   for lb in result.get("line_bugs", [])]),
            fixed_code=result.get("fixed_code", code),
            explanation=result.get("explanation", ""),
        )
        s.add(rec); s.commit(); s.refresh(rec)
        return rec.id


def get_history(limit: int = 20) -> list[dict]:
    with Session() as s:
        rows = s.query(AnalysisRecord).order_by(AnalysisRecord.id.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "bug_probability": r.bug_probability,
                "confidence": r.confidence,
                "issues": json.loads(r.issues),
                "created_at": r.created_at.isoformat() if r.created_at else "",
            }
            for r in rows
        ]


def clear_history() -> int:
    with Session() as s:
        deleted = s.query(AnalysisRecord).delete()
        s.commit()
        return deleted
