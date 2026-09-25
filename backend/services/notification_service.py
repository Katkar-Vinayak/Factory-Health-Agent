"""
Notification Service for Factory Health & Response Agent
========================================================
Manages persistent notification storage, status lifecycles, and deduplication
for the Human-in-the-Loop (HITL) maintenance workflow.

Strictly CSV-based storage:
  - backend/data/notifications.csv
  - backend/data/action_records.csv
  - backend/data/vendors.csv
  - backend/data/replacement_requests.csv
"""

import os
import csv
import re
from datetime import datetime
from typing import Dict, Any, List, Optional

# Base data directory
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

NOTIFICATIONS_CSV = os.path.join(DATA_DIR, "notifications.csv")
ACTION_RECORDS_CSV = os.path.join(DATA_DIR, "action_records.csv")
VENDORS_CSV = os.path.join(DATA_DIR, "vendors.csv")
REPLACEMENT_REQUESTS_CSV = os.path.join(DATA_DIR, "replacement_requests.csv")

# CSV Schemas
NOTIFICATION_HEADERS = [
    "notification_id",
    "machine_id",
    "timestamp",
    "severity",
    "title",
    "message",
    "component",
    "root_cause",
    "failure_probability",
    "recommendation",
    "status",
    "created_at",
    "resolved_at",
    "rejection_reason"
]

ACTION_RECORD_HEADERS = [
    "action_id",
    "notification_id",
    "machine_id",
    "action_type",
    "component",
    "priority",
    "reason",
    "status",
    "approved_at",
    "completed_at",
    "result",
    "verification_status"
]

VENDOR_HEADERS = [
    "vendor_id",
    "vendor_name",
    "part_type",
    "part_number",
    "email",
    "lead_time_days"
]

REPLACEMENT_REQUEST_HEADERS = [
    "request_id",
    "notification_id",
    "machine_id",
    "part_name",
    "part_number",
    "vendor_id",
    "vendor_email",
    "quantity",
    "priority",
    "status",
    "created_at",
    "sent_at"
]

# Allowed Statuses
ALLOWED_STATUSES = {
    "PENDING",
    "ACCEPTED",
    "REJECTED",
    "ACTION_IN_PROGRESS",
    "COMPLETED",
    "FAILED",
    "VERIFICATION_PENDING"
}

# Unresolved statuses that trigger deduplication
UNRESOLVED_STATUSES = {
    "PENDING",
    "ACTION_IN_PROGRESS",
    "VERIFICATION_PENDING"
}

# Demo Vendors Seed Data
DEFAULT_DEMO_VENDORS = [
    {
        "vendor_id": "V001",
        "vendor_name": "Demo Industrial Bearings Ltd",
        "part_type": "Bearing",
        "part_number": "BRG-6205",
        "email": "demo-bearings@example.com",
        "lead_time_days": "3"
    },
    {
        "vendor_id": "V002",
        "vendor_name": "Demo ElectroDrive Systems",
        "part_type": "Motor",
        "part_number": "MTR-440V-75KW",
        "email": "demo-motors@example.com",
        "lead_time_days": "5"
    },
    {
        "vendor_id": "V003",
        "vendor_name": "Demo Thermal & Cooling Solutions",
        "part_type": "Cooling Pump",
        "part_number": "PMP-COOL-220",
        "email": "demo-cooling@example.com",
        "lead_time_days": "2"
    },
    {
        "vendor_id": "V004",
        "vendor_name": "Demo Fluid Power & Hydraulics",
        "part_type": "Hydraulic Valve & Seal Kit",
        "part_number": "HYD-VLV-350",
        "email": "demo-hydraulics@example.com",
        "lead_time_days": "4"
    },
    {
        "vendor_id": "V005",
        "vendor_name": "Demo Precision Power Electronics",
        "part_type": "Inverter & Phase Relay",
        "part_number": "ELC-RLY-480",
        "email": "demo-electrical@example.com",
        "lead_time_days": "2"
    }
]


