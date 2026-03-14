"""WebSocket broadcast service for sending messages to channels."""

from app.modules.websocket.constants.socket_message_types import (
    SCRAP_CLIENT_COMPLETED,
    SCRAP_CLIENT_ERROR,
    SCRAP_CLIENT_IN_PROGRESS,
    SCRAP_CLIENT_LOG,
    SCRAP_CLIENT_PENDING,
    SCRAP_CLIENT_STOPPED,
    SCRAP_CLIENT_TERMINATED,
    SCRAP_JOB_COMPLETED,
    SCRAP_JOB_ERROR,
    SCRAP_JOB_IN_PROGRESS,
    SCRAP_JOB_LOG,
    SCRAP_JOB_PENDING,
    SCRAP_JOB_STOPPED,
    SCRAP_JOB_TERMINATED,
)
from app.modules.websocket.manager import connection_manager

SCRAP_JOB_CHANNEL_PREFIX = "/ws/scrap_job/"
SCRAP_CLIENT_CHANNEL_PREFIX = "/ws/scrap_client/"


def _scrap_job_log_data(log: dict) -> dict:
    """Build data payload for scrap job log socket messages."""
    created_at = log.get("created_at")
    if hasattr(created_at, "isoformat"):
        created_at = created_at.isoformat()
    return {
        "id": log.get("id"),
        "scrap_job_id": log.get("scrap_job_id"),
        "action": log.get("action"),
        "progress": log.get("progress"),
        "status": log.get("status"),
        "details": log.get("details"),
        "meta_data": log.get("meta_data", {}),
        "created_at": created_at,
    }


async def broadcast_scrap_job_log(log: dict) -> None:
    """
    Broadcast scrap job log update to all users subscribed to scrap job channel.
    """
    data = _scrap_job_log_data(log)
    await connection_manager.broadcast_to_channel_prefix(
        SCRAP_JOB_CHANNEL_PREFIX,
        SCRAP_JOB_LOG,
        data,
    )


def _scrap_job_data(scrap_job: dict) -> dict:
    """Build data payload for scrap job socket messages."""
    created_at = scrap_job.get("created_at")
    updated_at = scrap_job.get("updated_at")
    if hasattr(created_at, "isoformat"):
        created_at = created_at.isoformat()
    if hasattr(updated_at, "isoformat"):
        updated_at = updated_at.isoformat()
    return {
        "id": scrap_job.get("id"),
        "name": scrap_job.get("name"),
        "job_site_id": scrap_job.get("job_site_id"),
        "status": scrap_job.get("status"),
        "created_at": created_at,
        "updated_at": updated_at,
    }


async def broadcast_scrap_job_status(
    scrap_job: dict,
    status: str,
) -> None:
    """
    Broadcast scrap job status update to all users subscribed to scrap job channel.
    """
    status_to_type = {
        "pending": SCRAP_JOB_PENDING,
        "in_progress": SCRAP_JOB_IN_PROGRESS,
        "completed": SCRAP_JOB_COMPLETED,
        "error": SCRAP_JOB_ERROR,
        "terminated": SCRAP_JOB_TERMINATED,
        "stopped": SCRAP_JOB_STOPPED,
    }
    message_type = status_to_type.get(status)
    if message_type is None:
        return
    data = _scrap_job_data(scrap_job)
    await connection_manager.broadcast_to_channel_prefix(
        SCRAP_JOB_CHANNEL_PREFIX,
        message_type,
        data,
    )


def _scrap_client_log_data(log: dict) -> dict:
    """Build data payload for scrap client log socket messages."""
    created_at = log.get("created_at")
    if hasattr(created_at, "isoformat"):
        created_at = created_at.isoformat()
    return {
        "id": log.get("id"),
        "scrap_client_job_id": log.get("scrap_client_job_id"),
        "action": log.get("action"),
        "progress": log.get("progress"),
        "status": log.get("status"),
        "details": log.get("details"),
        "meta_data": log.get("meta_data", {}),
        "created_at": created_at,
    }


async def broadcast_scrap_client_log(log: dict) -> None:
    """Broadcast scrap client log update to all users subscribed to scrap client channel."""
    data = _scrap_client_log_data(log)
    await connection_manager.broadcast_to_channel_prefix(
        SCRAP_CLIENT_CHANNEL_PREFIX,
        SCRAP_CLIENT_LOG,
        data,
    )


def _scrap_client_data(scrap_client_job: dict) -> dict:
    """Build data payload for scrap client socket messages."""
    created_at = scrap_client_job.get("created_at")
    updated_at = scrap_client_job.get("updated_at")
    if hasattr(created_at, "isoformat"):
        created_at = created_at.isoformat()
    if hasattr(updated_at, "isoformat"):
        updated_at = updated_at.isoformat()
    return {
        "id": scrap_client_job.get("id"),
        "name": scrap_client_job.get("name"),
        "status": scrap_client_job.get("status"),
        "meta_data": scrap_client_job.get("meta_data") or {},
        "created_at": created_at,
        "updated_at": updated_at,
    }


async def broadcast_scrap_client_status(
    scrap_client_job: dict,
    status: str,
) -> None:
    """Broadcast scrap client status update to all users subscribed to scrap client channel."""
    status_to_type = {
        "pending": SCRAP_CLIENT_PENDING,
        "in_progress": SCRAP_CLIENT_IN_PROGRESS,
        "completed": SCRAP_CLIENT_COMPLETED,
        "error": SCRAP_CLIENT_ERROR,
        "terminated": SCRAP_CLIENT_TERMINATED,
        "stopped": SCRAP_CLIENT_STOPPED,
    }
    message_type = status_to_type.get(status)
    if message_type is None:
        return
    data = _scrap_client_data(scrap_client_job)
    await connection_manager.broadcast_to_channel_prefix(
        SCRAP_CLIENT_CHANNEL_PREFIX,
        message_type,
        data,
    )
