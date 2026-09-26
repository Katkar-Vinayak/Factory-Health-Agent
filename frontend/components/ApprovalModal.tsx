"use client";

import React, { useState } from "react";
import {
  NotificationItem,
  AcceptNotificationResponse,
  RejectNotificationResponse,
  ActionResultItem
} from "../types";
import { acceptNotification, rejectNotification } from "../lib/api";
import {
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Loader2,
  ShieldCheck,
  Wrench,
  Mail,
  Calendar,
  FileCheck,
  AlertOctagon,
  Info,
  Clock,
  ExternalLink
} from "lucide-react";

interface ApprovalModalProps {
  isOpen: boolean;
  mode: "accept" | "reject";
  notification: NotificationItem | null;
  onClose: () => void;
  onSuccess: (result?: AcceptNotificationResponse | RejectNotificationResponse) => void;
}

const AVAILABLE_ACTIONS = [
  {
    id: "schedule_inspection",
    label: "Schedule Physical Inspection",
    description: "Dispatch maintenance team for diagnostic inspection of the component",
    icon: Calendar,
    defaultChecked: true
  },
  {
    id: "create_replacement_request",
    label: "Create Replacement Part Request",
    description: "Create purchase requisition from configured vendor catalog",
    icon: Wrench,
    defaultChecked: true
  },
  {
    id: "send_vendor_email",
    label: "Send Vendor RFQ / Part Inquiry",
    description: "Dispatch email inquiry to component supplier (simulated demo mode)",
    icon: Mail,
    defaultChecked: true
  },
  {
    id: "create_maintenance_ticket",
    label: "Create Maintenance Work Order",
    description: "Log an official work order ticket in plant maintenance queue",
    icon: FileCheck,
    defaultChecked: false
  },
  {
    id: "create_alert",
    label: "Broadcast Floor Alert",
    description: "Issue high-priority notification to plant operations console",
    icon: AlertOctagon,
    defaultChecked: false
  }
];

