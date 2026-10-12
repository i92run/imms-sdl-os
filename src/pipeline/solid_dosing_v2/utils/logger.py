"""
utils/logger.py
===============
Abstract logging framework implementing the Strategy Pattern.
Allows hot-swapping CSV logging with Database (e.g., Prefect/MongoDB) logging.
"""

import os
import csv
import time
import logging
from abc import ABC, abstractmethod

CSV_HEADERS = [
    "Timestamp",
    "Target Vial",
    "Dispensed Matter",
    "Target Value",
    "Target Unit",
    "Validated Mass",
    "Mass Unit",
    "Cycle Duration (s)",
    "Execution Status",
    "Error Diagnostic",
]

class BaseLogger(ABC):
    """Abstract base class defining the logging interface."""
    
    @abstractmethod
    def log_record(self, vial: str, substance: str, target_val: float, target_unit: str,
                   actual_val: float, actual_unit: str, duration: float, 
                   status: str, error_msg: str = "") -> None:
        pass

class CSVLogger(BaseLogger):
    """Concrete implementation for logging metrics to a structured CSV file."""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        # Ensure the data directory exists
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)

    def log_record(self, vial: str, substance: str, target_val: float, target_unit: str,
                   actual_val: float, actual_unit: str, duration: float, 
                   status: str, error_msg: str = "") -> None:
        """Appends execution metrics to a structured CSV file."""
        file_exists = os.path.isfile(self.filepath)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        row_data = [
            timestamp,
            vial,
            substance,
            target_val,
            target_unit,
            actual_val if actual_val is not None else "N/A",
            actual_unit if actual_unit is not None else "N/A",
            duration if duration is not None else "N/A",
            status,
            error_msg if error_msg else "None",
        ]

        try:
            with open(self.filepath, mode="a", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                if not file_exists:
                    writer.writerow(CSV_HEADERS)
                writer.writerow(row_data)
            logging.info("CSV Logging: Records successfully committed to '%s'.", self.filepath)
        except Exception as err:
            logging.error("Failed to write record to CSV file '%s': %s", self.filepath, err)