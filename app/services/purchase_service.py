import time
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.models import Item

def purchase(db: Session, item_id: str, cash_inserted: int) -> dict:
    with db.begin():
        item = (
            db.query(Item)
            .filter(Item.id == item_id)
            .with_for_update()
            .first()
        )

        if not item:
            raise ValueError("item_not_found")

        time.sleep(0.05)  # demo: widens race window for concurrent purchase/restock

        if item.quantity <= 0:
            raise ValueError("out_of_stock")

        if cash_inserted < item.price:
            raise ValueError("insufficient_cash", item.price, cash_inserted)

        change = cash_inserted - item.price
        item.quantity -= 1
        item.slot.current_item_count -= 1

    db.refresh(item)

    return {
        "item": item.name,
        "price": item.price,
        "cash_inserted": cash_inserted,
        "change_returned": change,
        "remaining_quantity": item.quantity,
        "message": "Purchase successful",
    }

def change_breakdown(change: int) -> dict:
    denominations = sorted(settings.SUPPORTED_DENOMINATIONS, reverse=True)
    result: dict[str, int] = {}
    remaining = change
    for d in denominations:
        if remaining <= 0:
            break
        count = remaining // d
        if count > 0:
            result[str(d)] = count
            remaining -= count * d
    return {"change": change, "denominations": result}
