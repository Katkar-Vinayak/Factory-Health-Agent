import React from "react";
import { LucideIcon } from "lucide-react";

interface SummaryCardProps {
  title: string;
  count: number | string;
  subtitle: string;
  icon: LucideIcon;
  variant: "default" | "healthy" | "warning" | "critical" | "high_criticality";
  isActive?: boolean;
  onClick?: () => void;
}

export function SummaryCard({
  title,
  count,
  subtitle,
  icon: Icon,
  variant,
  isActive = false,
  onClick
}: SummaryCardProps) {
  const variantStyles = {
    default: {
      border: "border-[#DCDCD4]",
      bg: "bg-[#FAFAF5]",
      iconBg: "bg-[#EFEFE8] text-[#171717]",
      countText: "text-[#171717]"
    },
    healthy: {
      border: "border-[#C8E0CD]",
      bg: "bg-[#FAFAF5]",
      iconBg: "bg-[#EDF5EE] text-[#1E4D2B]",
      countText: "text-[#1E4D2B]"
    },
    warning: {
      border: "border-[#EADBB8]",
      bg: "bg-[#FAFAF5]",
      iconBg: "bg-[#FAF4E8] text-[#8C5E14]",
      countText: "text-[#8C5E14]"
    },
    critical: {
      border: "border-[#F2C2BD]",
      bg: "bg-[#FAFAF5]",
      iconBg: "bg-[#FDF0EE] text-[#9E2A2B]",
      countText: "text-[#9E2A2B]"
    },
    high_criticality: {
      border: "border-[#DCDCD4]",
      bg: "bg-[#FAFAF5]",
      iconBg: "bg-[#EFEFE8] text-[#171717]",
      countText: "text-[#171717]"
    }
  }[variant];

  return (
    <div
      onClick={onClick}
      className={`rounded-xl p-5 border transition ${variantStyles.border} ${variantStyles.bg} ${
        onClick ? "cursor-pointer hover:border-[#171717]/40 hover:shadow-xs" : ""
      } ${isActive ? "ring-2 ring-[#171717] shadow-xs" : "shadow-2xs"} h-full flex flex-col justify-between`}
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-[#6B6B66]">
            {title}
          </p>
          <div className="flex items-baseline space-x-2 mt-1.5">
            <span className={`text-3xl font-bold tracking-tight ${variantStyles.countText}`}>
              {count}
            </span>
          </div>
          <p className="text-xs text-[#6B6B66] mt-1">{subtitle}</p>
        </div>
        <div className={`p-3 rounded-xl shrink-0 ml-3 ${variantStyles.iconBg}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  );
}
