"""Telemetry data generator with realistic patterns and fault injection and dynamic metrics support."""
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class TelemetryPoint:
    """Single telemetry data point with dynamic fields.
    
    Attributes:
        device_id: Device identifier
        timestamp: ISO-8601 formatted UTC timestamp
        schema_version: Schema version string
        metrics: Dictionary of metric name to value
    """
    device_id: str
    timestamp: str
    schema_version: str
    metrics: Dict[str, float]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result: dict = {
            "device_id": self.device_id,
            "timestamp": self.timestamp,
            "schema_version": self.schema_version,
        }
        for key, value in self.metrics.items():
            result[key] = value
        return result


class TelemetryGenerator:
    """Generate realistic telemetry data with configurable metrics.
    
    This generator creates smooth, realistic variations in sensor readings
    with configurable noise levels and optional fault injection for testing.
    Supports any numeric metrics defined at initialization.
    """
    
    DEFAULT_METRICS = {
        "voltage": {"base": 230.0, "min": 200.0, "max": 250.0, "noise": 1.0, "drift": 2.0},
        "current": {"base": 0.85, "min": 0.0, "max": 2.0, "noise": 0.05, "drift": 0.1},
        "power": {"base": 195.5, "min": 0.0, "max": 500.0, "noise": 2.0, "drift": 5.0},
        "temperature": {"base": 45.0, "min": 20.0, "max": 80.0, "noise": 0.3, "drift": 0.5},
    }
    
    def __init__(
        self,
        device_id: str,
        fault_mode: str = "none",
        noise_factor: float = 0.02,
        metric_config: Optional[Dict[str, List[float]]] = None,
    ):
        """Initialize telemetry generator.
        
        Args:
            device_id: Device identifier
            fault_mode: Fault injection mode ('none', 'spike', 'drop', 'overheating')
            noise_factor: Amount of random noise (0.0 to 1.0)
            metric_config: Dictionary of metric name to [min, max] range
        """
        self._device_id = device_id
        self._fault_mode = fault_mode
        self._noise_factor = noise_factor
        
        if metric_config:
            self._metrics = {}
            for name, range_vals in metric_config.items():
                if len(range_vals) >= 2:
                    base = (range_vals[0] + range_vals[1]) / 2
                    self._metrics[name] = {
                        "base": base,
                        "min": range_vals[0],
                        "max": range_vals[1],
                        "noise": (range_vals[1] - range_vals[0]) * 0.02,
                        "drift": (range_vals[1] - range_vals[0]) * 0.05,
                    }
        else:
            self._metrics = self.DEFAULT_METRICS.copy()
        
        self._current_values = {name: config["base"] for name, config in self._metrics.items()}
        
        self._fault_counter = 0
        self._in_fault_state = False
    
    def generate(self) -> TelemetryPoint:
        """Generate next telemetry data point.
        
        Returns:
            TelemetryPoint with realistic sensor values
        """
        for name, config in self._metrics.items():
            self._current_values[name] = self._update_value(
                self._current_values[name],
                config["base"],
                max_delta=config["drift"],
                noise_scale=config["noise"]
            )
        
        if self._fault_mode != "none":
            self._current_values = self._apply_fault(self._current_values)
        
        clamped_values = {}
        for name, config in self._metrics.items():
            value = self._current_values[name]
            value = max(config["min"], min(config["max"], value))
            if name == "power":
                value = round(value, 2)
            else:
                value = round(value, 3) if abs(value) < 10 else round(value, 2)
            clamped_values[name] = value
        
        return TelemetryPoint(
            device_id=self._device_id,
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            schema_version="v1",
            metrics=clamped_values,
        )
    
    def _update_value(
        self,
        current: float,
        target: float,
        max_delta: float,
        noise_scale: float,
    ) -> float:
        """Update value with smooth transition towards target plus noise."""
        drift = (target - current) * 0.1
        drift = max(-max_delta, min(max_delta, drift))
        
        noise = random.gauss(0, noise_scale) * self._noise_factor
        
        return current + drift + noise
    
    def _apply_fault(self, values: Dict[str, float]) -> Dict[str, float]:
        """Apply fault injection patterns."""
        self._fault_counter += 1
        
        if self._fault_mode == "spike":
            if "voltage" in values and random.random() < 0.1:
                values["voltage"] += random.uniform(20, 50)
                self._in_fault_state = True
            elif self._in_fault_state and random.random() < 0.3:
                self._in_fault_state = False
                
        elif self._fault_mode == "drop":
            if "current" in values and random.random() < 0.05:
                values["current"] = random.uniform(0.01, 0.1)
                if "power" in values:
                    values["power"] = values.get("voltage", 230) * values["current"]
                self._in_fault_state = True
            elif self._in_fault_state and random.random() < 0.5:
                self._in_fault_state = False
                
        elif self._fault_mode == "overheating":
            if "temperature" in values and self._fault_counter % 20 == 0:
                values["temperature"] += random.uniform(2, 5)
                self._in_fault_state = True
            elif "temperature" in values and values["temperature"] > 70:
                values["temperature"] -= random.uniform(0.5, 1.5)
                if values["temperature"] < 50:
                    self._in_fault_state = False
                    self._fault_counter = 0
        
        return values
    
    @property
    def metrics(self) -> List[str]:
        """Get list of metric names."""
        return list(self._metrics.keys())