export function ApprovalModal({
  isOpen,
  mode,
  notification,
  onClose,
  onSuccess
}: ApprovalModalProps) {
  const [operatorId, setOperatorId] = useState("demo_operator");
  const [selectedActions, setSelectedActions] = useState<string[]>([
    "schedule_inspection",
    "create_replacement_request",
    "send_vendor_email"
  ]);
  const [notes, setNotes] = useState("");
  const [rejectionReason, setRejectionReason] = useState(
    "Maintenance will be reviewed during next scheduled shift."
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [executionResult, setExecutionResult] = useState<AcceptNotificationResponse | null>(null);

  if (!isOpen || !notification) return null;

  const toggleAction = (actionId: string) => {
    setSelectedActions((prev) =>
      prev.includes(actionId)
        ? prev.filter((id) => id !== actionId)
        : [...prev, actionId]
    );
  };

  const handleAccept = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!operatorId.trim()) {
      setError("Operator identifier is required.");
      return;
    }
    if (selectedActions.length === 0) {
      setError("Please select at least one approved action.");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const res = await acceptNotification(notification.notification_id, {
        explicit_approval: true,
        approved_by: operatorId.trim(),
        approved_actions: selectedActions,
        notes: notes.trim() || undefined
      });
      setExecutionResult(res);
      onSuccess(res);
    } catch (err: unknown) {
      if (err instanceof Error) {
        if (err.message.includes("409") || err.message.toLowerCase().includes("already")) {
          setError("This notification has already been processed or approved.");
        } else {
          setError(err.message);
        }
      } else {
        setError("Failed to process approval.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleReject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!operatorId.trim()) {
      setError("Operator identifier is required.");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const res = await rejectNotification(notification.notification_id, {
        rejected_by: operatorId.trim(),
        rejection_reason: rejectionReason.trim() || undefined
      });
      onSuccess(res);
      onClose();
    } catch (err: unknown) {
      if (err instanceof Error) {
        if (err.message.includes("409") || err.message.toLowerCase().includes("already")) {
          setError("This notification has already been processed or rejected.");
        } else {
          setError(err.message);
        }
      } else {
        setError("Failed to reject notification.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-[#FAFAF5] rounded-xl max-w-2xl w-full p-6 sm:p-7 shadow-xl border border-[#DCDCD4] animate-fadeIn">
        {/* Modal Header */}
        <div className="flex items-start justify-between pb-4 border-b border-[#DCDCD4]">
          <div className="flex items-center space-x-3">
            <div
              className={`p-2 rounded-lg text-white shadow-2xs ${
                mode === "accept"
                  ? "bg-[#171717]"
                  : "bg-[#9C382E]"
              }`}
            >
              {mode === "accept" ? (
                <ShieldCheck className="w-5 h-5" />
              ) : (
                <AlertTriangle className="w-5 h-5" />
              )}
            </div>
            <div>
              <h2 className="text-base sm:text-lg font-bold text-[#171717]">
                {mode === "accept"
                  ? "Human Approval — Maintenance Execution Gate"
                  : "Reject Recommendation"}
              </h2>
              <p className="text-xs text-[#6B6B66]">
                Notification <span className="font-mono font-semibold text-[#171717]">{notification.notification_id}</span> • Machine{" "}
                <span className="font-mono font-semibold text-[#171717]">{notification.machine_id}</span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={submitting}
            className="text-[#6B6B66] hover:text-[#171717] p-1 rounded hover:bg-[#EFEFE8] transition cursor-pointer"
          >
            ✕
          </button>
        </div>

        {/* If Execution Result is present, show structured outcome */}
        {executionResult ? (
          <div className="mt-5 space-y-4">
            <div className="p-4 rounded-lg bg-[#EDF5EE] border border-[#94C09A] text-[#1D4E29]">
              <div className="flex items-center space-x-2">
                <CheckCircle2 className="w-5 h-5 text-[#2A6E3B] shrink-0" />
                <h3 className="text-sm font-semibold">
                  Approved Actions Executed Successfully
                </h3>
              </div>
              <p className="text-xs text-[#2A6E3B] mt-1">
                {executionResult.message}
              </p>
              <div className="mt-2 flex flex-wrap gap-3 text-[11px] font-mono text-[#1D4E29]">
                <span>Status: <strong>{executionResult.status}</strong></span>
                <span>Approved By: <strong>{executionResult.approved_by}</strong></span>
                <span>Timestamp: <strong>{new Date(executionResult.approved_at).toLocaleTimeString()}</strong></span>
              </div>
            </div>

            {/* Verification Safe Guard Banner */}
            <div className="p-3.5 rounded-lg bg-[#F5F5EE] border border-[#DCDCD4] text-[#171717] text-xs flex items-start space-x-2.5">
              <Info className="w-4 h-4 text-[#6B6B66] shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-[#171717]">
                  Verification Safeguard Active
                </p>
                <p className="text-[#6B6B66] mt-0.5">
                  Software actions have been recorded. Physical machine recovery requires verified sensor telemetry and remains in <strong>VERIFICATION_PENDING</strong>.
                </p>
              </div>
            </div>

            {/* Per-Action Execution Breakdown */}
            <div>
              <h4 className="text-xs font-mono font-medium uppercase tracking-wider text-[#6B6B66] mb-2">
                Per-Action Execution Results ({executionResult.actions.length})
              </h4>
              <div className="space-y-2">
                {executionResult.actions.map((act: ActionResultItem, idx: number) => {
                  const isSimulated = act.status === "SIMULATED";
                  const isPending = act.status === "VERIFICATION_PENDING";
                  const isFailed = act.status === "FAILED";

                  return (
                    <div
                      key={idx}
                      className="p-3 rounded-md border border-[#DCDCD4] bg-white flex items-center justify-between text-xs"
                    >
                      <div className="flex items-center space-x-2.5">
                        <span className="font-mono font-semibold text-[#171717]">
                          {act.action_type}
                        </span>
                        {act.action_id && (
                          <span className="font-mono text-[10px] text-[#6B6B66] bg-[#F5F5EE] px-1.5 py-0.5 rounded border border-[#DCDCD4]">
                            {act.action_id}
                          </span>
                        )}
                      </div>

                      <div className="flex items-center space-x-2">
                        {isSimulated ? (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-[#FAF4E8] text-[#8B6E28] border border-[#E8DFC8]">
                            Vendor email: SIMULATED
                          </span>
                        ) : isPending ? (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-[#F5F5EE] text-[#4A4A45] border border-[#DCDCD4]">
                            VERIFICATION_PENDING
                          </span>
                        ) : isFailed ? (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-[#FDF0EE] text-[#9C382E] border border-[#DE9E98]">
                            FAILED
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-[#EDF5EE] text-[#2A6E3B] border border-[#94C09A]">
                            {act.status}
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-md font-semibold bg-[#171717] hover:bg-[#262626] text-white text-xs transition cursor-pointer"
              >
                Close &amp; Return to Dashboard
              </button>
            </div>
          </div>
        ) : mode === "accept" ? (
          /* Accept Form */
          <form onSubmit={handleAccept} className="mt-5 space-y-5">
            {/* Machine & Root Cause Context Card */}
            <div className="p-3.5 rounded-lg bg-[#F5F5EE] border border-[#DCDCD4] grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
              <div>
                <span className="text-[#6B6B66] font-mono uppercase text-[10px]">Target Machine</span>
                <p className="font-semibold text-[#171717] font-mono text-sm mt-0.5">
                  {notification.machine_id}
                </p>
              </div>
              <div>
                <span className="text-[#6B6B66] font-mono uppercase text-[10px]">Component</span>
                <p className="font-semibold text-[#171717] text-sm mt-0.5">
                  {notification.component || "Bearing"}
                </p>
              </div>
              <div>
                <span className="text-[#6B6B66] font-mono uppercase text-[10px]">Diagnosed Root Cause</span>
                <p className="font-semibold text-[#171717] text-sm mt-0.5 truncate" title={notification.root_cause}>
                  {notification.root_cause || "Bearing Degradation"}
                </p>
              </div>
            </div>

            {/* Explicit Action Selection */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-mono font-semibold uppercase tracking-wider text-[#171717]">
                  Select Approved Actions (Human Authorization Gate):
                </label>
                <span className="text-[11px] text-[#6B6B66]">
                  Physical control commands strictly blocked
                </span>
              </div>

              <div className="space-y-2">
                {AVAILABLE_ACTIONS.map((action) => {
                  const Icon = action.icon;
                  const isChecked = selectedActions.includes(action.id);

                  return (
                    <label
                      key={action.id}
                      className={`flex items-start space-x-3 p-3 rounded-lg border transition cursor-pointer select-none ${
                        isChecked
                          ? "bg-white border-[#171717] ring-1 ring-[#171717]"
                          : "bg-white border-[#DCDCD4] hover:bg-[#F5F5EE]"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => toggleAction(action.id)}
                        disabled={submitting}
                        className="mt-0.5 h-4 w-4 rounded border-[#DCDCD4] accent-[#171717] cursor-pointer"
                      />
                      <div className="flex-1">
                        <div className="flex items-center space-x-2">
                          <Icon className="w-3.5 h-3.5 text-[#6B6B66]" />
                          <span className="text-xs font-semibold text-[#171717]">
                            {action.label}
                          </span>
                        </div>
                        <p className="text-[11px] text-[#6B6B66] mt-0.5">
                          {action.description}
                        </p>
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>

            {/* Operator Identifier Audit Field */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              <div>
                <label className="block text-xs font-semibold text-[#171717] mb-1">
                  Operator Identity (Audit Trail):
                </label>
                <input
                  type="text"
                  value={operatorId}
                  onChange={(e) => setOperatorId(e.target.value)}
                  disabled={submitting}
                  className="w-full px-3 py-1.5 rounded-md text-xs bg-white border border-[#DCDCD4] font-mono text-[#171717] focus:outline-hidden focus:border-[#171717]"
                  placeholder="e.g. demo_operator"
                  required
                />
                <p className="text-[10px] text-[#6B6B66] mt-1">
                  Operator audit attribution for hackathon demo (non-auth)
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#171717] mb-1">
                  Optional Operator Notes:
                </label>
                <input
                  type="text"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  disabled={submitting}
                  className="w-full px-3 py-1.5 rounded-md text-xs bg-white border border-[#DCDCD4] text-[#171717] focus:outline-hidden focus:border-[#171717]"
                  placeholder="e.g. Approved during morning shift"
                />
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div className="p-3 rounded-md bg-[#FDF0EE] border border-[#DE9E98] text-[#9C382E] text-xs flex items-center space-x-2">
                <AlertTriangle className="w-4 h-4 text-[#9C382E] shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* Actions Footer */}
            <div className="flex items-center justify-end space-x-2.5 pt-3 border-t border-[#DCDCD4]">
              <button
                type="button"
                onClick={onClose}
                disabled={submitting}
                className="px-4 py-2 rounded-md text-xs font-medium text-[#4A4A45] border border-[#DCDCD4] bg-white hover:bg-[#F5F5EE] transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting || selectedActions.length === 0}
                className="inline-flex items-center space-x-2 px-5 py-2 rounded-md font-semibold bg-[#171717] hover:bg-[#262626] text-white text-xs shadow-xs transition disabled:opacity-50 cursor-pointer"
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-white" />
                    <span>Processing Approval...</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Confirm &amp; Execute ({selectedActions.length} Actions)</span>
                  </>
                )}
              </button>
            </div>
          </form>
        ) : (
          /* Reject Form */
          <form onSubmit={handleReject} className="mt-5 space-y-5">
            <div className="p-4 rounded-lg bg-[#FDF0EE] border border-[#DE9E98] text-xs text-[#9C382E]">
              <p className="font-semibold">
                Are you sure you want to reject this maintenance recommendation?
              </p>
              <p className="mt-1">
                Zero actions will be dispatched. The notification will be marked as REJECTED and archived in the plant audit log.
              </p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#171717] mb-1">
                Operator Identity (Audit Trail):
              </label>
              <input
                type="text"
                value={operatorId}
                onChange={(e) => setOperatorId(e.target.value)}
                disabled={submitting}
                className="w-full px-3 py-1.5 rounded-md text-xs bg-white border border-[#DCDCD4] font-mono text-[#171717] focus:outline-hidden focus:border-[#171717]"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#171717] mb-1">
                Rejection Reason:
              </label>
              <textarea
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                disabled={submitting}
                rows={3}
                className="w-full px-3 py-2 rounded-md text-xs bg-white border border-[#DCDCD4] text-[#171717] focus:outline-hidden focus:border-[#171717]"
                placeholder="State reason for rejecting maintenance recommendation..."
              />
            </div>

            {error && (
              <div className="p-3 rounded-md bg-[#FDF0EE] border border-[#DE9E98] text-[#9C382E] text-xs flex items-center space-x-2">
                <AlertTriangle className="w-4 h-4 text-[#9C382E] shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div className="flex items-center justify-end space-x-2.5 pt-3 border-t border-[#DCDCD4]">
              <button
                type="button"
                onClick={onClose}
                disabled={submitting}
                className="px-4 py-2 rounded-md text-xs font-medium text-[#4A4A45] border border-[#DCDCD4] bg-white hover:bg-[#F5F5EE] transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="inline-flex items-center space-x-2 px-5 py-2 rounded-md font-semibold bg-[#9C382E] hover:bg-[#852E25] text-white text-xs shadow-xs transition disabled:opacity-50 cursor-pointer"
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-white" />
                    <span>Rejecting...</span>
                  </>
                ) : (
                  <>
                    <XCircle className="w-4 h-4" />
                    <span>Confirm Rejection</span>
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
