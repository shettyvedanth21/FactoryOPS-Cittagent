"""Dead Letter Queue repository with file-based persistent storage."""

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Protocol

from src.config import settings
from src.models import DLQEntry
from src.utils import get_logger

logger = get_logger(__name__)


class DLQBackend(Protocol):
    """Protocol for DLQ backend implementations."""
    
    def send(self, entry: DLQEntry) -> bool:
        """Send entry to DLQ."""
        ...
    
    def close(self) -> None:
        """Close the backend."""
        ...


class FileBasedDLQBackend:
    """
    File-based DLQ backend with rotation support.
    
    Features:
    - Thread-safe file operations
    - JSON lines format
    - Automatic file rotation based on size
    - Configurable max files
    """
    
    def __init__(
        self,
        directory: str = "./dlq",
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        max_files: int = 10,
    ):
        """
        Initialize file-based DLQ backend.
        
        Args:
            directory: Directory to store DLQ files
            max_file_size: Maximum size of each DLQ file in bytes
            max_files: Maximum number of DLQ files to keep
        """
        self.directory = Path(directory)
        self.max_file_size = max_file_size
        self.max_files = max_files
        self._lock = threading.Lock()
        self._current_file: Optional[Path] = None
        self._file_handle: Optional[Any] = None
        
        # Ensure directory exists
        self.directory.mkdir(parents=True, exist_ok=True)
        
        # Open initial file
        self._open_current_file()
        
        logger.info(
            "FileBasedDLQBackend initialized",
            directory=str(self.directory),
            max_file_size=self.max_file_size,
            max_files=self.max_files,
        )
    
    def _open_current_file(self) -> None:
        """Open or create current DLQ file."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self._current_file = self.directory / f"dlq_{timestamp}.jsonl"
        
        # Open in append mode
        self._file_handle = open(self._current_file, "a", encoding="utf-8")
        
        logger.debug(
            "Opened new DLQ file",
            file=str(self._current_file),
        )
    
    def _rotate_if_needed(self) -> None:
        """Rotate file if size exceeds limit."""
        if self._current_file is None:
            return
        
        current_size = self._current_file.stat().st_size
        if current_size >= self.max_file_size:
            # Close current file
            if self._file_handle:
                self._file_handle.close()
            
            # Open new file
            self._open_current_file()
            
            # Clean up old files
            self._cleanup_old_files()
    
    def _cleanup_old_files(self) -> None:
        """Remove old DLQ files if exceeding max_files."""
        dlq_files = sorted(
            self.directory.glob("dlq_*.jsonl"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        
        if len(dlq_files) > self.max_files:
            files_to_remove = dlq_files[self.max_files:]
            for file_path in files_to_remove:
                try:
                    file_path.unlink()
                    logger.info(
                        "Removed old DLQ file",
                        file=str(file_path),
                    )
                except OSError as e:
                    logger.error(
                        "Failed to remove old DLQ file",
                        file=str(file_path),
                        error=str(e),
                    )
    
    def send(self, entry: DLQEntry) -> bool:
        """
        Send entry to DLQ.
        
        Args:
            entry: DLQ entry to store
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            try:
                # Rotate if needed
                self._rotate_if_needed()
                
                # Write entry as JSON line
                entry_dict = entry.model_dump()
                json_line = json.dumps(entry_dict, default=str)
                
                if self._file_handle:
                    self._file_handle.write(json_line + "\n")
                    self._file_handle.flush()
                
                logger.debug(
                    "DLQ entry written",
                    error_type=entry.error_type,
                    file=str(self._current_file),
                )
                
                return True
                
            except Exception as e:
                logger.error(
                    "Failed to write DLQ entry",
                    error=str(e),
                    error_type=entry.error_type,
                )
                return False
    
    def close(self) -> None:
        """Close the file handle."""
        with self._lock:
            if self._file_handle:
                try:
                    self._file_handle.close()
                    logger.info("DLQ file handle closed")
                except Exception as e:
                    logger.error(
                        "Error closing DLQ file handle",
                        error=str(e),
                    )


class DLQRepository:
    """
    Dead Letter Queue repository with pluggable backend.
    
    This repository provides a thread-safe interface for sending
    failed messages to a dead letter queue for later analysis.
    """
    
    def __init__(self, backend: Optional[DLQBackend] = None):
        """
        Initialize DLQ repository.
        
        Args:
            backend: DLQ backend implementation (defaults to FileBasedDLQBackend)
        """
        self.backend = backend or FileBasedDLQBackend(
            directory=settings.dlq_directory,
            max_file_size=settings.dlq_max_file_size,
            max_files=settings.dlq_max_files,
        )
        
        logger.info("DLQRepository initialized")
    
    def send(
        self,
        original_payload: Dict[str, Any],
        error_type: str,
        error_message: str,
        retry_count: int = 0,
    ) -> bool:
        """
        Send failed message to DLQ.
        
        Args:
            original_payload: Original message that failed
            error_type: Classification of error
            error_message: Detailed error message
            retry_count: Number of retry attempts made
            
        Returns:
            True if successfully queued, False otherwise
        """
        entry = DLQEntry(
            original_payload=original_payload,
            error_type=error_type,
            error_message=error_message,
            retry_count=retry_count,
        )
        
        success = self.backend.send(entry)
        
        if success:
            logger.info(
                "Message sent to DLQ",
                error_type=error_type,
                device_id=original_payload.get("device_id", "unknown"),
            )
        else:
            logger.error(
                "Failed to send message to DLQ",
                error_type=error_type,
                device_id=original_payload.get("device_id", "unknown"),
            )
        
        return success
    
    def close(self) -> None:
        """Close the repository and its backend."""
        self.backend.close()
