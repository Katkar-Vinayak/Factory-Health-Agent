import React from "react";
import { Recommendation } from "../types";
import { CheckSquare, ShieldCheck, DollarSign, AlertCircle } from "lucide-react";

interface RecommendationListProps {
  recommendations: Recommendation[];
}

export function RecommendationList({ recommendations }: RecommendationListProps) {
  if (!recommendations || recommendations.length === 0) {
    return (
      <div className="bg-[#EDF5EE] border border-[#94C09A] rounded-lg p-5 text-center text-[#1D4E29]">
        <ShieldCheck className="w-7 h-7 mx-auto mb-2 text-[#2A6E3B]" />
        <h2 className="text-sm font-semibold">Machine Operating Under Nominal Conditions</h2>
        <p className="text-xs text-[#2A6E3B] mt-1">
          No corrective maintenance required. Maintain standard preventive inspection cadence.
        </p>
      </div>
    );
  }

  const priorityColors: Record<string, string> = {
    HIGH: "bg-[#FDF0EE] text-[#9C382E] border-[#DE9E98]",
    CRITICAL: "bg-[#FDF0EE] text-[#9C382E] border-[#DE9E98]",
    MEDIUM: "bg-[#FAF4E8] text-[#8B6E28] border-[#E8DFC8]",
    LOW: "bg-[#EDF5EE] text-[#2A6E3B] border-[#94C09A]"
  };

  return (
    <div className="space-y-3">
      {recommendations.map((rec, idx) => (
        <div
          key={idx}
          className="bg-[#FAFAF5] border border-[#DCDCD4] hover:border-[#B8B8AE] rounded-lg p-4 sm:p-5 shadow-2xs transition"
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-3 border-b border-[#DCDCD4]">
            <div>
              <span className="text-[10px] font-mono font-medium uppercase tracking-wider text-[#6B6B66]">
                Decision Agent Recommendation
              </span>
              <h2 className="text-sm sm:text-base font-semibold text-[#171717] mt-0.5">{rec.action}</h2>
            </div>
            <div className="flex items-center space-x-2 self-start sm:self-center">
              <span
                className={`text-xs px-2.5 py-0.5 rounded-full font-semibold border ${
                  priorityColors[rec.priority.toUpperCase()] || "bg-[#F0F0EA] text-[#4A4A45] border-[#DCDCD4]"
                }`}
              >
                {rec.priority} Priority
              </span>
              {rec.estimated_cost_impact && (
                <span className="inline-flex items-center text-xs px-2 py-0.5 rounded-full font-medium bg-[#F5F5EE] text-[#4A4A45] border border-[#DCDCD4]">
                  <DollarSign className="w-3 h-3 mr-0.5 text-[#6B6B66]" />
                  Cost: {rec.estimated_cost_impact}
                </span>
              )}
            </div>
          </div>

          <p className="text-xs sm:text-sm text-[#4A4A45] mt-3 leading-relaxed">
            {rec.details}
          </p>

          {rec.recommended_actions && rec.recommended_actions.length > 0 && (
            <div className="mt-3.5 pt-3 border-t border-[#DCDCD4] bg-[#F5F5EE] rounded-md p-3.5">
              <p className="text-xs font-semibold text-[#171717] mb-2 flex items-center">
                <CheckSquare className="w-3.5 h-3.5 mr-1.5 text-[#4A4A45]" />
                Prescribed Safety &amp; Operational Action Steps:
              </p>
              <ul className="space-y-1.5">
                {rec.recommended_actions.map((act, actIdx) => (
                  <li key={actIdx} className="flex items-start text-xs text-[#4A4A45]">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#171717] mt-1.5 mr-2 shrink-0" />
                    <span>{act}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
