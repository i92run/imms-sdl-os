"""
workflows/dosing_workflow.py
============================
High-level state machine orchestrating XPRController and UR3eController.
"""

from ..libs.mt_xpr_webservice import DosingJob
from ..hardware.xpr_controller import XPRController
from ..hardware.ur3_controller import UR3eController
from ..utils.logger import BaseLogger
from ..config.settings import SUBSTANCE_RECIPES, DOSING_METHOD, VIAL_NAME, DOSING_TOLERANCE


class DosingWorkflowManager:
    """Manages end-to-end recipe selection, hardware execution, and logging."""

    def __init__(self, logger: BaseLogger):
        self.logger = logger
        self.xpr = XPRController()
        self.ur3e = UR3eController(balance_controller=self.xpr)

    def initialize_hardware(self):
        """Runs pre-flight connection checks."""
        self.xpr.connect()
        self.ur3e.connect()

    def prompt_substance(self) -> tuple:
        print("============================================================")
        print("RECIPE INDEX: " + ", ".join(SUBSTANCE_RECIPES.keys()))
        user_substance = input("Input: Enter the name of the target substance: ").strip()
        print("============================================================")
        
        if user_substance not in SUBSTANCE_RECIPES:
            print(f"Error: '{user_substance}' is not registered in recipes.")
            return None, None, None

        target_val, target_unit = SUBSTANCE_RECIPES[user_substance]
        return user_substance, target_val, target_unit

    def run(self):
        substance_name, target_value, target_unit = self.prompt_substance()
        if not substance_name:
            return

        with self.xpr.session():
            self.xpr.wakeup_and_zero()
            self.xpr.start_task(DOSING_METHOD)

            if not self.xpr.verify_dosing_head(substance_name):
                self.xpr.cancel_task()
                return

            self.xpr.tare()

            tol_value = target_value * (DOSING_TOLERANCE / 100.0)
            job_list = [DosingJob(
                substance_name=substance_name,
                vial_name=VIAL_NAME,
                target_value=target_value,
                target_unit=target_unit,
                lower_tolerance=tol_value,
                upper_tolerance=tol_value
            )]

            try:
                # Automated loop: XPR triggers ur3e.place_vial() callback natively[cite: 4]
                results = self.xpr.run_dosing_jobs(jobs=job_list, robot_driver=self.ur3e)
                
                weight_sample = self.xpr.get_stable_weight()
                final_val, final_unit = weight_sample.net_value, weight_sample.net_unit

                for res in results:
                    status_str = "SUCCESS" if res.success else "FAILURE"
                    #print(f"\nFinal Result: {res.substance_name} -> {final_val} {final_unit} [{status_str}]")
                    # --- Detailed Terminal Output ---
                    print("\n" + "="*40)
                    print("[Dosing Result Summary]")
                    print(f"  Status   : {status_str}")
                    print(f"  Target   : {target_value} {res.target_unit} of {res.substance_name} into {res.vial_name}")
                    print(f"  Actual   : {final_val} {final_unit}")
                    print(f"  Duration : {res.duration_s:.2f} seconds")
                    if res.error:
                        print(f"  Error    : {res.error}")
                    print("="*40 + "\n")

                    self.logger.log_record(
                        vial=res.vial_name,
                        substance=res.substance_name,
                        target_val=target_value,
                        target_unit=res.target_unit,
                        actual_val=final_val,
                        actual_unit=final_unit,
                        duration=res.duration_s,
                        status=status_str,
                        error_msg=res.error
                    )

                # Explicit removal: XPR does not trigger remove_vial natively after dosing
                print("\n[Workflow] Dosing phase complete. Initiating explicit vial removal...")
                self.ur3e.remove_vial(VIAL_NAME)

            except Exception as e:
                print(f"Workflow Exception: {e}")
                self.xpr.cancel_task()
                raise e

            self.xpr.complete_task()