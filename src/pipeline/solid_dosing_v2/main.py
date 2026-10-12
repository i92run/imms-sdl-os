"""
main.py
=======
Main entry point script with global exception handling.
"""

import sys
from workflows.dosing_workflow import DosingWorkflowManager
from utils.logger import CSVLogger
from utils.exceptions import HardwareConnectionError, XPRDoorError
from config.settings import CSV_FILE_NAME


def main():
    logger = CSVLogger(filepath=CSV_FILE_NAME)
    manager = DosingWorkflowManager(logger=logger)

    try:
        manager.initialize_hardware()
        manager.run()
        
    except (HardwareConnectionError, XPRDoorError) as safe_err:
        print(f"\n[System Halt] {safe_err}")
        sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n\n[EMERGENCY STOP] Ctrl+C detected. Initiating safe hardware shutdown...")
        
        # Safely detach robot and cancel balance operations
        manager.ur3e.disconnect()
        try:
            manager.xpr.cancel_task()
            print("XPR Balance task cancelled successfully.")
        except Exception as e:
            print(f"Failed to cleanly cancel XPR task: {e}")
            
        print("Shutdown complete. Exiting gracefully.")
        sys.exit(130)

if __name__ == "__main__":
    main()