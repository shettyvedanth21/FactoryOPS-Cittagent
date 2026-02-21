"""Device metadata enrichment service."""

import asyncio
from datetime import datetime
from typing import Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config import settings
from src.models import DeviceMetadata, EnrichmentStatus, TelemetryPayload
from src.utils import get_logger

logger = get_logger(__name__)


class EnrichmentServiceError(Exception):
    """Raised when enrichment service encounters an error."""
    pass


class EnrichmentService:
    """
    Service for enriching telemetry with device metadata.

    Features:
    - Non-blocking enrichment with async HTTP calls
    - Configurable retries with exponential backoff
    - Timeout handling
    - Enrichment status tracking
    """

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[float] = None):
        """
        Initialize enrichment service.

        Args:
            base_url: Device service base URL
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or settings.device_service_url
        self.timeout = timeout or settings.device_service_timeout
        self.max_retries = settings.device_service_max_retries

        # Create async HTTP client
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )

        logger.info(
            "EnrichmentService initialized",
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )

    async def enrich_telemetry(
        self,
        payload: TelemetryPayload,
    ) -> TelemetryPayload:
        """
        Enrich telemetry payload with device metadata.

        This method performs non-blocking enrichment. If the device service
        is unavailable or times out, the payload is marked with the
        appropriate enrichment_status and returned.

        Args:
            payload: Telemetry payload to enrich

        Returns:
            Enriched payload with metadata and status
        """
        try:
            device_metadata = await self._fetch_device_metadata(payload.device_id)

            payload.device_metadata = device_metadata
            payload.enrichment_status = EnrichmentStatus.SUCCESS
            payload.enriched_at = datetime.utcnow()

            logger.debug(
                "Telemetry enriched successfully",
                device_id=payload.device_id,
                device_name=device_metadata.name,
                device_type=device_metadata.type,
            )

        except asyncio.TimeoutError:
            logger.warning(
                "Enrichment timeout",
                device_id=payload.device_id,
                timeout=self.timeout,
            )
            payload.enrichment_status = EnrichmentStatus.TIMEOUT

        except Exception as e:
            logger.error(
                "Enrichment failed",
                device_id=payload.device_id,
                error=str(e),
            )
            payload.enrichment_status = EnrichmentStatus.FAILED

        return payload

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, asyncio.TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _fetch_device_metadata(self, device_id: str) -> DeviceMetadata:
        """
        Fetch device metadata from device service.

        Args:
            device_id: Device identifier

        Returns:
            Device metadata
        """
        url = f"{self.base_url}/api/v1/devices/{device_id}"

        try:
            response = await self.client.get(url)
            response.raise_for_status()

            data = response.json()

            # Handle nested response structure
            if "data" in data:
                device_data = data["data"]
            else:
                device_data = data

            # ---- FIX: map device-service fields to DeviceMetadata ----
            metadata = DeviceMetadata(
                id=device_data["device_id"],
                name=device_data["device_name"],
                type=device_data["device_type"],
                location=device_data.get("location"),
                status=device_data["status"],
                metadata={
                    "manufacturer": device_data.get("manufacturer"),
                    "model": device_data.get("model"),
                },
            )

            logger.debug(
                "Device metadata fetched",
                device_id=device_id,
                device_name=metadata.name,
            )

            return metadata

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(
                    "Device not found",
                    device_id=device_id,
                    url=url,
                )

                return DeviceMetadata(
                    id=device_id,
                    name=f"Unknown Device ({device_id})",
                    type="unknown",
                    status="unknown",
                )

            raise EnrichmentServiceError(
                f"HTTP error: {e.response.status_code}"
            ) from e

        except httpx.RequestError as e:
            raise EnrichmentServiceError(f"Request error: {e}") from e

    async def health_check(self) -> bool:
        """
        Check if device service is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/health",
                timeout=5.0,
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(
                "Device service health check failed",
                error=str(e),
            )
            return False

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()
        logger.info("EnrichmentService HTTP client closed")
