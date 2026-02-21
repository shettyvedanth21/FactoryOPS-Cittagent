"""Rule Engine client for asynchronous rule evaluation."""

import asyncio
from typing import Any, Dict, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config import settings
from src.models import TelemetryPayload
from src.utils import get_logger

logger = get_logger(__name__)


class RuleEngineError(Exception):
    """Raised when rule engine call fails."""
    pass


class RuleEngineClient:
    """
    Client for asynchronous Rule Engine service calls.
    
    Features:
    - Non-blocking rule evaluation
    - Configurable retries with exponential backoff
    - Circuit breaker pattern support
    - Timeout handling
    - Dynamic field support
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        retry_delay: Optional[float] = None,
    ):
        self.base_url = base_url or settings.rule_engine_url
        self.timeout = timeout or settings.rule_engine_timeout
        self.max_retries = max_retries or settings.rule_engine_max_retries
        self.retry_delay = retry_delay or settings.rule_engine_retry_delay
        
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )
        
        self._circuit_open = False
        self._failure_count = 0
        self._circuit_threshold = 5
        self._circuit_timeout = 30
        
        logger.info(
            "RuleEngineClient initialized",
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )
    
    async def evaluate_rules(
        self,
        payload: TelemetryPayload,
    ) -> None:
        """Asynchronously evaluate rules for telemetry payload."""
        if self._circuit_open:
            logger.warning(
                "Circuit breaker open, skipping rule evaluation",
                device_id=payload.device_id,
            )
            return
        
        try:
            await self._send_evaluation_request(payload)
            self._failure_count = 0
            
        except Exception as e:
            self._failure_count += 1
            
            if self._failure_count >= self._circuit_threshold:
                self._circuit_open = True
                logger.error(
                    "Circuit breaker opened due to repeated failures",
                    failure_count=self._failure_count,
                )
                asyncio.create_task(self._reset_circuit())
            
            logger.error(
                "Rule evaluation failed",
                device_id=payload.device_id,
                error=str(e),
                retry_count=self.max_retries,
            )
    
    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, asyncio.TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _send_evaluation_request(self, payload: TelemetryPayload) -> None:
        """Send rule evaluation request to rule engine."""
        url = f"{self.base_url}/api/v1/rules/evaluate"
        
        dynamic_fields = payload.get_dynamic_fields()
        
        request_data: Dict[str, Any] = {
            "device_id": payload.device_id,
            "timestamp": payload.timestamp.isoformat(),
            "schema_version": payload.schema_version or "v1",
            "enrichment_status": payload.enrichment_status.value,
        }
        
        for key, value in dynamic_fields.items():
            request_data[key] = value
        
        if payload.device_metadata:
            request_data["device_type"] = payload.device_metadata.type
            if payload.device_metadata.location:
                request_data["device_location"] = payload.device_metadata.location
        
        try:
            response = await self.client.post(
                url,
                json=request_data,
            )
            response.raise_for_status()
            
            logger.debug(
                "Rule evaluation request sent",
                device_id=payload.device_id,
                status_code=response.status_code,
            )
            
        except httpx.HTTPStatusError as e:
            logger.warning(
                "Rule engine returned error status",
                device_id=payload.device_id,
                status_code=e.response.status_code,
                response=e.response.text,
            )
            raise RuleEngineError(f"HTTP error: {e.response.status_code}") from e
            
        except httpx.RequestError as e:
            raise RuleEngineError(f"Request error: {e}") from e
    
    async def _reset_circuit(self) -> None:
        """Reset circuit breaker after timeout."""
        await asyncio.sleep(self._circuit_timeout)
        self._circuit_open = False
        self._failure_count = 0
        logger.info("Circuit breaker reset")
    
    async def health_check(self) -> bool:
        """Check if rule engine service is healthy."""
        try:
            response = await self.client.get(
                f"{self.base_url}/health",
                timeout=5.0,
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(
                "Rule engine health check failed",
                error=str(e),
            )
            return False
    
    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()
        logger.info("RuleEngineClient HTTP client closed")
