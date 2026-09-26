"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { NotificationItem } from "../types";
import { getNotifications } from "../lib/api";
import { ApprovalModal } from "./ApprovalModal";
import {
  Bell,
  AlertTriangle,
  ShieldCheck,
  XCircle,
  Loader2,
  ChevronRight,
  RefreshCw
} from "lucide-react";

interface NotificationCenterProps {
  onActionComplete?: () => void;
  machineIdFilter?: string;
}

export function NotificationCenter({
  onActionComplete,
  machineIdFilter
}: NotificationCenterProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal State for Review/Accept/Reject
  const [selectedNotification, setSelectedNotification] = useState<NotificationItem | null>(null);
  const [modalMode, setModalMode] = useState<"accept" | "reject">("accept");
  const [isModalOpen, setIsModalOpen] = useState(false);

  const dropdownRef = useRef<HTMLDivElement>(null);

  const fetchNotifications = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getNotifications({
        machine_id: machineIdFilter || undefined
      });
      setNotifications(res.notifications || []);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Unable to load notifications from server.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 10000);
    return () => clearInterval(interval);
  }, [machineIdFilter]);

  // Close dropdown on outside click or Escape key, unless ApprovalModal is open
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        if (!isModalOpen) {
          setIsOpen(false);
        }
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        if (!isModalOpen) {
          setIsOpen(false);
        }
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isModalOpen]);

  const handleOpenModal = (notif: NotificationItem, mode: "accept" | "reject") => {
    setSelectedNotification(notif);
    setModalMode(mode);
    setIsModalOpen(true);
  };

  const handleModalSuccess = () => {
    fetchNotifications();
    if (onActionComplete) {
      onActionComplete();
    }
  };

  // Filter only unresolved notifications: PENDING, ACTION_IN_PROGRESS, VERIFICATION_PENDING
  const unresolvedNotifications = notifications.filter((n) => {
    const st = (n.status || "").toUpperCase();
    return (
      st === "PENDING" ||
      st === "ACTION_IN_PROGRESS" ||
      st === "VERIFICATION_PENDING"
    );
  });

  const unresolvedCount = unresolvedNotifications.length;

  // Sort: PENDING first, then by CRITICAL / HIGH severity
  const sortedNotifications = [...unresolvedNotifications].sort((a, b) => {
    const aPending = (a.status || "").toUpperCase() === "PENDING" ? 1 : 0;
    const bPending = (b.status || "").toUpperCase() === "PENDING" ? 1 : 0;
    if (aPending !== bPending) return bPending - aPending;

    const aCrit =
      (a.severity || "").toUpperCase() === "CRITICAL" ||
      (a.severity || "").toUpperCase() === "HIGH"
        ? 1
        : 0;
    const bCrit =
      (b.severity || "").toUpperCase() === "CRITICAL" ||
      (b.severity || "").toUpperCase() === "HIGH"
        ? 1
        : 0;
    return bCrit - aCrit;
  });

  return (
    <div className="relative" ref={dropdownRef}>
      {/* 1. TOP-RIGHT NOTIFICATION BELL ICON */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className={`relative p-2 rounded-lg border transition cursor-pointer flex items-center justify-center ${
          isOpen
            ? "bg-[#EFEFE8] border-[#171717] text-[#171717]"
            : "bg-[#FAFAF5] hover:bg-[#EFEFE8] border-[#DCDCD4] text-[#171717]"
        }`}
        title="Maintenance Notifications"
        aria-label="Maintenance Notifications"
        aria-expanded={isOpen}
      >
        <Bell className="w-4 h-4" />
        {unresolvedCount > 0 ? (
          <span className="absolute -top-1.5 -right-1.5 flex h-4 min-w-4 px-1 items-center justify-center rounded-full bg-[#9E2A2B] text-[10px] font-bold text-white shadow-2xs">
            {unresolvedCount}
          </span>
        ) : (
          <span className="absolute -top-1 -right-1 flex h-3.5 min-w-3.5 px-0.5 items-center justify-center rounded-full bg-[#E8E8E0] text-[9px] font-bold text-[#6B6B66]">
            0
          </span>
        )}
      </button>

      {/* 2. COLLAPSIBLE NOTIFICATION DROPDOWN PANEL */}
      {isOpen && (
        <div
          className="absolute right-0 top-full mt-2 z-40 w-[380px] sm:w-[390px] max-w-[calc(100vw-24px)] max-h-[70vh] flex flex-col bg-[#FAFAF5] rounded-xl border border-[#DCDCD4] shadow-lg overflow-hidden animate-in fade-in slide-in-from-top-2 duration-150"
          style={{ scrollbarWidth: "thin" }}
        >
          {/* Dropdown Header */}
          <div className="p-3.5 border-b border-[#DCDCD4] bg-[#F5F5EE] flex items-center justify-between shrink-0">
            <div className="flex items-center space-x-2">
              <div className="p-1 rounded bg-[#EFEFE8] text-[#171717]">
                <Bell className="w-3.5 h-3.5" />
              </div>
              <h4 className="text-xs font-bold text-[#171717]">
                Notifications
              </h4>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-[#ECECE5] text-[#171717]">
                {unresolvedCount}
              </span>
            </div>
            <button
              type="button"
              onClick={fetchNotifications}
              disabled={loading}
              className="p-1 rounded text-[#6B6B66] hover:text-[#171717] hover:bg-[#E8E8E0] transition cursor-pointer"
              title="Refresh Notifications"
            >
              <RefreshCw
                className={`w-3.5 h-3.5 ${
                  loading ? "animate-spin text-[#171717]" : ""
                }`}
              />
            </button>
          </div>

          {/* Scrollable Notifications List */}
          <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
            {/* Error Message */}
            {error && (
              <div className="p-2.5 rounded-lg bg-[#FDF0EE] border border-[#F2C2BD] text-[#9E2A2B] text-[11px] flex items-center justify-between">
                <div className="flex items-center space-x-1.5 truncate">
                  <AlertTriangle className="w-3.5 h-3.5 text-[#9E2A2B] shrink-0" />
                  <span className="truncate">Unable to sync alerts</span>
                </div>
                <button
                  type="button"
                  onClick={fetchNotifications}
                  className="px-2 py-0.5 bg-[#9E2A2B] text-white rounded text-[10px] font-bold hover:bg-[#852324] cursor-pointer"
                >
                  Retry
                </button>
              </div>
            )}

            {/* Empty State when no unresolved notifications exist */}
            {!loading && !error && unresolvedCount === 0 && (
              <div className="py-8 px-4 text-center">
                <ShieldCheck className="w-7 h-7 text-[#1E4D2B] mx-auto mb-2 opacity-80" />
                <h4 className="text-xs font-bold text-[#171717]">
                  No pending alerts
                </h4>
                <p className="text-[11px] text-[#6B6B66] mt-1 max-w-xs mx-auto leading-relaxed">
                  All monitored assets are currently operating within the active notification threshold.
                </p>
              </div>
            )}

            {/* Notification Cards */}
            {sortedNotifications.map((notif) => {
              const st = (notif.status || "").toUpperCase();
              const isPending = st === "PENDING";
              const isVerification = st === "VERIFICATION_PENDING";
              const isProgress = st === "ACTION_IN_PROGRESS";
              const isCritical =
                (notif.severity || "").toUpperCase() === "CRITICAL" ||
                (notif.severity || "").toUpperCase() === "HIGH";

              // Short summary extraction
              const shortMessage = notif.message
                ? notif.message
                : Array.isArray(notif.recommendation) &&
                  notif.recommendation.length > 0
                ? String(notif.recommendation[0])
                : typeof notif.recommendation === "string"
                ? notif.recommendation.split(";")[0]
                : "Degradation detected. Review and schedule inspection.";

              return (
                <div
                  key={notif.notification_id}
                  className={`p-3 rounded-lg border transition-all ${
                    isPending && isCritical
                      ? "bg-[#FDF9F8] border-[#F2C2BD]"
                      : isPending
                      ? "bg-[#FCFAF5] border-[#EADBB8]"
                      : isVerification
                      ? "bg-[#F0F2FA] border-[#D0D4EA]"
                      : "bg-white border-[#DCDCD4]"
                  }`}
                >
                  {/* Card Header: Icon + Title + Severity Badge */}
                  <div className="flex items-center justify-between gap-2 pb-1.5 border-b border-[#E8E8E0]">
                    <div className="flex items-center space-x-1.5 min-w-0">
                      <div
                        className={`p-1 rounded shrink-0 ${
                          isCritical
                            ? "bg-[#FDF0EE] text-[#9E2A2B]"
                            : "bg-[#FAF4E8] text-[#8C5E14]"
                        }`}
                      >
                        <Bell className="w-3 h-3" />
                      </div>
                      <h5 className="text-xs font-bold text-[#171717] truncate">
                        {isCritical
                          ? "Critical Maintenance"
                          : "Maintenance Alert"}
                      </h5>
                    </div>
                    <span
                      className={`text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider shrink-0 border ${
                        isCritical
                          ? "bg-[#FDF0EE] text-[#9E2A2B] border-[#F2C2BD]"
                          : "bg-[#FAF4E8] text-[#8C5E14] border-[#EADBB8]"
                      }`}
                    >
                      {notif.severity}
                    </span>
                  </div>

                  {/* Machine ID • Component & ID */}
                  <div className="mt-2 flex items-center justify-between text-xs">
                    <div className="flex items-center space-x-1.5 font-mono font-bold text-[#171717]">
                      <span className="bg-[#ECECE5] text-[#171717] px-1.5 py-0.5 rounded text-[10px] border border-[#DCDCD4]">
                        {notif.machine_id}
                      </span>
                      <span className="text-[#8C8C85]">•</span>
                      <span className="text-[#555550] font-sans font-semibold">
                        {notif.component || "Bearing"}
                      </span>
                    </div>
                    <Link
                      href={`/machines/${notif.machine_id}`}
                      className="text-[11px] font-semibold text-[#171717] hover:underline flex items-center space-x-0.5 transition"
                      title="Inspect Machine Details"
                    >
                      <span>Inspect</span>
                      <ChevronRight className="w-3 h-3 text-[#6B6B66]" />
                    </Link>
                  </div>

                  {/* Diagnosed Root Cause */}
                  <div
                    className="mt-1 text-xs font-bold text-[#171717] truncate"
                    title={notif.root_cause}
                  >
                    {notif.root_cause || "Bearing Degradation"}
                  </div>

                  {/* Risk & Failure Metrics */}
                  <div className="mt-1 flex items-center space-x-2 text-[11px] font-semibold text-[#6B6B66]">
                    <span>
                      Risk:{" "}
                      <strong
                        className={
                          isCritical ? "text-[#9E2A2B]" : "text-[#8C5E14]"
                        }
                      >
                        {notif.severity}
                      </strong>
                    </span>
                    <span className="text-[#DCDCD4]">•</span>
                    <span>
                      Failure:{" "}
                      <strong className="text-[#9E2A2B] font-mono">
                        {(Number(notif.failure_probability || 0) * 100).toFixed(
                          0
                        )}
                        %
                      </strong>
                    </span>
                  </div>

                  {/* Short Message / Recommendation */}
                  <p className="mt-1 text-[11px] text-[#6B6B66] line-clamp-2 leading-snug">
                    {shortMessage}
                  </p>

                  {/* Action Buttons: ACCEPT on LEFT, REJECT on RIGHT */}
                  {isPending ? (
                    <div className="mt-2.5 pt-2 border-t border-[#E8E8E0] flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => handleOpenModal(notif, "accept")}
                        className="flex-1 inline-flex items-center justify-center space-x-1.5 py-1.5 px-3 rounded-lg font-bold bg-[#171717] hover:bg-[#262626] text-white text-xs shadow-2xs transition cursor-pointer"
                      >
                        <ShieldCheck className="w-3.5 h-3.5" />
                        <span>ACCEPT</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => handleOpenModal(notif, "reject")}
                        className="flex-1 inline-flex items-center justify-center space-x-1.5 py-1.5 px-3 rounded-lg font-bold bg-[#FAFAF5] hover:bg-[#FDF0EE] text-[#9E2A2B] border border-[#F2C2BD] text-xs shadow-2xs transition cursor-pointer"
                      >
                        <XCircle className="w-3.5 h-3.5" />
                        <span>REJECT</span>
                      </button>
                    </div>
                  ) : isVerification ? (
                    <div className="mt-2 pt-1.5 border-t border-[#D0D4EA] flex items-center justify-between text-[11px] text-[#2A3563]">
                      <div className="flex items-center space-x-1.5 font-medium">
                        <ShieldCheck className="w-3.5 h-3.5 text-[#2A3563] shrink-0" />
                        <span>Verification Pending</span>
                      </div>
                      <span className="text-[10px] text-[#2A3563]/80">
                        Awaiting Telemetry
                      </span>
                    </div>
                  ) : isProgress ? (
                    <div className="mt-2 pt-1.5 border-t border-[#DCDCD4] flex items-center space-x-1.5 text-[11px] text-[#171717]">
                      <Loader2 className="w-3.5 h-3.5 text-[#171717] animate-spin shrink-0" />
                      <span>Action in progress...</span>
                    </div>
                  ) : (
                    <div className="mt-2 pt-1.5 border-t border-[#E8E8E0] text-[11px] text-[#6B6B66] font-mono">
                      Status: {notif.status}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 3. EXISTING APPROVAL & REJECTION REVIEW MODAL (Higher z-50 index) */}
      <ApprovalModal
        isOpen={isModalOpen}
        mode={modalMode}
        notification={selectedNotification}
        onClose={() => setIsModalOpen(false)}
        onSuccess={handleModalSuccess}
      />
    </div>
  );
}
