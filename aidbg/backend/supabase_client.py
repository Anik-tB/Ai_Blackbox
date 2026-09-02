"""
Supabase client helper for direct API calls, storage, and Realtime broadcasts.
Fails gracefully if Supabase credentials are not provided.
"""

from __future__ import annotations
import logging
from typing import Any, Dict, Optional
from aidbg.backend.config import settings

logger = logging.getLogger("aidbg.supabase")

_supabase_client = None


def get_supabase_client() -> Optional[Any]:
    """Get initialized Supabase client if credentials are configured."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    s_url, s_key = settings.get_supabase_api_credentials()
    if not s_url or not s_key:
        return None

    try:
        from supabase import create_client
        _supabase_client = create_client(s_url, s_key)
        return _supabase_client
    except Exception as e:
        logger.warning(f"Failed to initialize Supabase client: {e}")
        return None


async def broadcast_incident_event(incident_id: str, event_name: str, payload: Dict[str, Any]) -> None:
    """Broadcast incident updates via Supabase Realtime channel if available."""
    client = get_supabase_client()
    if not client:
        return

    try:
        channel = client.channel(f"incident:{incident_id}")
        channel.send_broadcast(event_name, payload)
    except Exception as e:
        logger.debug(f"Supabase broadcast notice: {e}")
