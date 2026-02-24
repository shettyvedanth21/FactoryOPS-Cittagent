import asyncio
import logging
from datetime import datetime, timedelta
from uuid import uuid4

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.config import settings
from src.database import AsyncSessionLocal
from src.repositories.report_repository import ReportRepository
from src.repositories.scheduled_repository import ScheduledRepository
from src.storage.minio_client import minio_client
from src.tasks.report_task import run_consumption_report
from src.tasks.notification_stub import notify_report_ready

logger = logging.getLogger(__name__)

scheduler: AsyncIOScheduler | None = None

FREQUENCY_OFFSETS = {
    "daily": timedelta(days=1),
    "weekly": timedelta(days=7),
    "monthly": timedelta(days=30),
}

RETRY_INTERVAL = timedelta(minutes=30)
MAX_RETRIES = 3


async def check_due_schedules() -> None:
    logger.info("Checking for due schedules...")
    
    async with AsyncSessionLocal() as db:
        scheduled_repo = ScheduledRepository(db)
        report_repo = ReportRepository(db)
        
        due_schedules = await scheduled_repo.get_due_schedules()
        
        if not due_schedules:
            logger.info("No due schedules found")
            return
        
        logger.info(f"Found {len(due_schedules)} due schedules")
        
        for schedule in due_schedules:
            await process_schedule(schedule, scheduled_repo, report_repo)


async def process_schedule(
    schedule,
    scheduled_repo: ScheduledRepository,
    report_repo: ReportRepository
) -> None:
    schedule_id = schedule.schedule_id
    tenant_id = schedule.tenant_id
    frequency = schedule.frequency.value if hasattr(schedule.frequency, 'value') else str(schedule.frequency)
    report_type = schedule.report_type.value if hasattr(schedule.report_type, 'value') else str(schedule.report_type)
    params_template = schedule.params_template or {}
    
    logger.info(f"Processing schedule {schedule_id}, type={report_type}, freq={frequency}")
    
    await scheduled_repo.update_schedule(
        schedule_id,
        last_run_at=datetime.utcnow(),
        retry_count=schedule.retry_count + 1
    )
    
    try:
        params = build_params_from_template(params_template, frequency, tenant_id)
        
        report_id = str(uuid4())
        
        await report_repo.create_report(
            report_id=report_id,
            tenant_id=tenant_id,
            report_type=report_type,
            params=params
        )
        
        logger.info(f"Created report {report_id} for schedule {schedule_id}")
        
        if report_type == "consumption":
            await run_consumption_report(report_id, params)
        else:
            logger.warning(f"Comparison reports not yet implemented in scheduler, skipping {schedule_id}")
            await scheduled_repo.update_schedule(
                schedule_id,
                last_status="skipped",
                next_run_at=datetime.utcnow() + FREQUENCY_OFFSETS.get(frequency, timedelta(days=1)),
                retry_count=0
            )
            return
        
        await wait_for_report_completion(report_id)
        
        async with AsyncSessionLocal() as db:
            repo = ReportRepository(db)
            report = await repo.get_report(report_id, tenant_id)
        
        if report and report.status == "completed" and report.s3_key:
            presigned_url = minio_client.get_presigned_url(report.s3_key)
            
            logger.info(
                f"SCHEDULED_REPORT_READY: schedule_id={schedule_id}, "
                f"report_id={report_id}, url={presigned_url}"
            )
            
            await notify_report_ready(
                tenant_id=tenant_id,
                schedule_id=schedule_id,
                report_id=report_id,
                download_url=presigned_url,
                frequency=frequency
            )
            
            next_run = datetime.utcnow() + FREQUENCY_OFFSETS.get(frequency, timedelta(days=1))
            
            await scheduled_repo.update_schedule(
                schedule_id,
                last_status="completed",
                last_result_url=presigned_url,
                next_run_at=next_run,
                retry_count=0
            )
        else:
            raise Exception("Report did not complete successfully")
            
    except Exception as e:
        logger.error(f"Schedule {schedule_id} failed: {str(e)}")
        
        current_schedule = await scheduled_repo.get_schedule(schedule_id)
        new_retry_count = (current_schedule.retry_count or 0) + 1
        
        if new_retry_count >= MAX_RETRIES:
            logger.warning(f"SCHEDULED_REPORT_DISABLED: schedule_id={schedule_id} after 3 failures")
            
            await scheduled_repo.update_schedule(
                schedule_id,
                last_status="failed",
                is_active=False
            )
        else:
            next_retry = datetime.utcnow() + RETRY_INTERVAL
            
            await scheduled_repo.update_schedule(
                schedule_id,
                last_status="failed",
                retry_count=new_retry_count,
                next_run_at=next_retry
            )


def build_params_from_template(params_template: dict, frequency: str, tenant_id: str) -> dict:
    today = datetime.utcnow().date()
    
    if frequency == "daily":
        start_date = today - timedelta(days=1)
        end_date = today - timedelta(days=1)
    elif frequency == "weekly":
        start_date = today - timedelta(days=7)
        end_date = today - timedelta(days=1)
    else:
        start_date = today - timedelta(days=30)
        end_date = today - timedelta(days=1)
    
    params = {
        "tenant_id": tenant_id,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }
    
    if "device_ids" in params_template:
        params["device_ids"] = params_template["device_ids"]
    
    if "group_by" in params_template:
        params["group_by"] = params_template["group_by"]
    
    return params


async def wait_for_report_completion(report_id: str, max_wait: int = 300) -> None:
    for _ in range(max_wait):
        await asyncio.sleep(2)
        
        async with AsyncSessionLocal() as db:
            repo = ReportRepository(db)
            report = await repo.get_report(report_id, None)
            
            if report and report.status in ["completed", "failed"]:
                return
    
    raise Exception(f"Report {report_id} did not complete within timeout")


def start_scheduler() -> AsyncIOScheduler:
    global scheduler
    
    if scheduler is not None:
        return scheduler
    
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_due_schedules,
        trigger=IntervalTrigger(minutes=5),
        id="check_due_schedules",
        name="Check due scheduled reports",
        replace_existing=True
    )
    
    logger.info("APScheduler initialized with check_due_schedules job (every 5 minutes)")
    
    return scheduler


def stop_scheduler() -> None:
    global scheduler
    
    if scheduler:
        scheduler.shutdown()
        scheduler = None
        logger.info("APScheduler stopped")
