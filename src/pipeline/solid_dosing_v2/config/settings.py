"""
settings.py
=========
Shared configuration settings for hardware connection, recipe profiles,
and operational parameters.
"""

# Balance Connection
BALANCE_HOST = "192.168.1.10"
BALANCE_PORT = 81
BALANCE_PASSWORD = "00000000"
USE_HTTPS = False

# Dosing Tolerance Settings
DOSING_TOLERANCE = 1  # Default +/- 1% tolerance window

# UR3e Robot Connection
UR_HOST = "192.168.1.20"
UR_PORT = 30002

# Robotiq Gripper Settings
# 0 = minimum speed (~22 mm/s), 255 = maximum speed (~110 mm/s)
GRIPPER_SPEED = 0

# File Paths & Constants
WAYPOINTS_XML = "src/pipeline/solid_dosing_v2/vial_waypoints.xml"
CSV_FILE_NAME = "src/pipeline/solid_dosing_v2/logs/output.csv"
DOOR_SETTLE_S = 1.0
DOSING_METHOD = "0415_AD"
VIAL_NAME     = "Vial1"

# Dosing Recipes Registry: "Name": (Target Mass, Unit)
SUBSTANCE_RECIPES = {
    "BDC":               (10, "Milligram"),
    "KB":                (10, "Milligram"),
    "Aluminum Oxide":    (16, "Milligram"),
    "Lithium Carbonate": (12, "Milligram"),
}