import os
import sqlite3

from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Annotated

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Response,
    status,
)

from pydantic import BaseModel, Field, ConfigDict


# --------------------------------------------------
# 1. DATABASE CONFIGURATION
# --------------------------------------------------

def database_path() -> Path:
    return Path(
        os.getenv("DATABASE_PATH", "data/receipts.db")
    )


def get_db():

    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row

    try:
        yield connection
    finally:
        connection.close()


def init_db():

    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as connection:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant TEXT NOT NULL,
                amount TEXT NOT NULL,
                currency TEXT NOT NULL,
                category TEXT NOT NULL,
                purchase_date TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        connection.commit()


# --------------------------------------------------
# 2. APPLICATION LIFECYCLE
# --------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):

    init_db()

    yield


# --------------------------------------------------
# 3. FASTAPI APPLICATION
# --------------------------------------------------

app = FastAPI(
    title="Receipt Expense API",
    description=(
        "API for managing receipt information "
        "and expense summaries."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# --------------------------------------------------
# 4. PYDANTIC DATA MODELS
# --------------------------------------------------

class ReceiptCreate(BaseModel):

    merchant: str = Field(
        min_length=1,
        max_length=150
    )

    amount: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2
    )

    currency: str = Field(
        min_length=3,
        max_length=3,
        pattern=r"^[A-Z]{3}$"
    )

    category: str = Field(
        min_length=1,
        max_length=100
    )

    purchase_date: date


class ReceiptUpdate(BaseModel):

    merchant: str | None = Field(
        default=None,
        min_length=1,
        max_length=150
    )

    amount: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2
    )

    currency: str | None = Field(
        default=None,
        min_length=3,
        max_length=3,
        pattern=r"^[A-Z]{3}$"
    )

    category: str | None = Field(
        default=None,
        min_length=1,
        max_length=100
    )

    purchase_date: date | None = None


class ReceiptResponse(BaseModel):

    id: int
    merchant: str
    amount: Decimal
    currency: str
    category: str
    purchase_date: date
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------
# 5. HEALTH ENDPOINT
# --------------------------------------------------

@app.get("/health", tags=["System"])
def health_check():

    return {
        "status": "healthy",
        "service": "receipt-api"
    }


# --------------------------------------------------
# 6. CREATE RECEIPT
# --------------------------------------------------

