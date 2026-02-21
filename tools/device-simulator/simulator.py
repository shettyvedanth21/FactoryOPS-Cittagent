"""Core device simulator implementation."""
import logging
import signal
import sys
import time
from typing import Optional

from config import SimulatorConfig
from mqtt_client import MQTTClient
from telemetry_generator import TelemetryGenerator

logger = logging.getLogger(__name__)


class DeviceSimulator:
    """Production-grade device simulator for MQTT telemetry.
    
    This simulator generates realistic telemetry data and publishes it to
    an MQTT broker with automatic reconnection and graceful shutdown support.
    
    Features:
    - Realistic time-series data generation
    - Dynamic metric support
    - MQTT QoS 1 publishing
    - Automatic reconnection with exponential backoff
    - Graceful shutdown on SIGINT/SIGTERM
    - Structured logging
    - Fault injection for testing
    """
    
    def __init__(self, config: SimulatorConfig):
        """Initialize device simulator.
        
        Args:
            config: Simulator configuration
        """
        self._config = config
        self._mqtt_client: Optional[MQTTClient] = None
        self._telemetry_generator: Optional[TelemetryGenerator] = None
        self._running = False
        self._message_count = 0
        
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def start(self) -> None:
        """Start the device simulator."""
        logger.info(
            "Starting device simulator",
            extra={
                "device_id": self._config.device_id,
                "interval": self._config.publish_interval,
                "broker": f"{self._config.broker_host}:{self._config.broker_port}",
                "fault_mode": self._config.fault_mode,
                "metrics": list(self._config.metric_config.keys()),
            }
        )
        
        self._telemetry_generator = TelemetryGenerator(
            device_id=self._config.device_id,
            fault_mode=self._config.fault_mode,
            metric_config=self._config.metric_config,
        )
        
        self._mqtt_client = MQTTClient(
            broker_host=self._config.broker_host,
            broker_port=self._config.broker_port,
            client_id=f"simulator_{self._config.device_id}"
        )
        
        if not self._mqtt_client.connect():
            logger.error("Failed to connect to MQTT broker. Exiting.")
            sys.exit(1)
        
        self._running = True
        self._run_loop()
    
    def stop(self) -> None:
        """Stop the device simulator gracefully."""
        if not self._running:
            return
            
        logger.info(
            "Stopping device simulator",
            extra={
                "device_id": self._config.device_id,
                "messages_published": self._message_count
            }
        )
        
        self._running = False
        
        if self._mqtt_client:
            self._mqtt_client.disconnect()
        
        logger.info("Device simulator stopped")
    
    def _run_loop(self) -> None:
        """Main simulation loop."""
        last_publish_time = 0.0
        
        while self._running:
            current_time = time.time()
            
            if current_time - last_publish_time >= self._config.publish_interval:
                self._publish_telemetry()
                last_publish_time = current_time
            
            time.sleep(0.1)
    
    def _publish_telemetry(self) -> None:
        """Generate and publish telemetry data."""
        if not self._telemetry_generator or not self._mqtt_client:
            return
        
        telemetry = self._telemetry_generator.generate()
        payload = telemetry.to_dict()
        
        success = self._mqtt_client.publish(
            topic=self._config.topic,
            payload=payload
        )
        
        if success:
            self._message_count += 1
            log_data = {
                "device_id": payload["device_id"],
                "message_count": self._message_count,
            }
            for key in payload:
                if key not in ("device_id", "timestamp", "schema_version"):
                    log_data[key] = payload[key]
            
            logger.info(
                "Telemetry published",
                extra=log_data,
            )
        else:
            logger.warning(
                "Failed to publish telemetry",
                extra={"device_id": self._config.device_id}
            )
    
    def _signal_handler(self, signum, frame) -> None:
        """Handle shutdown signals gracefully."""
        signal_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
        logger.info(f"Received {signal_name}, initiating graceful shutdown")
        self.stop()
        sys.exit(0)
