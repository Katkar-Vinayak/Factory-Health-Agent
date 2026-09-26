"use client";

import React, { useState, useEffect } from "react";
import { AgentAnalysis, NotificationItem } from "../types";
import { analyzeMachine, getNotification, getNotifications } from "../lib/api";
import { RiskBadge } from "./RiskBadge";
import { AgentTrace } from "./AgentTrace";
import { ImpactPanel } from "./ImpactPanel";
import { RecommendationList } from "./RecommendationList";
import { WhatIfSimulator } from "./WhatIfSimulator";
import { ApprovalModal } from "./ApprovalModal";
import { PlantEngineeringReport } from "./PlantEngineeringReport";
import {
  Sparkles,
  Loader2,
  AlertTriangle,
  Brain,
  Search,
  CheckCircle,
  CheckCircle2,
  Sliders,
  ShieldAlert,
  ShieldCheck,
  Flame,
  Gauge
} from "lucide-react";

interface AIAnalysisProps {
  machineId: string;
  defaultTimestamp?: string;
}

export function AIAnalysis({ machineId, defaultTimestamp }: AIAnalysisProps) {
  const [analysis, setAnalysis] = useState<AgentAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [customTimestamp, setCustomTimestamp] = useState<string>(defaultTimestamp || "");
  const [selectedScenario, setSelectedScenario] = useState<"normal" | "pre-failure" | "custom" | null>(null);
  const [showSimulator, setShowSimulator] = useState(false);
  const [approvalNotif, setApprovalNotif] = useState<NotificationItem | null>(null);
  const [isApprovalOpen, setIsApprovalOpen] = useState(false);
  const [approvalMode, setApprovalMode] = useState<"accept" | "reject">("accept");

  const loadMachineNotification = async () => {
    try {
      const res = await getNotifications({ machine_id: machineId });
      if (res.notifications && res.notifications.length > 0) {
        setApprovalNotif(res.notifications[0]);
      } else {
        setApprovalNotif(null);
      }
    } catch {
      // ignore non-critical load failure
    }
  };

  useEffect(() => {
    loadMachineNotification();
  }, [machineId]);

  // Representative real pre-failure timestamps from dataset for seamless demo
  const demoTimestamps: Record<string, { label: string; timestamp: string }> = {
    M_003: {
      label: "Bearing Degradation Incident",
      timestamp: "2023-01-19 22:00:00"
    },
    M_001: {
      label: "Motor Overheating Incident",
      timestamp: "2023-01-12 02:00:00"
    },
    M_004: {
      label: "Cooling Failure Incident",
      timestamp: "2023-01-27 10:00:00"
    },
    M_006: {
      label: "Hydraulic Pressure Loss",
      timestamp: "2023-02-08 14:00:00"
    },
    M_002: {
      label: "Electrical Surge Incident",
      timestamp: "2023-01-11 07:00:00"
    }
  };

  const preFailureDemo = demoTimestamps[machineId] || {
    label: "Pre-Failure Incident",
    timestamp: "2023-01-19 22:00:00"
  };

  const handleAnalyze = async (overrideTimestamp?: string, scenarioType?: "normal" | "pre-failure" | "custom") => {
    setLoading(true);
    setError(null);
    setShowSimulator(false);
    if (scenarioType) {
      setSelectedScenario(scenarioType);
    }
    const tsToUse = overrideTimestamp !== undefined ? overrideTimestamp : customTimestamp || undefined;

    try {
      const result = await analyzeMachine(machineId, tsToUse);
      setAnalysis(result);

      if (result.notification_id) {
        try {
          const notif = await getNotification(result.notification_id);
          setApprovalNotif(notif);
        } catch {
          await loadMachineNotification();
        }
      } else {
        await loadMachineNotification();
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Failed to execute AI analysis workflow.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-[#FAFAF5] rounded-xl border border-[#DCDCD4] p-6 sm:p-7 shadow-2xs">
      {/* Header Banner & Primary CTA */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5 pb-5 border-b border-[#DCDCD4]">
        <div className="flex items-start space-x-3.5">
          <div className="p-2.5 bg-[#171717] text-white rounded-lg shadow-2xs">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-lg sm:text-xl font-bold text-[#171717] tracking-tight">
                AI Factory Investigation
              </h2>
              <span className="px-2 py-0.5 rounded-full text-[11px] font-mono font-medium bg-[#F0F0EA] text-[#4A4A45] border border-[#DCDCD4]">
                Multi-Agent Workflow
              </span>
            </div>
            <p className="text-xs sm:text-sm text-[#6B6B66] mt-0.5">
              Autonomous orchestration of Monitoring, Investigation, RCA, Impact, and Decision Agents
            </p>
          </div>
        </div>

        {/* Primary CTA Button: Industrial & Professional */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <button
            onClick={() => handleAnalyze(undefined, "custom")}
            disabled={loading}
            className="inline-flex flex-col items-center justify-center px-5 py-2.5 rounded-md font-semibold bg-[#171717] hover:bg-[#262626] active:bg-black text-white shadow-xs transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer text-center group"
          >
            <div className="flex items-center space-x-2 text-xs sm:text-sm font-semibold tracking-tight">
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-white" />
                  <span>Agents Investigating...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 text-[#DCDCD4]" />
                  <span>Analyze with Factory AI</span>
                </>
              )}
            </div>
            <span className="text-[10px] text-[#A8A89F] font-mono tracking-wide mt-0.5">
              Detect → Investigate → Diagnose → Recommend
            </span>
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="mt-5 p-3.5 rounded-lg bg-[#FDF0EE] border border-[#DE9E98] text-[#9C382E] flex items-start space-x-2.5">
          <AlertTriangle className="w-4 h-4 text-[#9C382E] shrink-0 mt-0.5" />
          <div className="text-xs sm:text-sm">
            <strong className="font-semibold">Investigation Error:</strong> {error}
          </div>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && (
        <div className="mt-6 p-10 text-center border border-dashed border-[#DCDCD4] rounded-lg bg-[#F5F5EE]">
          <Loader2 className="w-8 h-8 animate-spin text-[#171717] mx-auto mb-3" />
          <h2 className="text-sm font-semibold text-[#171717]">
            Agents are investigating machine health...
          </h2>
          <p className="text-xs text-[#6B6B66] mt-1 max-w-md mx-auto">
            Monitoring Agent evaluating telemetry → Investigation Agent correlating sensor and maintenance logs → RCA Agent computing candidate root causes → Decision Agent generating action plan.
          </p>
        </div>
      )}

      {/* AI Investigation Results */}
      {analysis && !loading && (
        <div className="mt-6 space-y-6 animate-fadeIn">
          {/* Executive Diagnostic Callout Banner */}
          {analysis.risk_level === "HIGH" ? (
            <div className="rounded-lg border border-[#DE9E98] bg-[#FDF0EE] p-5 shadow-2xs">
              <div className="flex items-center justify-between pb-3 mb-4 border-b border-[#DE9E98]/60">
                <div className="flex items-center space-x-2">
                  <span className="w-2 h-2 rounded-full bg-[#9C382E]" />
                  <span className="text-xs font-bold uppercase tracking-wider text-[#9C382E]">
                    Pre-Failure Executive Assessment
                  </span>
                </div>
                <span className="text-[11px] font-mono font-medium px-2 py-0.5 rounded bg-white text-[#9C382E] border border-[#DE9E98]">
                  AI Multi-Agent Consensus
                </span>
              </div>

              {/* 4 Prominent Result Metrics */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {/* 1. Risk Assessment */}
                <div className="bg-[#FAFAF5] rounded-md p-3 border border-[#DE9E98]/60 text-center shadow-2xs">
                  <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-[#9C382E]">
                    Risk Assessment
                  </span>
                  <p className="text-xl sm:text-2xl font-bold text-[#9C382E] mt-1">
                    {analysis.risk_level} RISK
                  </p>
                  <span className="text-[10px] text-[#6B6B66]">ML + Isolation Forest</span>
                </div>

                {/* 2. Failure Probability */}
                <div className="bg-[#FAFAF5] rounded-md p-3 border border-[#DE9E98]/60 text-center shadow-2xs">
                  <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-[#9C382E]">
                    Failure Probability
                  </span>
                  <p className="text-xl sm:text-2xl font-bold text-[#9C382E] mt-1">
                    {(analysis.failure_probability * 100).toFixed(0)}%
                  </p>
                  <span className="text-[10px] text-[#6B6B66]">Failure Probability</span>
                </div>

                {/* 3. Probable Root Cause */}
                <div className="bg-[#FAFAF5] rounded-md p-3 border border-[#DCDCD4] text-center shadow-2xs">
                  <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-[#171717]">
                    Probable Root Cause
                  </span>
                  <p
                    className="text-base sm:text-lg font-bold text-[#171717] mt-1 truncate"
                    title={analysis.root_cause || "Mechanical Failure"}
                  >
                    {analysis.root_cause || "Bearing Degradation"}
                  </p>
                  <span className="text-[10px] text-[#6B6B66]">Deterministic RCA</span>
                </div>

                {/* 4. Confidence */}
                <div className="bg-[#FAFAF5] rounded-md p-3 border border-[#DCDCD4] text-center shadow-2xs">
                  <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-[#171717]">
                    Diagnosis Confidence
                  </span>
                  <p className="text-xl sm:text-2xl font-bold text-[#171717] mt-1">
                    {analysis.confidence !== undefined && analysis.confidence !== null
                      ? `${(analysis.confidence * 100).toFixed(0)}%`
                      : "N/A"}
                  </p>
                  <span className="text-[10px] text-[#6B6B66]">Confidence Score</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="rounded-lg border border-[#94C09A] bg-[#EDF5EE] p-4 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-[#1D4E29]">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-[#2A6E3B] text-white rounded-md">
                  <CheckCircle className="w-4 h-4" />
                </div>
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="text-xs sm:text-sm font-semibold">
                      {analysis.risk_level} RISK — Operating Within Nominal Boundaries
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.2 rounded-full bg-white text-[#2A6E3B] font-medium border border-[#94C09A]">
                      {(analysis.failure_probability * 100).toFixed(0)}% Failure Prob
                    </span>
                  </div>
                  <p className="text-xs text-[#2A6E3B] mt-0.5">
                    All telemetry measurements align with nominal operating baselines. Routine monitoring continues.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* HITL Action Required / Verification Status Callout Banner */}
          {approvalNotif && (approvalNotif.status === "PENDING" || analysis.approval_status === "PENDING") && (
            <div className="rounded-lg border border-[#E8DFC8] bg-[#FAF4E8] p-4 shadow-2xs animate-fadeIn">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-start space-x-3">
                  <div className="p-2 bg-[#8B6E28] text-white rounded-md mt-0.5 shrink-0 shadow-2xs">
                    <ShieldAlert className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-[#8B6E28]">
                        ACTION REQUIRED — Operator Approval Gate
                      </span>
                      <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-white text-[#8B6E28] font-semibold border border-[#E8DFC8]">
                        {approvalNotif.notification_id}
                      </span>
                    </div>
                    <p className="text-xs font-semibold text-[#171717] mt-1">
                      {approvalNotif.root_cause || analysis.root_cause || "Component Degradation"} diagnosed on {approvalNotif.component || "target component"}.
                    </p>
                    <div className="mt-1 text-xs text-[#4A4A45]">
                      <span className="font-semibold text-[#171717]">Recommended Actions:</span>{" "}
                      {Array.isArray(approvalNotif.recommendation)
                        ? approvalNotif.recommendation.join(" • ")
                        : String(approvalNotif.recommendation)}
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-2 shrink-0 self-end sm:self-center">
                  <button
                    type="button"
                    onClick={() => {
                      setApprovalMode("accept");
                      setIsApprovalOpen(true);
                    }}
                    className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-md text-xs font-semibold bg-[#8B6E28] hover:bg-[#735A1E] text-white shadow-2xs transition cursor-pointer"
                  >
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>REVIEW &amp; APPROVE</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setApprovalMode("reject");
                      setIsApprovalOpen(true);
                    }}
                    className="inline-flex items-center space-x-1.5 px-3 py-2 rounded-md text-xs font-medium bg-white hover:bg-[#FDF0EE] text-[#9C382E] border border-[#DE9E98] transition cursor-pointer"
                  >
                    <span>REJECT</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Verification Safeguard Active Banner */}
          {approvalNotif && approvalNotif.status === "VERIFICATION_PENDING" && (
            <div className="rounded-lg border border-[#DCDCD4] bg-[#F5F5EE] p-3.5 text-xs text-[#171717] flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-2xs">
              <div className="flex items-center space-x-2.5">
                <div className="p-1.5 bg-[#171717] text-white rounded shrink-0">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                </div>
                <div>
                  <span className="font-semibold text-[#171717]">
                    Maintenance Action: Verification Pending
                  </span>
                  <p className="text-[#6B6B66] text-[11px] mt-0.5">
                    Software action recorded successfully. Physical recovery requires verified new sensor telemetry.
                  </p>
                </div>
              </div>
              <span className="font-mono text-[10px] bg-white px-2 py-0.5 rounded border border-[#DCDCD4] text-[#4A4A45] font-semibold self-start sm:self-auto">
                {approvalNotif.notification_id} • PENDING_TELEMETRY
              </span>
            </div>
          )}

          {/* Section A: Risk Summary */}
          <div>
            <div className="flex items-center space-x-2 mb-2.5">
              <h3 className="text-xs font-mono font-medium uppercase tracking-wider text-[#6B6B66]">
                A. Machine Risk Summary
              </h3>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
              <div className="bg-[#FAFAF5] border border-[#DCDCD4] rounded-lg p-4 shadow-2xs">
                <span className="text-xs font-mono uppercase text-[#6B6B66]">Evaluated Risk Level</span>
                <div className="mt-2">
                  <RiskBadge riskLevel={analysis.risk_level} size="lg" />
                </div>
              </div>

              <div className="bg-[#FAFAF5] border border-[#DCDCD4] rounded-lg p-4 shadow-2xs">
                <span className="text-xs font-mono uppercase text-[#6B6B66]">24-Hour Failure Probability</span>
                <div className="mt-2 flex items-baseline space-x-2">
                  <span
                    className={`text-2xl font-bold tracking-tight ${
                      analysis.failure_probability > 0.5 ? "text-[#9C382E]" : "text-[#2A6E3B]"
                    }`}
                  >
                    {(analysis.failure_probability * 100).toFixed(1)}%
                  </span>
                  <span className="text-xs text-[#6B6B66]">ML Random Forest</span>
                </div>
              </div>

              <div className="bg-[#FAFAF5] border border-[#DCDCD4] rounded-lg p-4 shadow-2xs">
                <span className="text-xs font-mono uppercase text-[#6B6B66]">Isolation Forest Anomaly</span>
                <div className="mt-2 flex items-center space-x-2">
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                      analysis.anomaly
                        ? "bg-[#FDF0EE] text-[#9C382E] border-[#DE9E98]"
                        : "bg-[#EDF5EE] text-[#2A6E3B] border-[#94C09A]"
                    }`}
                  >
                    {analysis.anomaly ? "Outlier Anomaly Detected" : "Normal Inlier"}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Section B: Root Cause Analysis */}
          {analysis.risk_level === "HIGH" && (
            <div className="border border-[#DCDCD4] bg-[#F5F5EE] rounded-lg p-5">
              <div className="flex items-center justify-between flex-wrap gap-2 pb-3 mb-3 border-b border-[#DCDCD4]">
                <div className="flex items-center space-x-2">
                  <div className="p-1.5 bg-[#171717] text-white rounded">
                    <Brain className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-[#171717]">
                      B. Deterministic Root Cause Analysis
                    </h3>
                  </div>
                </div>

                {analysis.confidence !== undefined && analysis.confidence !== null && (
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-medium bg-[#FAFAF5] text-[#4A4A45] border border-[#DCDCD4]">
                    Confidence: {(analysis.confidence * 100).toFixed(0)}%
                  </span>
                )}
              </div>

              <div className="mt-2">
                <p className="text-xs text-[#6B6B66]">Diagnosed Probable Root Cause:</p>
                <h4 className="text-base sm:text-lg font-bold text-[#171717] mt-0.5">
                  {analysis.root_cause || "Unknown Mechanical/Electrical Failure"}
                </h4>
              </div>

              {/* Candidate Scores Breakdown */}
              {analysis.candidate_scores && (
                <div className="mt-4 pt-3 border-t border-[#DCDCD4]">
                  <p className="text-xs font-semibold text-[#171717] mb-2">
                    Evidence Scores Across 5 Failure Categories:
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-5 gap-2">
                    {Object.entries(analysis.candidate_scores).map(([cause, score]) => {
                      const isWinner = cause === analysis.root_cause;
                      return (
                        <div
                          key={cause}
                          className={`p-2.5 rounded-md border text-center transition ${
                            isWinner
                              ? "bg-[#FAFAF5] border-2 border-[#171717] font-semibold text-[#171717] shadow-xs"
                              : "bg-[#FAFAF5] border-[#DCDCD4] text-[#6B6B66] text-xs"
                          }`}
                        >
                          <p className="text-[11px] truncate" title={cause}>
                            {cause}
                          </p>
                          <p className="text-sm font-semibold mt-1">
                            {score.toFixed(1)} <span className="text-[10px] font-normal">pts</span>
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Qwen RCA Physics & Candidate Scores Explanation */}
              {analysis.rca_explanation && (
                <div className="mt-3.5 p-3.5 rounded-md bg-[#FAFAF5] border border-[#DCDCD4] text-xs text-[#4A4A45] leading-relaxed shadow-2xs">
                  <div className="flex items-center space-x-1.5 font-semibold text-[11px] uppercase tracking-wider text-[#171717] mb-1">
                    <Sparkles className="w-3.5 h-3.5 text-[#6B6B66]" />
                    <span>RCA Physics &amp; Evidence Explanation</span>
                  </div>
                  <p>{analysis.rca_explanation}</p>
                </div>
              )}
            </div>
          )}

          {/* Section C: Evidence */}
          {analysis.evidence && analysis.evidence.length > 0 && (
            <div>
              <div className="flex items-center space-x-2 mb-2.5">
                <Search className="w-3.5 h-3.5 text-[#6B6B66]" />
                <h3 className="text-xs font-mono font-medium uppercase tracking-wider text-[#6B6B66]">
                  C. Correlated Evidence &amp; Telemetry Signals ({analysis.evidence.length} Points)
                </h3>
              </div>
              <div className="bg-[#FAFAF5] border border-[#DCDCD4] rounded-lg p-5 shadow-2xs">
                {/* Qwen Investigation Telemetry Explanation */}
                {analysis.investigation_explanation && (
                  <div className="mb-3.5 p-3 rounded-md bg-[#F5F5EE] border border-[#DCDCD4] text-xs text-[#4A4A45] leading-relaxed">
                    <div className="flex items-center space-x-1.5 font-semibold text-[11px] uppercase tracking-wider text-[#171717] mb-1">
                      <Sparkles className="w-3.5 h-3.5 text-[#6B6B66]" />
                      <span>Telemetry Coupling &amp; Investigation Summary</span>
                    </div>
                    <p>{analysis.investigation_explanation}</p>
                  </div>
                )}
                <ul className="space-y-2">
                  {analysis.evidence.map((point, idx) => (
                    <li key={idx} className="flex items-start text-xs sm:text-sm text-[#4A4A45]">
                      <span className="flex items-center justify-center w-5 h-5 rounded-full bg-[#F0F0EA] text-[#171717] border border-[#DCDCD4] text-[11px] font-mono font-semibold mr-2.5 shrink-0 mt-0.5">
                        {idx + 1}
                      </span>
                      <span className="leading-relaxed">{point}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Section D: Operational Impact */}
          {analysis.impact && Object.keys(analysis.impact).length > 0 && (
            <div>
              <h3 className="text-xs font-mono font-medium uppercase tracking-wider text-[#6B6B66] mb-2.5">
                D. Operational &amp; Energy Impact
              </h3>
              <ImpactPanel impact={analysis.impact} />
            </div>
          )}

          {/* Section E: Recommended Actions */}
          {analysis.recommendations && analysis.recommendations.length > 0 && (
            <div>
              <h3 className="text-xs font-mono font-medium uppercase tracking-wider text-[#6B6B66] mb-2.5">
                E. Prescribed Corrective Action Plan
              </h3>
              {/* Qwen Decision Explanation */}
              {analysis.decision_explanation && (
                <div className="mb-3 p-3 rounded-md bg-[#F5F5EE] border border-[#DCDCD4] text-xs text-[#4A4A45] leading-relaxed">
                  <div className="flex items-center space-x-1.5 font-semibold text-[11px] uppercase tracking-wider text-[#171717] mb-1">
                    <Sparkles className="w-3.5 h-3.5 text-[#6B6B66]" />
                    <span>Operational Decision Rationale</span>
                  </div>
                  <p>{analysis.decision_explanation}</p>
                </div>
              )}
              <RecommendationList recommendations={analysis.recommendations} />
            </div>
          )}

          {/* Section F: What-If 24-Hour Impact Simulator */}
          <div className="pt-1">
            <h3 className="text-xs font-mono font-medium uppercase tracking-wider text-[#6B6B66] mb-2.5">
              F. 24-Hour Operational Scenario Simulator
            </h3>
            {analysis.risk_level === "MEDIUM" || analysis.risk_level === "HIGH" ? (
              <div className="space-y-3.5">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 rounded-lg border border-[#DCDCD4] bg-[#F5F5EE] gap-3 shadow-2xs">
                  <div className="flex items-center space-x-3">
                    <div className="p-2 bg-[#171717] text-white rounded-md shadow-2xs shrink-0">
                      <Sliders className="w-4 h-4" />
                    </div>
                    <div>
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-[#171717]">
                        What-If Decision Support Simulator
                      </h4>
                      <p className="text-xs text-[#6B6B66] mt-0.5">
                        Model the projected 24-hour operational trajectory: Compare <strong className="text-[#171717]">Intervene Now</strong> vs. <strong className="text-[#171717]">Do Nothing</strong>.
                      </p>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => setShowSimulator(!showSimulator)}
                    className="px-4 py-2 rounded-md bg-[#171717] hover:bg-[#262626] text-white text-xs font-semibold transition shadow-xs flex items-center justify-center space-x-2 shrink-0 cursor-pointer"
                  >
                    <Sliders className="w-3.5 h-3.5" />
                    <span>{showSimulator ? "Hide Simulator" : "Simulate 24h Impact"}</span>
                  </button>
                </div>

                {showSimulator && (
                  <WhatIfSimulator
                    machineId={machineId}
                    timestamp={analysis.timestamp || customTimestamp || undefined}
                    onClose={() => setShowSimulator(false)}
                  />
                )}
              </div>
            ) : (
              <div className="p-3.5 rounded-lg border border-[#DCDCD4] bg-[#F5F5EE] text-[#6B6B66] text-xs flex items-center space-x-2.5">
                <CheckCircle className="w-4 h-4 text-[#2A6E3B] shrink-0" />
                <span>No intervention scenario required for low-risk operation.</span>
              </div>
            )}
          </div>

          {/* Section G: Agent Execution Trace */}
          {analysis.agent_trace && analysis.agent_trace.length > 0 && (
            <div>
              <h3 className="text-xs font-mono font-medium uppercase tracking-wider text-[#6B6B66] mb-2.5">
                G. Agent Activity &amp; Reasoning Pipeline
              </h3>
              <AgentTrace trace={analysis.agent_trace} />
            </div>
          )}

          {/* Section H: Plant Engineering Summary Report */}
          {analysis.final_report && (
            <PlantEngineeringReport
              reportText={analysis.final_report}
              machineId={machineId}
              timestamp={analysis.timestamp || customTimestamp}
            />
          )}
        </div>
      )}

      {/* Human Approval Modal for AI Analysis Section */}
      <ApprovalModal
        isOpen={isApprovalOpen}
        mode={approvalMode}
        notification={approvalNotif}
        onClose={() => setIsApprovalOpen(false)}
        onSuccess={() => {
          loadMachineNotification();
        }}
      />
    </div>
  );
}
