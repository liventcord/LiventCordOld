import logging
import sys
import os
from colorama import Fore, init

os.makedirs('logs', exist_ok=True)
init()

COLORS = {
    'DEBUG': '\x1b[34m',    # Blue
    'INFO': '\x1b[32m',     # Green
    'WARNING': '\x1b[33m',  # Yellow
    'ERROR': '\x1b[31m',    # Red
    'CRITICAL': '\x1b[35m', # Magenta
    'RESET': '\x1b[0m'      # Reset color
}

class ColoredFormatter(logging.Formatter):
    def format(self, record):
        log_level = record.levelname
        formatted_message = super().format(record)
        return f"{log_level} - {formatted_message}"

class ExcludeModulesFilter(logging.Filter):
    def filter(self, record):
        return not (record.name.startswith('werkzeug') or
                    record.name.startswith('db_main_class') or
                    record.name.startswith('urllib3') or
                    'watchdog' in record.name)

# Create a common formatter
formatter = ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Configure the main logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Create a StreamHandler to print to terminal
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
stream_handler.addFilter(ExcludeModulesFilter())
logger.addHandler(stream_handler)

# Create a file handler for the main logger
main_file_handler = logging.FileHandler("logs/log.log")
main_file_handler.setFormatter(formatter)
main_file_handler.addFilter(ExcludeModulesFilter())
logger.addHandler(main_file_handler)

# Configure the db_main_class logger
db_logger = logging.getLogger('db_main_class')
db_logger.setLevel(logging.DEBUG)

# Create a file handler for the db_main_class logger
db_file_handler = logging.FileHandler("logs/db_log.log")
db_file_handler.setFormatter(formatter)
db_logger.addHandler(db_file_handler)

# Configure the werkzeug logger
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.DEBUG)

# Add a specific handler to werkzeug logger
werkzeug_handler = logging.FileHandler("logs/werkzeug.log")
werkzeug_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
werkzeug_logger.addHandler(werkzeug_handler)

# Configure urllib3 logging if needed
urllib3_logger = logging.getLogger('urllib3')
urllib3_logger.setLevel(logging.DEBUG)
urllib3_handler = logging.FileHandler("logs/urllib3.log")
urllib3_handler.setFormatter(formatter)
urllib3_logger.addHandler(urllib3_handler)
