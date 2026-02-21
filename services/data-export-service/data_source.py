"""Data source client for reading telemetry data.

Supports reading from InfluxDB directly (preferred for production)
or from Data Service API (fallback or testing).
"""

from datetime import datetime, timedelta
from typing import Optional

from influxdb_client import InfluxDBClient
from influxdb_client.client.flux_table import TableList

from config import Settings
from logging_config import get_logger
from models import TelemetryData

logger = get_logger(__name__)


class DataSourceClient:
    """Client for reading telemetry data from InfluxDB."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: Optional[InfluxDBClient] = None
        self._query_api = None
    
    def initialize(self) -> None:
        """Initialize InfluxDB client."""
        self._client = InfluxDBClient(
            url=self.settings.influxdb_url,
            token=self.settings.influxdb_token,
            org=self.settings.influxdb_org,
            timeout=self.settings.influxdb_timeout_seconds * 1000,
        )
        self._query_api = self._client.query_api()
        logger.info(
            "InfluxDB client initialized",
            extra={"url": self.settings.influxdb_url, "org": self.settings.influxdb_org}
        )
    
    def close(self) -> None:
        """Close InfluxDB client connection."""
        if self._client:
            self._client.close()
            logger.info("InfluxDB client closed")
    
    async def query_telemetry(
        self,
        device_id: str,
        start_time: datetime,
        end_time: datetime,
        batch_size: int = 1000
    ) -> list[TelemetryData]:
        """Query telemetry data from InfluxDB.
        
        Args:
            device_id: Device identifier
            start_time: Start of time range
            end_time: End of time range
            batch_size: Maximum records to return
            
        Returns:
            List of telemetry data points
        """
        # Convert to ISO format for Flux
        start_iso = start_time.isoformat()
        end_iso = end_time.isoformat()
        
        query = f"""
        from(bucket: "{self.settings.influxdb_bucket}")
            |> range(start: {start_iso}, stop: {end_iso})
            |> filter(fn: (r) => r._measurement == "device_telemetry")
            |> filter(fn: (r) => r.device_id == "{device_id}")
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            |> sort(columns: ["_time"])
            |> limit(n: {batch_size})
        """
        
        try:
            tables: TableList = self._query_api.query(query)
            records = []
            
            for table in tables:
                for record in table.records:
                    telemetry = TelemetryData(
                        timestamp=record.values.get("_time"),
                        device_id=device_id,
                        device_type=record.values.get("device_type", "unknown"),
                        location=record.values.get("location", "unknown"),
                        voltage=record.values.get("voltage"),
                        current=record.values.get("current"),
                        power=record.values.get("power"),
                        temperature=record.values.get("temperature"),
                    )
                    records.append(telemetry)
            
            logger.info(
                f"Queried {len(records)} telemetry records",
                extra={
                    "device_id": device_id,
                    "start_time": start_iso,
                    "end_time": end_iso,
                }
            )
            
            return records
            
        except Exception as e:
            logger.error(
                f"Failed to query telemetry: {e}",
                extra={
                    "device_id": device_id,
                    "start_time": start_iso,
                    "end_time": end_iso,
                }
            )
            raise
    
    async def get_latest_timestamp(self, device_id: str) -> Optional[datetime]:
        """Get the timestamp of the most recent telemetry record.
        
        Args:
            device_id: Device identifier
            
        Returns:
            Timestamp of latest record or None if no data
        """
        query = f"""
        from(bucket: "{self.settings.influxdb_bucket}")
            |> range(start: -30d)
            |> filter(fn: (r) => r._measurement == "device_telemetry")
            |> filter(fn: (r) => r.device_id == "{device_id}")
            |> last()
        """
        
        try:
            tables = self._query_api.query(query)
            
            for table in tables:
                for record in table.records:
                    return record.values.get("_time")
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get latest timestamp: {e}")
            return None
    
    async def count_records(
        self,
        device_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> int:
        """Count telemetry records in time range.
        
        Args:
            device_id: Device identifier
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            Record count
        """
        start_iso = start_time.isoformat()
        end_iso = end_time.isoformat()
        
        query = f"""
        from(bucket: "{self.settings.influxdb_bucket}")
            |> range(start: {start_iso}, stop: {end_iso})
            |> filter(fn: (r) => r._measurement == "device_telemetry")
            |> filter(fn: (r) => r.device_id == "{device_id}")
            |> filter(fn: (r) => r._field == "power")
            |> count()
        """
        
        try:
            tables = self._query_api.query(query)
            
            for table in tables:
                for record in table.records:
                    return record.values.get("_value", 0)
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to count records: {e}")
            return 0
    
    async def health_check(self) -> bool:
        """Check InfluxDB connectivity.
        
        Returns:
            True if InfluxDB is accessible
        """
        try:
            # Try a simple health check
            self._client.health()
            return True
        except Exception as e:
            logger.error(f"InfluxDB health check failed: {e}")
            raise
