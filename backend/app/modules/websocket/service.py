"""WebSocket broadcast service for sending messages to channels."""

from app.modules.websocket.constants.socket_message_types import (
    SCRAP_JOB_COMPLETED,
    SCRAP_JOB_ERROR,
    SCRAP_JOB_IN_PROGRESS,
    SCRAP_JOB_PENDING,
    SCRAP_JOB_STOPPED,
    SCRAP_JOB_TERMINATED,
)
from app.modules.websocket.manager import connection_manager

SCRAP_JOB_CHANNEL_PREFIX = "/ws/scrap_job/"


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
