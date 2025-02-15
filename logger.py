import logging
from datetime import datetime
import json

# Configure logging
# Get the root logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set the logging level

# Custom LogRecord class
class CustomLogRecord(logging.LogRecord):
    def getMessage(self):
        # Override getMessage to preserve dictionary messages
        if isinstance(self.msg, dict):
            return self.msg  # Return the dictionary as-is
        return super().getMessage()

class JSONFormatter(logging.Formatter):
    def format(self, record):
        # Create the base log record
        log_data = {
            "formatted_timestamp": datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S'),
            "level": record.levelname,
            "filename": record.filename,
            "line_number": record.lineno,
            "message": record.getMessage(),
            "logger_name": record.name,
            "app": "ItineraryGen"
        }
        
        # Include exc_info if it exists
        if record.exc_info:
            log_data['exc_info'] = self.formatException(record.exc_info)
            
        # Include extra fields if they exist
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
            
        return json.dumps(log_data)

# Patch the logging module to use the custom LogRecord
logging.setLogRecordFactory(CustomLogRecord)

# Check if the logger already has handlers to avoid adding duplicates
if not logger.handlers:
    # Create and configure a StreamHandler
    stream_handler = logging.StreamHandler()
    formatter = JSONFormatter()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

# Log levels usage:
# CRITICAL (50): Application crashes, data corruption, security breaches
# ERROR (40): Runtime errors that require immediate attention
# WARNING (30): Unexpected behavior that doesn't affect core functionality
# INFO (20): General operational events, successful operations
# DEBUG (10): Detailed information for debugging purposes