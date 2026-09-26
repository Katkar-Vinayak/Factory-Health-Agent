import React from "react";
import { AlertTriangle, Clock, Factory, Zap } from "lucide-react";

interface ImpactPanelProps {
  impact: {
    production_impact?: string;
    energy_impact?: string;
    downtime_risk?: string;
    urgency?: string;
  };
}

export function ImpactPanel({ impact }: ImpactPanelProps) {
  const urgency = (impact?.urgency || "LOW").toUpperCase();
  const urgencyColors: Record<string, string> = {
    HIGH: "text-[#9C382E] bg-[#FDF0EE] border-[#DE9E98]",
    CRITICAL: "text-[#9C382E] bg-[#FDF0EE] border-[#DE9E98]",
    MEDIUM: "text-[#8B6E28] bg-[#FAF4E8] border-[#E8DFC8]",
    LOW: "text-[#2A6E3B] bg-[#EDF5EE] border-[#94C09A]"
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
      {/* Production Impact */}
      <div className="bg-[#FAFAF5] border border-[#DCDCD4] rounded-lg p-4 shadow-2xs">
        <div className="flex items-center space-x-2 text-[#6B6B66] mb-1.5">
          <Factory className="w-3.5 h-3.5 text-[#4A4A45]" />
          <span className="text-[11px] font-mono font-medium uppercase tracking-wider text-[#6B6B66]">
            Production Impact
          </span>
        </div>
        <p className="text-sm font-semibold text-[#171717] mt-1">
          {impact.production_impact || "Nominal"}
        </p>
      </div>

      {/* Energy Impact */}
      <div className="bg-[#FAFAF5] border border-[#DCDCD4] rounded-lg p-4 shadow-2xs">
        <div className="flex items-center space-x-2 text-[#6B6B66] mb-1.5">
          <Zap className="w-3.5 h-3.5 text-[#8B6E28]" />
          <span className="text-[11px] font-mono font-medium uppercase tracking-wider text-[#6B6B66]">
            Energy Impact
          </span>
        </div>
        <p className="text-sm font-semibold text-[#171717] mt-1">
          {impact.energy_impact || "Nominal"}
        </p>
      </div>

      {/* Downtime Risk */}
      <div className="bg-[#FAFAF5] border border-[#DCDCD4] rounded-lg p-4 shadow-2xs">
        <div className="flex items-center space-x-2 text-[#6B6B66] mb-1.5">
          <Clock className="w-3.5 h-3.5 text-[#9C382E]" />
          <span className="text-[11px] font-mono font-medium uppercase tracking-wider text-[#6B6B66]">
            Downtime Risk
          </span>
        </div>
        <p className="text-sm font-semibold text-[#171717] mt-1">
          {impact.downtime_risk || "Minimal Risk"}
        </p>
      </div>

      {/* Urgency */}
      <div className="bg-[#FAFAF5] border border-[#DCDCD4] rounded-lg p-4 shadow-2xs">
        <div className="flex items-center space-x-2 text-[#6B6B66] mb-1.5">
          <AlertTriangle className="w-3.5 h-3.5 text-[#6B6B66]" />
          <span className="text-[11px] font-mono font-medium uppercase tracking-wider text-[#6B6B66]">
            Urgency Level
          </span>
        </div>
        <div className="mt-1">
          <span
            className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
              urgencyColors[urgency] || urgencyColors.LOW
            }`}
          >
            {impact.urgency || "LOW"}
          </span>
        </div>
      </div>
    </div>
  );
}
