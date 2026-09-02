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

    if not settings.supabase_url or not (settings.supabase_key or settings.supabase_service_role_key):
        return None

    try:
        from supabase import create_client, Client
        key = settings.supabase_service_role_key or settings.supabase_key
        _supabase_client = create_client(settings.supabase_url, key)
        return _supabase_client
    except ImportError:
        logger.debug("supabase-py library not installed, falling back to direct SQLAlchemy.")
        return None
    except Exception as e:
        logger.warning(f"Failed to initialize Supabase client: {e}")
        return None


async def broadcast_incident_event(incident_id: str, event_name: str, payload: Dict[str, Any]) -> None:
    """Broadcast incident updates via Supabase Realtime channel if available."""
    client = get_supabase_client()
    if not client:
        return

    try:
        # Broadcast on channel 'incidents'
        channel = client.channel(f"incident:{incident_id}")
        channel.send_broadcast(event_name, payload)
    except Exception as e:
        logger.debug(f"Supabase broadcast notice: {e}")
