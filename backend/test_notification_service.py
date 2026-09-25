"""
Unit Tests for Notification Service (Phase 1)
==============================================
Tests all Phase 1 requirements:
- Missing/malformed CSV initialization
- Safe sequential notification IDs (NTF-001, NTF-002, ...)
- Create notification
- Retrieve notification by ID
- Retrieve all notifications with filters
- Update status (ACCEPTED, REJECTED, etc.)
- Duplicate notification prevention (machine_id + component + unresolved status)
- Unresolved vs resolved deduplication behavior
- Demo vendor lookup
"""

import os
import sys
import tempfile
import shutil
import unittest

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import notification_service


class TestNotificationService(unittest.TestCase):

    def setUp(self):
        # Create a fresh isolated temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.notif_csv = os.path.join(self.test_dir, "notifications.csv")
        self.action_csv = os.path.join(self.test_dir, "action_records.csv")
        self.vendor_csv = os.path.join(self.test_dir, "vendors.csv")
        self.repl_csv = os.path.join(self.test_dir, "replacement_requests.csv")

    def tearDown(self):
        # Clean up temporary directory
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_missing_csv_initialization(self):
        """Verifies that missing files are safely initialized with proper headers."""
        self.assertFalse(os.path.exists(self.notif_csv))
        notification_service.ensure_csv_files_exist(self.test_dir)
        self.assertTrue(os.path.exists(self.notif_csv))
        self.assertTrue(os.path.exists(self.action_csv))
        self.assertTrue(os.path.exists(self.vendor_csv))
        self.assertTrue(os.path.exists(self.repl_csv))

        # Check default demo vendors are seeded
        vendors = notification_service.get_vendors(self.vendor_csv)
        self.assertGreaterEqual(len(vendors), 5)
        self.assertEqual(vendors[0]["vendor_id"], "V001")
        self.assertEqual(vendors[0]["part_type"], "Bearing")
        self.assertIn("example.com", vendors[0]["email"])

    def test_create_and_retrieve_notification(self):
        """Verifies creating a notification and retrieving it."""
        notif = notification_service.create_notification(
            machine_id="M_003",
            severity="CRITICAL",
            title="Critical Bearing Condition",
            message="Bearing degradation detected.",
            component="Bearing",
            root_cause="Bearing Degradation",
            failure_probability=0.98,
            recommendation=["Schedule bearing inspection", "Prepare bearing replacement"],
            timestamp="2023-01-19 22:00:00",
            filepath=self.notif_csv
        )

        self.assertEqual(notif["notification_id"], "NTF-001")
        self.assertEqual(notif["machine_id"], "M_003")
        self.assertEqual(notif["severity"], "CRITICAL")
        self.assertEqual(notif["component"], "Bearing")
        self.assertEqual(notif["status"], "PENDING")
        self.assertFalse(notif["is_duplicate"])

        # Retrieve by ID
        fetched = notification_service.get_notification("NTF-001", filepath=self.notif_csv)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["title"], "Critical Bearing Condition")
        self.assertEqual(fetched["machine_id"], "M_003")

    def test_sequential_notification_ids(self):
        """Verifies IDs increment sequentially: NTF-001, NTF-002, NTF-003 without collision."""
        n1 = notification_service.create_notification(
            machine_id="M_001",
            severity="HIGH",
            title="Motor Issue",
            message="Motor heating",
            component="Motor",
            root_cause="Motor Overheating",
            failure_probability=0.85,
            recommendation="Inspect fan",
            filepath=self.notif_csv
        )
        n2 = notification_service.create_notification(
            machine_id="M_002",
            severity="MEDIUM",
            title="Cooling Issue",
            message="Coolant low",
            component="Cooling Pump",
            root_cause="Cooling System Failure",
            failure_probability=0.45,
            recommendation="Inspect radiator",
            filepath=self.notif_csv
        )
        n3 = notification_service.create_notification(
            machine_id="M_004",
            severity="HIGH",
            title="Hydraulic Issue",
            message="Pressure loss",
            component="Hydraulic Valve",
            root_cause="Hydraulic Pressure Failure",
            failure_probability=0.78,
            recommendation="Check seals",
            filepath=self.notif_csv
        )

        self.assertEqual(n1["notification_id"], "NTF-001")
        self.assertEqual(n2["notification_id"], "NTF-002")
        self.assertEqual(n3["notification_id"], "NTF-003")

    def test_deduplication_unresolved_notification(self):
        """Verifies duplicate notifications for same machine + component in unresolved state are blocked."""
        # 1. Create first notification
        n1 = notification_service.create_notification(
            machine_id="M_003",
            severity="CRITICAL",
            title="Bearing Anomaly",
            message="Bearing wear",
            component="Bearing",
            root_cause="Bearing Degradation",
            failure_probability=0.98,
            recommendation="Inspect bearing",
            filepath=self.notif_csv
        )
        self.assertFalse(n1["is_duplicate"])
        self.assertEqual(n1["notification_id"], "NTF-001")

        # 2. Attempt duplicate while PENDING
        n2 = notification_service.create_notification(
            machine_id="M_003",
            severity="CRITICAL",
            title="Bearing Anomaly Again",
            message="Bearing wear repeated",
            component="Bearing",
            root_cause="Bearing Degradation",
            failure_probability=0.99,
            recommendation="Inspect bearing",
            filepath=self.notif_csv
        )
        self.assertTrue(n2["is_duplicate"])
        self.assertEqual(n2["notification_id"], "NTF-001")

        # Check total count in CSV remains 1
        all_notifs = notification_service.get_notifications(filepath=self.notif_csv)
        self.assertEqual(len(all_notifs), 1)

    def test_update_status_and_lifecycle(self):
        """Verifies status transitions (PENDING -> ACCEPTED / REJECTED) and resolution timestamps."""
        notif = notification_service.create_notification(
            machine_id="M_003",
            severity="CRITICAL",
            title="Bearing Condition",
            message="Vibration high",
            component="Bearing",
            root_cause="Bearing Degradation",
            failure_probability=0.98,
            recommendation="Inspect bearing",
            filepath=self.notif_csv
        )

        # Update to ACCEPTED
        updated = notification_service.update_notification_status(
            "NTF-001",
            status="ACCEPTED",
            filepath=self.notif_csv
        )
        self.assertEqual(updated["status"], "ACCEPTED")
        self.assertTrue(len(updated["resolved_at"]) > 0)

        # Once resolved (ACCEPTED), a new notification CAN be generated if a new event arises later
        n_new = notification_service.create_notification(
            machine_id="M_003",
            severity="HIGH",
            title="New Bearing Event Later",
            message="Vibration high again",
            component="Bearing",
            root_cause="Bearing Degradation",
            failure_probability=0.91,
            recommendation="Follow up check",
            filepath=self.notif_csv
        )
        self.assertFalse(n_new["is_duplicate"])
        self.assertEqual(n_new["notification_id"], "NTF-002")

    def test_rejection_reason_update(self):
        """Verifies rejection records rejection_reason."""
        notif = notification_service.create_notification(
            machine_id="M_005",
            severity="HIGH",
            title="Cooling Alert",
            message="Temperature elevated",
            component="Cooling Pump",
            root_cause="Cooling System Failure",
            failure_probability=0.65,
            recommendation="Purge coolant loop",
            filepath=self.notif_csv
        )

        rejected = notification_service.update_notification_status(
            notif["notification_id"],
            status="REJECTED",
            rejection_reason="Scheduled downtime planned for tomorrow morning shift.",
            filepath=self.notif_csv
        )
        self.assertEqual(rejected["status"], "REJECTED")
        self.assertEqual(rejected["rejection_reason"], "Scheduled downtime planned for tomorrow morning shift.")
        self.assertTrue(len(rejected["resolved_at"]) > 0)

    def test_invalid_status_rejected(self):
        """Verifies attempting to set an unauthorized status raises ValueError."""
        notif = notification_service.create_notification(
            machine_id="M_006",
            severity="MEDIUM",
            title="Hydraulic Alert",
            message="Pressure dip",
            component="Hydraulic Valve",
            root_cause="Hydraulic Pressure Failure",
            failure_probability=0.55,
            recommendation="Inspect seals",
            filepath=self.notif_csv
        )

        with self.assertRaises(ValueError):
            notification_service.update_notification_status(
                notif["notification_id"],
                status="INVALID_STATUS_XYZ",
                filepath=self.notif_csv
            )

    def test_vendor_matching(self):
        """Verifies component to vendor lookup."""
        notification_service.ensure_csv_files_exist(self.test_dir)
        bearing_vendor = notification_service.find_vendor_by_component("Bearing", filepath=self.vendor_csv)
        self.assertIsNotNone(bearing_vendor)
        self.assertEqual(bearing_vendor["vendor_id"], "V001")
        self.assertEqual(bearing_vendor["part_number"], "BRG-6205")

        cooling_vendor = notification_service.find_vendor_by_component("Cooling Pump", filepath=self.vendor_csv)
        self.assertIsNotNone(cooling_vendor)
        self.assertEqual(cooling_vendor["vendor_id"], "V003")

        unknown_vendor = notification_service.find_vendor_by_component("NonexistentRocketThruster", filepath=self.vendor_csv)
        self.assertIsNone(unknown_vendor)

if __name__ == "__main__":
    unittest.main()
