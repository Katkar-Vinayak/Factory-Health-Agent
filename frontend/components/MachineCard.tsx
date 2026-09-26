import React from "react";
import Link from "next/link";
import { MachineWithStatus } from "../types";
import { ArrowRight } from "lucide-react";

interface MachineCardProps {
  machine: MachineWithStatus;
}

export function MachineCard({ machine }: MachineCardProps) {
  const { metadata, latest_sensor, analysis } = machine;
  const hasTelemetry = Boolean(latest_sensor || (analysis && analysis.risk_level !== "UNKNOWN"));
  const riskLevel = hasTelemetry ? (analysis?.risk_level || "LOW") : "UNKNOWN";
  const failureProb = analysis ? analysis.failure_probability : 0.0;
  const isCritical = riskLevel === "HIGH";
  const isWarning = riskLevel === "MEDIUM";

  // Distinct Business Criticality styling (independent from operational health risk)
  const criticalityBadge = {
    High: "bg-[#F0F0EA] text-[#333330] border-[#DCDCD4]",
    Medium: "bg-[#FAFAF5] text-[#6B6B66] border-[#DCDCD4]",
    Low: "bg-[#FAFAF5] text-[#8C8C85] border-[#DCDCD4]"
  }[metadata.criticality_level] || "bg-[#FAFAF5] text-[#6B6B66] border-[#DCDCD4]";

  // Operational health status indicator styling
  const statusConfig = {
    HIGH: {
      dot: "bg-[#9E2A2B]",
      badge: "bg-[#FDF0EE] text-[#9E2A2B] border-[#F2C2BD]",
      label: "Critical"
    },
    MEDIUM: {
      dot: "bg-[#8C5E14]",
      badge: "bg-[#FAF4E8] text-[#8C5E14] border-[#EADBB8]",
      label: "Warning"
    },
    LOW: {
      dot: "bg-[#1E4D2B]",
      badge: "bg-[#EDF5EE] text-[#1E4D2B] border-[#C8E0CD]",
      label: "Healthy"
    },
    UNKNOWN: {
      dot: "bg-[#6B6B66]",
      badge: "bg-[#F0F0EA] text-[#6B6B66] border-[#DCDCD4]",
      label: "Awaiting Data"
    }
  }[riskLevel] || {
    dot: "bg-[#1E4D2B]",
    badge: "bg-[#EDF5EE] text-[#1E4D2B] border-[#C8E0CD]",
    label: "Healthy"
  };

  return (
    <Link
      href={`/machines/${encodeURIComponent(metadata.machine_id)}`}
      className={`group flex flex-col justify-between rounded-xl bg-[#FAFAF5] border p-5 transition hover:border-[#171717]/40 hover:shadow-xs ${
        isCritical ? "border-[#F2C2BD]" : isWarning ? "border-[#EADBB8]" : "border-[#DCDCD4]"
      }`}
    >
      <div>
        {/* Top Header: ID + Criticality + Status Pill */}
        <div className="flex items-center justify-between gap-2 pb-3 border-b border-[#E8E8E0]">
          <div className="flex items-center space-x-2">
            <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-[#ECECE5] text-[#171717] border border-[#DCDCD4]">
              {metadata.machine_id}
            </span>
            <span className={`text-[11px] px-2 py-0.5 rounded font-medium border ${criticalityBadge}`}>
              {metadata.criticality_level} Criticality
            </span>
          </div>

          <div className={`flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${statusConfig.badge}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${statusConfig.dot}`} />
            <span>{statusConfig.label}</span>
          </div>
        </div>

        {/* Machine Identity */}
        <div className="mt-3.5">
          <h2 className="text-base font-bold text-[#171717] group-hover:text-[#000000] transition tracking-tight">
            {metadata.machine_name}
          </h2>
          <p className="text-xs text-[#6B6B66] mt-0.5">{metadata.machine_type}</p>
        </div>

        {/* Key Metrics: Clean Editorial Rows */}
        <div className="mt-4 pt-3 border-t border-[#E8E8E0] space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <span className="text-[#6B6B66]">Vibration</span>
            <span className="font-medium text-[#171717] font-mono">
              {latest_sensor?.vibration_mm_s !== undefined
                ? `${latest_sensor.vibration_mm_s.toFixed(2)} mm/s`
                : "—"}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-[#6B6B66]">Temperature</span>
            <span className="font-medium text-[#171717] font-mono">
              {latest_sensor?.temperature_c !== undefined
                ? `${latest_sensor.temperature_c.toFixed(1)}°C`
                : "—"}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-[#6B6B66]">Failure Probability</span>
            <span
              className={`font-semibold font-mono ${
                failureProb > 0.5 ? "text-[#9E2A2B]" : failureProb > 0.3 ? "text-[#8C5E14]" : "text-[#1E4D2B]"
              }`}
            >
              {hasTelemetry ? `${(failureProb * 100).toFixed(0)}%` : "Pending"}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-[#6B6B66]">Operating Hours</span>
            <span className="font-medium text-[#171717] font-mono">
              {metadata.operating_hours.toLocaleString()} hrs
            </span>
          </div>
        </div>
      </div>

      {/* Footer Link */}
      <div className="mt-5 pt-3 border-t border-[#E8E8E0] flex items-center justify-between text-xs font-medium text-[#171717] group-hover:translate-x-0.5 transition">
        <span>View investigation</span>
        <ArrowRight className="w-3.5 h-3.5 text-[#6B6B66] group-hover:text-[#171717] transition" />
      </div>
    </Link>
  );
}
