"""
Notification and Human-in-the-Loop Approval Routes
===================================================
Provides REST endpoints for:
- Listing and querying notifications (GET /api/notifications)
- Retrieving single notification details (GET /api/notifications/{notification_id})
- Executing human approval for selected actions (POST /api/notifications/{notification_id}/accept)
- Recording human rejection without execution (POST /api/notifications/{notification_id}/reject)
- Retrieving action audit history (GET /api/notifications/actions/history)

SAFETY GUARANTEES:
- Strictly enforces explicit human approval (explicit_approval=True, approved_by non-empty).
- Prohibits all physical machinery control operations.
- Duplicate approval and duplicate rejection protection (409 Conflict).
- Orchestrates via action_executor_service without embedding SMTP or low-level logic in routes.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from datetime import datetime
from typing import Optional, List, Dict, Any

from services.auth_service import get_current_user

from app.schemas import (
    NotificationItem,
    NotificationListResponse,
    AcceptNotificationRequest,
    AcceptNotificationResponse,
    RejectNotificationRequest,
    RejectNotificationResponse,
    ActionHistoryResponse
)
from services import notification_service
from services import action_executor_service
from services import machine_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])

UNRESOLVED_STATUSES = {"PENDING", "ACTION_IN_PROGRESS", "VERIFICATION_PENDING"}


def _format_notification_item(raw: Dict[str, Any]) -> NotificationItem:
    """Safely converts raw CSV dictionary into typed NotificationItem schema."""
    prob_raw = raw.get("failure_probability", 0.0)
    try:
        failure_prob = float(prob_raw)
    except Exception:
        failure_prob = 0.0

    raw_rec = raw.get("recommendation", "")
    if isinstance(raw_rec, str) and ";" in raw_rec:
        recommendations = [r.strip() for r in raw_rec.split(";") if r.strip()]
    elif isinstance(raw_rec, list):
        recommendations = raw_rec
    elif raw_rec:
        recommendations = [str(raw_rec).strip()]
    else:
        recommendations = []

    return NotificationItem(
        notification_id=str(raw.get("notification_id", "")).strip(),
        machine_id=str(raw.get("machine_id", "")).strip(),
        timestamp=raw.get("timestamp"),
        severity=str(raw.get("severity", "MEDIUM")).strip().upper(),
        title=str(raw.get("title", "")).strip(),
        message=str(raw.get("message", "")).strip(),
        component=str(raw.get("component", "")).strip(),
        root_cause=str(raw.get("root_cause", "")).strip(),
        failure_probability=failure_prob,
        recommendation=recommendations,
        status=str(raw.get("status", "PENDING")).strip().upper(),
        created_at=str(raw.get("created_at", "")).strip(),
        resolved_at=raw.get("resolved_at") or None,
        rejection_reason=raw.get("rejection_reason") or None
    )


@router.get("", response_model=NotificationListResponse)
def get_notifications(
    status: Optional[str] = Query(None, description="Filter by status (e.g. PENDING, ALL)"),
    machine_id: Optional[str] = Query(None, description="Filter by machine ID (e.g. M_003)"),
    severity: Optional[str] = Query(None, description="Filter by severity (e.g. HIGH, MEDIUM)")
):
    """
    Retrieves persisted notification records.
    Default behavior returns active/unresolved notifications (PENDING, ACTION_IN_PROGRESS, VERIFICATION_PENDING).
    Pass status='ALL' to retrieve all notifications.
    """
    raw_list = notification_service.get_notifications(
        machine_id=machine_id,
        severity=severity
    )

    clean_status = status.strip().upper() if status else None

    filtered: List[NotificationItem] = []
    for item in raw_list:
        item_status = str(item.get("status", "")).strip().upper()

        if clean_status == "ALL":
            pass
        elif clean_status:
            if item_status != clean_status:
                continue
        else:
            # Default to unresolved notifications
            if item_status not in UNRESOLVED_STATUSES:
                continue

        filtered.append(_format_notification_item(item))

    return NotificationListResponse(
        notifications=filtered,
        count=len(filtered)
    )


@router.get("/actions/history", response_model=ActionHistoryResponse)
def get_action_history(
    machine_id: Optional[str] = Query(None, description="Filter by machine ID"),
    notification_id: Optional[str] = Query(None, description="Filter by notification ID"),
    status: Optional[str] = Query(None, description="Filter by action status (COMPLETED, FAILED)"),
    action_type: Optional[str] = Query(None, description="Filter by action type")
):
    """
    Retrieves the persistent software action audit trail from action_records.csv.
    """
    records = action_executor_service.get_action_records(
        machine_id=machine_id,
        notification_id=notification_id,
        action_type=action_type
    )

    if status:
        norm_status = status.strip().upper()
        records = [r for r in records if str(r.get("status", "")).strip().upper() == norm_status]

    return ActionHistoryResponse(
        actions=records,
        count=len(records)
    )


@router.get("/{notification_id}", response_model=NotificationItem)
def get_single_notification(notification_id: str):
    """
    Retrieves a single notification by notification_id.
    Returns HTTP 404 if not found.
    """
    raw = notification_service.get_notification(notification_id)
    if not raw:
        raise HTTPException(status_code=404, detail=f"Notification '{notification_id}' not found")

    return _format_notification_item(raw)


@router.post("/{notification_id}/accept", response_model=AcceptNotificationResponse)
def accept_notification(
    notification_id: str,
    req: AcceptNotificationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Explicit human operator approval endpoint.
    Executes operator-selected software actions in sequence through Action Executor.
    Prevents duplicate acceptance (HTTP 409).
    """
    # 1. Validate explicit approval
    if not req.explicit_approval:
        raise HTTPException(
            status_code=400,
            detail="Explicit human approval flag ('explicit_approval') must be true."
        )

    # Use authenticated operator email for audit attribution
    clean_approver = current_user.get("email") or current_user.get("name") or req.approved_by.strip()
    if not clean_approver:
        raise HTTPException(
            status_code=400,
            detail="Approver identity ('approved_by') is required and cannot be empty."
        )

    if not req.approved_actions:
        raise HTTPException(
            status_code=400,
            detail="At least one action must be explicitly selected in 'approved_actions'."
        )

    # 2. Check notification exists
    notif = notification_service.get_notification(notification_id)
    if not notif:
        raise HTTPException(status_code=404, detail=f"Notification '{notification_id}' not found")

    current_status = str(notif.get("status", "")).strip().upper()

    # 3. Check duplicate approval or non-actionable status
    if current_status in ("ACTION_IN_PROGRESS", "VERIFICATION_PENDING", "COMPLETED"):
        raise HTTPException(
            status_code=409,
            detail=f"Notification '{notification_id}' has already been approved (current status: '{current_status}'). Duplicate acceptance prevented."
        )
    if current_status == "REJECTED":
        raise HTTPException(
            status_code=409,
            detail=f"Notification '{notification_id}' was rejected by operator and cannot be accepted."
        )
    if current_status != "PENDING":
        raise HTTPException(
            status_code=409,
            detail=f"Notification '{notification_id}' is not actionable (current status: '{current_status}')."
        )

    # 4. Check action whitelist & prohibited physical commands
    for action in req.approved_actions:
        norm_a = str(action).strip().lower()
        for prohibited in action_executor_service.PROHIBITED_ACTION_KEYWORDS:
            if prohibited in norm_a:
                raise HTTPException(
                    status_code=400,
                    detail=f"Safety violation: Physical machinery control action '{action}' is strictly prohibited."
                )
        if norm_a not in action_executor_service.ALLOWED_ACTION_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid action type '{action}'. Allowed types: {sorted(action_executor_service.ALLOWED_ACTION_TYPES)}"
            )

    # 5. Check machine exists
    machine_id = str(notif.get("machine_id", "")).strip()
    machine = machine_service.get_machine(machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail=f"Machine '{machine_id}' not found in registry.")

    # 6. Lifecycle transition: Set status to ACTION_IN_PROGRESS before execution
    notification_service.update_notification_status(
        notification_id=notification_id,
        status="ACTION_IN_PROGRESS"
    )

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    action_results: List[Dict[str, Any]] = []
    any_success = False

    # 7. Execute selected actions sequentially through Action Executor
    for action_type in req.approved_actions:
        res = action_executor_service.execute_action(
            action_type=action_type,
            notification_id=notification_id,
            explicit_approval=True,
            approved_by=clean_approver,
            priority=notif.get("severity", "MEDIUM"),
            reason=notif.get("recommendation") or notif.get("root_cause"),
            component=notif.get("component"),
            notes=req.notes,
            allow_in_progress=True,
            update_notification=False
        )

        success = res.get("success", False)
        if success:
            any_success = True

        action_results.append({
            "action_id": res.get("action_id"),
            "action_type": action_type,
            "status": res.get("status", "FAILED"),
            "verification_status": res.get("verification_status", "FAILED"),
            "result": res.get("result") or res.get("error", "Execution finished"),
            "success": success,
            "details": res.get("details", {})
        })

    # 8. Set final notification status
    final_status = "VERIFICATION_PENDING" if any_success else "FAILED"
    notification_service.update_notification_status(
        notification_id=notification_id,
        status=final_status
    )

    return AcceptNotificationResponse(
        notification_id=notification_id,
        status=final_status,
        approved_by=clean_approver,
        approved_at=now_str,
        actions=action_results,
        message=(
            "Approved maintenance actions recorded in software backlog. "
            "Physical machine recovery requires new telemetry."
        )
    )


