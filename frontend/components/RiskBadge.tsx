import React from "react";
import { ShieldCheck, AlertTriangle, AlertOctagon, Clock } from "lucide-react";

interface RiskBadgeProps {
  riskLevel?: string | null;
  size?: "sm" | "md" | "lg";
  showIcon?: boolean;
}

export function RiskBadge({ riskLevel, size = "md", showIcon = true }: RiskBadgeProps) {
  const normalized = (riskLevel || "LOW").toUpperCase();

  let colorClasses = "bg-[#EDF5EE] text-[#1E4D2B] border-[#C8E0CD]";
  let label = "Healthy / Low Risk";
  let Icon = ShieldCheck;

  if (normalized === "HIGH" || normalized === "CRITICAL") {
    colorClasses = "bg-[#FDF0EE] text-[#9E2A2B] border-[#F2C2BD]";
    label = "Critical / High Risk";
    Icon = AlertOctagon;
  } else if (normalized === "MEDIUM" || normalized === "WARNING") {
    colorClasses = "bg-[#FAF4E8] text-[#8C5E14] border-[#EADBB8]";
    label = "Warning / Medium Risk";
    Icon = AlertTriangle;
  } else if (normalized === "UNKNOWN" || normalized === "AWAITING" || normalized === "UNAVAILABLE") {
    colorClasses = "bg-[#F0F0EA] text-[#555550] border-[#DCDCD4]";
    label = "Awaiting Telemetry";
    Icon = Clock;
  }

  const sizeClasses = {
    sm: "px-2 py-0.5 text-xs",
    md: "px-2.5 py-1 text-xs sm:text-sm",
    lg: "px-3.5 py-1.5 text-sm sm:text-base font-semibold"
  }[size];

  const iconSizes = {
    sm: "w-3 h-3 mr-1",
    md: "w-4 h-4 mr-1.5",
    lg: "w-5 h-5 mr-2"
  }[size];

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full border ${colorClasses} ${sizeClasses}`}
    >
      {showIcon && <Icon className={iconSizes} />}
      {label}
    </span>
  );
}
