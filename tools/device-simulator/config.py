"""Configuration management for device simulator."""
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
import json


@dataclass
class SimulatorConfig:
    """Configuration for device simulator.
    
    Attributes:
        device_id: Unique device identifier
        publish_interval: Time between telemetry messages in seconds
        broker_host: MQTT broker hostname or IP
        broker_port: MQTT broker port number
        fault_mode: Fault injection mode for testing
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        metrics: Comma-separated list of metrics to generate
        metrics_json: JSON object defining metrics with their ranges
    """
    device_id: str
    publish_interval: float = 5.0
    broker_host: str = "localhost"
    broker_port: int = 1883
    fault_mode: str = "none"
    log_level: str = "INFO"
    metrics: str = ""
    metrics_json: str = ""
    
    _parsed_metrics: Dict[str, List[float]] = field(default_factory=dict, init=False, repr=False)
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if not self.device_id:
            raise ValueError("device_id cannot be empty")
        if self.publish_interval <= 0:
            raise ValueError("publish_interval must be positive")
        if self.broker_port <= 0 or self.broker_port > 65535:
            raise ValueError("broker_port must be between 1 and 65535")
        valid_fault_modes = {"none", "spike", "drop", "overheating"}
        if self.fault_mode not in valid_fault_modes:
            raise ValueError(f"fault_mode must be one of {valid_fault_modes}")
        
        self._parse_metrics()
    
    def _parse_metrics(self) -> None:
        """Parse metrics from JSON or comma-separated string."""
        if self.metrics_json:
            try:
                self._parsed_metrics = json.loads(self.metrics_json)
                return
            except json.JSONDecodeError:
                pass
        
        if self.metrics:
            default_ranges = {
                "voltage": [200.0, 250.0],
                "current": [0.0, 2.0],
                "power": [0.0, 500.0],
                "temperature": [20.0, 80.0],
                "pressure": [0.0, 10.0],
                "humidity": [0.0, 100.0],
                "vibration": [0.0, 10.0],
                "frequency": [48.0, 52.0],
                "power_factor": [0.8, 1.0],
                "speed": [1000.0, 2000.0],
                "torque": [0.0, 500.0],
                "oil_pressure": [0.0, 5.0],
            }
            
            metric_list = [m.strip() for m in self.metrics.split(",")]
            for metric in metric_list:
                if metric in default_ranges:
                    self._parsed_metrics[metric] = default_ranges[metric]
                else:
                    self._parsed_metrics[metric] = [0.0, 100.0]
        else:
            self._parsed_metrics = {
                "voltage": [200.0, 250.0],
                "current": [0.0, 2.0],
                "power": [0.0, 500.0],
                "temperature": [20.0, 80.0],
            }
    
    @property
    def topic(self) -> str:
        """Generate MQTT topic for this device."""
        return f"devices/{self.device_id}/telemetry"
    
    @property
    def metric_config(self) -> Dict[str, List[float]]:
        """Get the parsed metric configuration."""
        return self._parsed_metrics
