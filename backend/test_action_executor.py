"""
Unit Tests for Action Executor and Email Service (Phase 2)
==========================================================
Tests all Phase 2 requirements:
1. Inspection scheduling (software-only application record)
2. Maintenance ticket creation (maintenance_tickets.csv, status CREATED)
3. Replacement request creation (replacement_requests.csv, status DRAFTED)
4. Vendor lookup from configured CSV
5. Missing vendor handling (clean error, zero fabrication)
6. Mock email mode (clearly marked SIMULATED, no crashes)
7. Action record persistence (auditable action_records.csv)
8. Sequential action IDs (ACT-001, ACT-002, ACT-003)
9. Invalid action rejection
10. Missing notification rejection
11. Duplicate execution prevention (lifecycle protection)
12. Strict prohibition of physical machinery control operations
13. Approval Safety Gate (rejection without explicit human approval)
"""

import os
import sys
import tempfile
import shutil
import unittest

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import notification_service
from services import action_executor_service
from services import email_service


class TestActionExecutorService(unittest.TestCase):

    def setUp(self):
        # Create an isolated temporary data directory for tests
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
            title=f"Sample Alert {component}",
            message=f"Degradation in {component}",
            component=component,
            root_cause=root_cause,
            failure_probability=0.95,
            recommendation=f"Inspect and replace {component}",
            filepath=self.paths["notifications"]
        )

    def test_approval_safety_gate(self):
        """Action executor MUST refuse execution if explicit approval is missing or unapproved."""
        notif = self._create_sample_notification()

        # 1. Missing explicit approval flag
        res1 = action_executor_service.execute_action(
            action_type="schedule_inspection",
            notification_id=notif["notification_id"],
            explicit_approval=False,
            approved_by="Operator Jane",
            data_dir=self.test_dir
        )
        self.assertFalse(res1["success"])
        self.assertEqual(res1["error_code"], "APPROVAL_REQUIRED")

        # 2. Missing approver identity
        res2 = action_executor_service.execute_action(
            action_type="schedule_inspection",
            notification_id=notif["notification_id"],
            explicit_approval=True,
            approved_by="",
            data_dir=self.test_dir
        )
        self.assertFalse(res2["success"])
        self.assertEqual(res2["error_code"], "APPROVER_REQUIRED")

    def test_inspection_scheduling(self):
        """Inspection scheduling creates persistent software record without claiming physical repair."""
        notif = self._create_sample_notification(machine_id="M_003", component="Bearing")

        res = action_executor_service.execute_action(
            action_type="schedule_inspection",
            notification_id=notif["notification_id"],
            explicit_approval=True,
            approved_by="Chief Engineer Bob",
            priority="HIGH",
            data_dir=self.test_dir
        )

        self.assertTrue(res["success"])
        self.assertEqual(res["action_id"], "ACT-001")
        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(res["verification_status"], "VERIFICATION_PENDING")
        self.assertIn("Inspection scheduled successfully", res["result"])
        # Must not claim physical inspection happened
        self.assertNotIn("repaired", res["result"].lower())

        # Verify notification status transitioned
        updated_notif = notification_service.get_notification(notif["notification_id"], filepath=self.paths["notifications"])
        self.assertEqual(updated_notif["status"], "VERIFICATION_PENDING")

    def test_maintenance_ticket_creation(self):
        """Maintenance ticket creates an entry in maintenance_tickets.csv with CREATED status."""
        notif = self._create_sample_notification(machine_id="M_001", component="Motor")

        res = action_executor_service.execute_action(
            action_type="create_maintenance_ticket",
            notification_id=notif["notification_id"],
            explicit_approval=True,
            approved_by="Planner Dave",
            priority="HIGH",
            reason="Thermal stress check",
            data_dir=self.test_dir
        )

        self.assertTrue(res["success"])
        self.assertEqual(res["action_id"], "ACT-001")
        self.assertIn("TCK-001", res["result"])

        # Check maintenance_tickets.csv
        tickets = []
        import csv
        with open(self.paths["maintenance_tickets"], "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            tickets = list(reader)

        self.assertEqual(len(tickets), 1)
        self.assertEqual(tickets[0]["ticket_id"], "TCK-001")
        self.assertEqual(tickets[0]["machine_id"], "M_001")
        self.assertEqual(tickets[0]["component"], "Motor")
        self.assertEqual(tickets[0]["status"], "CREATED")

    def test_replacement_request_creation(self):
        """Replacement request writes to replacement_requests.csv using configured vendor data."""
        notif = self._create_sample_notification(machine_id="M_003", component="Bearing")

        res = action_executor_service.execute_action(
            action_type="create_replacement_request",
            notification_id=notif["notification_id"],
            explicit_approval=True,
            approved_by="Procurement Lead Sarah",
            priority="CRITICAL",
            quantity=2,
            data_dir=self.test_dir
        )

        self.assertTrue(res["success"])
        self.assertEqual(res["action_id"], "ACT-001")
        self.assertIn("REQ-001", res["result"])

        import csv
        with open(self.paths["replacement_requests"], "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            requests = list(reader)

        self.assertEqual(len(requests), 1)
        req = requests[0]
        self.assertEqual(req["request_id"], "REQ-001")
        self.assertEqual(req["machine_id"], "M_003")
        self.assertEqual(req["part_name"], "Bearing")
        self.assertEqual(req["part_number"], "BRG-6205")
        self.assertEqual(req["vendor_id"], "V001")
        self.assertEqual(req["status"], "DRAFTED")
        self.assertEqual(req["quantity"], "2")

    def test_vendor_lookup(self):
        """Configured demo vendors are correctly identified for known components."""
        v_bearing = notification_service.find_vendor_by_component("Bearing", filepath=self.paths["vendors"])
        self.assertIsNotNone(v_bearing)
        self.assertEqual(v_bearing["vendor_id"], "V001")
        self.assertEqual(v_bearing["part_number"], "BRG-6205")

        v_motor = notification_service.find_vendor_by_component("Motor", filepath=self.paths["vendors"])
        self.assertIsNotNone(v_motor)
        self.assertEqual(v_motor["vendor_id"], "V002")
        self.assertEqual(v_motor["part_number"], "MTR-440V-75KW")

    def test_missing_vendor_handling(self):
        """Attempting to request replacement for an unconfigured component fails cleanly without hallucinating."""
        notif = self._create_sample_notification(
            machine_id="M_003",
            component="UnconfiguredPlasmaTorch",
            root_cause="Plasma Arc Breakdown"
        )

        res = action_executor_service.execute_action(
            action_type="create_replacement_request",
            notification_id=notif["notification_id"],
            explicit_approval=True,
            approved_by="Buyer Mike",
            data_dir=self.test_dir
        )

        self.assertFalse(res["success"])
        self.assertEqual(res["error_code"], "VENDOR_NOT_FOUND")
        self.assertEqual(
            res["error"],
            "Replacement request could not be created because no configured vendor was found."
        )

    def test_mock_email_mode(self):
        """When SMTP env vars are absent, vendor email generates safe SIMULATED message."""
        # Ensure SMTP env vars are unset
        for k in ["SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "SENDER_EMAIL"]:
            os.environ.pop(k, None)

        notif = self._create_sample_notification(machine_id="M_003", component="Bearing")

        res = action_executor_service.execute_action(
            action_type="send_vendor_email",
            notification_id=notif["notification_id"],
            explicit_approval=True,
            approved_by="Manager Lisa",
            data_dir=self.test_dir
        )

        self.assertTrue(res["success"])
        self.assertEqual(res["action_id"], "ACT-001")
        self.assertIn("SIMULATED", res["result"])

        # Check details from email service
        email_info = res["details"]
        self.assertTrue(email_info["is_simulated"])
        self.assertEqual(email_info["email_status"], "SIMULATED")
        self.assertEqual(email_info["recipient"], "demo-bearings@example.com")
        self.assertEqual(email_info["subject"], "Urgent Replacement Request — M_003 — Bearing")
        self.assertIn("BRG-6205", email_info["body"])
        self.assertIn("Dear Vendor", email_info["body"])

    def test_action_record_persistence(self):
        """Every executed action produces an auditable record in action_records.csv."""
        notif = self._create_sample_notification(machine_id="M_003", component="Bearing")

        action_executor_service.execute_action(
            action_type="schedule_inspection",
            notification_id=notif["notification_id"],
            explicit_approval=True,
            approved_by="Auditor Gary",
            priority="HIGH",
            reason="Vibration spike verified",
            data_dir=self.test_dir
        )

        records = action_executor_service.get_action_records(data_dir=self.test_dir)
        self.assertEqual(len(records), 1)
        r = records[0]
        self.assertEqual(r["action_id"], "ACT-001")
        self.assertEqual(r["notification_id"], notif["notification_id"])
        self.assertEqual(r["machine_id"], "M_003")
        self.assertEqual(r["action_type"], "schedule_inspection")
        self.assertEqual(r["component"], "Bearing")
        self.assertEqual(r["priority"], "HIGH")
        self.assertEqual(r["status"], "COMPLETED")
        self.assertTrue(len(r["approved_at"]) > 0)
        self.assertTrue(len(r["completed_at"]) > 0)
        self.assertEqual(r["verification_status"], "VERIFICATION_PENDING")

    def test_sequential_action_ids(self):
        """Action IDs increment sequentially: ACT-001, ACT-002, ACT-003 without collision."""
        n1 = self._create_sample_notification(machine_id="M_001", component="Bearing")
        n2 = self._create_sample_notification(machine_id="M_002", component="Motor")
        n3 = self._create_sample_notification(machine_id="M_004", component="Cooling Pump")

        r1 = action_executor_service.execute_action(
            action_type="schedule_inspection",
            notification_id=n1["notification_id"],
            explicit_approval=True,
            approved_by="Operator A",
            data_dir=self.test_dir
        )
        r2 = action_executor_service.execute_action(
            action_type="create_maintenance_ticket",
            notification_id=n2["notification_id"],
            explicit_approval=True,
            approved_by="Operator B",
            data_dir=self.test_dir
        )
        r3 = action_executor_service.execute_action(
            action_type="create_alert",
            notification_id=n3["notification_id"],
            explicit_approval=True,
            approved_by="Operator C",
            data_dir=self.test_dir
        )

        self.assertEqual(r1["action_id"], "ACT-001")
        self.assertEqual(r2["action_id"], "ACT-002")
        self.assertEqual(r3["action_id"], "ACT-003")

    def test_invalid_action_rejection(self):
        """Non-allowed action types are cleanly rejected."""
        notif = self._create_sample_notification()

        res = action_executor_service.execute_action(
            action_type="teleport_replacement_part",
            notification_id=notif["notification_id"],
            explicit_approval=True,
            approved_by="Tester",
            data_dir=self.test_dir
        )

        self.assertFalse(res["success"])
        self.assertEqual(res["error_code"], "INVALID_ACTION_TYPE")

    def test_missing_notification_rejection(self):
        """Executing an action against a non-existent notification ID fails cleanly."""
        res = action_executor_service.execute_action(
            action_type="schedule_inspection",
            notification_id="NTF-9999",
            explicit_approval=True,
            approved_by="Tester",
            data_dir=self.test_dir
        )

        self.assertFalse(res["success"])
        self.assertEqual(res["error_code"], "NOTIFICATION_NOT_FOUND")

    def test_duplicate_execution_prevention(self):
        """Notifications that are already ACTION_IN_PROGRESS, COMPLETED, or VERIFICATION_PENDING cannot be re-executed."""
        notif = self._create_sample_notification(machine_id="M_003", component="Bearing")

        # First execution succeeds
        r1 = action_executor_service.execute_action(
            action_type="schedule_inspection",
            notification_id=notif["notification_id"],
            explicit_approval=True,
            approved_by="Engineer 1",
            data_dir=self.test_dir
        )
        self.assertTrue(r1["success"])

        # Second execution on same notification is blocked
        r2 = action_executor_service.execute_action(
            action_type="schedule_inspection",
            notification_id=notif["notification_id"],
            explicit_approval=True,
            approved_by="Engineer 2",
            data_dir=self.test_dir
        )
        self.assertFalse(r2["success"])
        self.assertEqual(r2["error_code"], "ALREADY_PROCESSED")
        self.assertIn("Duplicate execution is prevented", r2["error"])

    def test_no_physical_control_operation_exists(self):
        """Any attempt to execute physical machinery control (PLC, motor, shutdown, breakers) is blocked by safety gate."""
        notif = self._create_sample_notification()

        dangerous_actions = [
            "shutdown_machine_now",
            "plc_trip_relay",
            "emergency_stop_actuator",
            "motor_control_speed",
            "valve_close_hydraulic"
        ]

        for danger in dangerous_actions:
            res = action_executor_service.execute_action(
                action_type=danger,
                notification_id=notif["notification_id"],
                explicit_approval=True,
                approved_by="Unauthorized Agent",
                data_dir=self.test_dir
            )
            self.assertFalse(res["success"], f"Action '{danger}' should have been rejected!")
            self.assertEqual(res["error_code"], "PHYSICAL_CONTROL_PROHIBITED")
            self.assertIn("Physical machinery control", res["error"])

    def test_update_machine_status_non_invasive(self):
        """Updating machine action status updates application status registry without altering ML models or risk states."""
        notif = self._create_sample_notification(machine_id="M_003", component="Bearing")

        res = action_executor_service.execute_action(
            action_type="update_machine_status",
            notification_id=notif["notification_id"],
            explicit_approval=True,
            approved_by="Floor Supervisor",
            notes="MAINTENANCE_SCHEDULED",
            data_dir=self.test_dir
        )

        self.assertTrue(res["success"])
        self.assertEqual(res["action_id"], "ACT-001")
        self.assertIn("MAINTENANCE_SCHEDULED", res["result"])


if __name__ == "__main__":
    unittest.main()
