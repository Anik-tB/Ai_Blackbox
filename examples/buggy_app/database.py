"""
Simulated database with connection pool and state for buggy demo application.
"""

import asyncio
import time
from typing import Dict, Optional


class ConnectionPoolExhaustedError(Exception):
    """Raised when connection pool has reached maximum concurrency limit."""
    pass


class DatabasePool:
    def __init__(self, max_connections: int = 3):
        self.max_connections = max_connections
        self.active_connections = 0
        self.lock = asyncio.Lock()

    async def acquire(self):
        async with self.lock:
            if self.active_connections >= self.max_connections:
                raise ConnectionPoolExhaustedError(
                    f"Database connection pool exhausted: {self.active_connections}/{self.max_connections} in use."
                )
            self.active_connections += 1

    async def release(self):
        async with self.lock:
            if self.active_connections > 0:
                self.active_connections -= 1


class User:
    def __init__(self, username: str, password: str, role: str = "user"):
        self.username = username
        self.password = password
        self.role = role


class Database:
    def __init__(self):
        self.pool = DatabasePool(max_connections=2)  # Low capacity to easily trigger Bug 2
        self.users: Dict[str, User] = {
            "alice": User("alice", "password123", "admin"),
            "bob": User("bob", "secret456", "user"),
        }
        self.accounts: Dict[str, float] = {
            "alice": 100.0,
            "bob": 50.0,
        }
        self.orders: Dict[str, Dict[str, str]] = {
            "ord_101": {"id": "ord_101", "status": "COMPLETED", "amount": 49.99},
            "ord_102": {"id": "ord_102", "status": "REFUNDED", "amount": 25.00},
        }

    def find_user(self, username: str) -> Optional[User]:
        """Returns User or None if not found."""
        return self.users.get(username, None)

    async def execute_heavy_query(self):
        """Simulates heavy report query occupying a pooled connection."""
        await self.pool.acquire()
        try:
            await asyncio.sleep(0.5)
        finally:
            await self.pool.release()


db = Database()
