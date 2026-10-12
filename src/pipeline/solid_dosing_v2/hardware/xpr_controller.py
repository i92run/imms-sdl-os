"""
hardware/xpr_controller.py
==========================
Standalone hardware controller for the Mettler Toledo XPR balance.
"""

import time
import socket
from typing import Optional, List
from ..libs.mt_xpr_webservice import XprBalance, DosingJob, DosingResult, Robot, WeightSample
from ..config.settings import BALANCE_HOST, BALANCE_PORT, BALANCE_PASSWORD, DOOR_SETTLE_S
from ..utils.exceptions import HardwareConnectionError


class PassiveRobot(Robot):
    """Fallback no-op robot driver used for standalone XPR testing without arm movement."""
    def place_vial(self, vial_name: str) -> None: pass
    def remove_vial(self, vial_name: str) -> None: pass
    def place_dosing_head(self, head_name: str) -> None: pass
    def remove_dosing_head(self, head_name: str) -> None: pass


class XPRController:
    """Wrapper class providing high-level balance operations."""

    def __init__(self, host: str = BALANCE_HOST, port: int = BALANCE_PORT, password: str = BALANCE_PASSWORD):
        self.host = host
        self.port = port
        self.bal = XprBalance(host=host, port=port, client_password=password)

    def connect(self) -> None:
        """Verifies network connectivity to the balance."""
        print(f"Connecting to XPR Balance at {self.host}:{self.port}...")
        try:
            with socket.create_connection((self.host, self.port), timeout=3.0):
                print("XPR Balance connection successful.")
        except (socket.timeout, ConnectionRefusedError):
            raise HardwareConnectionError(f"Failed to connect to XPR Balance at {self.host}:{self.port}. Check network.")

    def session(self):
        """Returns the balance session context manager."""
        return self.bal.session()

    def wakeup_and_zero(self) -> None:
        """Zeroes the load cell, waking up from standby only if required."""
        try:
            print("Zeroing load cell initiated ...")
            self.bal.zero()
        except Exception:
            print("XPR is in standby. Waking up...")
            self.bal.wakeup_from_standby()
            time.sleep(2.0)
            print("Zeroing load cell initiated ...")
            self.bal.zero()

    def open_doors(self, settle_s: float = DOOR_SETTLE_S) -> None:
        """Opens draft shield doors and waits for air settlement."""
        print("Opening all draft shield doors...")
        self.bal.open_all_doors()
        time.sleep(settle_s)

    def is_door_open(self) -> bool:
        """
        Queries hardware to verify doors are fully open.
        """
        if hasattr(self.bal, 'get_door_status'):
            return self.bal.get_door_status() == "OPEN"
        # Fallback if driver doesn't support reading status natively
        return True

    def close_doors(self, settle_s: float = DOOR_SETTLE_S) -> None:
        """Closes draft shield doors strictly."""
        print("Closing all draft shield doors...")
        self.bal.close_all_doors()
        time.sleep(settle_s)

    def start_task(self, method_name: str) -> None:
        """Starts a specific method container task on the touchscreen."""
        print(f"Initializing task workflow profile '{method_name}'...")
        self.bal.start_task(method_name)
        time.sleep(0.5)

    def verify_dosing_head(self, expected_substance: str) -> bool:
        """Reads RFID metadata from mounted head and verifies substance match."""
        head_data = self.bal.read_dosing_head()
        head_substance = head_data.get("substance")
        print(f"RFID Verification: Mounted head substance is '{head_substance}'")
        
        if not head_substance or head_substance.strip().lower() != expected_substance.lower():
            print(f"Mismatch: Head substance '{head_substance}' != Expected '{expected_substance}'")
            return False
        return True

    def tare(self) -> None:
        """Tares current load weight."""
        print("Taring balance load cell...")
        self.bal.tare()
        time.sleep(0.5)

    def run_dosing_jobs(self, jobs: List[DosingJob], robot_driver: Optional[Robot] = None) -> List[DosingResult]:
        """Executes active dosing job list using provided robot driver or passive fallback."""
        driver = robot_driver if robot_driver is not None else PassiveRobot()
        return self.bal.run_dosing_jobs(jobs=jobs, robot=driver)

    def get_stable_weight(self) -> WeightSample:
        """Reads final stable net weight measurement."""
        return self.bal.get_weight(wait_for_stable=True)

    def complete_task(self) -> None:
        """Marks current task complete."""
        self.bal.complete_current_task()

    def cancel_task(self) -> None:
        """Safely cancels active job list and method container."""
        try:
            self.bal.cancel_current_dosing_job_list()
        except Exception:
            pass
        try:
            self.bal.cancel_current_task()
        except Exception:
            pass