import React from "react";
import {
  CheckCircle2,
  ArrowDown,
  Activity,
  Search,
  Brain,
  Zap,
  ShieldCheck,
  FileText,
  Bell,
  UserCheck,
  Wrench,
  CheckCheck
} from "lucide-react";

interface AgentTraceProps {
  trace: string[];
}

export function AgentTrace({ trace }: AgentTraceProps) {
  if (!trace || trace.length === 0) {
    return null;
  }

  const getStepIcon = (text: string) => {
    const lower = text.toLowerCase();
    if (lower.includes("monitoring") || lower.includes("telemetry")) return Activity;
    if (lower.includes("investigation") || lower.includes("correlating")) return Search;
    if (lower.includes("rca") || lower.includes("root cause")) return Brain;
    if (lower.includes("impact") || lower.includes("loss")) return Zap;
    if (lower.includes("decision") || lower.includes("prescribing")) return ShieldCheck;
    if (lower.includes("notification") || lower.includes("alert")) return Bell;
    if (lower.includes("approval") || lower.includes("human") || lower.includes("operator")) return UserCheck;
    if (lower.includes("action") || lower.includes("executed") || lower.includes("dispatch")) return Wrench;
    if (lower.includes("verification") || lower.includes("verified")) return CheckCheck;
    if (lower.includes("report") || lower.includes("summary")) return FileText;
    return CheckCircle2;
  };

  const getStepColor = (text: string) => {
    const lower = text.toLowerCase();
    if (lower.includes("critical") || lower.includes("high") || lower.includes("warning")) {
      return "border-rose-400 bg-rose-50 text-rose-700";
    }
    if (lower.includes("rca") || lower.includes("bearing") || lower.includes("motor") || lower.includes("cooling")) {
      return "border-purple-300 bg-purple-50 text-purple-700";
    }
    if (lower.includes("notification") || lower.includes("alert")) {
      return "border-amber-300 bg-amber-50 text-amber-700";
    }
    if (lower.includes("approval") || lower.includes("human")) {
      return "border-blue-300 bg-blue-50 text-blue-700";
    }
    if (lower.includes("decision") || lower.includes("action") || lower.includes("verification")) {
      return "border-emerald-300 bg-emerald-50 text-emerald-700";
    }
    return "border-slate-300 bg-slate-50 text-slate-800";
  };

  return (
    <div className="bg-[#FAFAF5] text-[#171717] rounded-lg p-5 sm:p-6 shadow-2xs border border-[#DCDCD4]">
      <div className="flex items-center justify-between pb-3.5 mb-4 border-b border-[#DCDCD4]">
        <div className="flex items-center space-x-2.5">
          <div className="w-2 h-2 rounded-full bg-[#2A6E3B]" />
          <h2 className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-[#171717]">
            Agent Execution Activity ({trace.length} Steps)
          </h2>
        </div>
        <span className="text-[10px] font-mono text-[#6B6B66] bg-[#F5F5EE] px-2 py-0.5 rounded border border-[#DCDCD4]">
          LangGraph + HITL Workflow
        </span>
      </div>

      {/* Visual Workflow Stages Progression: Complete 10-Stage Pipeline */}
      <div className="mb-5 p-3 rounded-md bg-[#F5F5EE] border border-[#DCDCD4]">
        <p className="text-[10px] font-mono font-medium text-[#6B6B66] mb-2 uppercase tracking-wider">
          Multi-Agent Reasoning &amp; Human-in-the-Loop Architecture:
        </p>
        <div className="flex flex-wrap items-center gap-1.5 text-xs">
          {[
            "Monitoring",
            "Investigation",
            "RCA",
            "Impact",
            "Decision",
            "Notification",
            "Approval",
            "Action",
            "Verification",
            "Report"
          ].map((stage, sIdx, arr) => (
            <React.Fragment key={stage}>
              <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-[#FAFAF5] text-[#4A4A45] border border-[#DCDCD4]">
                {stage}
              </span>
              {sIdx < arr.length - 1 && (
                <span className="text-[#9E9E96] font-bold select-none text-[10px]">→</span>
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      <div className="relative pl-6 space-y-3.5 before:absolute before:left-3 before:top-2 before:bottom-2 before:w-px before:bg-[#DCDCD4]">
        {trace.map((step, idx) => {
          const Icon = getStepIcon(step);
          const isLast = idx === trace.length - 1;

          return (
            <div key={idx} className="relative group">
              {/* Timeline marker */}
              <div className="absolute -left-6 mt-1 flex items-center justify-center w-6 h-6 rounded-full bg-[#FAFAF5] border border-[#94C09A] text-[#2A6E3B] shadow-2xs">
                <CheckCircle2 className="w-3.5 h-3.5" />
              </div>

              {/* Step bubble */}
              <div className="bg-[#F5F5EE] hover:bg-[#EFEFE8] border border-[#DCDCD4] rounded-md p-3 transition">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start space-x-2.5">
                    <div className="p-1 rounded bg-[#E8E8DF] text-[#4A4A45] mt-0.5 shrink-0">
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                    <span className="text-xs sm:text-sm font-medium text-[#171717] leading-snug">
                      {step}
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-[#6B6B66] shrink-0 bg-[#FAFAF5] px-1.5 py-0.5 rounded border border-[#DCDCD4]">
                    Step {idx + 1}
                  </span>
                </div>
              </div>

              {!isLast && (
                <div className="flex justify-center -mb-2 mt-0.5 text-[#B8B8AE]">
                  <ArrowDown className="w-3 h-3 text-[#B8B8AE]" />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
