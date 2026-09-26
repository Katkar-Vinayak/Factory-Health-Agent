import React from "react";
import { LucideIcon } from "lucide-react";

interface SensorCardProps {
  label: string;
  value: number | string | undefined;
  unit: string;
  baseline: string;
  icon: LucideIcon;
  status: "normal" | "warning" | "critical";
  delta?: string;
}

export function SensorCard({
  label,
  value,
  unit,
  baseline,
  icon: Icon,
  status,
  delta
}: SensorCardProps) {
  const statusStyles = {
    normal: {
      border: "border-[#DCDCD4] bg-[#FAFAF5]",
      badge: "bg-[#EDF5EE] text-[#1E4D2B] border-[#C8E0CD]",
      badgeLabel: "Nominal",
      iconBg: "bg-[#EFEFE8] text-[#171717]",
      valueColor: "text-[#171717]"
    },
    warning: {
      border: "border-[#EADBB8] bg-[#FAFAF5]",
      badge: "bg-[#FAF4E8] text-[#8C5E14] border-[#EADBB8]",
      badgeLabel: "Elevated",
      iconBg: "bg-[#FAF4E8] text-[#8C5E14]",
      valueColor: "text-[#8C5E14]"
    },
    critical: {
      border: "border-[#F2C2BD] bg-[#FAFAF5]",
      badge: "bg-[#FDF0EE] text-[#9E2A2B] border-[#F2C2BD]",
      badgeLabel: "Critical",
      iconBg: "bg-[#FDF0EE] text-[#9E2A2B]",
      valueColor: "text-[#9E2A2B]"
    }
  }[status];

  const formattedValue =
    typeof value === "number"
      ? Number.isInteger(value)
        ? value.toString()
        : value.toFixed(2)
      : value ?? "--";

  return (
    <div
      className={`rounded-xl p-4 border transition shadow-2xs ${statusStyles.border}`}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center space-x-2">
          <div className={`p-2 rounded-lg shrink-0 ${statusStyles.iconBg}`}>
            <Icon className="w-4 h-4" />
          </div>
          <div>
            <p className="text-xs font-medium text-[#6B6B66]">{label}</p>
            <span
              className={`inline-block mt-0.5 px-2 py-0.2 rounded-full text-[10px] font-semibold border ${statusStyles.badge}`}
            >
              {statusStyles.badgeLabel}
            </span>
          </div>
        </div>

        {delta && (
          <span
            className={`text-xs font-semibold px-1.5 py-0.5 rounded border ${
              delta.startsWith("+")
                ? "bg-[#FDF0EE] text-[#9E2A2B] border-[#F2C2BD]"
                : "bg-[#EDF5EE] text-[#1E4D2B] border-[#C8E0CD]"
            }`}
          >
            {delta}
          </span>
        )}
      </div>

      <div className="mt-3 flex items-baseline space-x-1.5">
        <span className={`text-2xl font-bold font-mono tracking-tight ${statusStyles.valueColor}`}>
          {formattedValue}
        </span>
        <span className="text-xs font-medium text-[#6B6B66]">{unit}</span>
      </div>

      <p className="mt-2 text-[11px] text-[#8C8C85] border-t border-[#E8E8E0] pt-2">
        Baseline: <span className="text-[#171717] font-medium">{baseline}</span>
      </p>
    </div>
  );
}
