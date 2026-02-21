"""Analytics repository for accessing ML results from MySQL."""

from datetime import datetime
from typing import List, Optional

import aiomysql

from src.config import settings
from src.utils.exceptions import DatabaseError, AnalyticsLoadError
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class AnalyticsRepository:
    """Repository for accessing analytics results from MySQL."""

    def __init__(self):
        self.pool: Optional[aiomysql.Pool] = None

    async def connect(self) -> None:
        """Create database connection pool."""
        try:
            self.pool = await aiomysql.create_pool(
                host=settings.mysql_host,
                port=settings.mysql_port,
                user=settings.mysql_user,
                password=settings.mysql_password,
                db=settings.mysql_database,
                minsize=5,
                maxsize=settings.mysql_pool_size,
                autocommit=True,
            )
            logger.info("Connected to analytics database")
        except Exception as e:
            logger.error("Failed to connect to database", error=str(e))
            raise DatabaseError(f"Failed to connect: {str(e)}", operation="connect")

    async def disconnect(self) -> None:
        """Close database connection pool."""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            logger.info("Disconnected from analytics database")

    async def get_analytics_results(
        self,
        device_id: str,
        analysis_type: str,
        start_time: datetime,
        end_time: datetime,
    ) -> List[dict]:
        """Fetch analytics results for a device and time range."""
        if not self.pool:
            raise DatabaseError("Not connected to database", operation="query")

        query = """
            SELECT
                id,
                job_id,
                device_id,
                analysis_type,
                model_name,
                date_range_start,
                date_range_end,
                results,
                accuracy_metrics,
                status,
                created_at,
                completed_at
            FROM analytics_jobs
            WHERE device_id = %s
              AND analysis_type = %s
              AND created_at >= %s
              AND created_at <= %s
              AND status = 'completed'
            ORDER BY created_at DESC
        """

        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(query, (device_id, analysis_type, start_time, end_time))
                    rows = await cursor.fetchall()

                results = [dict(row) for row in rows]

                logger.info(
                    "Fetched analytics results",
                    device_id=device_id,
                    analysis_type=analysis_type,
                    result_count=len(results),
                )

                return results

        except Exception as e:
            logger.error(
                "Failed to fetch analytics results",
                error=str(e),
                device_id=device_id,
                analysis_type=analysis_type,
            )
            raise AnalyticsLoadError(
                f"Failed to load analytics: {str(e)}",
                device_id=device_id,
                analysis_type=analysis_type,
            )

    async def get_all_analytics_for_devices(
        self,
        device_ids: List[str],
        start_time: datetime,
        end_time: datetime,
    ) -> dict:
        """Fetch all analytics results for multiple devices."""
        results = {
            "anomaly": [],
            "prediction": [],
            "forecast": [],
        }

        for device_id in device_ids:
            for analysis_type in ["anomaly", "prediction", "forecast"]:
                try:
                    device_results = await self.get_analytics_results(
                        device_id,
                        analysis_type,
                        start_time,
                        end_time,
                    )
                    results[analysis_type].extend(device_results)
                except AnalyticsLoadError as e:
                    logger.warning(
                        "Failed to load analytics for device",
                        device_id=device_id,
                        analysis_type=analysis_type,
                        error=str(e),
                    )
                    continue

        return results

    async def health_check(self) -> bool:
        """Check database connectivity."""
        if not self.pool:
            return False

        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT 1")
                    await cursor.fetchone()
            return True
        except Exception:
            return False
