"use client";

import React, { useState, useEffect } from "react";
import { ActionRecord } from "../types";
import { getActionHistory } from "../lib/api";
import {
  History,
  RefreshCw,
  Search,
  Filter,
  Loader2,
  Calendar,
  Wrench,
  Mail,
  FileCheck,
  AlertOctagon,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  Info
} from "lucide-react";

interface ActionHistoryTableProps {
  machineIdFilter?: string;
  refreshTrigger?: number;
}

export function ActionHistoryTable({
  machineIdFilter,
  refreshTrigger
}: ActionHistoryTableProps) {
  const [actions, setActions] = useState<ActionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [riskFilter, setRiskFilter] = useState<"ALL" | "HIGH" | "MEDIUM" | "LOW">("ALL");
  const [pageSize, setPageSize] = useState<number>(10);
  const [expandedActionId, setExpandedActionId] = useState<string | null>(null);

  const fetchHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getActionHistory({
        machine_id: machineIdFilter || undefined
      });
      setActions(res.actions || []);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Unable to retrieve action audit history.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [machineIdFilter, refreshTrigger]);

  const getActionIcon = (actionType: string) => {
    switch (actionType) {
      case "schedule_inspection":
        return Calendar;
      case "create_replacement_request":
        return Wrench;
      case "send_vendor_email":
        return Mail;
      case "create_maintenance_ticket":
        return FileCheck;
      case "create_alert":
        return AlertOctagon;
      default:
        return Wrench;
    }
  };

  const formatActionName = (actionType: string) => {
    switch (actionType) {
      case "schedule_inspection":
        return "Schedule Inspection";
      case "create_replacement_request":
        return "Create Replacement Request";
      case "send_vendor_email":
        return "Send Vendor Email";
      case "create_maintenance_ticket":
        return "Create Maintenance Ticket";
      case "create_alert":
        return "Create Alert";
      case "update_machine_status":
        return "Update Machine Status";
      default:
        return actionType.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    }
  };

  // 1. Apply risk filter and search query
  const filteredActions = actions.filter((act) => {
    if (riskFilter !== "ALL") {
      const priority = (act.priority || "").trim().toUpperCase();
      if (riskFilter === "HIGH") {
        if (priority !== "HIGH" && priority !== "CRITICAL") return false;
      } else if (riskFilter === "MEDIUM") {
        if (priority !== "MEDIUM") return false;
      } else if (riskFilter === "LOW") {
        if (priority !== "LOW" && priority !== "NORMAL") return false;
      }
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchId = (act.action_id || "").toLowerCase().includes(q);
      const matchMachine = (act.machine_id || "").toLowerCase().includes(q);
      const matchType = (act.action_type || "").toLowerCase().includes(q);
      const matchComp = (act.component || "").toLowerCase().includes(q);
      const matchNotif = (act.notification_id || "").toLowerCase().includes(q);
      return matchId || matchMachine || matchType || matchComp || matchNotif;
    }

    return true;
  });

  // 2. Sort using existing/latest timestamp logic (most recent records first)
  const parseTime = (dateStr?: string | null): number => {
    if (!dateStr) return 0;
    const normalized = dateStr.includes("T") ? dateStr : dateStr.replace(" ", "T");
    const t = new Date(normalized).getTime();
    return isNaN(t) ? 0 : t;
  };

  const sortedActions = [...filteredActions].sort((a, b) => {
    const timeA = parseTime(a.approved_at || a.completed_at);
    const timeB = parseTime(b.approved_at || b.completed_at);
    if (timeA !== timeB) {
      return timeB - timeA;
    }
    return (b.action_id || "").localeCompare(a.action_id || "", undefined, { numeric: true });
  });

  // 3. Take/display selected number (default 10)
  const displayedActions = sortedActions.slice(0, pageSize);

  return (
    <div className="bg-[#FAFAF5] rounded-xl border border-[#DCDCD4] shadow-2xs p-5 sm:p-6 mb-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#DCDCD4]">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-[#171717] text-white rounded-lg shadow-2xs">
            <History className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-base font-bold text-[#171717] tracking-tight">
                Maintenance Action Audit Trail
              </h2>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-[#F0F0EA] text-[#4A4A45] border border-[#DCDCD4]">
                Action History
              </span>
            </div>
            <p className="text-xs text-[#6B6B66] mt-0.5">
              Historical record of agent decisions and executed maintenance actions.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 self-start sm:self-auto">
          {/* Record Count Dropdown: 10 (default), 20, 30, 40, 50 */}
          <div className="flex items-center space-x-1.5 text-xs">
            <label htmlFor="audit-record-count" className="text-xs text-[#6B6B66] font-medium whitespace-nowrap">
              Show:
            </label>
            <div className="relative">
              <select
                id="audit-record-count"
                aria-label="Records to show"
                value={pageSize}
                onChange={(e) => setPageSize(Number(e.target.value))}
                className="appearance-none bg-white border border-[#DCDCD4] text-[#171717] text-xs font-semibold rounded-md pl-3 pr-7 py-1.5 shadow-2xs focus:outline-hidden focus:border-[#171717] cursor-pointer hover:bg-[#F5F5EE] transition"
              >
                {[10, 20, 30, 40, 50].map((num) => (
                  <option key={num} value={num}>
                    {num}
                  </option>
                ))}
              </select>
              <ChevronDown className="w-3.5 h-3.5 text-[#6B6B66] pointer-events-none absolute right-2 top-1/2 -translate-y-1/2" />
            </div>
          </div>

          {/* Risk Filter Dropdown: All (default), High, Medium, Low */}
          <div className="flex items-center space-x-1.5 text-xs">
            <label htmlFor="audit-risk-filter" className="text-xs text-[#6B6B66] font-medium whitespace-nowrap">
              Filter:
            </label>
            <div className="relative">
              <select
                id="audit-risk-filter"
                aria-label="Filter by risk"
                value={riskFilter}
                onChange={(e) => setRiskFilter(e.target.value as "ALL" | "HIGH" | "MEDIUM" | "LOW")}
                className="appearance-none bg-white border border-[#DCDCD4] text-[#171717] text-xs font-semibold rounded-md pl-3 pr-7 py-1.5 shadow-2xs focus:outline-hidden focus:border-[#171717] cursor-pointer hover:bg-[#F5F5EE] transition"
              >
                <option value="ALL">All</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>
              <ChevronDown className="w-3.5 h-3.5 text-[#6B6B66] pointer-events-none absolute right-2 top-1/2 -translate-y-1/2" />
            </div>
          </div>

          <button
            onClick={fetchHistory}
            disabled={loading}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-md border border-[#DCDCD4] text-xs font-medium text-[#4A4A45] bg-white hover:bg-[#F5F5EE] transition cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-[#171717]" : "text-[#6B6B66]"}`} />
            <span className="hidden sm:inline">Refresh Audit Log</span>
          </button>
        </div>
      </div>

      {/* Risk Filter Buttons and Search Bar */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 pt-3.5 pb-2">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#6B6B66]" />
          <input
            type="text"
            placeholder="Search action ID, machine, or type..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 rounded-md text-xs bg-white border border-[#DCDCD4] text-[#171717] placeholder-[#6B6B66] focus:outline-hidden focus:border-[#171717]"
          />
        </div>

        <div className="flex items-center space-x-1.5 text-xs overflow-x-auto pb-1 md:pb-0">
          <Filter className="w-3.5 h-3.5 text-[#6B6B66] mr-0.5 shrink-0" />
          <span className="text-[#6B6B66] text-xs font-medium mr-1">Filter:</span>
          {(
            [
              { key: "ALL", label: "All" },
              { key: "HIGH", label: "High" },
              { key: "MEDIUM", label: "Medium" },
              { key: "LOW", label: "Low" },
            ] as const
          ).map(({ key, label }) => {
            const isActive = riskFilter === key;
            return (
              <button
                key={key}
                type="button"
                id={`audit-filter-btn-${key.toLowerCase()}`}
                onClick={() => setRiskFilter(key)}
                className={`px-3 py-1 rounded-md text-xs font-semibold transition cursor-pointer whitespace-nowrap ${
                  isActive
                    ? key === "HIGH"
                      ? "bg-[#9C382E] text-white shadow-2xs"
                      : key === "MEDIUM"
                      ? "bg-[#8B6E28] text-white shadow-2xs"
                      : key === "LOW"
                      ? "bg-[#2A6E3B] text-white shadow-2xs"
                      : "bg-[#171717] text-white shadow-2xs"
                    : "bg-[#F5F5EE] text-[#4A4A45] border border-[#DCDCD4] hover:bg-[#EFEFE8] hover:text-[#171717]"
                }`}
              >
                {label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Record Counter Summary */}
      {!loading && !error && filteredActions.length > 0 && (
        <div className="flex items-center justify-between text-[11px] text-[#6B6B66] px-0.5 pt-1 pb-2">
          <span>
            Showing latest <strong className="text-[#171717] font-semibold">{displayedActions.length}</strong> of{" "}
            <strong className="text-[#171717] font-semibold">{filteredActions.length}</strong>{" "}
            {riskFilter !== "ALL" ? `${riskFilter} risk` : ""} records
            {actions.length !== filteredActions.length ? ` (${actions.length} total in audit trail)` : ""}
          </span>
          {displayedActions.length < filteredActions.length && (
            <span className="text-[#8C8C85] hidden sm:inline">
              Adjust &quot;Show&quot; dropdown above to view up to {pageSize === 50 ? "all" : "50"}
            </span>
          )}
        </div>
      )}

      {/* Loading State */}
      {loading && actions.length === 0 && (
        <div className="py-12 text-center text-[#6B6B66] text-xs">
          <Loader2 className="w-6 h-6 animate-spin text-[#171717] mx-auto mb-2" />
          <span>Retrieving action records...</span>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="mt-3 p-3 rounded-md bg-[#FDF0EE] border border-[#DE9E98] text-[#9C382E] text-xs">
          {error}
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && filteredActions.length === 0 && (
        <div className="py-12 text-center text-[#6B6B66]">
          <p className="text-xs font-semibold text-[#171717]">
            {riskFilter !== "ALL"
              ? `No ${riskFilter}-risk maintenance actions found.`
              : searchQuery.trim()
              ? "No maintenance actions matching search query."
              : "No maintenance actions recorded yet."}
          </p>
          <p className="text-[11px] text-[#6B6B66] mt-0.5">
            {riskFilter !== "ALL"
              ? "Try selecting 'All' or a different risk filter."
              : "Approved maintenance recommendations will be logged here."}
          </p>
        </div>
      )}

      {/* Audit Log Table */}
      {!loading && filteredActions.length > 0 && (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-[#DCDCD4] text-[#6B6B66] uppercase font-mono text-[10px]">
                <th className="py-2.5 px-3">Action ID</th>
                <th className="py-2.5 px-3">Machine</th>
                <th className="py-2.5 px-3">Action Type</th>
                <th className="py-2.5 px-3">Component</th>
                <th className="py-2.5 px-3">Risk Level</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Verification</th>
                <th className="py-2.5 px-3">Approved By / At</th>
                <th className="py-2.5 px-3 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#DCDCD4]">
              {displayedActions.map((act) => {
                const Icon = getActionIcon(act.action_type);
                const isExpanded = expandedActionId === act.action_id;
                const isSimulated = (act.status || "").toUpperCase() === "SIMULATED";
                const isVerification = (act.status || "").toUpperCase() === "VERIFICATION_PENDING";
                const isCompleted = (act.status || "").toUpperCase() === "COMPLETED";
                const isFailed = (act.status || "").toUpperCase() === "FAILED";

                let parsedResult: Record<string, unknown> | null = null;
                try {
                  if (act.result && typeof act.result === "string" && act.result.startsWith("{")) {
                    parsedResult = JSON.parse(act.result);
                  }
                } catch {
                  // Raw text
                }

                return (
                  <React.Fragment key={act.action_id}>
                    <tr className="hover:bg-[#F5F5EE]/70 transition">
                      <td className="py-3 px-3 font-mono font-semibold text-[#171717] whitespace-nowrap">
                        {act.action_id}
                      </td>
                      <td className="py-3 px-3">
                        <span className="font-mono text-[11px] font-semibold px-2 py-0.5 rounded bg-[#171717] text-white">
                          {act.machine_id}
                        </span>
                      </td>
                      <td className="py-3 px-3">
                        <div className="flex items-center space-x-2">
                          <Icon className="w-3.5 h-3.5 text-[#6B6B66] shrink-0" />
                          <span className="font-medium text-[#171717]">
                            {formatActionName(act.action_type)}
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-3 font-medium text-[#4A4A45]">
                        {act.component || "N/A"}
                      </td>
                      <td className="py-3 px-3">
                        <span
                          className={`font-mono text-[10px] font-semibold px-2 py-0.5 rounded ${
                            (act.priority || "").toUpperCase() === "HIGH" || (act.priority || "").toUpperCase() === "CRITICAL"
                              ? "bg-[#FDF0EE] text-[#9C382E] border border-[#DE9E98]"
                              : (act.priority || "").toUpperCase() === "MEDIUM"
                              ? "bg-[#FAF4E8] text-[#8B6E28] border border-[#E8DFC8]"
                              : "bg-[#EDF5EE] text-[#2A6E3B] border border-[#94C09A]"
                          }`}
                        >
                          {act.priority || "NORMAL"}
                        </span>
                      </td>
                      <td className="py-3 px-3">
                        {isSimulated ? (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-[#FAF4E8] text-[#8B6E28] border border-[#E8DFC8]">
                            Vendor email: SIMULATED
                          </span>
                        ) : isVerification ? (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-[#F5F5EE] text-[#4A4A45] border border-[#DCDCD4]">
                            VERIFICATION PENDING
                          </span>
                        ) : isCompleted ? (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-[#EDF5EE] text-[#2A6E3B] border border-[#94C09A]">
                            COMPLETED
                          </span>
                        ) : isFailed ? (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-[#FDF0EE] text-[#9C382E] border border-[#DE9E98]">
                            FAILED
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-[#F0F0EA] text-[#4A4A45] border border-[#DCDCD4]">
                            {act.status}
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-[11px]">
                        {act.verification_status === "PENDING_TELEMETRY" || isVerification ? (
                          <span className="text-[#4A4A45] font-medium">
                            Pending new telemetry
                          </span>
                        ) : (
                          <span className="text-[#6B6B66] font-mono">
                            {act.verification_status || "N/A"}
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-[#6B6B66] whitespace-nowrap text-[11px]">
                        <div>
                          <span className="font-medium text-[#171717]">{act.reason?.includes("by") ? act.reason : "Operator"}</span>
                          <span className="text-[#6B6B66] block text-[10px] font-mono">
                            {act.approved_at ? new Date(act.approved_at).toLocaleString() : ""}
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-3 text-right">
                        <button
                          onClick={() =>
                            setExpandedActionId(isExpanded ? null : act.action_id)
                          }
                          className="p-1 rounded hover:bg-[#EFEFE8] text-[#6B6B66] transition cursor-pointer"
                          title="Toggle details"
                        >
                          {isExpanded ? (
                            <ChevronUp className="w-3.5 h-3.5" />
                          ) : (
                            <ChevronDown className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </td>
                    </tr>

                    {/* Collapsible Details Drawer */}
                    {isExpanded && (
                      <tr className="bg-[#F5F5EE]">
                        <td colSpan={9} className="p-4 border-b border-[#DCDCD4]">
                          <div className="text-xs space-y-2 max-w-3xl">
                            <div className="flex items-center space-x-2">
                              <Info className="w-3.5 h-3.5 text-[#6B6B66]" />
                              <span className="font-semibold text-[#171717]">
                                Action Audit Details — {act.action_id} (Notification {act.notification_id})
                              </span>
                            </div>
                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1 text-[11px]">
                              <div>
                                <span className="text-[#6B6B66]">Execution Priority:</span>
                                <p className="font-semibold text-[#171717]">{act.priority || "NORMAL"}</p>
                              </div>
                              <div>
                                <span className="text-[#6B6B66]">Completed At:</span>
                                <p className="font-mono text-[#171717]">{act.completed_at || "In Progress"}</p>
                              </div>
                              <div>
                                <span className="text-[#6B6B66]">Physical Safeguard Note:</span>
                                <p className="text-[#4A4A45] font-medium">
                                  Software action verified; physical recovery pending telemetry.
                                </p>
                              </div>
                            </div>
                            <div className="mt-2 pt-2 border-t border-[#DCDCD4]">
                              <span className="text-[#6B6B66] text-[10px] uppercase font-mono font-medium">
                                Stored Action Result Payload:
                              </span>
                              <pre className="mt-1 p-2 bg-[#1F1F1D] text-[#DCDCD4] font-mono text-[10px] rounded-md overflow-x-auto">
                                {parsedResult
                                  ? JSON.stringify(parsedResult, null, 2)
                                  : act.result || "No additional payload"}
                              </pre>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
