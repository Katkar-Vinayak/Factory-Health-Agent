"""
Unit Tests for Verification Service & LangGraph HITL State (Phase 3)
===================================================================
Tests all Phase 3 requirements:
1. Inspection action verification
2. Maintenance ticket verification
3. Replacement request verification
4. Simulated email verification
5. Real email status verification
6. Machine action status verification
7. Alert verification
8. Missing action record handling
9. Missing notification handling
10. Failed action handling
11. Pending telemetry status check
12. Physical health verification safeguard (no false healthy claims)
13. AgentState backward compatibility
14. LangGraph analysis workflow execution and safe PENDING state
"""

import os
import sys
import tempfile
import shutil
import csv
import unittest

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.state import AgentState
from agents.graph import run_agent_workflow
from services import notification_service
from services import action_executor_service
from services import verification_service


class TestVerificationService(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        action_executor_service.ensure_action_csv_files_exist(self.test_dir)
        self.paths = action_executor_service._get_csv_paths(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_sample_notification(
        self,
        machine_id: str = "M_003",
        component: str = "Bearing",
        severity: str = "CRITICAL",
        root_cause: str = "Bearing Degradation"
    ) -> dict:
        return notification_service.create_notification(
            machine_id=machine_id,
            severity=severity,
            title=f"Alert: {component}",
            message=f"Degradation in {component}",
            component=component,
            root_cause=root_cause,
            failure_probability=0.98,
            recommendation="Schedule bearing inspection and replacement",
            filepath=self.paths["notifications"]
        )

    def test_inspection_action_verification(self):
        """Verified that inspection action produces verified software record with PENDING_TELEMETRY."""
        notif = self._create_sample_notification()

        act_res = action_executor_service.execute_action(
            action_type="schedule_inspection",
            notification_id=notif["notification_id"],
            explicit_approval=True,
            approved_by="Lead Engineer",
            data_dir=self.test_dir
        )
        self.assertTrue(act_res["success"])

        ver_res = verification_service.verify_action_completion(
            notification_id=notif["notification_id"],
            action_id=act_res["action_id"],
            action_type="schedule_inspection",
            data_dir=self.test_dir
        )

        self.assertTrue(ver_res["action_verified"])
        self.assertFalse(ver_res["physical_health_verified"])
        self.assertEqual(ver_res["verification_status"], "PENDING_TELEMETRY")
        self.assertIn("inspection scheduled successfully", ver_res["message"].lower())

    def test_maintenance_ticket_verification(self):
        """Verified that maintenance ticket exists in maintenance_tickets.csv with status CREATED."""
        notif = self._create_sample_notification(machine_id="M_001", component="Motor")

        act_res = action_executor_service.execute_action(
            action_type="create_maintenance_ticket",
            notification_id=notif["notification_id"],
            explicit_approval=True,
            approved_by="Shift Manager",
            data_dir=self.test_dir
        )
        self.assertTrue(act_res["success"])

        ver_res = verification_service.verify_action_completion(
            notification_id=notif["notification_id"],
            action_id=act_res["action_id"],
            action_type="create_maintenance_ticket",
            data_dir=self.test_dir
        )

        self.assertTrue(ver_res["action_verified"])
        self.assertEqual(ver_res["verification_status"], "PENDING_TELEMETRY")
        self.assertEqual(ver_res["subsystem_details"]["status"], "CREATED")
        self.assertIn("TCK-001", ver_res["message"])

    def test_replacement_request_verification(self):
        """Verified that replacement request exists in replacement_requests.csv with configured vendor."""
        notif = self._create_sample_notification(machine_id="M_003", component="Bearing")

        act_res = action_executor_service.execute_action(
            action_type="create_replacement_request",
            notification_id=notif["notification_id"],
            explicit_approval=True,
            approved_by="Procurement Head",
            data_dir=self.test_dir
        )
        self.assertTrue(act_res["success"])

        ver_res = verification_service.verify_action_completion(
            notification_id=notif["notification_id"],
            action_id=act_res["action_id"],
            action_type="create_replacement_request",
            data_dir=self.test_dir
        )

        self.assertTrue(ver_res["action_verified"])
        self.assertEqual(ver_res["verification_status"], "PENDING_TELEMETRY")
        self.assertEqual(ver_res["subsystem_details"]["vendor_id"], "V001")
        self.assertEqual(ver_res["subsystem_details"]["part_number"], "BRG-6205")

    def test_simulated_email_verification(self):
        """Verified that mock email dispatch creates a SIMULATED record that passes verification."""
        for k in ["SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "SENDER_EMAIL"]:
            os.environ.pop(k, None)

        notif = self._create_sample_notification(machine_id="M_003", component="Bearing")

        act_res = action_executor_service.execute_action(
            action_type="send_vendor_email",
            notification_id=notif["notification_id"],
            explicit_approval=True,
            approved_by="Supply Lead",
            data_dir=self.test_dir
        )
        self.assertTrue(act_res["success"])

        ver_res = verification_service.verify_action_completion(
            notification_id=notif["notification_id"],
            action_id=act_res["action_id"],
            action_type="send_vendor_email",
            data_dir=self.test_dir
        )

        self.assertTrue(ver_res["action_verified"])
        self.assertEqual(ver_res["verification_status"], "PENDING_TELEMETRY")
        self.assertEqual(ver_res["subsystem_details"]["status"], "SIMULATED")

    def test_real_email_status_verification(self):
        """Verified that a replacement request record marked 'SENT' is successfully verified."""
        notif = self._create_sample_notification(machine_id="M_003", component="Bearing")

        # Create action record
        act_res = action_executor_service.execute_action(
            action_type="send_vendor_email",
            notification_id=notif["notification_id"],
            explicit_approval=True,
            approved_by="Procurement Lead",
            data_dir=self.test_dir
        )

        # Update replacement request status to SENT to test real mode verification
        req_csv = self.paths["replacement_requests"]
        rows = []
        with open(req_csv, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                r["status"] = "SENT"
                rows.append(r)
        with open(req_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=notification_service.REPLACEMENT_REQUEST_HEADERS)
            w.writeheader()
            w.writerows(rows)

        ver_res = verification_service.verify_action_completion(
            notification_id=notif["notification_id"],
            action_id=act_res["action_id"],
            action_type="send_vendor_email",
            data_dir=self.test_dir
        )

        self.assertTrue(ver_res["action_verified"])
        self.assertEqual(ver_res["subsystem_details"]["status"], "SENT")
        self.assertIn("Status: SENT", ver_res["message"])

    def test_machine_action_status_verification(self):
        """Verified that machine action status update is recorded in machine_action_status.csv."""
        notif = self._create_sample_notification(machine_id="M_003", component="Bearing")

        act_res = action_executor_service.execute_action(
            action_type="update_machine_status",
            notification_id=notif["notification_id"],
            explicit_approval=True,
            approved_by="Floor Director",
            notes="MAINTENANCE_SCHEDULED",
            data_dir=self.test_dir
        )
        self.assertTrue(act_res["success"])

        ver_res = verification_service.verify_action_completion(
            notification_id=notif["notification_id"],
            action_id=act_res["action_id"],
            action_type="update_machine_status",
            machine_id="M_003",
            data_dir=self.test_dir
        )

        self.assertTrue(ver_res["action_verified"])
        self.assertIn("MAINTENANCE_SCHEDULED", ver_res["message"])

    def test_alert_verification(self):
        """Verified that application alert is recorded with status ACTIVE."""
        notif = self._create_sample_notification(machine_id="M_004", component="Hydraulic Valve")

        act_res = action_executor_service.execute_action(
            action_type="create_alert",
            notification_id=notif["notification_id"],
            explicit_approval=True,
            approved_by="Safety Officer",
            data_dir=self.test_dir
        )
        self.assertTrue(act_res["success"])

        ver_res = verification_service.verify_action_completion(
            notification_id=notif["notification_id"],
            action_id=act_res["action_id"],
            action_type="create_alert",
            data_dir=self.test_dir
        )

        self.assertTrue(ver_res["action_verified"])
        self.assertEqual(ver_res["subsystem_details"]["status"], "ACTIVE")

    def test_missing_action_record(self):
        """Verification fails cleanly when no action record exists for a notification."""
        notif = self._create_sample_notification()

        ver_res = verification_service.verify_action_completion(
            notification_id=notif["notification_id"],
            data_dir=self.test_dir
        )

        self.assertFalse(ver_res["action_verified"])
        self.assertEqual(ver_res["verification_status"], "FAILED")
        self.assertEqual(ver_res["error_code"], "ACTION_RECORD_NOT_FOUND")

    def test_missing_notification(self):
        """Verification fails cleanly when notification ID does not exist."""
        ver_res = verification_service.verify_action_completion(
            notification_id="NTF-9999",
            data_dir=self.test_dir
        )

        self.assertFalse(ver_res["action_verified"])
        self.assertEqual(ver_res["verification_status"], "FAILED")
        self.assertEqual(ver_res["error_code"], "NOTIFICATION_NOT_FOUND")

    def test_failed_action_handling(self):
        """Verification marks FAILED when the underlying action record has status FAILED."""
        notif = self._create_sample_notification()

        # Write a failed action record into action_records.csv
        failed_record = {
            "action_id": "ACT-099",
            "notification_id": notif["notification_id"],
            "machine_id": "M_003",
            "action_type": "schedule_inspection",
            "component": "Bearing",
            "priority": "HIGH",
            "reason": "Test failure",
            "status": "FAILED",
            "approved_at": "2023-01-19 22:00:00",
            "completed_at": "2023-01-19 22:01:00",
            "result": "Database write error simulation",
            "verification_status": "FAILED"
        }
        with open(self.paths["action_records"], "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=notification_service.ACTION_RECORD_HEADERS)
            writer.writerow(failed_record)

        ver_res = verification_service.verify_action_completion(
            notification_id=notif["notification_id"],
            action_id="ACT-099",
            data_dir=self.test_dir
        )

        self.assertFalse(ver_res["action_verified"])
        self.assertEqual(ver_res["verification_status"], "FAILED")
        self.assertEqual(ver_res["error_code"], "ACTION_EXECUTION_FAILED")

    def test_pending_telemetry_status(self):
        """Verified that successful software actions set verification_status to PENDING_TELEMETRY by default."""
        notif = self._create_sample_notification()

        act_res = action_executor_service.execute_action(
            action_type="schedule_inspection",
            notification_id=notif["notification_id"],
            explicit_approval=True,
            approved_by="Auditor",
            data_dir=self.test_dir
        )

        ver_res = verification_service.verify_action_completion(
            notification_id=notif["notification_id"],
            action_id=act_res["action_id"],
            data_dir=self.test_dir
        )

        self.assertEqual(ver_res["verification_status"], "PENDING_TELEMETRY")
        self.assertFalse(ver_res["physical_health_verified"])

    def test_physical_health_safeguard(self):
        """CRITICAL: Software action NEVER claims physical health verified without genuine new telemetry."""
        notif = self._create_sample_notification()

        act_res = action_executor_service.execute_action(
            action_type="schedule_inspection",
            notification_id=notif["notification_id"],
            explicit_approval=True,
            approved_by="Auditor",
            data_dir=self.test_dir
        )

        # 1. Without new telemetry: physical_health_verified MUST be False
        ver_no_telemetry = verification_service.verify_action_completion(
            notification_id=notif["notification_id"],
            action_id=act_res["action_id"],
            new_telemetry_provided=False,
            data_dir=self.test_dir
        )
        self.assertFalse(ver_no_telemetry["physical_health_verified"])
        self.assertEqual(ver_no_telemetry["verification_status"], "PENDING_TELEMETRY")
        self.assertIn("Physical machine recovery requires new telemetry", ver_no_telemetry["message"])

        # 2. With nominal new telemetry: physical_health_verified CAN be True
        nominal_telemetry = {
            "vibration_mm_s": 1.6,
            "temperature_c": 44.0,
            "pressure_bar": 120.0,
            "energy_consumption_kwh": 65.0
        }
        ver_nominal = verification_service.verify_action_completion(
            notification_id=notif["notification_id"],
            action_id=act_res["action_id"],
            new_telemetry_provided=True,
            new_sensor_data=nominal_telemetry,
            data_dir=self.test_dir
        )
        self.assertTrue(ver_nominal["physical_health_verified"])
        self.assertEqual(ver_nominal["verification_status"], "VERIFIED")
        self.assertIn("health parameters nominal", ver_nominal["message"])

        # 3. With anomalous new telemetry: physical_health_verified remains False
        anomalous_telemetry = {
            "vibration_mm_s": 5.8,
            "temperature_c": 82.0,
            "pressure_bar": 80.0,
            "energy_consumption_kwh": 130.0
        }
        ver_anomalous = verification_service.verify_action_completion(
            notification_id=notif["notification_id"],
            action_id=act_res["action_id"],
            new_telemetry_provided=True,
            new_sensor_data=anomalous_telemetry,
            data_dir=self.test_dir
        )
        self.assertFalse(ver_anomalous["physical_health_verified"])
        self.assertEqual(ver_anomalous["verification_status"], "FAILED")

    def test_existing_agent_state_compatibility(self):
        """Verifies AgentState backward compatibility and safe default initialization."""
        legacy_state: AgentState = {
            "machine_id": "M_001",
            "risk_level": "LOW",
            "abnormal_signals": [],
            "evidence": [],
            "agent_trace": [],
            "final_report": "OK"
        }
        self.assertEqual(legacy_state["machine_id"], "M_001")
        # Optional HITL fields do not break legacy usage
        self.assertIsNone(legacy_state.get("notification_id"))
        self.assertIsNone(legacy_state.get("approval_status"))

    def test_existing_analysis_workflow(self):
        """
        End-to-end LangGraph analysis test:
        - Critical machine (M_003) creates PENDING notification without auto-executing actions.
        - Healthy machine (M_001) sets NOT_REQUIRED without notifications.
        - Neither blocks HTTP analysis request.
        """
        # Critical Machine M_003
        res_m003 = run_agent_workflow("M_003", "2023-01-19 22:00:00")
        self.assertEqual(res_m003["risk_level"], "HIGH")
        self.assertEqual(res_m003["root_cause"]["probable_root_cause"], "Bearing Degradation")
        self.assertIsNotNone(res_m003["notification_id"])
        self.assertEqual(res_m003["approval_status"], "PENDING")
        self.assertEqual(res_m003["verification_status"], "NOT_STARTED")
        # Critical safety check: No action was executed automatically!
        self.assertEqual(len(res_m003["action_records"]), 0)
        self.assertIn("Operational Status**: Maintenance action pending human approval", res_m003["final_report"])

        # Healthy Machine M_001
        res_m001 = run_agent_workflow("M_001", "2023-01-01 00:00:00")
        self.assertEqual(res_m001["risk_level"], "LOW")
        self.assertIsNone(res_m001["notification_id"])
        self.assertEqual(res_m001["approval_status"], "NOT_REQUIRED")
        self.assertEqual(res_m001["verification_status"], "NOT_STARTED")

    def test_routing_consistency_low_medium_high(self):
        """
        Phase 3.1 Routing Consistency Test:
        1. LOW risk (M_001) routes directly to report, creating NO notification.
        2. MEDIUM risk (M_005) routes through investigation -> RCA -> impact -> decision -> notification,
           creating PENDING notification.
        3. HIGH risk (M_003) routes through investigation -> RCA -> impact -> decision -> notification,
           creating PENDING notification.
        4. No automatic action is executed in any scenario (action_records empty).
        """
        # 1. LOW Risk: M_001
        res_low = run_agent_workflow("M_001")
        self.assertEqual(res_low["risk_level"], "LOW")
        self.assertIsNone(res_low["notification_id"])
        self.assertEqual(res_low["approval_status"], "NOT_REQUIRED")
        self.assertEqual(len(res_low["action_records"]), 0)
        # Verify trace bypassed investigation
        trace_str = " -> ".join(res_low["agent_trace"])
        self.assertNotIn("Investigation Agent", trace_str)
        self.assertIn("Report Agent", trace_str)

        # 2. MEDIUM Risk: M_005
        res_med = run_agent_workflow("M_005")
        self.assertEqual(res_med["risk_level"], "MEDIUM")
        self.assertIsNotNone(res_med["notification_id"])
        self.assertEqual(res_med["approval_status"], "PENDING")
        self.assertEqual(res_med["verification_status"], "NOT_STARTED")
        self.assertEqual(len(res_med["action_records"]), 0)  # No auto action execution!
        # Verify trace went through complete diagnostic pipeline
        med_trace = " -> ".join(res_med["agent_trace"])
        self.assertIn("Investigation Agent", med_trace)
        self.assertIn("RCA Agent", med_trace)
        self.assertIn("Impact Agent", med_trace)
        self.assertIn("Decision Agent", med_trace)
        self.assertIn("Notification Agent", med_trace)
        self.assertIn("Verification Agent", med_trace)
        self.assertIn("Report Agent", med_trace)

        # 3. HIGH Risk: M_003
        res_high = run_agent_workflow("M_003", "2023-01-19 22:00:00")
        self.assertEqual(res_high["risk_level"], "HIGH")
        self.assertIsNotNone(res_high["notification_id"])
        self.assertEqual(res_high["approval_status"], "PENDING")
        self.assertEqual(res_high["verification_status"], "NOT_STARTED")
        self.assertEqual(len(res_high["action_records"]), 0)  # No auto action execution!
        high_trace = " -> ".join(res_high["agent_trace"])
        self.assertIn("Investigation Agent", high_trace)
        self.assertIn("Decision Agent", high_trace)
        self.assertIn("Notification Agent", high_trace)
        self.assertIn("Report Agent", high_trace)


if __name__ == "__main__":
    unittest.main()
