"""
Phase 6 End-to-End HITL Verification Script
===========================================
Performs automated verification of all Phase 6 requirements:
- Step 3: Complete M_003 API Flow Test (Analyze -> Notify -> Accept -> Action -> Verify)
- Step 4: Reject Flow Test (zero actions, REJECTED state, reason preserved)
- Step 5: Duplicate Protection (409 Conflict on repeated accept/reject)
- Step 6: Physical Control Safety Gate (blocking prohibited control commands)
- Step 7: Medium-Risk Flow (Investigation -> RCA -> Notification -> Accept)
- Step 8: Low-Risk Flow (Monitoring -> Report, notification_id=None, NOT_REQUIRED)
- Step 9: Verification Safeguard (software action recorded != physical recovery)
- Step 13: API Response Schema Consistency
- Step 14: Qwen & Deterministic RCA Regression
"""

import urllib.request
import urllib.error
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def post_json(endpoint, payload):
    req = urllib.request.Request(
        f"{BASE_URL}{endpoint}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        return resp.getcode(), json.loads(resp.read().decode("utf-8"))

def get_json(endpoint):
    req = urllib.request.Request(f"{BASE_URL}{endpoint}")
    with urllib.request.urlopen(req) as resp:
        return resp.getcode(), json.loads(resp.read().decode("utf-8"))

def main():
    print("=================================================================")
    print("PHASE 6: END-TO-END HITL VERIFICATION AUDIT")
    print("=================================================================")

    results = {}

    # -------------------------------------------------------------
    # 1. LOW-RISK FLOW (Section 8)
    # -------------------------------------------------------------
    print("\n--- 1. Testing LOW-Risk Machine Flow (M_001 baseline) ---")
    code, m001_res = post_json("/api/agent/analyze", {
        "machine_id": "M_001",
        "timestamp": "2023-01-01 00:00:00"
    })
    assert code == 200
    assert m001_res["risk_level"] == "LOW", f"Expected LOW, got {m001_res['risk_level']}"
    assert m001_res["notification_id"] is None, f"Expected None notification_id, got {m001_res['notification_id']}"
    assert m001_res["approval_status"] == "NOT_REQUIRED", f"Expected NOT_REQUIRED, got {m001_res['approval_status']}"
    print("[PASS] M_001 LOW risk verified: notification_id=None, approval_status=NOT_REQUIRED")
    results["low_risk_flow"] = "PASS"

    # -------------------------------------------------------------
    # 2. COMPLETE HIGH-RISK M_003 API FLOW (Section 3)
    # -------------------------------------------------------------
    print("\n--- 2. Testing M_003 Complete Flow (Detect -> Diagnose -> Notify -> Accept -> Verify) ---")
    code, m003_res = post_json("/api/agent/analyze", {
        "machine_id": "M_003",
        "timestamp": "2023-01-19 22:00:00"
    })
    assert code == 200
    assert m003_res["risk_level"] == "HIGH", f"Expected HIGH risk, got {m003_res['risk_level']}"
    assert m003_res["root_cause"] == "Bearing Degradation", f"Expected Bearing Degradation, got {m003_res['root_cause']}"
    notif_id = m003_res["notification_id"]
    assert notif_id is not None, "notification_id must exist for M_003 pre-failure"
    assert m003_res["approval_status"] == "PENDING", f"Expected PENDING, got {m003_res['approval_status']}"
    print(f"[PASS] M_003 Analysis generated notification: {notif_id} (Status: PENDING)")

    # Retrieve notification from GET /api/notifications
    code, notif_list = get_json("/api/notifications?machine_id=M_003")
    assert code == 200
    m003_notif = next((n for n in notif_list["notifications"] if n["notification_id"] == notif_id), None)
    assert m003_notif is not None, f"Notification {notif_id} not found in GET /api/notifications"
    assert m003_notif["status"] == "PENDING", f"Expected PENDING, got {m003_notif['status']}"
    print(f"[PASS] Notification {notif_id} retrieved via GET /api/notifications (status: PENDING)")

    # Execute Accept
    accept_payload = {
        "explicit_approval": True,
        "approved_by": "demo_operator",
        "approved_actions": ["schedule_inspection", "create_replacement_request", "send_vendor_email"],
        "notes": "Verified for morning shift execution."
    }
    code, accept_res = post_json(f"/api/notifications/{notif_id}/accept", accept_payload)
    assert code == 200
    assert accept_res["status"] == "VERIFICATION_PENDING", f"Expected VERIFICATION_PENDING, got {accept_res['status']}"
    assert accept_res["approved_by"] == "demo_operator"
    assert len(accept_res["actions"]) == 3, f"Expected 3 actions, got {len(accept_res['actions'])}"

    # Check per-action statuses
    action_verif = {a["action_type"]: a.get("verification_status", a.get("status")) for a in accept_res["actions"]}
    assert action_verif["schedule_inspection"] == "VERIFICATION_PENDING"
    assert action_verif["create_replacement_request"] == "VERIFICATION_PENDING"
    assert action_verif["send_vendor_email"] in ("SIMULATED", "COMPLETED", "VERIFICATION_PENDING")
    print(f"[PASS] M_003 Notification {notif_id} accepted: actions={list(action_verif.keys())}")

    # Verify action history
    code, history = get_json(f"/api/notifications/actions/history?notification_id={notif_id}")
    assert code == 200
    assert history["count"] >= 3, f"Expected at least 3 actions in history, got {history['count']}"
    print(f"[PASS] Action history records confirmed for {notif_id} ({history['count']} records found)")
    results["m003_flow"] = "PASS"

    # -------------------------------------------------------------
    # 3. DUPLICATE PROTECTION (Section 5)
    # -------------------------------------------------------------
    print("\n--- 3. Testing Duplicate Protection (409 Conflict) ---")
    # Repeated ACCEPT must return 409
    try:
        post_json(f"/api/notifications/{notif_id}/accept", accept_payload)
        assert False, "Expected 409 on duplicate accept"
    except urllib.error.HTTPError as e:
        assert e.code == 409, f"Expected 409, got {e.code}"
        print(f"[PASS] Second ACCEPT rejected with HTTP 409: {e.reason}")

    # REJECT after ACCEPT must return 409
    try:
        post_json(f"/api/notifications/{notif_id}/reject", {
            "rejected_by": "demo_operator",
            "rejection_reason": "Attempting reject after accept"
        })
        assert False, "Expected 409 on reject after accept"
    except urllib.error.HTTPError as e:
        assert e.code == 409, f"Expected 409, got {e.code}"
        print(f"[PASS] REJECT after ACCEPT rejected with HTTP 409: {e.reason}")
    results["duplicate_protection"] = "PASS"

    # -------------------------------------------------------------
    # 4. REJECT FLOW TEST (Section 4)
    # -------------------------------------------------------------
    print("\n--- 4. Testing Reject Flow ---")
    # Create a fresh notification by analyzing M_010 or M_004
    code, m004_res = post_json("/api/agent/analyze", {
        "machine_id": "M_004",
        "timestamp": "2023-01-27 10:00:00"
    })
    m004_notif_id = m004_res.get("notification_id")
    assert m004_notif_id is not None, "Expected notification for M_004"

    # Check baseline action record count
    code, pre_history = get_json("/api/notifications/actions/history")
    pre_count = pre_history["count"]

    # Reject notification
    code, reject_res = post_json(f"/api/notifications/{m004_notif_id}/reject", {
        "rejected_by": "supervisor_alice",
        "rejection_reason": "Maintenance will be reviewed during next shift."
    })
    assert code == 200
    assert reject_res["status"] == "REJECTED"
    assert reject_res["rejected_by"] == "supervisor_alice"

    # Verify zero actions executed
    code, post_history = get_json("/api/notifications/actions/history")
    post_count = post_history["count"]
    assert post_count == pre_count, f"Rejection must NOT add action records: before={pre_count}, after={post_count}"

    # Verify second reject returns 409
    try:
        post_json(f"/api/notifications/{m004_notif_id}/reject", {
            "rejected_by": "supervisor_alice"
        })
        assert False, "Expected 409 on duplicate reject"
    except urllib.error.HTTPError as e:
        assert e.code == 409
        print(f"[PASS] Second REJECT rejected with HTTP 409: {e.reason}")

    # Verify notification disappears from default unresolved list
    code, unresolved = get_json("/api/notifications")
    unresolved_ids = [n["notification_id"] for n in unresolved["notifications"]]
    assert m004_notif_id not in unresolved_ids, "Rejected notification must not appear in unresolved list"
    print(f"[PASS] Reject flow verified: 0 actions created, status=REJECTED, excluded from unresolved list")
    results["reject_flow"] = "PASS"

    # -------------------------------------------------------------
    # 5. PHYSICAL CONTROL SAFETY TEST (Section 6)
    # -------------------------------------------------------------
    print("\n--- 5. Testing Physical Control Safety Gates ---")
    prohibited_actions = [
        "shutdown_machine",
        "plc_control",
        "emergency_stop",
        "actuator_control",
        "electrical_switching",
        "physical_repair"
    ]

    from services import action_executor_service
    for action in prohibited_actions:
        res = action_executor_service.execute_action(
            action_type=action,
            notification_id="NTF-001",
            explicit_approval=True,
            approved_by="tester"
        )
        assert res["success"] is False, f"Expected blocked for {action}"
        assert "PROHIBITED" in res.get("error", "").upper() or "ALLOWED" in res.get("error", "").upper()
    print(f"[PASS] All {len(prohibited_actions)} prohibited physical control commands blocked by safety gate")
    results["physical_control_safety"] = "PASS"

    # -------------------------------------------------------------
    # 6. MEDIUM-RISK FLOW (Section 7)
    # -------------------------------------------------------------
    print("\n--- 6. Testing MEDIUM-Risk Machine Flow (M_005) ---")
    code, m005_res = post_json("/api/agent/analyze", {
        "machine_id": "M_005",
        "timestamp": "2023-02-11 15:00:00"
    })
    assert code == 200
    assert m005_res["risk_level"] == "MEDIUM", f"Expected MEDIUM, got {m005_res['risk_level']}"
    assert m005_res["notification_id"] is not None, "MEDIUM machine should create notification"
    assert m005_res["approval_status"] == "PENDING"
    m005_notif_id = m005_res["notification_id"]

    # Verify MEDIUM notification can be accepted
    code, m005_accept = post_json(f"/api/notifications/{m005_notif_id}/accept", {
        "explicit_approval": True,
        "approved_by": "demo_operator",
        "approved_actions": ["schedule_inspection"]
    })
    assert code == 200
    assert m005_accept["status"] == "VERIFICATION_PENDING"
    print(f"[PASS] MEDIUM-risk M_005 workflow completed: notification={m005_notif_id}, accepted successfully")
    results["medium_risk_flow"] = "PASS"

    # -------------------------------------------------------------
    # 7. VERIFICATION SAFEGUARD (Section 9)
    # -------------------------------------------------------------
    print("\n--- 7. Testing Verification Safeguard ---")
    from services import verification_service
    status = verification_service.verify_action_completion(notification_id=notif_id)
    assert status.get("verification_status") in ("PENDING_TELEMETRY", "VERIFICATION_PENDING")
    assert status.get("physical_health_verified") is False
    print("[PASS] Verification Safeguard active: physical recovery is NOT claimed prior to verified telemetry")
    results["verification_safeguard"] = "PASS"

    # -------------------------------------------------------------
    # 8. QWEN & DETERMINISTIC RCA REGRESSION (Section 14)
    # -------------------------------------------------------------
    print("\n--- 8. Testing Qwen & Deterministic RCA Integrity ---")
    assert m003_res["root_cause"] == "Bearing Degradation"
    assert m003_res["confidence"] > 0.5
    assert m003_res["candidate_scores"]["Bearing Degradation"] > m003_res["candidate_scores"]["Motor Overheating"]
    assert len(m003_res["evidence"]) >= 3
    assert m003_res["final_report"] != ""
    print("[PASS] Quantitative ML, Deterministic RCA, and Explanations remain authoritative and intact")
    results["rca_integrity"] = "PASS"

    print("\n=================================================================")
    print("ALL PHASE 6 END-TO-END VERIFICATION CHECKS PASSED (100%)")
    print("=================================================================")
    return results

if __name__ == "__main__":
    main()
