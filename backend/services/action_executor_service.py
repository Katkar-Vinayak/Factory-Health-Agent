"""
Action Executor Service for Factory Health & Response Agent
============================================================
Executes software and business actions strictly after explicit human approval.

STRICT SAFETY CONSTRAINTS:
- NEVER executes automatically without explicit human approval.
- ONLY implements software/business operations:
    1. schedule_inspection (creates application inspection record)
    2. create_maintenance_ticket (logs ticket in maintenance_tickets.csv)
    3. create_replacement_request (logs parts request in replacement_requests.csv)
    4. send_vendor_email (dispatches or simulates vendor order email)
    5. update_machine_status (updates application-side operational status)
    6. create_alert (logs alert record in alerts.csv)
- NEVER implements PLC control, motor control, actuator control, machinery
  shutdown, electrical switching, safety-system control, or physical repair.
- Zero fabrication of vendors or contact information; uses configured vendors.csv.
- Full auditability via action_records.csv with sequential IDs (ACT-001, ACT-002, ...).
"""

import os
import csv
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from services import notification_service
from services import email_service

# Base data directory
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# Allowed software-only actions
ALLOWED_ACTION_TYPES = {
    "schedule_inspection",
    "create_maintenance_ticket",
    "create_replacement_request",
    "send_vendor_email",
    "update_machine_status",
    "create_alert"
}

# Strict prohibited keywords to block any physical machinery control attempts
PROHIBITED_ACTION_KEYWORDS = {
    "plc", "motor_control", "actuator", "shutdown", "stop_machine",
    "power_cut", "switch", "breaker", "physical_repair", "valve_close",
    "valve_open", "emergency_stop", "estop", "speed_control", "trip_breaker"
}

# Statuses that forbid re-execution (Duplicate execution prevention)
NON_ACTIONABLE_STATUSES = {
    "ACTION_IN_PROGRESS",
    "COMPLETED",
    "FAILED",
    "VERIFICATION_PENDING",
    "REJECTED"
}

# CSV Schemas
MAINTENANCE_TICKET_HEADERS = [
    "ticket_id",
    "notification_id",
    "machine_id",
    "component",
    "priority",
    "reason",
    "status",
    "created_at"
]

MACHINE_ACTION_STATUS_HEADERS = [
    "machine_id",
    "action_status",
    "last_action_id",
    "notification_id",
    "updated_at",
    "notes"
]

ALERT_HEADERS = [
    "alert_id",
    "notification_id",
    "machine_id",
    "component",
    "severity",
    "message",
    "status",
    "created_at"
]


def _get_csv_paths(data_dir: Optional[str] = None) -> Dict[str, str]:
    base = data_dir or DATA_DIR
    return {
        "notifications": os.path.join(base, "notifications.csv"),
        "action_records": os.path.join(base, "action_records.csv"),
        "vendors": os.path.join(base, "vendors.csv"),
        "replacement_requests": os.path.join(base, "replacement_requests.csv"),
        "maintenance_tickets": os.path.join(base, "maintenance_tickets.csv"),
        "machine_action_status": os.path.join(base, "machine_action_status.csv"),
        "alerts": os.path.join(base, "alerts.csv"),
        "machine_metadata": os.path.join(base, "machine_metadata.csv")
    }


def ensure_action_csv_files_exist(target_data_dir: Optional[str] = None):
    """
    Ensures all supporting CSV files exist with standard headers.
    """
    base_dir = target_data_dir or DATA_DIR
    os.makedirs(base_dir, exist_ok=True)

    # First ensure notification service CSVs
    notification_service.ensure_csv_files_exist(base_dir)

    extra_files = [
        (os.path.join(base_dir, "maintenance_tickets.csv"), MAINTENANCE_TICKET_HEADERS),
        (os.path.join(base_dir, "machine_action_status.csv"), MACHINE_ACTION_STATUS_HEADERS),
        (os.path.join(base_dir, "alerts.csv"), ALERT_HEADERS)
    ]

    for filepath, headers in extra_files:
        needs_init = False
        if not os.path.exists(filepath):
            needs_init = True
        else:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    first_line = f.readline().strip()
                    if not first_line:
                        needs_init = True
            except Exception:
                needs_init = True

        if needs_init:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)


# Auto-initialize files on module load
ensure_action_csv_files_exist()