def ensure_csv_files_exist(target_data_dir: Optional[str] = None):
    """
    Guarantees all 4 CSV files exist with standard headers and default demo vendors.
    Safely heals missing or empty files.
    """
    base_dir = target_data_dir or DATA_DIR
    os.makedirs(base_dir, exist_ok=True)

    files_and_headers = [
        (os.path.join(base_dir, "notifications.csv"), NOTIFICATION_HEADERS, None),
        (os.path.join(base_dir, "action_records.csv"), ACTION_RECORD_HEADERS, None),
        (os.path.join(base_dir, "vendors.csv"), VENDOR_HEADERS, DEFAULT_DEMO_VENDORS),
        (os.path.join(base_dir, "replacement_requests.csv"), REPLACEMENT_REQUEST_HEADERS, None)
    ]

    for filepath, headers, initial_rows in files_and_headers:
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
                if initial_rows:
                    dict_writer = csv.DictWriter(f, fieldnames=headers)
                    dict_writer.writerows(initial_rows)


# Auto-initialize on module load
ensure_csv_files_exist()


def _get_next_notification_id(filepath: Optional[str] = None) -> str:
    """
    Safely calculates the next sequential notification ID (NTF-001, NTF-002, etc.).
    Guarantees no duplicate IDs.
    """
    csv_path = filepath or NOTIFICATIONS_CSV
    max_id = 0

    if os.path.exists(csv_path):
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    nid = row.get("notification_id", "")
                    match = re.search(r"NTF-(\d+)", nid)
                    if match:
                        num = int(match.group(1))
                        if num > max_id:
                            max_id = num
        except Exception:
            pass

    return f"NTF-{max_id + 1:03d}"


