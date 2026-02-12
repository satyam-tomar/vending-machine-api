import time
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.models import Item, Slot
from app.schemas import ItemBulkEntry, ItemCreate


def add_item_to_slot(db: Session, slot_id: str, data: ItemCreate) -> Item:
    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if not slot:
        raise ValueError("slot_not_found")
    if slot.current_item_count + data.quantity > slot.capacity:
        raise ValueError("capacity_exceeded")

    item = Item(
        name=data.name,
        price=data.price,
        slot_id=slot_id,
        quantity=data.quantity,     
    )
    db.add(item)
    slot.current_item_count += data.quantity
    db.commit()
    db.refresh(item)
    return item

def bulk_add_items(db: Session, slot_id: str, entries: list[ItemBulkEntry]) -> int:
    try:
        with db.begin():
            slot = (
                db.query(Slot)
                .filter(Slot.id == slot_id)
                .with_for_update()
                .first()
            )
            if not slot:
                raise ValueError("slot_not_found")

            incoming_quantity = sum(e.quantity for e in entries if e.quantity > 0)

            if slot.current_item_count + incoming_quantity > slot.capacity:
                raise ValueError("capacity_exceeded")

            added_count = 0
            for e in entries:
                if e.quantity <= 0:
                    continue

                db.add(Item(
                    name=e.name,
                    price=e.price,
                    slot_id=slot_id,
                    quantity=e.quantity
                ))

                slot.current_item_count += e.quantity
                added_count += 1

        return added_count

    except SQLAlchemyError:
        raise


def list_items_by_slot(db: Session, slot_id: str) -> list[Item]:
    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if not slot:
        raise ValueError("slot_not_found")
    return list(slot.items)


def get_item_by_id(db: Session, item_id: str) -> Item | None:
    return db.query(Item).filter(Item.id == item_id).first()


def update_item_price(db: Session, item_id: str, price: int) -> None:
    item = get_item_by_id(db, item_id)
    if not item:
        raise ValueError("item_not_found")
    
    # SQLAlchemy/Postgres usually handles updated_at automatically,
    # prev_updated = item.updated_at
    item.price = price
    # item.updated_at = prev_updated
    db.commit()


def remove_item_quantity(
    db: Session, slot_id: str, item_id: str, quantity: int | None
) -> None:
    slot = (
        db.query(Slot)
        .filter(Slot.id == slot_id)
        .with_for_update()
        .first()
    )
    if not slot:
        raise ValueError("slot_not_found")

    item = (
        db.query(Item)
        .filter(Item.id == item_id, Item.slot_id == slot_id)
        .with_for_update()
        .first()
    )
    if not item:
        raise ValueError("item_not_found")
    if quantity is not None:
        to_remove = min(quantity, item.quantity)
        item.quantity -= to_remove
        slot.current_item_count -= to_remove
        if item.quantity <= 0:
            db.delete(item)
    else:
        slot.current_item_count -= item.quantity
        db.delete(item)
    db.commit()


def bulk_remove_items(
    db: Session, slot_id: str, item_ids: list[str] | None
) -> None:
    try:
        with db.begin():

            slot = (
                db.query(Slot)
                .filter(Slot.id == slot_id)
                .with_for_update()
                .first()
            )

            if not slot:
                raise ValueError("slot_not_found")

            if item_ids is not None:
                if not item_ids:
                    return 

                unique_ids = set(item_ids)

                items = (
                    db.query(Item)
                    .filter(
                        Item.slot_id == slot_id,
                        Item.id.in_(unique_ids),
                    )
                    .all()
                )

                if len(items) != len(unique_ids):
                    raise ValueError("one_or_more_items_not_found")

            else:
                items = list(slot.items)

            total_removed = sum(item.quantity for item in items)

            if total_removed > slot.current_item_count:
                raise ValueError("slot_count_inconsistent")

            for item in items:
                db.delete(item)

            slot.current_item_count -= total_removed

    except Exception:
        db.rollback()
        raise