@app.post(
    "/receipts",
    response_model=ReceiptResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Receipts"]
)
def create_receipt(
    receipt: ReceiptCreate,
    db: Annotated[sqlite3.Connection, Depends(get_db)]
):

    created_at = datetime.now(
        timezone.utc
    ).isoformat()

    cursor = db.execute(
        """
        INSERT INTO receipts (
            merchant,
            amount,
            currency,
            category,
            purchase_date,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            receipt.merchant,
            str(receipt.amount),
            receipt.currency,
            receipt.category,
            receipt.purchase_date.isoformat(),
            created_at,
        )
    )

    db.commit()

    receipt_id = cursor.lastrowid

    row = db.execute(
        "SELECT * FROM receipts WHERE id = ?",
        (receipt_id,)
    ).fetchone()

    return dict(row)


# --------------------------------------------------
# 7. GET ALL RECEIPTS
# --------------------------------------------------

@app.get(
    "/receipts",
    response_model=list[ReceiptResponse],
    tags=["Receipts"]
)
def get_receipts(
    db: Annotated[sqlite3.Connection, Depends(get_db)],
    category: str | None = None,
    currency: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):

    query = "SELECT * FROM receipts WHERE 1=1"
    parameters = []

    if category:
        query += " AND category = ?"
        parameters.append(category)

    if currency:
        query += " AND currency = ?"
        parameters.append(currency)

    query += " ORDER BY id DESC LIMIT ? OFFSET ?"

    parameters.extend([limit, offset])

    rows = db.execute(
        query,
        parameters
    ).fetchall()

    return [dict(row) for row in rows]

# --------------------------------------------------
# 11. EXPENSE SUMMARY
# --------------------------------------------------

@app.get(
    "/receipts/summary",
    tags=["Analytics"]
)
def expense_summary(
    db: Annotated[sqlite3.Connection, Depends(get_db)]
):

    rows = db.execute("""
        SELECT
            currency,
            category,
            amount
        FROM receipts
    """).fetchall()

    totals = {}
    category_totals = {}
    total_receipts = len(rows)

    for row in rows:

        currency = row["currency"]
        category = row["category"]
        amount = Decimal(row["amount"])

        totals[currency] = (
            totals.get(currency, Decimal("0")) + amount
        )

        key = (currency, category)

        category_totals[key] = (
            category_totals.get(key, Decimal("0")) + amount
        )

    return {
        "total_receipts": total_receipts,

        "totals_by_currency": {
            currency: str(amount)
            for currency, amount in totals.items()
        },

        "totals_by_category": [
            {
                "currency": currency,
                "category": category,
                "total": str(amount)
            }
            for (currency, category), amount
            in category_totals.items()
        ]
    }

# --------------------------------------------------
# 8. GET ONE RECEIPT
# --------------------------------------------------

@app.get(
    "/receipts/{receipt_id}",
    response_model=ReceiptResponse,
    tags=["Receipts"]
)
def get_receipt(
    receipt_id: int,
    db: Annotated[sqlite3.Connection, Depends(get_db)]
):

    row = db.execute(
        "SELECT * FROM receipts WHERE id = ?",
        (receipt_id,)
    ).fetchone()

    if row is None:

        raise HTTPException(
            status_code=404,
            detail="Receipt not found"
        )

    return dict(row)


# --------------------------------------------------
# 9. UPDATE RECEIPT
# --------------------------------------------------

@app.patch(
    "/receipts/{receipt_id}",
    response_model=ReceiptResponse,
    tags=["Receipts"]
)
def update_receipt(
    receipt_id: int,
    updates: ReceiptUpdate,
    db: Annotated[sqlite3.Connection, Depends(get_db)]
):

    row = db.execute(
        "SELECT * FROM receipts WHERE id = ?",
        (receipt_id,)
    ).fetchone()

    if row is None:

        raise HTTPException(
            status_code=404,
            detail="Receipt not found"
        )

    changes = updates.model_dump(exclude_unset=True)

    if not changes:

        raise HTTPException(
            status_code=400,
            detail="No update fields provided"
        )

    if any(value is None for value in changes.values()):

        raise HTTPException(
            status_code=422,
            detail="Update fields cannot be null"
        )

    if "amount" in changes:
        changes["amount"] = str(changes["amount"])

    if "purchase_date" in changes:
        changes["purchase_date"] = (
            changes["purchase_date"].isoformat()
        )

    allowed_fields = {
        "merchant",
        "amount",
        "currency",
        "category",
        "purchase_date"
    }

    if not set(changes).issubset(allowed_fields):
        raise HTTPException(
            status_code=400,
            detail="Invalid update fields"
        )

    assignments = ", ".join(
        f"{field} = ?" for field in changes
    )

    values = list(changes.values())
    values.append(receipt_id)

    db.execute(
        f"""
        UPDATE receipts
        SET {assignments}
        WHERE id = ?
        """,
        values
    )

    db.commit()

    updated = db.execute(
        "SELECT * FROM receipts WHERE id = ?",
        (receipt_id,)
    ).fetchone()

    return dict(updated)


# --------------------------------------------------
# 10. DELETE RECEIPT
# --------------------------------------------------

@app.delete(
    "/receipts/{receipt_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Receipts"]
)
def delete_receipt(
    receipt_id: int,
    db: Annotated[sqlite3.Connection, Depends(get_db)]
):

    cursor = db.execute(
        "DELETE FROM receipts WHERE id = ?",
        (receipt_id,)
    )

    if cursor.rowcount == 0:

        raise HTTPException(
            status_code=404,
            detail="Receipt not found"
        )

    db.commit()

    return Response(status_code=204)


