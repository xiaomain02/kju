import json
from sqlalchemy.orm import Session
from models import AuditLog

def log_action(
        db: Session,
        user_id: int,
        action: str,
        entity_type: str,
        entity_id: int,
        old_values: dict = None,
        new_values: dict = None
):
    log_entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_values=json.dumps(old_values, ensure_ascii=False) if old_values else
        None,
        new_values=json.dumps(new_values, ensure_ascii=False) if new_values else None
    )

    db.add(log_entry)
    db.commit()