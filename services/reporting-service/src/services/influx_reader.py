import logging
from datetime import datetime
from typing import Any, List

from influxdb_client.client.flux_table import FluxTable
from influxdb_client import InfluxDBClient
from influxdb_client.client.flux_table import TableList

from src.config import settings


logger = logging.getLogger(__name__)


class InfluxReader:
    def __init__(self):
        self.client = InfluxDBClient(
            url=settings.INFLUXDB_URL,
            token=settings.INFLUXDB_TOKEN,
            org=settings.INFLUXDB_ORG
        )
        self.bucket = settings.INFLUXDB_BUCKET
        self.measurement = settings.INFLUXDB_MEASUREMENT

    async def query_telemetry(
        self,
        device_id: str,
        start_dt: datetime,
        end_dt: datetime,
        fields: List[str]
    ) -> List[dict]:
        logger.info("="*60)
        logger.info("INFLUX QUERY PARAMETERS")
        logger.info(f"  device_id: {device_id}")
        logger.info(f"  start_dt: {start_dt}")
        logger.info(f"  end_dt: {end_dt}")
        logger.info(f"  fields: {fields}")
        logger.info(f"  duration: {(end_dt - start_dt).total_seconds()} seconds")
        logger.info("="*60)
        
        if not device_id:
            logger.warning("query_telemetry called with empty device_id")
            return []
        
        if not fields:
            logger.warning("query_telemetry called with empty fields list")
            return []
        
        if start_dt >= end_dt:
            logger.warning(f"query_telemetry called with invalid date range: {start_dt} >= {end_dt}")
            return []
        
        try:
            return self._query_sync(device_id, start_dt, end_dt, fields)
        except Exception as e:
            logger.error(f"InfluxDB query failed for device {device_id}: {str(e)}")
            return []

    def _query_sync(
        self,
        device_id: str,
        start_dt: datetime,
        end_dt: datetime,
        fields: List[str]
    ) -> List[dict]:
        field_parts = [f'r._field == "{f}"' for f in fields]
        field_filter = " or ".join(field_parts)
        
        aggregation_window = getattr(settings, 'INFLUX_AGGREGATION_WINDOW', '1m')
        
        start_str = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        flux_query = f'''
from(bucket: "{self.bucket}")
|> range(start: time(v: "{start_str}"), stop: time(v: "{end_str}"))
|> filter(fn: (r) => r._measurement == "{self.measurement}")
|> filter(fn: (r) => r.device_id == "{device_id}")
|> filter(fn: (r) => {field_filter})
|> aggregateWindow(every: {aggregation_window}, fn: mean, createEmpty: false)
|> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
|> sort(columns: ["_time"])
'''
        
        logger.info(f"Flux query for device {device_id}: {len(flux_query)} chars")
        logger.info(f"Query:\n{flux_query}")
        
        try:
            result: TableList = self.client.query_api().query(flux_query)
        except Exception as e:
            logger.error(f"InfluxDB query execution failed: {str(e)}")
            raise
        
        if result is None:
            logger.warning("InfluxDB returned None result")
            return []
        
        rows = []
        for table in result:
            if not table or not hasattr(table, 'records'):
                continue
                
            for record in table.records:
                if record is None:
                    continue
                    
                try:
                    ts = record.get_time()
                    if isinstance(ts, str):
                        from datetime import datetime
                        ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    row = {"timestamp": ts}
                    for field in fields:
                        if hasattr(record.values, '__getitem__'):
                            try:
                                row[field] = record.values.get(field)
                            except Exception:
                                pass
                    
                    if any(k in row for k in fields):
                        rows.append(row)
                except Exception as e:
                    logger.warning(f"Failed to parse record: {str(e)}")
                    continue
        
        logger.info(f"Query returned {len(rows)} rows for device {device_id}")
        
        if len(rows) > 0:
            logger.info(f"Sample row keys: {list(rows[0].keys())}")
        
        return rows

    def close(self):
        try:
            self.client.close()
        except Exception as e:
            logger.warning(f"Error closing InfluxDB client: {str(e)}")


influx_reader = InfluxReader()