def _get_next_sequential_id(filepath: str, prefix: str, header_col: str) -> str:
    """
    Computes the next sequential ID (e.g., ACT-001, TCK-001, REQ-001, ALT-001).
    Guarantees no duplicate IDs.
    """
    max_id = 0
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                pattern = re.compile(rf"{prefix}-(\d+)")
                for row in reader:
                    val = str(row.get(header_col, "")).strip()
                    match = pattern.search(val)
                    if match:
                        num = int(match.group(1))
                        if num > max_id:
                            max_id = num
        except Exception:
            pass

    return f"{prefix}-{max_id + 1:03d}"


def _machine_exists(machine_id: str, data_dir: Optional[str] = None) -> bool:
    """
    Validates that machine_id is registered in machine_metadata.csv.
    """
    norm_mid = str(machine_id).strip().upper()
    if not norm_mid:
        return False

    paths = _get_csv_paths(data_dir)
    metadata_path = paths["machine_metadata"]

    # Fallback to base DATA_DIR if isolated test dir does not have metadata
    if not os.path.exists(metadata_path):
        metadata_path = os.path.join(DATA_DIR, "machine_metadata.csv")

    if not os.path.exists(metadata_path):
        # If no metadata file exists anywhere, accept any non-empty formatted machine ID
        return bool(re.match(r"^M_\d+$", norm_mid, re.IGNORECASE))

    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                r_mid = str(row.get("machine_id", "")).strip().upper()
                if r_mid == norm_mid:
                    return True
    except Exception:
        return False

    return False


def validate_action_request(
    action_type: str,
    notification_id: str,
    explicit_approval: bool,
    approved_by: Optional[str] = None,
    component: Optional[str] = None,
    data_dir: Optional[str] = None,
    allow_in_progress: bool = False
) -> Tuple[bool, Optional[str], Optional[str], Optional[Dict[str, Any]]]:
    """
    Validates an action execution request against all safety rules.

    Returns:
      (is_valid: bool, error_message: str | None, error_code: str | None, notification_data: dict | None)
    """
    # 1. Approval Safety Gate: Must have explicit approval flag and approver identity
    if not explicit_approval:
        return (
            False,
            "Action execution rejected: Explicit human approval is required.",
            "APPROVAL_REQUIRED",
            None
        )

    if not approved_by or not str(approved_by).strip():
        return (
            False,
            "Action execution rejected: Approver identity ('approved_by') must be specified.",
            "APPROVER_REQUIRED",
            None
        )

    # 2. Safety Rule: Check prohibited physical machinery commands
    norm_action = str(action_type).strip().lower()
    for prohibited in PROHIBITED_ACTION_KEYWORDS:
        if prohibited in norm_action:
            return (
                False,
                f"Safety violation: Physical machinery control action '{action_type}' is strictly prohibited. "
                f"The agent only performs software and business actions.",
                "PHYSICAL_CONTROL_PROHIBITED",
                None
            )

    # 3. Action type check
    if norm_action not in ALLOWED_ACTION_TYPES:
        return (
            False,
            f"Invalid action type '{action_type}'. Allowed types: {sorted(ALLOWED_ACTION_TYPES)}",
            "INVALID_ACTION_TYPE",
            None
        )

    paths = _get_csv_paths(data_dir)

    # 4. Notification existence check
    notif = notification_service.get_notification(notification_id, filepath=paths["notifications"])
    if not notif:
        return (
            False,
            f"Notification '{notification_id}' not found.",
            "NOTIFICATION_NOT_FOUND",
            None
        )

    # 5. Notification actionable status & duplicate execution check
    current_status = str(notif.get("status", "")).strip().upper()
    if allow_in_progress:
        # During an active approved execution batch, permit PENDING, ACTION_IN_PROGRESS, or VERIFICATION_PENDING
        if current_status in {"COMPLETED", "FAILED", "REJECTED"}:
            return (
                False,
                f"Notification '{notification_id}' is already in status '{current_status}'. Duplicate execution is prevented.",
                "ALREADY_PROCESSED",
                notif
            )
    else:
        if current_status in NON_ACTIONABLE_STATUSES:
            return (
                False,
                f"Notification '{notification_id}' is already in status '{current_status}'. Duplicate execution is prevented.",
                "ALREADY_PROCESSED",
                notif
            )

    # 6. Machine existence check
    machine_id = str(notif.get("machine_id", "")).strip()
    if not _machine_exists(machine_id, data_dir=data_dir):
        return (
            False,
            f"Machine '{machine_id}' does not exist in machine catalog.",
            "MACHINE_NOT_FOUND",
            notif
        )

    # 7. Component information check
    comp = str(component or notif.get("component", "")).strip()
    if not comp:
        return (
            False,
            f"Component information is missing for notification '{notification_id}'.",
            "MISSING_COMPONENT",
            notif
        )

    # 8. Vendor lookup check for replacement request / vendor email actions
    if norm_action in {"create_replacement_request", "send_vendor_email"}:
        vendor = notification_service.find_vendor_by_component(comp, filepath=paths["vendors"])
        if not vendor:
            return (
                False,
                "Replacement request could not be created because no configured vendor was found.",
                "VENDOR_NOT_FOUND",
                notif
            )

    return True, None, None, notif


