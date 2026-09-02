# AI Black Box Debugger (AIBD / `aidbg`)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Database: Supabase](https://img.shields.io/badge/Database-Supabase%20%2F%20Postgres-3ECF8E.svg)](https://supabase.com)

> **Collect evidence → reconstruct execution → identify probable root cause → explain it clearly → suggest a safe fix.**

**AI Black Box Debugger (AIBD)** is an enterprise developer observability and AI-assisted root cause analysis platform. It answers not just **where** an application failed, but **why** it failed, providing verifiable evidence chains and safe regression patches.

---

## Key Capabilities

* **Fail-Open Observation Agent**: Zero-overhead exception interception (`sys.excepthook`, `threading`, `asyncio`, FastAPI ASGI). If the backend is unreachable or under heavy load, the host application continues running uninterrupted without performance degradation.
* **Automatic Secret Redaction**: Eliminates security risks by recursively scrubbing passwords, tokens, bearer authorizations, cookies, credit cards, and API keys before transmission or AI processing.
* **Incident Fingerprinting & Deduplication**: Groups 10,000 identical exceptions into 1 actionable incident with exact occurrences, first/last seen timestamps, and dynamic variable normalization.
* **Static AST & Control-Flow Analysis**: Inspects Python source code using native AST to detect NULL/None pointer access paths, missing guard checks, and unhandled resource leaks without relying blindly on an LLM.
* **Git History & Blame Correlation**: Automatically connects runtime errors with recent commits, line blames, author changes, and diffs to estimate change correlation confidence.
* **Causal Graph Reconstruction**: Synthesizes verified facts, telemetry anomalies, and execution traces into a Directed Acyclic Graph (DAG) with explicit confidence scores.
* **Hybrid Root Cause Engine with Offline Fallback**: Combines deterministic heuristic rules with multi-provider LLM intelligence (Gemini, OpenAI, Anthropic) and works 100% offline when no API key is set.
* **Automated Safe Patch & Test Synthesis**: Produces unified Git diffs and Pytest regression test suites without ever modifying production code directly.
* **Supabase Integration**: Native PostgreSQL schema, Realtime broadcasts, and transaction connection pooling, alongside a zero-dependency local SQLite fallback.

---

## Quickstart (Under 5 Minutes)

### 1. Installation
```bash
pip install aidbg
```
*(Or for local development: `pip install -e .`)*

### 2. Initialize Project
```bash
aidbg init --service "my-service"
```
This generates `.aidbg/config.yaml` with your service name, Supabase settings, and secret redaction rules.

### 3. Run Your Application with AIBD Observation
```bash
aidbg run uvicorn app:app --port 8000
```
Or for standard scripts:
```bash
aidbg run python main.py
```

### 4. Inspect Incidents via CLI
```bash
aidbg incidents
```
Output:
```text
ID       ERROR                    COUNT    SEVERITY    SERVICE
─────────────────────────────────────────────────────────────────────────────
A7F82C   DatabaseTimeout          1231     CRITICAL    billing-service
B81DA2   NullPointerException      231     HIGH        auth-service
```

### 5. Explain Root Cause
```bash
aidbg explain B81DA2
```
Output:
```text
ROOT CAUSE
─────────────────────────────────────────────────────────────────────────────
Attempted to access attribute '.password' on variable 'user', which evaluated
to None due to an unhandled missing record or failed lookup.

CONFIDENCE
94%

CAUSAL CHAIN
  HTTP POST /api/login
      ↓ (Function called at line 41)
  user is None
      ↓ (Missing guard check)
  Access .password on None
      ↓ (Unhandled exception)
  AttributeError Raised
      ↓ (Internal server error sent to client)
  HTTP 500 Response

EVIDENCE (VERIFIED FACTS)
  ✓ Uncaught AttributeError: 'NoneType' object has no attribute 'password'
  ✓ Occurred during POST /api/login
  ✓ AST Analysis: Variable 'user' assigned at line 41 is accessed as '.password' at line 42 without an explicit 'is not None' check.
  ✓ Recent commit da8537f: 'Refactor login endpoint and database user lookup' (Last modified the failing line directly)

RECOMMENDED FIX
─────────────────────────────────────────────────────────────────────────────
Add a guard clause checking if 'user' is None before accessing '.password'.
Return an appropriate HTTP 404/400 response or raise a descriptive exception.
```

### 6. View Safe Patch & Test Suite
```bash
aidbg fix B81DA2
```
To automatically create a Git branch for the fix:
```bash
aidbg fix B81DA2 --branch
```

---

## Supabase Configuration

To use Supabase as your database:
1. In your Supabase Dashboard, open the **SQL Editor** and run `aidbg/backend/migrations/supabase_schema.sql`.
2. Configure `.aidbg/config.yaml` or set environment variables:
```bash
export SUPABASE_URL="https://<your-project-id>.supabase.co"
export SUPABASE_KEY="<your-anon-or-service-key>"
export SUPABASE_DB_URL="postgresql+asyncpg://postgres:<password>@db.<project-id>.supabase.co:5432/postgres"
```
*(If omitted, AIBD seamlessly uses local SQLite in WAL mode with zero configuration needed).*

---

## Architecture Overview

```text
Host Application
      │  (Fail-open hooks: sys.excepthook, threading, asyncio, OTel)
      ▼
aidbg Agent (Redaction -> Bounded Queue -> Circuit Breaker)
      │
      ▼ (HTTP / JSON)
AIBD Ingestion Server (FastAPI)
      │
      ├──> Fingerprint & Deduplication (e.g. 10,000 errors -> 1 Incident)
      │
      ├──> Static AST Analyzer (Python AST: Null propagation & Call hierarchy)
      │
      ├──> Git Analyzer (Blame, recent commits, diffs)
      │
      ├──> Causal Graph Engine (Facts vs Hypotheses DAG)
      │
      ├──> AI Reasoning Engine (Gemini / OpenAI / Deterministic Fallback)
      │
      ├──> Storage (Supabase PostgreSQL / SQLite fallback)
      │
      └──> Consumers: CLI (`aidbg`) & Next.js Web Dashboard
```
