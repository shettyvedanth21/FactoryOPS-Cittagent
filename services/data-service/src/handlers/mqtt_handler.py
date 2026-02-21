# services/data-service/src/handlers/mqtt_handler.py

"""MQTT message handler."""

import asyncio
import json
import uuid
from typing import Any, Dict, Optional

import paho.mqtt.client as mqtt

from src.config import settings
from src.services.telemetry_service import TelemetryService
from src.utils import get_logger

logger = get_logger(__name__)


class MQTTHandler:
    """
    MQTT message handler with reconnect support.

    Features:
    - Automatic reconnect with exponential backoff
    - QoS 1 message handling
    - Async processing to avoid blocking MQTT loop
    - Connection state management
    """

    def __init__(
        self,
        telemetry_service: Optional[TelemetryService] = None,
    ):
        """
        Initialize MQTT handler.

        Args:
            telemetry_service: Telemetry service instance
        """
        self.telemetry_service = telemetry_service
        self.client: Optional[mqtt.Client] = None

        # >>> FIX: store main asyncio loop
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        self._connected = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = settings.mqtt_max_reconnect_attempts
        self._reconnect_interval = settings.mqtt_reconnect_interval

        logger.info(
            "MQTTHandler initialized",
            broker_host=settings.mqtt_broker_host,
            broker_port=settings.mqtt_broker_port,
            topic=settings.mqtt_topic,
            qos=settings.mqtt_qos,
        )

    def connect(self) -> None:
        """Connect to MQTT broker."""

        # >>> FIX: capture the running asyncio loop
        self._loop = asyncio.get_running_loop()

        # Create client
        self.client = mqtt.Client(
            client_id=f"data-service-{uuid.uuid4().hex[:8]}",
            clean_session=True,
        )

        # Set callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_subscribe = self._on_subscribe

        # Set authentication if configured
        if settings.mqtt_username and settings.mqtt_password:
            self.client.username_pw_set(
                settings.mqtt_username,
                settings.mqtt_password,
            )

        # Enable automatic reconnect
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)

        try:
            # Connect to broker
            self.client.connect(
                host=settings.mqtt_broker_host,
                port=settings.mqtt_broker_port,
                keepalive=settings.mqtt_keepalive,
            )

            # Start network loop in background thread
            self.client.loop_start()

            logger.info(
                "MQTT client connecting",
                host=settings.mqtt_broker_host,
                port=settings.mqtt_broker_port,
            )

        except Exception as e:
            logger.error(
                "Failed to connect to MQTT broker",
                error=str(e),
            )
            # Schedule reconnect
            asyncio.create_task(self._reconnect())

    def disconnect(self) -> None:
        """Disconnect from MQTT broker."""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("MQTT client disconnected")

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: Dict[str, Any],
        rc: int,
    ) -> None:
        """
        Callback when connected to MQTT broker.
        """
        if rc == 0:
            self._connected = True
            self._reconnect_attempts = 0

            logger.info(
                "Connected to MQTT broker",
                host=settings.mqtt_broker_host,
                port=settings.mqtt_broker_port,
            )

            # Subscribe to topic
            result, mid = client.subscribe(
                settings.mqtt_topic,
                qos=settings.mqtt_qos,
            )

            if result == mqtt.MQTT_ERR_SUCCESS:
                logger.info(
                    "Subscribed to MQTT topic",
                    topic=settings.mqtt_topic,
                    qos=settings.mqtt_qos,
                    message_id=mid,
                )
            else:
                logger.error(
                    "Failed to subscribe to topic",
                    topic=settings.mqtt_topic,
                    result=result,
                )
        else:
            logger.error(
                "Failed to connect to MQTT broker",
                return_code=rc,
            )

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        rc: int,
    ) -> None:
        """
        Callback when disconnected from MQTT broker.
        """
        self._connected = False

        if rc != 0:
            logger.warning(
                "Unexpected MQTT disconnection",
                return_code=rc,
            )
            # Schedule reconnect
            asyncio.create_task(self._reconnect())
        else:
            logger.info("MQTT client disconnected cleanly")

    def _on_subscribe(
        self,
        client: mqtt.Client,
        userdata: Any,
        mid: int,
        granted_qos: list,
    ) -> None:
        """
        Callback when subscription is acknowledged.
        """
        logger.info(
            "MQTT subscription acknowledged",
            message_id=mid,
            granted_qos=granted_qos,
        )

    def _on_message(
        self,
        client: mqtt.Client,
        userdata: Any,
        msg: mqtt.MQTTMessage,
    ) -> None:
        """
        Callback when message received.
        """
        correlation_id = str(uuid.uuid4())

        logger.debug(
            "MQTT message received",
            topic=msg.topic,
            qos=msg.qos,
            payload_size=len(msg.payload),
            correlation_id=correlation_id,
        )

        # Parse message payload
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse MQTT message payload",
                topic=msg.topic,
                error=str(e),
                correlation_id=correlation_id,
            )
            return

        # >>> FIX: submit coroutine safely to the main asyncio loop
        if self.telemetry_service and self._loop:

            coro = self.telemetry_service.process_telemetry_message(
                raw_payload=payload,
                correlation_id=correlation_id,
            )

            self._loop.call_soon_threadsafe(
                asyncio.create_task,
                coro,
            )

    async def _reconnect(self) -> None:
        """Attempt to reconnect to MQTT broker with backoff."""
        while (
            not self._connected
            and self._reconnect_attempts < self._max_reconnect_attempts
        ):
            self._reconnect_attempts += 1

            wait_time = min(
                self._reconnect_interval * (2 ** (self._reconnect_attempts - 1)),
                60,  # Max 60 seconds
            )

            logger.info(
                "Attempting MQTT reconnect",
                attempt=self._reconnect_attempts,
                max_attempts=self._max_reconnect_attempts,
                wait_time=wait_time,
            )

            await asyncio.sleep(wait_time)

            try:
                if self.client:
                    self.client.reconnect()
                    # Wait for connection
                    await asyncio.sleep(2)

                    if self._connected:
                        logger.info("MQTT reconnected successfully")
                        return

            except Exception as e:
                logger.error(
                    "MQTT reconnect attempt failed",
                    attempt=self._reconnect_attempts,
                    error=str(e),
                )

        if not self._connected:
            logger.error(
                "Max MQTT reconnect attempts reached",
                max_attempts=self._max_reconnect_attempts,
            )

    @property
    def is_connected(self) -> bool:
        """Check if connected to MQTT broker."""
        return self._connected