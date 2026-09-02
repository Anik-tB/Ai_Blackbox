# AIBD Buggy Demo Application (10-Minute Walkthrough)

This example demonstrates how **AI Black Box Debugger (AIBD)** detects, reconstructs, explains, and fixes application failures in real-time.

## 5 Realistic Bug Scenarios Included

1. **Bug 1: NULL User Exception (`POST /api/login`)**
   - Attempting login for a non-existent user returns `None`, resulting in `AttributeError: 'NoneType' object has no attribute 'password'`.
2. **Bug 2: Connection Pool Exhaustion (`POST /api/reports/heavy`)**
   - High concurrency rapidly exhausts the database connection pool, triggering timeouts.
3. **Bug 3: Concurrency Race Condition (`POST /api/wallet/transfer`)**
   - Unlocked balance transfer allows concurrent double-spending.
4. **Bug 4: Illegal API State Transition (`POST /api/orders/{id}/refund`)**
   - Attempting to refund an already refunded order raises an unhandled transition error.
5. **Bug 5: Slow Database Query Timeout (`GET /api/analytics/summary`)**
   - Unindexed full table scan exceeding the 1000ms deadline.

---

## 5-Minute Quickstart

### 1. Start the AIBD Backend Ingestion Server
In terminal 1:
```bash
python3 -m aidbg.backend.main
```
*(Runs on `http://127.0.0.1:8765` with Supabase or automatic local SQLite fallback)*

### 2. Run the Buggy Application with AIBD
In terminal 2:
```bash
cd examples/buggy_app
aidbg init --service "payment-auth-service"
aidbg run python3 -m uvicorn app:app --port 8000
```

### 3. Trigger Bug 1 (NULL User Lookup)
In terminal 3:
```bash
curl -X POST http://127.0.0.1:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username": "ghost_user", "password": "secret_password"}'
```
*Notice: Even though the endpoint fails with HTTP 500, the application never crashes, and sensitive passwords are automatically redacted.*

### 4. Inspect Incidents via CLI
```bash
aidbg incidents
```
Output:
```text
ID       ERROR                    COUNT    SEVERITY    SERVICE
─────────────────────────────────────────────────────────────────────────────
B81DA2   AttributeError           1        HIGH        payment-auth-ser
```

### 5. Generate Root Cause Analysis
```bash
aidbg explain B81DA2
```
Outputs the complete causal explanation, confidence percentage, execution chain, and verified evidence!

### 6. View the Proposed Safe Patch & Regression Test
```bash
aidbg fix B81DA2
```
Outputs a unified Git diff adding the missing `if user is None:` guard clause and a generated Pytest test suite!

To automatically create a Git branch for the fix:
```bash
aidbg fix B81DA2 --branch
```
