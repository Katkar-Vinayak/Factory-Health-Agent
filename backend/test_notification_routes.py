"""
Comprehensive REST API Integration Tests for Notifications & HITL (Phase 4)
=============================================================================
Tests all Phase 4 requirements:
1. GET /api/notifications (retrieval & filtering)
2. GET /api/notifications/{id} (single notification)
3. Invalid notification ID -> HTTP 404
4. Accept without explicit approval -> HTTP 400
5. Accept without approver identity -> HTTP 400/422
6. Valid accept workflow
7. Valid action execution upon acceptance
8. Multiple approved actions executed in sequence
9. Duplicate accept attempt -> HTTP 409 Conflict
10. Valid reject workflow
11. Reject with reason preserved
12. Duplicate reject attempt -> HTTP 409 Conflict
13. Reject does NOT execute any software action
14. Action history retrieval (GET /api/notifications/actions/history)
15. Physical control action attempt -> HTTP 400 blocked
16. Missing vendor handling in replacement actions -> safe structured response
17. Existing POST /api/agent/analyze endpoint compatibility
18. LOW machine (M_001) produces no unnecessary notification
19. MEDIUM machine (M_005) notification can be accepted
20. HIGH machine (M_003) notification can be accepted
"""

import os
import sys
import unittest
from fastapi.testclient import TestClient

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.main import app
from services import notification_service
from services import action_executor_service


