"""
Intentionally Buggy FastAPI Application for AI Black Box Debugger Demo.
Contains 5 realistic failure modes:
  1. NULL user causing AttributeError (missing None guard)
  2. Database connection pool exhaustion under concurrency
  3. Race condition on concurrent wallet balance deductions
  4. Illegal API state transition on refunding already refunded order
  5. Slow database query timeout
"""

import asyncio
import time
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

import aidbg
from aidbg.agent.instrumentation import AidbgFastAPIMiddleware
from examples.buggy_app.database import db, ConnectionPoolExhaustedError

# Initialize aidbg agent with local endpoint
aidbg.init(
    endpoint_url="http://127.0.0.1:8765/api/v1/incidents/ingest",
    service_name="payment-auth-service",
    environment="production"
)

app = FastAPI(title="Buggy Demo Application")
app.add_middleware(AidbgFastAPIMiddleware)


class LoginRequest(BaseModel):
    username: str
    password: str


class TransferRequest(BaseModel):
    from_user: str
    to_user: str
    amount: float


class IllegalStateTransitionError(Exception):
    """Raised when an order transition is invalid."""
    pass


class QueryTimeoutError(Exception):
    """Raised when an unindexed database query exceeds timeout."""
    pass


@app.get("/")
def root():
    return {
        "status": "online",
        "bugs": [
            "POST /api/login (Bug 1: NULL pointer)",
            "POST /api/reports/heavy (Bug 2: DB Pool Exhaustion)",
            "POST /api/wallet/transfer (Bug 3: Race condition)",
            "POST /api/orders/{id}/refund (Bug 4: Illegal State Transition)",
            "GET  /api/analytics/summary (Bug 5: Slow Query Timeout)"
        ]
    }


# ==============================================================================
# BUG 1: NULL user causing AttributeError (No None check)
# ==============================================================================
@app.post("/api/login")
def login(req: LoginRequest):
    aidbg.add_breadcrumb(f"Attempting login for username: {req.username}")
    
    # Culprit line: find_user returns None for unknown users
    user = db.find_user(req.username)

    # Missing: if user is None: raise HTTPException(404, "User not found")
    # This raises AttributeError: 'NoneType' object has no attribute 'password'
    if user.password == req.password:
        return {"token": f"jwt_token_for_{user.username}", "role": user.role}

    return {"error": "Invalid password"}


# ==============================================================================
# BUG 2: Connection Pool Exhaustion under concurrency
# ==============================================================================
@app.post("/api/reports/heavy")
async def generate_heavy_report():
    aidbg.add_breadcrumb("Acquiring connection from database pool for heavy reporting")
    # Tries to acquire from pool with limit=2; concurrent requests will trigger exhaustion
    await db.pool.acquire()
    try:
        await asyncio.sleep(0.4)
        return {"report": "generated successfully"}
    finally:
        await db.pool.release()


# ==============================================================================
# BUG 3: Race Condition on Wallet Transfer
# ==============================================================================
@app.post("/api/wallet/transfer")
async def wallet_transfer(req: TransferRequest):
    aidbg.add_breadcrumb(f"Transferring {req.amount} from {req.from_user} to {req.to_user}")

    # Read current balance
    current_balance = db.accounts.get(req.from_user, 0.0)
    if current_balance < req.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")

    # Race window: context switch without atomic lock
    await asyncio.sleep(0.05)

    # Deduction based on stale read
    db.accounts[req.from_user] = current_balance - req.amount
    db.accounts[req.to_user] = db.accounts.get(req.to_user, 0.0) + req.amount

    return {"status": "transferred", "new_balance": db.accounts[req.from_user]}


# ==============================================================================
# BUG 4: Illegal API State Transition
# ==============================================================================
@app.post("/api/orders/{order_id}/refund")
def refund_order(order_id: str):
    aidbg.add_breadcrumb(f"Processing refund for order: {order_id}")
    order = db.orders.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order["status"] == "REFUNDED":
        # Unhandled state transition error
        raise IllegalStateTransitionError(
            f"Cannot refund order {order_id}: order is already in REFUNDED state."
        )

    order["status"] = "REFUNDED"
    return {"status": "success", "order": order}


# ==============================================================================
# BUG 5: Slow Database Query Timeout
# ==============================================================================
@app.get("/api/analytics/summary")
async def analytics_summary():
    aidbg.add_breadcrumb("Running full unindexed table scan for analytics summary")
    start = time.time()
    await asyncio.sleep(1.0)
    duration = time.time() - start
    if duration >= 1.0:
        raise QueryTimeoutError(
            f"Query on 'transaction_events' exceeded deadline of 1000ms (took {duration*1000:.1f}ms). Missing composite index on (created_at, account_id)."
        )
    return {"summary": "computed"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
