"""MQTT client wrapper with reconnect support and QoS 1."""
import json
import logging
import random
import time
from typing import Optional

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MQTTClient:
    """Production-grade MQTT client with automatic reconnection.
    
    This client implements:
    - QoS 1 publishing (at least once delivery)
    - Exponential backoff for reconnection
    - Connection state tracking
    - Graceful disconnect handling
    """
    
    def __init__(
        self,
        broker_host: str,
        broker_port: int,
        client_id: str,
        reconnect_min_delay: float = 1.0,
        reconnect_max_delay: float = 60.0
    ):
        """Initialize MQTT client.
        
        Args:
            broker_host: MQTT broker hostname
            broker_port: MQTT broker port
            client_id: Unique client identifier
            reconnect_min_delay: Minimum reconnection delay in seconds
            reconnect_max_delay: Maximum reconnection delay in seconds
        """
        self._broker_host = broker_host
        self._broker_port = broker_port
        self._client_id = client_id
        self._reconnect_min_delay = reconnect_min_delay
        self._reconnect_max_delay = reconnect_max_delay
        
        self._client: Optional[mqtt.Client] = None
        self._connected = False
        self._reconnect_delay = reconnect_min_delay
        self._shutdown_requested = False
    
    def connect(self) -> bool:
        """Connect to MQTT broker with retry logic.
        
        Returns:
            True if connected successfully, False otherwise
        """
        self._client = mqtt.Client(client_id=self._client_id)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_publish = self._on_publish
        
        while not self._connected and not self._shutdown_requested:
            try:
                logger.info(
                    "Connecting to MQTT broker",
                    extra={
                        "broker_host": self._broker_host,
                        "broker_port": self._broker_port
                    }
                )
                self._client.connect(
                    self._broker_host,
                    self._broker_port,
                    keepalive=60
                )
                self._client.loop_start()
                
                # Wait for connection (with timeout)
                timeout = 5.0
                elapsed = 0.0
                while not self._connected and elapsed < timeout:
                    time.sleep(0.1)
                    elapsed += 0.1
                
                if self._connected:
                    self._reconnect_delay = self._reconnect_min_delay
                    return True
                else:
                    raise TimeoutError("Connection timeout")
                    
            except Exception as e:
                logger.error(
                    "Failed to connect to MQTT broker",
                    extra={
                        "error": str(e),
                        "retry_delay": self._reconnect_delay
                    }
                )
                if not self._shutdown_requested:
                    time.sleep(self._reconnect_delay)
                    self._reconnect_delay = min(
                        self._reconnect_delay * 2,
                        self._reconnect_max_delay
                    )
        
        return False
    
    def publish(self, topic: str, payload: dict) -> bool:
        """Publish message to MQTT topic with QoS 1.
        
        Args:
            topic: MQTT topic to publish to
            payload: Dictionary payload to publish
            
        Returns:
            True if published successfully, False otherwise
        """
        if not self._connected or not self._client:
            logger.warning("Cannot publish: not connected to broker")
            return False
        
        try:
            message = json.dumps(payload, separators=(',', ':'))
            result = self._client.publish(topic, message, qos=1)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(
                    "Message published",
                    extra={"topic": topic, "payload_size": len(message)}
                )
                return True
            else:
                logger.error(
                    "Failed to publish message",
                    extra={"topic": topic, "error_code": result.rc}
                )
                return False
                
        except Exception as e:
            logger.error(
                "Exception while publishing",
                extra={"topic": topic, "error": str(e)}
            )
            return False
    
    def disconnect(self) -> None:
        """Disconnect from MQTT broker gracefully."""
        self._shutdown_requested = True
        
        if self._client:
            logger.info("Disconnecting from MQTT broker")
            self._client.loop_stop()
            self._client.disconnect()
            self._connected = False
    
    def _on_connect(self, client, userdata, flags, rc):
        """Handle connection callback."""
        if rc == 0:
            self._connected = True
            logger.info("Connected to MQTT broker successfully")
        else:
            self._connected = False
            logger.error(
                "Failed to connect to MQTT broker",
                extra={"return_code": rc}
            )
    
    def _on_disconnect(self, client, userdata, rc):
        """Handle disconnection callback."""
        self._connected = False
        if rc != 0:
            logger.warning(
                "Unexpected disconnection from MQTT broker",
                extra={"return_code": rc}
            )
        else:
            logger.info("Disconnected from MQTT broker")
    
    def _on_publish(self, client, userdata, mid):
        """Handle publish confirmation callback."""
        logger.debug(f"Message {mid} published successfully")
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected
