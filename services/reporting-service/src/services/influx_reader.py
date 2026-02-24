from datetime import datetime
from typing import Any

from influxdb_client.client.flux_table import FluxTable
from influxdb_client import InfluxDBClient

from src.config import settings


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
        fields: list[str]
    ) -> list[dict]:
        field_parts = [f'r._field == "{f}"' for f in fields]
        field_filter = " or ".join(field_parts)
        
        aggregation_window = settings.INFLUX_AGGREGATION_WINDOW
        
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
        
        import logging
        logging.getLogger(__name__).info(f"Flux query: {flux_query}")
        
        result = self.client.query_api().query(flux_query)
        
        rows = []
        for table in result:
            for record in table.records:
                row = {"timestamp": record.get_time()}
                for field in fields:
                    if field in record.values:
                        row[field] = record.values.get(field)
                if any(k in row for k in fields):
                    rows.append(row)
        
        return rows

    def close(self):
        self.client.close()


influx_reader = InfluxReader()