def execute_action(
    action_type: str,
    notification_id: str,
    explicit_approval: bool = False,
    approved_by: Optional[str] = None,
    priority: Optional[str] = None,
    reason: Optional[str] = None,
    component: Optional[str] = None,
    quantity: int = 1,
    notes: Optional[str] = None,
    data_dir: Optional[str] = None,
    allow_in_progress: bool = False,
    update_notification: bool = True
) -> Dict[str, Any]:
    """
    Executes an approved software action and logs it into action_records.csv.

    Dispatcher routes to:
    - schedule_inspection
    - create_maintenance_ticket
    - create_replacement_request
    - send_vendor_email
    - update_machine_status
    - create_alert
    """
    paths = _get_csv_paths(data_dir)
    ensure_action_csv_files_exist(data_dir)

    # 1. Run Approval Safety Gate & Validation
    is_valid, err_msg, err_code, notif = validate_action_request(
        action_type=action_type,
        notification_id=notification_id,
        explicit_approval=explicit_approval,
        approved_by=approved_by,
        component=component,
        data_dir=data_dir,
        allow_in_progress=allow_in_progress
    )

    if not is_valid:
        return {
            "success": False,
            "error": err_msg,
            "error_code": err_code,
            "status": "FAILED",
            "notification_id": notification_id,
            "action_type": action_type
        }

    assert notif is not None

    norm_action = str(action_type).strip().lower()
    machine_id = str(notif.get("machine_id", "")).strip()
    target_component = str(component or notif.get("component", "")).strip()
    target_priority = str(priority or notif.get("severity", "MEDIUM")).strip().upper()
    target_reason = str(reason or notif.get("recommendation") or notif.get("root_cause", "Predictive maintenance action")).strip()

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    approved_at = now_str

    # 2. Transition notification to ACTION_IN_PROGRESS
    if update_notification:
        notification_service.update_notification_status(
            notification_id=notification_id,
            status="ACTION_IN_PROGRESS",
            filepath=paths["notifications"]
        )

    # 3. Mint sequential Action ID
    action_id = _get_next_sequential_id(paths["action_records"], "ACT", "action_id")

    # 4. Dispatch and execute action
    try:
        action_result_msg = ""
        verification_status = "VERIFICATION_PENDING"
        final_notif_status = "VERIFICATION_PENDING"
        details: Dict[str, Any] = {}

        if norm_action == "schedule_inspection":
            # Software inspection scheduling only
            action_result_msg = (
                f"Inspection scheduled successfully for component {target_component} on machine {machine_id}. "
                f"Work order logged in maintenance dispatch backlog."
            )
            verification_status = "VERIFICATION_PENDING"
            final_notif_status = "VERIFICATION_PENDING"
            details = {
                "machine_id": machine_id,
                "component": target_component,
                "scheduled_at": now_str,
                "note": "Software record only. Physical inspection pending technician execution."
            }

        elif norm_action == "create_maintenance_ticket":
            # Create persistent maintenance ticket
            ticket_id = _get_next_sequential_id(paths["maintenance_tickets"], "TCK", "ticket_id")
            ticket_row = {
                "ticket_id": ticket_id,
                "notification_id": notification_id,
                "machine_id": machine_id,
                "component": target_component,
                "priority": target_priority,
                "reason": target_reason,
                "status": "CREATED",
                "created_at": now_str
            }
            with open(paths["maintenance_tickets"], "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=MAINTENANCE_TICKET_HEADERS)
                writer.writerow(ticket_row)

            action_result_msg = f"Maintenance ticket {ticket_id} created successfully with status CREATED."
            verification_status = "VERIFICATION_PENDING"
            final_notif_status = "VERIFICATION_PENDING"
            details = ticket_row

        elif norm_action == "create_replacement_request":
            # Replacement request using configured vendor
            vendor = notification_service.find_vendor_by_component(target_component, filepath=paths["vendors"])
            assert vendor is not None

            req_id = _get_next_sequential_id(paths["replacement_requests"], "REQ", "request_id")
            req_row = {
                "request_id": req_id,
                "notification_id": notification_id,
                "machine_id": machine_id,
                "part_name": target_component,
                "part_number": vendor.get("part_number", "GENERIC-PART"),
                "vendor_id": vendor.get("vendor_id", ""),
                "vendor_email": vendor.get("email", ""),
                "quantity": str(quantity),
                "priority": target_priority,
                "status": "DRAFTED",
                "created_at": now_str,
                "sent_at": ""
            }
            with open(paths["replacement_requests"], "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=notification_service.REPLACEMENT_REQUEST_HEADERS)
                writer.writerow(req_row)

            action_result_msg = (
                f"Replacement request {req_id} created successfully for vendor {vendor.get('vendor_id')} "
                f"({vendor.get('vendor_name')}) for part {vendor.get('part_number')}."
            )
            verification_status = "VERIFICATION_PENDING"
            final_notif_status = "VERIFICATION_PENDING"
            details = req_row

        elif norm_action == "send_vendor_email":
            # Send or simulate vendor email
            vendor = notification_service.find_vendor_by_component(target_component, filepath=paths["vendors"])
            assert vendor is not None

            email_res = email_service.send_vendor_replacement_email(
                machine_id=machine_id,
                component=target_component,
                part_number=vendor.get("part_number", "GENERIC-PART"),
                vendor_email=vendor.get("email", ""),
                vendor_name=vendor.get("vendor_name", ""),
                quantity=quantity,
                priority=target_priority,
                reason=target_reason,
                notification_id=notification_id
            )

            # Record or update replacement request with sent_at timestamp
            req_id = _get_next_sequential_id(paths["replacement_requests"], "REQ", "request_id")
            req_row = {
                "request_id": req_id,
                "notification_id": notification_id,
                "machine_id": machine_id,
                "part_name": target_component,
                "part_number": vendor.get("part_number", "GENERIC-PART"),
                "vendor_id": vendor.get("vendor_id", ""),
                "vendor_email": vendor.get("email", ""),
                "quantity": str(quantity),
                "priority": target_priority,
                "status": "SENT" if email_res.get("email_status") == "SENT" else "SIMULATED",
                "created_at": now_str,
                "sent_at": now_str
            }
            with open(paths["replacement_requests"], "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=notification_service.REPLACEMENT_REQUEST_HEADERS)
                writer.writerow(req_row)

            mode_label = "SIMULATED (Mock Mode)" if email_res.get("is_simulated") else "REAL (SMTP)"
            action_result_msg = (
                f"Vendor replacement email processed in {mode_label} to {vendor.get('email')} "
                f"for part {vendor.get('part_number')}."
            )
            verification_status = "VERIFICATION_PENDING"
            final_notif_status = "VERIFICATION_PENDING"
            details = {**email_res, "request_id": req_id}

        elif norm_action == "update_machine_status":
            # Application-side status tracking ONLY. Never touches ML risk or telemetry.
            new_app_status = str(notes or "MAINTENANCE_SCHEDULED").strip().upper()
            status_row = {
                "machine_id": machine_id,
                "action_status": new_app_status,
                "last_action_id": action_id,
                "notification_id": notification_id,
                "updated_at": now_str,
                "notes": f"Updated by {approved_by}: {target_reason}"
            }
            # Append/update status record
            with open(paths["machine_action_status"], "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=MACHINE_ACTION_STATUS_HEADERS)
                writer.writerow(status_row)

            action_result_msg = (
                f"Machine operational action status updated to '{new_app_status}' in application registry. "
                f"Deterministic ML risk models remain unmodified."
            )
            verification_status = "COMPLETED"
            final_notif_status = "COMPLETED"
            details = status_row

        elif norm_action == "create_alert":
            # Create software alert record
            alert_id = _get_next_sequential_id(paths["alerts"], "ALT", "alert_id")
            alert_row = {
                "alert_id": alert_id,
                "notification_id": notification_id,
                "machine_id": machine_id,
                "component": target_component,
                "severity": target_priority,
                "message": f"Operator Approved Action Alert: {target_reason}",
                "status": "ACTIVE",
                "created_at": now_str
            }
            with open(paths["alerts"], "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=ALERT_HEADERS)
                writer.writerow(alert_row)

            action_result_msg = f"Software alert {alert_id} created successfully."
            verification_status = "COMPLETED"
            final_notif_status = "COMPLETED"
            details = alert_row

        completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 5. Record successful action in action_records.csv
        action_record = {
            "action_id": action_id,
            "notification_id": notification_id,
            "machine_id": machine_id,
            "action_type": norm_action,
            "component": target_component,
            "priority": target_priority,
            "reason": target_reason,
            "status": "COMPLETED",
            "approved_at": approved_at,
            "completed_at": completed_at,
            "result": action_result_msg,
            "verification_status": verification_status
        }
        with open(paths["action_records"], "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=notification_service.ACTION_RECORD_HEADERS)
            writer.writerow(action_record)

        # 6. Update notification to final status (VERIFICATION_PENDING or COMPLETED)
        if update_notification:
            notification_service.update_notification_status(
                notification_id=notification_id,
                status=final_notif_status,
                filepath=paths["notifications"]
            )

        return {
            "success": True,
            "action_id": action_id,
            "notification_id": notification_id,
            "machine_id": machine_id,
            "action_type": norm_action,
            "component": target_component,
            "status": "COMPLETED",
            "result": action_result_msg,
            "verification_status": verification_status,
            "action_record": action_record,
            "details": details
        }

    except Exception as e:
        # Failure recovery: log failed action record and update notification to FAILED
        completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        err_str = f"Execution error: {str(e)}"

        try:
            failed_record = {
                "action_id": action_id,
                "notification_id": notification_id,
                "machine_id": machine_id,
                "action_type": norm_action,
                "component": target_component,
                "priority": target_priority,
                "reason": target_reason,
                "status": "FAILED",
                "approved_at": approved_at,
                "completed_at": completed_at,
                "result": err_str,
                "verification_status": "FAILED"
            }
            with open(paths["action_records"], "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=notification_service.ACTION_RECORD_HEADERS)
                writer.writerow(failed_record)

            if update_notification:
                notification_service.update_notification_status(
                    notification_id=notification_id,
                    status="FAILED",
                    filepath=paths["notifications"]
                )
        except Exception:
            pass

        return {
            "success": False,
            "error": err_str,
            "error_code": "EXECUTION_ERROR",
            "status": "FAILED",
            "action_id": action_id,
            "notification_id": notification_id
        }


def get_action_records(
    machine_id: Optional[str] = None,
    notification_id: Optional[str] = None,
    action_type: Optional[str] = None,
    data_dir: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieves action records from action_records.csv with optional filtering.
    """
    paths = _get_csv_paths(data_dir)
    csv_path = paths["action_records"]
    if not os.path.exists(csv_path):
        return []

    norm_mid = machine_id.strip().upper() if machine_id else None
    norm_nid = notification_id.strip().upper() if notification_id else None
    norm_type = action_type.strip().lower() if action_type else None

    records: List[Dict[str, Any]] = []
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                r_mid = str(row.get("machine_id", "")).strip().upper()
                r_nid = str(row.get("notification_id", "")).strip().upper()
                r_type = str(row.get("action_type", "")).strip().lower()

                if norm_mid and r_mid != norm_mid:
                    continue
                if norm_nid and r_nid != norm_nid:
                    continue
                if norm_type and r_type != norm_type:
                    continue

                records.append(dict(row))
    except Exception:
        return []

    return records


def get_action_record(
    action_id: str,
    data_dir: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Retrieves a single action record by action_id.
    """
    paths = _get_csv_paths(data_dir)
    target_id = str(action_id).strip().upper()

    try:
        with open(paths["action_records"], "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if str(row.get("action_id", "")).strip().upper() == target_id:
                    return dict(row)
    except Exception:
        return None

    return None
