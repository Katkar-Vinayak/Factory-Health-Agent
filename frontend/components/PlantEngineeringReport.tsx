"use client";

import React from "react";
import { FileText } from "lucide-react";

interface PlantEngineeringReportProps {
  reportText: string;
  machineId?: string;
  timestamp?: string;
}

function cleanMarkdown(text: string): string {
  if (!text) return "";
  return text
    .replace(/^#{1,6}\s*/gm, "")
    .replace(/\*{1,3}/g, "")
    .replace(/_{1,3}/g, "")
    .trim();
}

interface ParsedSection {
  title: string;
  items: string[];
}

export function parsePlantEngineeringReport(finalReport: string): {
  observationTimestamp: string;
  machineHeader: string;
  activeSections: ParsedSection[];
} {
  if (!finalReport) {
    return { observationTimestamp: "", machineHeader: "", activeSections: [] };
  }

  const rawLines = finalReport.split("\n").map((l) => l.trim()).filter(Boolean);

  let observationTimestamp = "";
  let machineHeader = "";

  const sections: Record<string, string[]> = {
    condition: [],
    anomalyRisk: [],
    rca: [],
    impact: [],
    recommendations: [],
    verification: []
  };

  let currentSection: string | null = null;

  for (const rawLine of rawLines) {
    const isHeading = /^#{1,6}\s+/.test(rawLine);
    const cleaned = cleanMarkdown(rawLine);
    const lower = cleaned.toLowerCase();

    // Check header lines
    if (lower.startsWith("executive health assessment:") || lower.startsWith("executive health summary:")) {
      machineHeader = cleaned;
      continue;
    }
    if (lower.startsWith("observation timestamp:")) {
      observationTimestamp = cleaned.replace(/^observation timestamp:\s*/i, "").trim();
      continue;
    }

    // Check explicit markdown heading transitions
    if (isHeading) {
      if (lower.includes("observed data") || lower.includes("telemetry baseline") || lower.includes("condition")) {
        currentSection = "condition";
      } else if (lower.includes("ml prediction") || lower.includes("risk assessment") || lower.includes("anomaly")) {
        currentSection = "anomalyRisk";
      } else if (lower.includes("root cause analysis") || lower.includes("deterministic root cause") || lower.includes("rca")) {
        currentSection = "rca";
      } else if (lower.includes("prescribed action") && lower.includes("operational impact")) {
        currentSection = "actionAndImpact";
      } else if (lower.includes("operational impact") || lower.includes("impact")) {
        currentSection = "impact";
      } else if (lower.includes("action") || lower.includes("recommendation")) {
        currentSection = "recommendations";
      } else if (lower.includes("status") || lower.includes("verification")) {
        currentSection = "verification";
      }
      continue;
    }

    // Check Operational Status (HITL)
    if (lower.startsWith("operational status:")) {
      sections.verification.push(cleaned.replace(/^operational status:\s*/i, "").trim());
      continue;
    }

    // Categorize single-line bullet reports
    if (/^[-*•]?\s*observed data:/i.test(cleaned)) {
      sections.condition.push(cleaned.replace(/^[-*•]?\s*observed data:\s*/i, "").trim());
      continue;
    }
    if (/^[-*•]?\s*model prediction:/i.test(cleaned)) {
      sections.anomalyRisk.push(cleaned.replace(/^[-*•]?\s*model prediction:\s*/i, "").trim());
      continue;
    }
    if (/^[-*•]?\s*deterministic rca:/i.test(cleaned)) {
      sections.rca.push(cleaned.replace(/^[-*•]?\s*deterministic rca:\s*/i, "").trim());
      continue;
    }
    if (/^[-*•]?\s*operational impact:/i.test(cleaned)) {
      sections.impact.push(cleaned.replace(/^[-*•]?\s*operational impact:\s*/i, "").trim());
      continue;
    }
    if (/^[-*•]?\s*recommended action(\s*plan)?:/i.test(cleaned)) {
      sections.recommendations.push(cleaned.replace(/^[-*•]?\s*recommended action(\s*plan)?:\s*/i, "").trim());
      continue;
    }
    if (/^[-*•]?\s*urgency:/i.test(cleaned)) {
      sections.recommendations.push(cleaned.replace(/^[-*•]?\s*/, "").trim());
      continue;
    }

    // Categorize by current active section
    if (currentSection === "actionAndImpact") {
      if (lower.includes("production:") || lower.includes("energy:")) {
        sections.impact.push(cleaned.replace(/^[-*•]?\s*(operational impact:\s*)?/i, "").trim());
      } else {
        sections.recommendations.push(cleaned.replace(/^[-*•]?\s*/, "").trim());
      }
    } else if (currentSection && sections[currentSection]) {
      const lineWithoutBullet = cleaned.replace(/^[-*•]\s*/, "").trim();
      if (lineWithoutBullet && lineWithoutBullet.toLowerCase() !== "observed evidence:") {
        sections[currentSection].push(lineWithoutBullet);
      }
    } else {
      // Check inline keywords in freeform text
      if (lower.includes("failure probability") && lower.includes("risk")) {
        sections.anomalyRisk.push(cleaned);
      } else if (lower.includes("root cause")) {
        sections.rca.push(cleaned);
      } else if (lower.includes("recommended action")) {
        sections.recommendations.push(cleaned);
      } else {
        sections.condition.push(cleaned);
      }
    }
  }

  const activeSections: ParsedSection[] = [
    { title: "Machine Condition Assessment", items: sections.condition },
    { title: "Anomaly and Failure Risk", items: sections.anomalyRisk },
    { title: "Root Cause Analysis", items: sections.rca },
    { title: "Operational Impact", items: sections.impact },
    { title: "Recommended Maintenance Actions", items: sections.recommendations },
    { title: "Verification Status", items: sections.verification }
  ].filter((s) => s.items && s.items.length > 0);

  return {
    observationTimestamp,
    machineHeader,
    activeSections
  };
}

export function PlantEngineeringReport({
  reportText,
  machineId,
  timestamp
}: PlantEngineeringReportProps) {
  if (!reportText) return null;

  const { observationTimestamp, activeSections } = parsePlantEngineeringReport(reportText);
  const effectiveTimestamp = observationTimestamp || timestamp || "";

  return (
    <div className="bg-[#FAFAF5] border border-[#DCDCD4] rounded-xl p-6 sm:p-7 shadow-2xs">
      {/* Formal Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 border-b border-[#DCDCD4]">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 bg-[#171717] text-white rounded-lg shrink-0 shadow-2xs">
            <FileText className="w-4 h-4 text-[#FAFAF5]" />
          </div>
          <div>
            <h3 className="text-sm sm:text-base font-bold text-[#171717] tracking-tight">
              H. Plant Engineering Summary Report
            </h3>
            {machineId && (
              <p className="text-[11px] font-mono text-[#6B6B66] mt-0.5">
                Equipment Unit: {machineId}
              </p>
            )}
          </div>
        </div>

        {effectiveTimestamp && (
          <div className="text-[11px] font-mono text-[#6B6B66] bg-[#F0F0EA] px-2.5 py-1 rounded-md border border-[#DCDCD4] self-start sm:self-auto">
            Observation: {effectiveTimestamp}
          </div>
        )}
      </div>

      {/* Formal Introductory Description Paragraph */}
      <p className="text-xs sm:text-sm text-[#4A4A45] leading-relaxed mt-4 mb-6">
        This report provides a consolidated engineering assessment of the selected machine based on its latest available telemetry, operational performance, anomaly detection results, predicted failure risk, root cause analysis, operational impact, and recommended maintenance actions. It presents the current equipment condition and the associated engineering findings in a structured format to support maintenance planning, operational decision-making, and risk mitigation.
      </p>

      {/* Structured Engineering Subsections */}
      {activeSections.length > 0 ? (
        <div className="space-y-5 pt-1">
          {activeSections.map((section, idx) => (
            <div
              key={idx}
              className="pb-5 last:pb-0 border-b last:border-b-0 border-[#E8E8E0]"
            >
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#171717] mb-3 flex items-center space-x-2">
                <span className="w-1.5 h-1.5 rounded-full bg-[#171717]" />
                <span>{section.title}</span>
              </h4>

              <div className="space-y-2 pl-3.5 border-l-2 border-[#DCDCD4]">
                {section.items.map((item, itemIdx) => {
                  // Check if item contains a key-value pattern like "Key: Value"
                  const colonIdx = item.indexOf(":");
                  const candidateLabel = colonIdx > 0 ? item.slice(0, colonIdx).trim() : "";
                  const isReasonableLabel =
                    colonIdx > 0 &&
                    colonIdx < 40 &&
                    !candidateLabel.includes(",") &&
                    !candidateLabel.includes(".") &&
                    !candidateLabel.includes(";") &&
                    candidateLabel.length < 35;

                  if (isReasonableLabel) {
                    const label = candidateLabel;
                    const value = item.slice(colonIdx + 1).trim();
                    return (
                      <div key={itemIdx} className="text-xs sm:text-sm text-[#4A4A45]">
                        <span className="font-semibold text-[#171717]">{label}: </span>
                        <span>{value}</span>
                      </div>
                    );
                  }

                  return (
                    <div key={itemIdx} className="text-xs sm:text-sm text-[#4A4A45] leading-relaxed">
                      {item}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-xs sm:text-sm text-[#4A4A45] leading-relaxed pt-2">
          {cleanMarkdown(reportText)}
        </div>
      )}
    </div>
  );
}
