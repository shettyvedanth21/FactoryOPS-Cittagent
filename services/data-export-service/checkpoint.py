"""Checkpoint repository for tracking export progress in MySQL."""

from datetime import timezone
from typing import Optional

import aiomysql

from config import Settings
from logging_config import get_logger
from models import Checkpoint, ExportStatus

logger = get_logger(__name__)


class CheckpointRepository:
    """MySQL-backed checkpoint repository."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._pool: aiomysql.Pool | None = None

    async def initialize(self) -> None:
        """Initialize database connection pool and create tables."""
        try:
            self._pool = await aiomysql.create_pool(
                host=self.settings.checkpoint_db_host,
                port=self.settings.checkpoint_db_port,
                user=self.settings.checkpoint_db_user,
                password=self.settings.checkpoint_db_password,
                db=self.settings.checkpoint_db_name,
                minsize=2,
                maxsize=10,
                autocommit=True,
            )
            await self._create_table()
            logger.info("Checkpoint repository initialized")
        except Exception as e:
            logger.error(f"Failed to initialize checkpoint repository: {e}")
            raise

    async def close(self) -> None:
        """Close database connection pool."""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            logger.info("Checkpoint repository closed")

    async def _create_table(self) -> None:
        """Create checkpoint table if not exists."""
        table_name = self.settings.checkpoint_table

        create_table_query = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                device_id VARCHAR(50) NOT NULL,
                last_exported_at DATETIME(6) NOT NULL,
                last_sequence INT DEFAULT 0,
                status VARCHAR(50) NOT NULL,
                s3_key VARCHAR(500),
                record_count INT DEFAULT 0,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uq_device_exported_at (device_id, last_exported_at)
            )
        """

        index_queries = [
            f"CREATE INDEX idx_checkpoint_device_id ON {table_name}(device_id)",
            f"CREATE INDEX idx_checkpoint_status ON {table_name}(status)",
            f"CREATE INDEX idx_checkpoint_updated ON {table_name}(updated_at)",
        ]

        if not self._pool:
            raise RuntimeError("Checkpoint repository not initialized")

        async with self._pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(create_table_query)
                for query in index_queries:
                    try:
                        await cursor.execute(query)
                    except Exception:
                        # Index already exists.
                        pass

    async def get_last_checkpoint(self, device_id: str) -> Optional[Checkpoint]:
        """Get the most recent checkpoint for a device."""
        query = f"""
            SELECT id, device_id, last_exported_at, last_sequence, status,
                   s3_key, record_count, error_message, created_at, updated_at
            FROM {self.settings.checkpoint_table}
            WHERE device_id = %s
            ORDER BY last_exported_at DESC
            LIMIT 1
        """

        if not self._pool:
            raise RuntimeError("Checkpoint repository not initialized")

        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, (device_id,))
                row = await cursor.fetchone()

                if row:
                    return Checkpoint(
                        id=str(row["id"]),
                        device_id=row["device_id"],
                        last_exported_at=row["last_exported_at"].replace(tzinfo=timezone.utc),
                        last_sequence=row["last_sequence"],
                        status=ExportStatus(row["status"]),
                        s3_key=row["s3_key"],
                        record_count=row["record_count"],
                        error_message=row["error_message"],
                        created_at=row["created_at"].replace(tzinfo=timezone.utc),
                        updated_at=row["updated_at"].replace(tzinfo=timezone.utc),
                    )

                return None

    async def save_checkpoint(self, checkpoint: Checkpoint) -> Checkpoint:
        """Save a checkpoint to the database."""
        query = f"""
            INSERT INTO {self.settings.checkpoint_table}
                (device_id, last_exported_at, last_sequence, status, s3_key,
                 record_count, error_message)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                last_sequence = VALUES(last_sequence),
                status = VALUES(status),
                s3_key = VALUES(s3_key),
                record_count = VALUES(record_count),
                error_message = VALUES(error_message),
                updated_at = CURRENT_TIMESTAMP
        """

        lookup_query = f"""
            SELECT id, created_at, updated_at
            FROM {self.settings.checkpoint_table}
            WHERE device_id = %s AND last_exported_at = %s
            LIMIT 1
        """

        if not self._pool:
            raise RuntimeError("Checkpoint repository not initialized")

        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    query,
                    (
                        checkpoint.device_id,
                        checkpoint.last_exported_at.replace(tzinfo=None),
                        checkpoint.last_sequence,
                        checkpoint.status.value,
                        checkpoint.s3_key,
                        checkpoint.record_count,
                        checkpoint.error_message,
                    ),
                )
                await cursor.execute(
                    lookup_query,
                    (
                        checkpoint.device_id,
                        checkpoint.last_exported_at.replace(tzinfo=None),
                    ),
                )
                row = await cursor.fetchone()

            if row:
                checkpoint.id = str(row["id"])
                checkpoint.created_at = row["created_at"].replace(tzinfo=timezone.utc)
                checkpoint.updated_at = row["updated_at"].replace(tzinfo=timezone.utc)

        logger.info(
            "Checkpoint saved",
            extra={
                "device_id": checkpoint.device_id,
                "checkpoint_id": checkpoint.id,
                "status": checkpoint.status.value,
                "record_count": checkpoint.record_count,
            },
        )

        return checkpoint

    async def health_check(self) -> bool:
        """Check database connectivity."""
        if not self._pool:
            raise RuntimeError("Checkpoint repository not initialized")

        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT 1")
                    await cursor.fetchone()
            return True
        except Exception as e:
            logger.error(f"Checkpoint repository health check failed: {e}")
            raise
