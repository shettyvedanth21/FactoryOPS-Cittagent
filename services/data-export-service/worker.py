"""Continuous export worker.

Manages the background export loop, periodically exporting
telemetry data for configured devices.
"""

import asyncio
from datetime import datetime, timezone

from config import Settings
from checkpoint import CheckpointRepository
from data_source import DataSourceClient
from exporter import TelemetryExporter
from logging_config import get_logger
from s3_writer import S3Writer

logger = get_logger(__name__)


class ExportWorker:
    """Background worker that continuously exports telemetry data."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._running = False
        self._task: asyncio.Task | None = None
        self._shutdown_event = asyncio.Event()
        
        # Initialize components
        self.data_source = DataSourceClient(settings)
        self.s3_writer = S3Writer(settings)
        self.checkpoint_store = CheckpointRepository(settings)
        
        # Initialize exporter
        self.exporter = TelemetryExporter(
            settings=settings,
            data_source=self.data_source,
            s3_writer=self.s3_writer,
            checkpoint_repo=self.checkpoint_store,
        )
        
        self._device_ids = settings.get_device_ids()
    
    async def start(self) -> None:
        """Initialize and start the export worker."""
        logger.info("Initializing export worker components...")
        
        # Initialize data source
        self.data_source.initialize()
        
        # Initialize S3 writer
        self.s3_writer.initialize()
        
        # Initialize checkpoint repository
        await self.checkpoint_store.initialize()
        
        # Start background task
        self._running = True
        self._shutdown_event.clear()
        self._task = asyncio.create_task(self._run_loop())
        
        logger.info(
            "Export worker started",
            extra={
                "device_ids": self._device_ids,
                "export_interval_seconds": self.settings.export_interval_seconds,
            }
        )
    
    async def stop(self) -> None:
        """Gracefully stop the export worker."""
        logger.info("Stopping export worker...")
        
        self._running = False
        self._shutdown_event.set()
        
        # Cancel running task
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        # Close components
        await self.checkpoint_store.close()
        self.data_source.close()
        await self.s3_writer.close()
        
        logger.info("Export worker stopped")
    
    def is_running(self) -> bool:
        """Check if worker is running.
        
        Returns:
            True if worker is running
        """
        return self._running and (self._task is not None and not self._task.done())
    
    async def _run_loop(self) -> None:
        """Main export loop."""
        logger.info("Export loop started")
        
        # Do initial export
        await self._export_all_devices()
        
        while self._running:
            try:
                # Wait for next interval or shutdown signal
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=self.settings.export_interval_seconds
                    )
                    # Shutdown event was set
                    break
                except asyncio.TimeoutError:
                    # Normal interval timeout, continue with export
                    pass
                
                if not self._running:
                    break
                
                # Export all devices
                await self._export_all_devices()
                
            except asyncio.CancelledError:
                logger.info("Export loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in export loop: {e}", extra={"error": str(e)})
                # Continue running despite errors
                await asyncio.sleep(5)
        
        logger.info("Export loop ended")
    
    async def _export_all_devices(self) -> None:
        """Export data for all configured devices."""
        logger.debug(f"Starting export for {len(self._device_ids)} devices")
        
        for device_id in self._device_ids:
            if not self._running:
                break
            
            try:
                result = await self.exporter.export_device_data(device_id)
                
                if result.success:
                    if result.record_count > 0:
                        logger.info(
                            f"Exported {result.record_count} records for {device_id}",
                            extra={
                                "device_id": device_id,
                                "record_count": result.record_count,
                                "duration_seconds": result.duration_seconds,
                            }
                        )
                    else:
                        logger.debug(f"No new data for {device_id}")
                else:
                    logger.error(
                        f"Export failed for {device_id}: {result.error_message}",
                        extra={
                            "device_id": device_id,
                            "error": result.error_message,
                        }
                    )
                
            except Exception as e:
                logger.error(
                    f"Unexpected error exporting {device_id}: {e}",
                    extra={"device_id": device_id, "error": str(e)}
                )
                # Continue with next device
                continue
    
    async def force_export(self, device_id: str | None = None) -> None:
        """Force immediate export.
        
        Args:
            device_id: Specific device to export, or None for all devices
        """
        if device_id:
            devices = [device_id]
        else:
            devices = self._device_ids
        
        for dev_id in devices:
            try:
                result = await self.exporter.export_device_data(
                    dev_id, force_full=True
                )
                logger.info(
                    f"Force export completed for {dev_id}",
                    extra={
                        "device_id": dev_id,
                        "record_count": result.record_count,
                        "success": result.success,
                    }
                )
            except Exception as e:
                logger.error(
                    f"Force export failed for {dev_id}: {e}",
                    extra={"device_id": dev_id, "error": str(e)}
                )
