"""
Helper functions to the configuration process
"""

import os

# paths (RM 2018-05-28T11:04:58.081BRT)
PROJECT_DIR = os.path.dirname(os.path.realpath(__file__))
LOG_DIR = os.path.join(PROJECT_DIR, ".log/")
MAX_BUFFER_SIZE = 4096

# Creates log directory if not available
try:
    os.mkdir(LOG_DIR)
except OSError:
    pass