@router.post("/{notification_id}/reject", response_model=RejectNotificationResponse)
def reject_notification(
    notification_id: str,
    req: RejectNotificationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Explicit human operator rejection endpoint.
    Marks notification as REJECTED without executing any software or physical action.
    Prevents duplicate rejection (HTTP 409).
    """
    # Use authenticated operator email for audit attribution
    clean_rejecter = current_user.get("email") or current_user.get("name") or req.rejected_by.strip()
    if not clean_rejecter:
        raise HTTPException(
            status_code=400,
            detail="Rejecter identity ('rejected_by') is required and cannot be empty."
        )

    # 1. Check notification exists
    notif = notification_service.get_notification(notification_id)
    if not notif:
        raise HTTPException(status_code=404, detail=f"Notification '{notification_id}' not found")

    current_status = str(notif.get("status", "")).strip().upper()

    # 2. Check duplicate rejection or non-rejectable status
    if current_status == "REJECTED":
        raise HTTPException(
            status_code=409,
            detail=f"Notification '{notification_id}' has already been rejected."
        )
    if current_status in ("ACTION_IN_PROGRESS", "VERIFICATION_PENDING", "COMPLETED"):
        raise HTTPException(
            status_code=409,
            detail=f"Notification '{notification_id}' has already been approved (status: '{current_status}') and cannot be rejected."
        )
    if current_status != "PENDING":
        raise HTTPException(
            status_code=409,
            detail=f"Notification '{notification_id}' cannot be rejected in status '{current_status}'."
        )

    # 3. Update status to REJECTED with rejection reason
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    reason_str = req.rejection_reason.strip() if req.rejection_reason else "Operator rejected recommendation."

    updated = notification_service.update_notification_status(
        notification_id=notification_id,
        status="REJECTED",
        rejection_reason=f"Rejected by {clean_rejecter}: {reason_str}"
    )

    return RejectNotificationResponse(
        notification_id=notification_id,
        status="REJECTED",
        rejected_by=clean_rejecter,
        rejected_at=now_str,
        rejection_reason=reason_str,
        message="Recommendation rejected. No action was executed."
    )