class TestNotificationRoutes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        cls.backup_files = {}

        # Backup CSV files to isolate route tests and restore pristine state on completion
        for fname in [
            "notifications.csv",
            "action_records.csv",
            "maintenance_tickets.csv",
            "replacement_requests.csv",
            "alerts.csv",
            "machine_action_status.csv"
        ]:
            fpath = os.path.join(cls.data_dir, fname)
            if os.path.exists(fpath):
                with open(fpath, "r", encoding="utf-8") as f:
                    cls.backup_files[fpath] = f.read()
                # Clear content keeping only header line
                lines = cls.backup_files[fpath].splitlines()
                header = lines[0] if lines else ""
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(header + "\n")

    @classmethod
    def tearDownClass(cls):
        # Restore original CSV file states
        for fpath, content in cls.backup_files.items():
            try:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception:
                pass

    def test_01_get_notifications(self):
        """GET /api/notifications returns list of unresolved notifications with count."""
        # Create a pending notification
        notification_service.create_notification(
            machine_id="M_011",
            severity="HIGH",
            title="Initial Test Alert",
            message="Bearing anomaly",
            component="Bearing",
            root_cause="Bearing Degradation",
            failure_probability=0.88,
            recommendation="Inspect bearing"
        )

        res = self.client.get("/api/notifications")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("notifications", data)
        self.assertIn("count", data)
        self.assertIsInstance(data["notifications"], list)
        self.assertGreaterEqual(data["count"], 1)

    def test_02_get_single_notification(self):
        """GET /api/notifications/{id} returns the specific notification."""
        notif = notification_service.create_notification(
            machine_id="M_012",
            severity="HIGH",
            title="Single Notification Test",
            message="Thermal alert",
            component="Motor",
            root_cause="Motor Overheating",
            failure_probability=0.79,
            recommendation="Inspect cooling fan"
        )
        nid = notif["notification_id"]

        res = self.client.get(f"/api/notifications/{nid}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["notification_id"], nid)
        self.assertEqual(data["machine_id"], "M_012")
        self.assertEqual(data["severity"], "HIGH")

    def test_03_invalid_notification_404(self):
        """GET /api/notifications/NTF-9999 returns HTTP 404."""
        res = self.client.get("/api/notifications/NTF-9999")
        self.assertEqual(res.status_code, 404)
        self.assertIn("not found", res.json()["detail"].lower())

    def test_04_accept_without_explicit_approval_rejected(self):
        """POST /accept with explicit_approval=False returns HTTP 400."""
        notif = notification_service.create_notification(
            machine_id="M_013",
            severity="HIGH",
            title="Unapproved Action Alert",
            message="Bearing anomaly",
            component="Bearing",
            root_cause="Bearing Degradation",
            failure_probability=0.85,
            recommendation="Inspect bearing"
        )
        nid = notif["notification_id"]

        payload = {
            "explicit_approval": False,
            "approved_by": "operator_alice",
            "approved_actions": ["schedule_inspection"]
        }
        res = self.client.post(f"/api/notifications/{nid}/accept", json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("explicit human approval", res.json()["detail"].lower())

    def test_05_accept_without_approver_identity_rejected(self):
        """POST /accept with empty approved_by returns HTTP 400 or 422."""
        notif = notification_service.create_notification(
            machine_id="M_014",
            severity="HIGH",
            title="Approver Check Alert",
            message="Bearing anomaly",
            component="Bearing",
            root_cause="Bearing Degradation",
            failure_probability=0.85,
            recommendation="Inspect bearing"
        )
        nid = notif["notification_id"]

        payload = {
            "explicit_approval": True,
            "approved_by": "   ",
            "approved_actions": ["schedule_inspection"]
        }
        res = self.client.post(f"/api/notifications/{nid}/accept", json=payload)
        self.assertIn(res.status_code, (400, 422))

    def test_06_valid_accept(self):
        """POST /accept successfully approves a pending notification."""
        notif = notification_service.create_notification(
            machine_id="M_015",
            severity="HIGH",
            title="Hydraulic Alert 1",
            message="Pressure dip detected",
            component="Hydraulic Valve",
            root_cause="Hydraulic Pressure Failure",
            failure_probability=0.88,
            recommendation="Inspect valve manifold"
        )
        nid = notif["notification_id"]

        payload = {
            "explicit_approval": True,
            "approved_by": "operator_bob",
            "approved_actions": ["schedule_inspection"]
        }
        res = self.client.post(f"/api/notifications/{nid}/accept", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["notification_id"], nid)
        self.assertEqual(data["status"], "VERIFICATION_PENDING")
        self.assertEqual(data["approved_by"], "operator_bob")

    def test_07_valid_accepted_action_execution(self):
        """Accepted action executes and produces auditable action records."""
        notif = notification_service.create_notification(
            machine_id="M_016",
            severity="HIGH",
            title="Hydraulic Alert 2",
            message="Pressure dip check",
            component="Hydraulic Valve",
            root_cause="Hydraulic Pressure Failure",
            failure_probability=0.88,
            recommendation="Inspect valve manifold"
        )
        nid = notif["notification_id"]

        payload = {
            "explicit_approval": True,
            "approved_by": "operator_bob",
            "approved_actions": ["schedule_inspection"]
        }
        res = self.client.post(f"/api/notifications/{nid}/accept", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data["actions"]), 1)
        self.assertTrue(data["actions"][0]["success"])
        self.assertEqual(data["actions"][0]["action_type"], "schedule_inspection")

        records = action_executor_service.get_action_records(notification_id=nid)
        self.assertGreaterEqual(len(records), 1)

    def test_08_multiple_approved_actions(self):
        """POST /accept executes multiple selected actions sequentially."""
        notif = notification_service.create_notification(
            machine_id="M_017",
            severity="HIGH",
            title="Motor Thermal Alert",
            message="Temperature elevated",
            component="Motor",
            root_cause="Motor Overheating",
            failure_probability=0.85,
            recommendation="Inspect motor and prepare replacement"
        )
        nid = notif["notification_id"]

        payload = {
            "explicit_approval": True,
            "approved_by": "maintenance_lead",
            "approved_actions": [
                "schedule_inspection",
                "create_maintenance_ticket",
                "create_replacement_request"
            ]
        }
        res = self.client.post(f"/api/notifications/{nid}/accept", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data["actions"]), 3)
        action_types = [a["action_type"] for a in data["actions"]]
        self.assertIn("schedule_inspection", action_types)
        self.assertIn("create_maintenance_ticket", action_types)
        self.assertIn("create_replacement_request", action_types)
        for a in data["actions"]:
            self.assertTrue(a["success"])

    def test_09_duplicate_accept_blocked_409(self):
        """A second acceptance attempt on an already processed notification returns HTTP 409 Conflict."""
        notif = notification_service.create_notification(
            machine_id="M_018",
            severity="HIGH",
            title="Duplicate Accept Check",
            message="Bearing wear",
            component="Bearing",
            root_cause="Bearing Degradation",
            failure_probability=0.90,
            recommendation="Inspect bearing"
        )
        target_nid = notif["notification_id"]

        # First accept succeeds
        p1 = {
            "explicit_approval": True,
            "approved_by": "operator_charlie",
            "approved_actions": ["schedule_inspection"]
        }
        r1 = self.client.post(f"/api/notifications/{target_nid}/accept", json=p1)
        self.assertEqual(r1.status_code, 200)

        # Second accept returns 409 Conflict
        r2 = self.client.post(f"/api/notifications/{target_nid}/accept", json=p1)
        self.assertEqual(r2.status_code, 409)
        self.assertIn("duplicate acceptance prevented", r2.json()["detail"].lower())

    def test_10_valid_reject(self):
        """POST /reject transitions notification to REJECTED."""
        notif = notification_service.create_notification(
            machine_id="M_019",
            severity="MEDIUM",
            title="Packaging Anomaly 1",
            message="Minor conveyor friction",
            component="Cooling Pump",
            root_cause="Cooling System Failure",
            failure_probability=0.45,
            recommendation="Inspect pump"
        )
        nid = notif["notification_id"]

        res = self.client.post(f"/api/notifications/{nid}/reject", json={"rejected_by": "supervisor_dave"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["notification_id"], nid)
        self.assertEqual(data["status"], "REJECTED")

    def test_11_reject_with_reason(self):
        """POST /reject preserves rejection reason."""
        notif = notification_service.create_notification(
            machine_id="M_020",
            severity="MEDIUM",
            title="Packaging Anomaly 2",
            message="Minor conveyor friction",
            component="Cooling Pump",
            root_cause="Cooling System Failure",
            failure_probability=0.45,
            recommendation="Inspect pump"
        )
        nid = notif["notification_id"]

        payload = {
            "rejected_by": "supervisor_dave",
            "rejection_reason": "Scheduled downtime planned for tomorrow morning."
        }
        res = self.client.post(f"/api/notifications/{nid}/reject", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("Scheduled downtime", data["rejection_reason"])

        updated = notification_service.get_notification(nid)
        self.assertEqual(updated["status"], "REJECTED")

    def test_12_duplicate_reject_blocked_409(self):
        """A second rejection attempt on an already rejected notification returns HTTP 409 Conflict."""
        notif = notification_service.create_notification(
            machine_id="M_021",
            severity="MEDIUM",
            title="Repeat Reject Test",
            message="Cooling issue",
            component="Cooling Pump",
            root_cause="Cooling System Failure",
            failure_probability=0.42,
            recommendation="Inspect pump"
        )
        target_nid = notif["notification_id"]

        # First reject
        r1 = self.client.post(f"/api/notifications/{target_nid}/reject", json={"rejected_by": "supervisor_dave"})
        self.assertEqual(r1.status_code, 200)

        # Second reject
        r2 = self.client.post(f"/api/notifications/{target_nid}/reject", json={"rejected_by": "supervisor_dave"})
        self.assertEqual(r2.status_code, 409)
        self.assertIn("already been rejected", r2.json()["detail"].lower())

    def test_13_reject_does_not_execute_actions(self):
        """Rejection produces zero records in action_records.csv for that notification."""
        notif = notification_service.create_notification(
            machine_id="M_022",
            severity="MEDIUM",
            title="Spindle Alert",
            message="Minor heat",
            component="Motor",
            root_cause="Motor Overheating",
            failure_probability=0.42,
            recommendation="Check ventilation"
        )
        nid = notif["notification_id"]

        self.client.post(f"/api/notifications/{nid}/reject", json={"rejected_by": "op_test"})

        records = action_executor_service.get_action_records(notification_id=nid)
        self.assertEqual(len(records), 0)

    def test_14_action_history_retrieval(self):
        """GET /api/notifications/actions/history returns action audit trail."""
        res = self.client.get("/api/notifications/actions/history")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("actions", data)
        self.assertIn("count", data)
        self.assertGreaterEqual(data["count"], 1)

    def test_15_physical_control_blocked_400(self):
        """Attempting to accept physical machinery commands returns HTTP 400."""
        notif = notification_service.create_notification(
            machine_id="M_023",
            severity="HIGH",
            title="Physical Control Attempt Alert",
            message="Bearing anomaly",
            component="Bearing",
            root_cause="Bearing Degradation",
            failure_probability=0.89,
            recommendation="Inspect bearing"
        )
        nid = notif["notification_id"]

        payload = {
            "explicit_approval": True,
            "approved_by": "rogue_operator",
            "approved_actions": ["shutdown_machine", "plc_trip_relay"]
        }
        res = self.client.post(f"/api/notifications/{nid}/accept", json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("physical machinery control", res.json()["detail"].lower())

    def test_16_missing_vendor_safe_failure(self):
        """If a replacement action has no configured vendor, it returns safe failure without crashing."""
        notif = notification_service.create_notification(
            machine_id="M_024",
            severity="HIGH",
            title="Unconfigured Subsystem",
            message="Unknown part anomaly",
            component="ExoticLaserDiode",
            root_cause="Laser Degradation",
            failure_probability=0.75,
            recommendation="Replace diode"
        )
        nid = notif["notification_id"]

        payload = {
            "explicit_approval": True,
            "approved_by": "lead_tech",
            "approved_actions": ["create_replacement_request"]
        }
        res = self.client.post(f"/api/notifications/{nid}/accept", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data["actions"]), 1)
        self.assertFalse(data["actions"][0]["success"])
        self.assertIn("no configured vendor was found", data["actions"][0]["result"].lower())

    def test_17_existing_agent_analyze_still_works(self):
        """POST /api/agent/analyze remains operational and returns HITL fields."""
        res = self.client.post("/api/agent/analyze", json={"machine_id": "M_001"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["machine_id"], "M_001")
        self.assertEqual(data["risk_level"], "LOW")
        self.assertIn("notification_id", data)
        self.assertIn("approval_status", data)
        self.assertEqual(data["approval_status"], "NOT_REQUIRED")

    def test_18_low_machine_produces_no_notification(self):
        """LOW machine (M_001) produces no notification_id and approval_status NOT_REQUIRED."""
        res = self.client.post("/api/agent/analyze", json={"machine_id": "M_001"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIsNone(data["notification_id"])
        self.assertEqual(data["approval_status"], "NOT_REQUIRED")

    def test_19_medium_notification_can_be_accepted(self):
        """MEDIUM machine (M_005) produces PENDING notification that can be accepted via API."""
        analyze_res = self.client.post("/api/agent/analyze", json={"machine_id": "M_005"})
        self.assertEqual(analyze_res.status_code, 200)
        data = analyze_res.json()
        self.assertEqual(data["risk_level"], "MEDIUM")
        nid = data["notification_id"]
        self.assertIsNotNone(nid)

        accept_res = self.client.post(f"/api/notifications/{nid}/accept", json={
            "explicit_approval": True,
            "approved_by": "operator_m005",
            "approved_actions": ["schedule_inspection"]
        })
        self.assertEqual(accept_res.status_code, 200)
        self.assertEqual(accept_res.json()["status"], "VERIFICATION_PENDING")

    def test_20_high_m003_notification_can_be_accepted(self):
        """HIGH machine (M_003) produces PENDING notification that can be accepted via API."""
        analyze_res = self.client.post("/api/agent/analyze", json={
            "machine_id": "M_003",
            "timestamp": "2023-01-19 22:00:00"
        })
        self.assertEqual(analyze_res.status_code, 200)
        data = analyze_res.json()
        self.assertEqual(data["risk_level"], "HIGH")
        nid = data["notification_id"]
        self.assertIsNotNone(nid)

        accept_res = self.client.post(f"/api/notifications/{nid}/accept", json={
            "explicit_approval": True,
            "approved_by": "chief_reliability_engineer",
            "approved_actions": ["schedule_inspection", "create_replacement_request"]
        })
        self.assertEqual(accept_res.status_code, 200)
        self.assertEqual(accept_res.json()["status"], "VERIFICATION_PENDING")
        self.assertEqual(len(accept_res.json()["actions"]), 2)


if __name__ == "__main__":
    unittest.main()
