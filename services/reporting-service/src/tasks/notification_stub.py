import logging

logger = logging.getLogger(__name__)


async def notify_report_ready(
    tenant_id: str,
    schedule_id: str,
    report_id: str,
    download_url: str,
    frequency: str
) -> None:
    """
    Email notification placeholder.
    SMTP not yet configured.
    When SMTP is ready, implement actual email sending here.
    For now: log the notification intent only.
    """
    logger.info(
        f"NOTIFICATION_PENDING | tenant={tenant_id} | "
        f"schedule={schedule_id} | report={report_id} | "
        f"frequency={frequency} | url={download_url}"
    )
