"""Telemetry processing service."""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from src.config import settings
from src.models import TelemetryPayload
from src.repositories import DLQRepository, InfluxDBRepository
from src.services.enrichment_service import EnrichmentService
from src.services.rule_engine_client import RuleEngineClient
from src.utils import (
    get_logger,
    log_telemetry_error,
    log_telemetry_processed,
    TelemetryValidator,
)

logger = get_logger(__name__)


class TelemetryServiceError(Exception):
    """Raised when telemetry processing fails."""
    pass


class TelemetryService:
    """
    Main service for processing telemetry data.

    Orchestrates:
    - Validation
    - Metadata enrichment
    - Rule engine calls
    - InfluxDB persistence
    - WebSocket broadcasting
    - DLQ handling for failures
    """

    def __init__(
        self,
        influx_repository: Optional[InfluxDBRepository] = None,
        dlq_repository: Optional[DLQRepository] = None,
        enrichment_service: Optional[EnrichmentService] = None,
        rule_engine_client: Optional[RuleEngineClient] = None,
    ):
        self.influx_repository = influx_repository or InfluxDBRepository()
        self.dlq_repository = dlq_repository or DLQRepository()
        self.enrichment_service = enrichment_service or EnrichmentService()
        self.rule_engine_client = rule_engine_client or RuleEngineClient()

        self._processing_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None

        logger.info("TelemetryService initialized")

    async def start(self) -> None:
        """Start background worker for async processing."""
        self._worker_task = asyncio.create_task(self._processing_worker())
        logger.info("TelemetryService background worker started")

    async def stop(self) -> None:
        """Stop background worker."""
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("TelemetryService background worker stopped")

    async def process_telemetry_message(
        self,
        raw_payload: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> None:
        """Process incoming telemetry message."""
        correlation_id = correlation_id or str(uuid.uuid4())

        try:
            is_valid, error_type, error_message = TelemetryValidator.validate_payload(
                raw_payload
            )

            if not is_valid:
                self.dlq_repository.send(
                    original_payload=raw_payload,
                    error_type=error_type or "validation_error",
                    error_message=error_message or "Validation failed",
                )
                log_telemetry_error(
                    logger=logger,
                    device_id=raw_payload.get("device_id", "unknown"),
                    correlation_id=correlation_id,
                    error_type=error_type or "validation_error",
                    error_message=error_message or "Validation failed",
                    payload=raw_payload,
                )
                return

            try:
                payload = TelemetryPayload(**raw_payload)
            except Exception as e:
                self.dlq_repository.send(
                    original_payload=raw_payload,
                    error_type="parse_error",
                    error_message=str(e),
                )
                log_telemetry_error(
                    logger=logger,
                    device_id=raw_payload.get("device_id", "unknown"),
                    correlation_id=correlation_id,
                    error_type="parse_error",
                    error_message=str(e),
                    payload=raw_payload,
                )
                return

            await self._processing_queue.put(
                {
                    "payload": payload,
                    "correlation_id": correlation_id,
                    "raw_payload": raw_payload,
                }
            )

            logger.debug(
                "Telemetry queued for processing",
                device_id=payload.device_id,
                correlation_id=correlation_id,
            )

        except Exception as e:
            logger.error(
                "Unexpected error processing telemetry message",
                error=str(e),
                correlation_id=correlation_id,
            )
            self.dlq_repository.send(
                original_payload=raw_payload,
                error_type="unexpected_error",
                error_message=str(e),
            )

    async def _processing_worker(self) -> None:
        """Background worker to process queued telemetry."""
        logger.info("Processing worker started")

        while True:
            try:
                item = await self._processing_queue.get()

                try:
                    await self._process_telemetry_async(
                        payload=item["payload"],
                        correlation_id=item["correlation_id"],
                        raw_payload=item["raw_payload"],
                    )
                except Exception as e:
                    logger.error(
                        "Error in processing worker",
                        error=str(e),
                    )
                finally:
                    self._processing_queue.task_done()

            except asyncio.CancelledError:
                logger.info("Processing worker cancelled")
                break
            except Exception as e:
                logger.error(
                    "Unexpected error in processing worker",
                    error=str(e),
                )

    async def _process_telemetry_async(
        self,
        payload: TelemetryPayload,
        correlation_id: str,
        raw_payload: Dict[str, Any],
    ) -> None:
        """Process telemetry asynchronously."""
        try:
            payload = await self.enrichment_service.enrich_telemetry(payload)

            write_success = self.influx_repository.write_telemetry(payload)

            if not write_success:
                self.dlq_repository.send(
                    original_payload=raw_payload,
                    error_type="influxdb_write_error",
                    error_message="Failed to write to InfluxDB",
                )
                log_telemetry_error(
                    logger=logger,
                    device_id=payload.device_id,
                    correlation_id=correlation_id,
                    error_type="influxdb_write_error",
                    error_message="Failed to write to InfluxDB",
                    payload=raw_payload,
                )
                return

            asyncio.create_task(self.rule_engine_client.evaluate_rules(payload))

            dynamic_fields = payload.get_dynamic_fields()
            
            try:
                from src.api.websocket import broadcast_telemetry
                await broadcast_telemetry(
                    device_id=payload.device_id,
                    telemetry_data=dynamic_fields,
                )
            except Exception as e:
                logger.warning(
                    "Failed to broadcast telemetry via WebSocket",
                    device_id=payload.device_id,
                    error=str(e),
                )
            
            try:
                import httpx
                device_service_url = settings.device_service_url or "http://device-service:8000"
                async with httpx.AsyncClient(timeout=5.0) as client:
                    # First, update the heartbeat (last_seen_timestamp)
                    await client.post(
                        f"{device_service_url}/api/v1/devices/{payload.device_id}/heartbeat"
                    )
                    # Then sync properties if there are any new ones
                    await client.post(
                        f"{device_service_url}/api/v1/devices/{payload.device_id}/properties/sync",
                        json=dynamic_fields
                    )
            except Exception as e:
                logger.warning(
                    "Failed to sync with device service",
                    device_id=payload.device_id,
                    error=str(e),
                )

            log_telemetry_processed(
                logger=logger,
                device_id=payload.device_id,
                correlation_id=correlation_id,
                enrichment_status=payload.enrichment_status.value,
            )

        except Exception as e:
            logger.error(
                "Error in async processing",
                device_id=payload.device_id,
                correlation_id=correlation_id,
                error=str(e),
            )
            self.dlq_repository.send(
                original_payload=raw_payload,
                error_type="processing_error",
                error_message=str(e),
            )
            log_telemetry_error(
                logger=logger,
                device_id=payload.device_id,
                correlation_id=correlation_id,
                error_type="processing_error",
                error_message=str(e),
                payload=raw_payload,
            )

    async def query_telemetry(
        self,
        device_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ):
        return self.influx_repository.query_telemetry(
            device_id=device_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    async def get_telemetry(
        self,
        device_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        fields: Optional[list[str]] = None,
        aggregate: Optional[str] = None,
        interval: Optional[str] = None,
        limit: int = 1000,
    ) -> list:
        return self.influx_repository.query_telemetry(
            device_id=device_id,
            start_time=start_time,
            end_time=end_time,
            fields=fields,
            aggregate=aggregate,
            interval=interval,
            limit=limit,
        )

    async def get_stats(
        self,
        device_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Optional[Any]:
        return self.influx_repository.get_stats(
            device_id=device_id,
            start_time=start_time,
            end_time=end_time,
        )

    async def close(self) -> None:
        """Close all service connections."""
        await self.stop()
        self.influx_repository.close()
        self.dlq_repository.close()
        await self.enrichment_service.close()
        await self.rule_engine_client.close()
        logger.info("TelemetryService closed")
