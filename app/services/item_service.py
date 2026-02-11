import time
from sqlalchemy.orm import Session

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
    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if not slot:
        raise ValueError("slot_not_found")

    incoming_quantity = sum(e.quantity for e in entries if e.quantity > 0)

    if slot.current_item_count + incoming_quantity > slot.capacity:
        raise ValueError("capacity_exceeded")

    added_count = 0
    for e in entries:
        if e.quantity <= 0:
            continue
        
        item = Item(
            name=e.name, 
            price=e.price, 
            slot_id=slot_id, 
            quantity=e.quantity
        )
        db.add(item)
        
        slot.current_item_count += e.quantity
        added_count += 1

    db.commit()
    return added_count


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
    item = db.query(Item).filter(Item.id == item_id, Item.slot_id == slot_id).first()
    if not item:
        slot_exists = db.query(Slot).filter(Slot.id == slot_id).first()
        if not slot_exists:
            raise ValueError("slot_not_found")
        raise ValueError("item_not_found")

    if quantity is None:
        reduction_amount = item.quantity
        db.delete(item)
    
    else:
        if quantity <= 0:
            raise ValueError("quantity_must_be_positive")
        elif quantity > item.quantity:
            raise ValueError("quantity_exceeds_available")
            
        reduction_amount = quantity
        if quantity == item.quantity:
            db.delete(item)
        else:
            item.quantity -= quantity
    item.slot.current_item_count -= reduction_amount
    db.commit()


def bulk_remove_items(
    db: Session, slot_id: str, item_ids: list[str] | None
) -> None:
    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if not slot:
        raise ValueError("slot_not_found")
    if item_ids is not None and len(item_ids) > 0:
        items = db.query(Item).filter(
            Item.slot_id == slot_id,
            Item.id.in_(item_ids),
        ).all()
        for item in items:
            slot.current_item_count -= item.quantity
            db.delete(item)
    else:
        for item in list(slot.items):
            slot.current_item_count -= item.quantity
            db.delete(item)
    db.commit()
