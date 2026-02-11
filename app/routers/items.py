from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    BulkRemoveBody,
    ItemDetailResponse,
    ItemPriceUpdate,
    MessageResponse,
)
from app.services import item_service

router = APIRouter()


def _slot_404():
    raise HTTPException(status_code=404, detail="Slot not found")


def _item_404():
    raise HTTPException(status_code=404, detail="Item not found")


@router.get("/items/{item_id}", response_model=ItemDetailResponse)
def get_item(item_id: str, db: Session = Depends(get_db)):
    item = item_service.get_item_by_id(db, item_id)
    if not item:
        _item_404()
    return ItemDetailResponse(
        id=item.id,
        name=item.name,
        price=item.price,
        quantity=item.quantity,
        slot_id=item.slot_id,
    )


@router.patch("/items/{item_id}/price", response_model=MessageResponse)
def update_item_price(
    item_id: str, data: ItemPriceUpdate, db: Session = Depends(get_db)
):
    try:
        item_service.update_item_price(db, item_id, data.price)
        return MessageResponse(message="Price updated successfully")
    except ValueError as e:
        if str(e) == "item_not_found":
            _item_404()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update price"
        )



@router.delete("/slots/{slot_id}/items/{item_id}", response_model=MessageResponse)
def remove_item_from_slot(
    slot_id: str,
    item_id: str,
    quantity: int | None = Query(None, gt=0),
    db: Session = Depends(get_db),
):
    try:
        item_service.remove_item_quantity(db, slot_id, item_id, quantity)
        return MessageResponse(message="Item(s) removed successfully")
    except ValueError as e:
        if str(e) == "slot_not_found":
            _slot_404()
        if str(e) == "item_not_found":
            _item_404()
        if str(e) == "quantity_must_be_positive":
            raise HTTPException(status_code=404, detail="Quantity is negative or zero")
        if str(e) == "quantity_exceeds_available": 
            raise HTTPException(status_code=400, detail="Quantity is exceeds the capacity")
        raise


@router.delete("/slots/{slot_id}/items", response_model=MessageResponse)
def bulk_remove_items(
    slot_id: str,
    body: BulkRemoveBody | None = Body(None),
    db: Session = Depends(get_db),
):
    item_ids = body.item_ids if body else None
    try:
        item_service.bulk_remove_items(db, slot_id, item_ids)
        return MessageResponse(message="Slot cleared successfully")
    except ValueError as e:
        if str(e) == "slot_not_found":
            _slot_404()
        raise
