import json
from sqlalchemy.orm import Session
from models import AuditLog, Column, Board, User, Card


def log_action(
        db: Session,
        user_id: int,
        action: str,
        entity_type: str,
        entity_id: int,
        board_id: int = None,
        old_values: dict = None,
        new_values: dict = None
):
    """
    Запись действия в audit_log с сохранением названий сущностей.
    """
    # Если есть старые или новые значения — обогащаем их названиями
    enriched_old = enrich_entity_names(db, old_values, entity_type) if old_values else None
    enriched_new = enrich_entity_names(db, new_values, entity_type) if new_values else None

    log_entry = AuditLog(
        user_id=user_id,
        board_id=board_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_values=json.dumps(enriched_old, ensure_ascii=False) if enriched_old else None,
        new_values=json.dumps(enriched_new, ensure_ascii=False) if enriched_new else None
    )
    db.add(log_entry)
    db.commit()


def enrich_entity_names(db: Session, values: dict, entity_type: str) -> dict:
    """
    Преобразует ID в названия для читаемых логов.
    """
    result = dict(values)

    # Если есть column_id — добавляем название колонки
    if 'column_id' in values and values['column_id']:
        column = db.query(Column).filter(Column.id == values['column_id']).first()
        if column:
            result['column_name'] = column.title

    # Если есть board_id — добавляем название доски
    if 'board_id' in values and values['board_id']:
        board = db.query(Board).filter(Board.id == values['board_id']).first()
        if board:
            result['board_name'] = board.title

    # Если это лог об участнике — добавляем название доски
    if entity_type == 'board_member':
        if 'board_id' in values and values['board_id']:
            board = db.query(Board).filter(Board.id == values['board_id']).first()
            if board:
                result['board_name'] = board.title
        if 'email' in values:
            result['email'] = values['email']

    # 👇 ДОБАВЛЯЕМ НАЗВАНИЕ КАРТОЧКИ
    if 'card_id' in values and values['card_id']:
        card = db.query(Card).filter(Card.id == values['card_id']).first()
        if card:
            result['card_name'] = card.title

    # 👇 Добавляем название карточки по assignee_id (если есть)
    if 'assignee_id' in values and values['assignee_id']:
        user = db.query(User).filter(User.id == values['assignee_id']).first()
        if user:
            result['assignee_name'] = user.username

    # 👇 Если это лог о создании/обновлении карточки — добавляем название самой карточки
    if entity_type == 'card':
        if 'title' in values and values['title']:
            # Название уже есть
            result['card_name'] = values['title']
        elif 'id' in values and values['id']:
            card = db.query(Card).filter(Card.id == values['id']).first()
            if card:
                result['card_name'] = card.title

    return result