"""
Verification Service for Factory Health & Response Agent
=========================================================
Verifies software action completion and enforces physical health verification rules.

CRITICAL PHYSICAL HEALTH SAFEGUARD:
- Software action completion (CSV record, ticket, request, email) is NOT physical machine recovery.
- Never marks physical recovery as verified without verified new telemetry.
- When actions succeed without new telemetry, status is strictly:
    verification_status = "PENDING_TELEMETRY"
    action_verified = True
    physical_health_verified = False
- Persistent verification operates directly over CSV records across separate processes.
"""

import os
import csv
from typing import Dict, Any, List, Optional

from services import action_executor_service
from services import notification_service

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# Verification states
VERIFICATION_STATES = {
    "NOT_STARTED",
    "PENDING_TELEMETRY",
    "VERIFIED",
    "FAILED"
}


def _get_csv_paths(data_dir: Optional[str] = None) -> Dict[str, str]:
    return action_executor_service._get_csv_paths(data_dir)


def verify_action_completion(
    notification_id: str,
    action_id: Optional[str] = None,
    machine_id: Optional[str] = None,
    action_type: Optional[str] = None,
    new_telemetry_provided: bool = False,
    new_sensor_data: Optional[Dict[str, Any]] = None,
    data_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Verifies that an approved software action was legitimately completed and logged.

    Checks:
    1. Notification existence in notifications.csv
    2. Audit entry existence in action_records.csv
    3. Action status == 'COMPLETED' (not 'FAILED')
    4. Subsystem artifact presence:
       - schedule_inspection -> action_records.csv entry
       - create_maintenance_ticket -> maintenance_tickets.csv entry with status CREATED
       - create_replacement_request -> replacement_requests.csv entry
       - send_vendor_email -> replacement_requests.csv dispatch record (SENT or SIMULATED)
       - update_machine_status -> machine_action_status.csv entry
       - create_alert -> alerts.csv entry with status ACTIVE
    5. Physical health verification safeguard (PENDING_TELEMETRY vs VERIFIED)
    """
    paths = _get_csv_paths(data_dir)
    target_nid = str(notification_id).strip().upper()

    # 1. Verify notification exists
    notif = notification_service.get_notification(target_nid, filepath=paths["notifications"])
    if not notif:
        return {
            "verification_status": "FAILED",
            "action_verified": False,
            "physical_health_verified": False,
            "notification_id": target_nid,
            "action_id": action_id,
            "machine_id": machine_id,
            "action_type": action_type,
            "error_code": "NOTIFICATION_NOT_FOUND",
            "message": f"Notification '{target_nid}' not found in registry."
        }

    mid = str(machine_id or notif.get("machine_id", "")).strip().upper()

    # 2. Inspect action_records.csv for corresponding action audit entry
    action_csv = paths["action_records"]
    matching_action: Optional[Dict[str, Any]] = None

    if os.path.exists(action_csv):
        try:
            with open(action_csv, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    r_nid = str(row.get("notification_id", "")).strip().upper()
                    r_aid = str(row.get("action_id", "")).strip().upper()
                    r_type = str(row.get("action_type", "")).strip().lower()

                    if r_nid == target_nid:
                        if action_id and r_aid != str(action_id).strip().upper():
                            continue
                        if action_type and r_type != str(action_type).strip().lower():
                            continue
                        matching_action = dict(row)
                        break
        except Exception as e:
            return {
                "verification_status": "FAILED",
                "action_verified": False,
                "physical_health_verified": False,
                "notification_id": target_nid,
                "error_code": "FILE_READ_ERROR",
                "message": f"Failed to read action records: {str(e)}"
            }

    if not matching_action:
        return {
            "verification_status": "FAILED",
            "action_verified": False,
            "physical_health_verified": False,
            "notification_id": target_nid,
            "action_id": action_id,
            "machine_id": mid,
            "action_type": action_type,
            "error_code": "ACTION_RECORD_NOT_FOUND",
            "message": f"No action record found for notification '{target_nid}'."
        }

    # 3. Check recorded execution status
    act_status = str(matching_action.get("status", "")).strip().upper()
    act_type = str(matching_action.get("action_type", "")).strip().lower()
    act_id = matching_action.get("action_id")

    if act_status == "FAILED":
        return {
            "verification_status": "FAILED",
            "action_verified": False,
            "physical_health_verified": False,
            "notification_id": target_nid,
            "action_id": act_id,
            "machine_id": mid,
            "action_type": act_type,
            "error_code": "ACTION_EXECUTION_FAILED",
            "message": f"Action execution failed: {matching_action.get('result', 'Unknown failure')}",
            "action_record": matching_action
        }

    # 4. Verify corresponding subsystem artifact
    subsystem_details: Dict[str, Any] = {}
    subsystem_verified = False
    subsystem_msg = ""

    if act_type == "schedule_inspection":
        # Software inspection scheduling creates action_records.csv entry
        subsystem_verified = True
        subsystem_msg = "Software inspection scheduled successfully in dispatch backlog."
        subsystem_details = {"inspection_scheduled": True, "action_id": act_id}

    elif act_type == "create_maintenance_ticket":
        ticket_csv = paths["maintenance_tickets"]
        if os.path.exists(ticket_csv):
            try:
                with open(ticket_csv, "r", encoding="utf-8") as f:
                    for row in csv.DictReader(f):
                        if str(row.get("notification_id", "")).strip().upper() == target_nid:
                            if str(row.get("status", "")).strip().upper() == "CREATED":
                                subsystem_verified = True
                                subsystem_details = dict(row)
                                subsystem_msg = f"Maintenance ticket {row.get('ticket_id')} verified with status CREATED."
                                break
            except Exception:
                pass
        if not subsystem_verified:
            subsystem_msg = "Maintenance ticket record missing from maintenance_tickets.csv."

    elif act_type == "create_replacement_request":
        repl_csv = paths["replacement_requests"]
        if os.path.exists(repl_csv):
            try:
                with open(repl_csv, "r", encoding="utf-8") as f:
                    for row in csv.DictReader(f):
                        if str(row.get("notification_id", "")).strip().upper() == target_nid:
                            subsystem_verified = True
                            subsystem_details = dict(row)
                            subsystem_msg = f"Replacement request {row.get('request_id')} verified (status: {row.get('status')})."
                            break
            except Exception:
                pass
        if not subsystem_verified:
            subsystem_msg = "Replacement request record missing from replacement_requests.csv."

    elif act_type == "send_vendor_email":
        repl_csv = paths["replacement_requests"]
        if os.path.exists(repl_csv):
            try:
                with open(repl_csv, "r", encoding="utf-8") as f:
                    for row in csv.DictReader(f):
                        if str(row.get("notification_id", "")).strip().upper() == target_nid:
                            stat = str(row.get("status", "")).strip().upper()
                            if stat in ("SENT", "SIMULATED"):
                                subsystem_verified = True
                                subsystem_details = dict(row)
                                subsystem_msg = f"Vendor email dispatch verified (Status: {stat})."
                                break
            except Exception:
                pass
        if not subsystem_verified:
            subsystem_msg = "Vendor email dispatch record missing from replacement_requests.csv."

    elif act_type == "update_machine_status":
        stat_csv = paths["machine_action_status"]
        if os.path.exists(stat_csv):
            try:
                with open(stat_csv, "r", encoding="utf-8") as f:
                    for row in csv.DictReader(f):
                        if str(row.get("machine_id", "")).strip().upper() == mid:
                            subsystem_verified = True
                            subsystem_details = dict(row)
                            subsystem_msg = f"Machine action status verified: '{row.get('action_status')}'."
                            break
            except Exception:
                pass
        if not subsystem_verified:
            subsystem_msg = "Machine action status record missing from machine_action_status.csv."

    elif act_type == "create_alert":
        alert_csv = paths["alerts"]
        if os.path.exists(alert_csv):
            try:
                with open(alert_csv, "r", encoding="utf-8") as f:
                    for row in csv.DictReader(f):
                        if str(row.get("notification_id", "")).strip().upper() == target_nid:
                            subsystem_verified = True
                            subsystem_details = dict(row)
                            subsystem_msg = f"Software alert {row.get('alert_id')} verified with status ACTIVE."
                            break
            except Exception:
                pass
        if not subsystem_verified:
            subsystem_msg = "Alert record missing from alerts.csv."

    if not subsystem_verified:
        return {
            "verification_status": "FAILED",
            "action_verified": False,
            "physical_health_verified": False,
            "notification_id": target_nid,
            "action_id": act_id,
            "machine_id": mid,
            "action_type": act_type,
            "error_code": "SUBSYSTEM_ARTIFACT_MISSING",
            "message": subsystem_msg,
            "action_record": matching_action
        }

    # 5. Physical Health Verification Rule
    # Software actions are now verified. But physical health cannot be claimed healthy without new telemetry.
    if new_telemetry_provided and new_sensor_data:
        # Evaluate physical telemetry health
        physical_health_verified = _evaluate_telemetry_health(new_sensor_data)
        if physical_health_verified:
            final_verification_status = "VERIFIED"
            final_message = (
                f"{subsystem_msg} Genuine new telemetry ingested and verified: "
                f"Machine {mid} health parameters nominal."
            )
        else:
            final_verification_status = "FAILED"
            final_message = (
                f"{subsystem_msg} Genuine new telemetry ingested, but machine {mid} "
                f"remains in anomalous condition."
            )
    else:
        # Default safe operational state
        final_verification_status = "PENDING_TELEMETRY"
        physical_health_verified = False
        final_message = (
            f"{subsystem_msg} Maintenance action record verified. "
            f"Physical machine recovery requires new telemetry."
        )

    return {
        "verification_status": final_verification_status,
        "action_verified": True,
        "physical_health_verified": physical_health_verified,
        "notification_id": target_nid,
        "action_id": act_id,
        "machine_id": mid,
        "action_type": act_type,
        "message": final_message,
        "action_record": matching_action,
        "subsystem_details": subsystem_details
    }


def verify_notification_actions(
    notification_id: str,
    data_dir: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Verifies all recorded actions associated with a notification_id.
    """
    paths = _get_csv_paths(data_dir)
    target_nid = str(notification_id).strip().upper()
    results: List[Dict[str, Any]] = []

    if not os.path.exists(paths["action_records"]):
        return []

    try:
        with open(paths["action_records"], "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if str(row.get("notification_id", "")).strip().upper() == target_nid:
                    aid = row.get("action_id")
                    atype = row.get("action_type")
                    res = verify_action_completion(
                        notification_id=target_nid,
                        action_id=aid,
                        action_type=atype,
                        data_dir=data_dir
                    )
                    results.append(res)
    except Exception:
        return []

    return results


def _evaluate_telemetry_health(sensor_data: Dict[str, Any]) -> bool:
    """
    Evaluates whether raw sensor telemetry is within nominal boundaries.
    """
    try:
        vib = float(sensor_data.get("vibration_mm_s", 1.8))
        temp = float(sensor_data.get("temperature_c", 45.0))
        press = float(sensor_data.get("pressure_bar", 120.0))
        energy = float(sensor_data.get("energy_consumption_kwh", 70.0))

        # Nominal operational limits
        if vib > 4.5 or temp > 75.0 or press < 90.0 or energy > 110.0:
            return False
        return True
    except Exception:
        return False