def find_existing_unresolved_notification(
    machine_id: str,
    component: str,
    filepath: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Searches for an existing notification matching:
      machine_id + component + unresolved status (PENDING, ACTION_IN_PROGRESS, VERIFICATION_PENDING)
    Returns the matching record dictionary or None.
    """
    csv_path = filepath or NOTIFICATIONS_CSV
    if not os.path.exists(csv_path):
        return None

    norm_mid = str(machine_id).strip().upper()
    norm_comp = str(component).strip().upper()

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                r_mid = str(row.get("machine_id", "")).strip().upper()
                r_comp = str(row.get("component", "")).strip().upper()
                r_status = str(row.get("status", "")).strip().upper()

                if r_mid == norm_mid and r_comp == norm_comp and r_status in UNRESOLVED_STATUSES:
                    return dict(row)
    except Exception:
        return None

    return None


def create_notification(
    machine_id: str,
    severity: str,
    title: str,
    message: str,
    component: str,
    root_cause: str,
    failure_probability: float,
    recommendation: Any,
    timestamp: Optional[str] = None,
    status: str = "PENDING",
    filepath: Optional[str] = None
) -> Dict[str, Any]:
    """
    Creates a new maintenance notification with deduplication protection.
    
    If an unresolved notification already exists for machine_id + component,
    the existing notification is returned with 'is_duplicate': True without writing a new row.
    """
    csv_path = filepath or NOTIFICATIONS_CSV
    ensure_csv_files_exist(os.path.dirname(csv_path) if filepath else None)

    # 1. Validate status
    norm_status = str(status).strip().upper()
    if norm_status not in ALLOWED_STATUSES:
        raise ValueError(f"Invalid status '{status}'. Must be one of {sorted(ALLOWED_STATUSES)}")

    # 2. Check deduplication: machine_id + component + unresolved status
    existing = find_existing_unresolved_notification(machine_id, component, filepath=csv_path)
    if existing:
        return {**existing, "is_duplicate": True}

    # 3. Format recommendation string
    if isinstance(recommendation, list):
        rec_str = "; ".join(str(r) for r in recommendation)
    else:
        rec_str = str(recommendation or "").strip()

    # 4. Generate next sequential ID
    notif_id = _get_next_notification_id(csv_path)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    obs_ts = str(timestamp or now_str).strip()

    record: Dict[str, Any] = {
        "notification_id": notif_id,
        "machine_id": str(machine_id).strip(),
        "timestamp": obs_ts,
        "severity": str(severity).strip().upper(),
        "title": str(title).strip(),
        "message": str(message).strip(),
        "component": str(component).strip(),
        "root_cause": str(root_cause).strip(),
        "failure_probability": f"{float(failure_probability):.2f}",
        "recommendation": rec_str,
        "status": norm_status,
        "created_at": now_str,
        "resolved_at": "",
        "rejection_reason": ""
    }

    # 5. Append to CSV
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=NOTIFICATION_HEADERS)
        writer.writerow(record)

    return {**record, "is_duplicate": False}


def get_notifications(
    status: Optional[str] = None,
    machine_id: Optional[str] = None,
    severity: Optional[str] = None,
    filepath: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieves all notifications from notifications.csv with optional filtering.
    """
    csv_path = filepath or NOTIFICATIONS_CSV
    if not os.path.exists(csv_path):
        ensure_csv_files_exist(os.path.dirname(csv_path) if filepath else None)
        return []

    norm_status = status.strip().upper() if status else None
    norm_mid = machine_id.strip().upper() if machine_id else None
    norm_sev = severity.strip().upper() if severity else None

    notifications: List[Dict[str, Any]] = []

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                r_status = str(row.get("status", "")).strip().upper()
                r_mid = str(row.get("machine_id", "")).strip().upper()
                r_sev = str(row.get("severity", "")).strip().upper()

                if norm_status and r_status != norm_status:
                    continue
                if norm_mid and r_mid != norm_mid:
                    continue
                if norm_sev and r_sev != norm_sev:
                    continue

                notifications.append(dict(row))
    except Exception:
        return []

    return notifications


def get_notification(
    notification_id: str,
    filepath: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Retrieves a single notification by notification_id.
    """
    csv_path = filepath or NOTIFICATIONS_CSV
    if not os.path.exists(csv_path):
        return None

    target_id = str(notification_id).strip().upper()

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if str(row.get("notification_id", "")).strip().upper() == target_id:
                    return dict(row)
    except Exception:
        return None

    return None


def update_notification_status(
    notification_id: str,
    status: str,
    resolved_at: Optional[str] = None,
    rejection_reason: Optional[str] = None,
    filepath: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Updates the status, resolved_at timestamp, and rejection reason of an existing notification.
    Enforces allowed status validation.
    """
    csv_path = filepath or NOTIFICATIONS_CSV
    if not os.path.exists(csv_path):
        return None

    norm_status = str(status).strip().upper()
    if norm_status not in ALLOWED_STATUSES:
        raise ValueError(f"Invalid status '{status}'. Must be one of {sorted(ALLOWED_STATUSES)}")

    target_id = str(notification_id).strip().upper()
    rows: List[Dict[str, Any]] = []
    updated_record: Optional[Dict[str, Any]] = None

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if str(row.get("notification_id", "")).strip().upper() == target_id:
                row["status"] = norm_status
                if norm_status in ("ACCEPTED", "REJECTED", "COMPLETED", "FAILED"):
                    row["resolved_at"] = str(resolved_at or now_str).strip()
                elif resolved_at:
                    row["resolved_at"] = str(resolved_at).strip()

                if rejection_reason is not None:
                    row["rejection_reason"] = str(rejection_reason).strip()

                updated_record = dict(row)
            rows.append(row)

    if updated_record:
        # Rewrite CSV atomically
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=NOTIFICATION_HEADERS)
            writer.writeheader()
            writer.writerows(rows)

    return updated_record


def get_vendors(filepath: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Returns configured demo vendors from vendors.csv.
    """
    csv_path = filepath or VENDORS_CSV
    if not os.path.exists(csv_path):
        ensure_csv_files_exist(os.path.dirname(csv_path) if filepath else None)

    vendors: List[Dict[str, Any]] = []
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                vendors.append(dict(row))
    except Exception:
        return []
    return vendors


def find_vendor_by_component(
    component_name: str,
    filepath: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Finds matching demo vendor for a given component or part type.
    """
    vendors = get_vendors(filepath)
    comp_norm = str(component_name).strip().lower()

    for v in vendors:
        part_type = str(v.get("part_type", "")).strip().lower()
        if comp_norm in part_type or part_type in comp_norm:
            return v
    return None
