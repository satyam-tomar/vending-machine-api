from contextlib import contextmanager

from fastapi import FastAPI

from app.db import Base, engine
from app.routers import items, purchase, slots

@contextmanager
def lifespan(app: FastAPI):
    import os
    if os.getenv("ENVIRONMENT") == "development":
        Base.metadata.create_all(bind=engine)
    yield
    

app = FastAPI(title="Vending Machine API", lifespan=lifespan)

app.include_router(slots.router)
app.include_router(items.router)
app.include_router(purchase.router)


@app.get("/health")
def health():
    try:
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
