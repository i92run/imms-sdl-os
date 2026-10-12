"""
hardware/ur3_controller.py
==========================
Standalone hardware controller for UR3e arm and Robotiq gripper.
"""

import time
import socket
import xml.etree.ElementTree as ET
from typing import Optional

from rtde_control import RTDEControlInterface
from ..libs.mt_xpr_webservice import Robot
from ..libs.robotiq_preamble import ROBOTIQ_PREAMBLE
from ..config.settings import UR_HOST, UR_PORT, WAYPOINTS_XML, GRIPPER_SPEED, DOOR_SETTLE_S
from ..hardware.xpr_controller import XPRController
from ..utils.exceptions import HardwareConnectionError, XPRDoorError

SPEED_JOINT = 1.0
ACCEL_JOINT = 1.4
SPEED_LINEAR = 0.12
ACCEL_LINEAR = 0.4
SPEED_INSERT = 0.04
ACCEL_INSERT = 0.2


class UR3eController(Robot):
    """UR3e arm and Robotiq gripper controller."""

    def __init__(self, robot_ip: str = UR_HOST, robot_port: int = UR_PORT, 
                 balance_controller: Optional[XPRController] = None, 
                 waypoints_file: str = WAYPOINTS_XML, door_settle_s: float = DOOR_SETTLE_S):
        self.robot_ip = robot_ip
        self.robot_port = robot_port
        self.xpr = balance_controller
        self.waypoints_file = waypoints_file
        self.door_settle_s = door_settle_s
        self.rtde_c: Optional[RTDEControlInterface] = None

    def connect(self) -> None:
        """Verifies network connectivity to the UR3e controller."""
        print(f"Connecting to UR3e at {self.robot_ip}:{self.robot_port}...")
        try:
            with socket.create_connection((self.robot_ip, self.robot_port), timeout=3.0):
                print("UR3e connection successful.")
        except (socket.timeout, ConnectionRefusedError):
            raise HardwareConnectionError(f"Failed to connect to UR3e at {self.robot_ip}:{self.robot_port}.")

    def disconnect(self) -> None:
        """Safely terminates active RTDE connections."""
        if self.rtde_c:
            try:
                self.rtde_c.stopScript()
                self.rtde_c.disconnect()
            except Exception:
                pass
            self.rtde_c = None

    def _safe_open_doors(self) -> None:
        if self.xpr:
            self.xpr.open_doors(self.door_settle_s)
            if not self.xpr.is_door_open():
                raise XPRDoorError("Draft shield doors failed to open. Halting robot to prevent collision.")

    def _safe_close_doors(self) -> None:
        if self.xpr:
            self.xpr.close_doors(self.door_settle_s)

    def _load_sequence_from_xml(self, sequence_name: str):
        try:
            tree = ET.parse(self.waypoints_file)
            root = tree.getroot()
            sequence_node = root.find(f"./sequence[@name='{sequence_name}']")
            if sequence_node is None:
                print(f"[XML Error] Sequence '{sequence_name}' not found in {self.waypoints_file}.")
                return []

            commands = []
            for step in sequence_node:
                if step.tag == "move":
                    commands.append({
                        "type": "move",
                        "move_type": step.get("type"),
                        "pose": [
                            float(step.get("x")), float(step.get("y")), float(step.get("z")),
                            float(step.get("rx")), float(step.get("ry")), float(step.get("rz"))
                        ]
                    })
                elif step.tag == "gripper":
                    commands.append({
                        "type": "gripper",
                        "action": step.get("action"),
                        "power": float(step.get("power", 10.0))
                    })
            return commands
        except Exception as e:
            print(f"[XML Parse Error] Could not read {self.waypoints_file}: {e}")
            return []

    def _gripper_call(self, rtde_c: RTDEControlInterface, name: str, script_function: str) -> bool:
        full_script = ROBOTIQ_PREAMBLE + "\n" + script_function + "\n"
        return rtde_c.sendCustomScriptFunction("ROBOTIQ_" + name, full_script)

    def _gripper_control(self, rtde_c: RTDEControlInterface, close: bool, xml_power: float) -> None:
        target_force = max(0, min(255, int((xml_power / 10.0) * 255)))
        target_speed = GRIPPER_SPEED

        action_str = "close" if close else "open"
        script = f"rq_set_force({target_force})\nrq_set_speed({target_speed})\nrq_{action_str}_and_wait()"
        self._gripper_call(rtde_c, action_str.upper(), script)
        time.sleep(1.5)

    def execute_sequence(self, sequence_name: str, descriptive_label: str) -> None:
        """Executes a named waypoint trajectory sequence from XML."""
        commands = self._load_sequence_from_xml(sequence_name)
        if not commands:
            print(f"[Warning] Sequence '{sequence_name}' skipped: No commands found.")
            return

        print(f"Connecting to UR3e RTDE interface at {self.robot_ip}...")
        self.rtde_c = RTDEControlInterface(self.robot_ip)
        self._gripper_call(self.rtde_c, "ACTIVATE", "rq_activate_and_wait()")

        try:
            print(f"--- Starting Action: {descriptive_label} ---")
            for cmd in commands:
                if cmd["type"] == "move":
                    pose = cmd["pose"]
                    is_inside = (pose[2] <= 0.28)
                    l_speed = SPEED_INSERT if is_inside else SPEED_LINEAR
                    l_accel = ACCEL_INSERT if is_inside else ACCEL_LINEAR

                    if cmd["move_type"] == "joint":
                        self.rtde_c.moveJ_IK(pose, SPEED_JOINT, ACCEL_JOINT)
                    elif cmd["move_type"] == "linear":
                        self.rtde_c.moveL(pose, l_speed, l_accel)

                elif cmd["type"] == "gripper":
                    self._gripper_control(self.rtde_c, close=(cmd["action"] == "close"), xml_power=cmd["power"])

            print(f"--- Action Complete: {descriptive_label} ---")
        finally:
            self.disconnect()

    def place_vial(self, vial_name: str) -> None:
        print(f"\n[Robot] Executing place_vial for '{vial_name}'...")
        self._safe_open_doors()
        self.execute_sequence("place", f"Place Vial ({vial_name})")
        self._safe_close_doors()

    def remove_vial(self, vial_name: str) -> None:
        print(f"\n[Robot] Executing remove_vial for '{vial_name}'...")
        self._safe_open_doors()
        self.execute_sequence("remove", f"Remove Vial ({vial_name})")
        self._safe_close_doors()

    def place_dosing_head(self, head_name: str) -> None: pass
    def remove_dosing_head(self, head_name: str) -> None: pass