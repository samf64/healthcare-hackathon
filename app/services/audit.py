from sqlalchemy.orm import Session

from app.models import AuditLog


def log_audit_event(db: Session, user_id: int, action: str, details: str = "") -> None:
    db.add(AuditLog(user_id=user_id, action=action, details=details))

