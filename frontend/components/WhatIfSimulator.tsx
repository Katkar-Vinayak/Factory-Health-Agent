"use client";

import React, { useState, useEffect } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine
} from "recharts";
import { WhatIfSimulationResponse } from "../types";
import { simulateWhatIf } from "../lib/api";
import { RiskBadge } from "./RiskBadge";
import {
  Sliders,
  TrendingDown,
  TrendingUp,
  AlertTriangle,
  ShieldCheck,
  Zap,
  Clock,
  Package,
  ChevronDown,
  ChevronUp,
  Info,
  Activity,
  Loader2,
  CheckCircle2,
  Sparkles
} from "lucide-react";

interface WhatIfSimulatorProps {
  machineId: string;
  timestamp?: string;
  onClose?: () => void;
}

export function WhatIfSimulator({ machineId, timestamp, onClose }: WhatIfSimulatorProps) {
  const [data, setData] = useState<WhatIfSimulationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAssumptions, setShowAssumptions] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const loadSimulation = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await simulateWhatIf(machineId, timestamp);
        if (isMounted) {
          setData(res);
        }
      } catch (err: unknown) {
        if (isMounted) {
          if (err instanceof Error) {
            setError(err.message);
          } else {
            setError("Failed to generate 24-hour what-if scenario.");
          }
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    loadSimulation();

    return () => {
      isMounted = false;
    };
  }, [machineId, timestamp]);

  if (loading) {
    return (
      <div className="rounded-xl border border-[#DCDCD4] bg-[#FAFAF5] p-8 sm:p-12 text-center animate-pulse">
        <Loader2 className="w-8 h-8 animate-spin text-[#171717] mx-auto mb-3" />
        <h3 className="text-sm font-semibold text-[#171717]">Building 24-hour scenarios...</h3>
        <p className="text-xs text-[#6B6B66] mt-1 max-w-md mx-auto">
          Projecting operational trajectories comparing immediate proactive intervention against continued unmitigated degradation.
        </p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-xl border border-[#DE9E98] bg-[#FDF0EE] p-5 text-[#9C382E] flex items-start space-x-3">
        <AlertTriangle className="w-5 h-5 text-[#9C382E] shrink-0 mt-0.5" />
        <div>
          <h4 className="text-sm font-semibold">Simulator Error</h4>
          <p className="text-xs mt-1">{error || "Unable to load simulation data."}</p>
        </div>
      </div>
    );
  }

  const {
    current_state,
    assumptions,
    intervene_now,
    do_nothing,
    estimated_difference
  } = data;

  // Chart data: merge hourly trajectory points
  const chartData = intervene_now.trajectory.map((intPoint, idx) => {
    const dnPoint = do_nothing.trajectory[idx] || {};
    return {
      hourLabel: `+${intPoint.hour}h`,
      hour: intPoint.hour,
      interveneRisk: intPoint.projected_risk_index,
      doNothingRisk: dnPoint.projected_risk_index,
      interveneProd: intPoint.projected_production,
      doNothingProd: dnPoint.projected_production,
      interveneEnergy: intPoint.projected_energy,
      doNothingEnergy: dnPoint.projected_energy
    };
  });

  return (
    <div className="rounded-xl border border-[#DCDCD4] bg-[#FAFAF5] p-6 sm:p-7 shadow-2xs space-y-6">
      {/* 1. Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-[#DCDCD4] gap-4">
        <div className="flex items-start space-x-3">
          <div className="p-2 bg-[#171717] text-white rounded-lg shadow-2xs">
            <Sliders className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-base sm:text-lg font-bold text-[#171717] tracking-tight">
                WHAT-IF SIMULATOR: 24-HOUR IMPACT
              </h3>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold uppercase tracking-wider bg-[#FAF4E8] text-[#8B6E28] border border-[#E8DFC8]">
                Decision Support
              </span>
            </div>
            <p className="text-xs text-[#6B6B66] mt-0.5">
              Comparative scenario modeling: <strong className="text-[#171717]">Intervene Now</strong> vs.{" "}
              <strong className="text-[#171717]">Do Nothing</strong> over next 24 operating hours.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-[11px] font-mono text-[#6B6B66] bg-[#F5F5EE] px-2.5 py-1 rounded border border-[#DCDCD4]">
            Scenario Estimate • Not Physical Guarantee
          </span>
          {onClose && (
            <button
              onClick={onClose}
              className="text-xs px-2.5 py-1 rounded border border-[#DCDCD4] bg-white hover:bg-[#F5F5EE] text-[#4A4A45] font-semibold transition cursor-pointer"
            >
              Hide
            </button>
          )}
        </div>
      </div>

      {/* 2. Current State Snapshot Bar */}
      <div className="bg-[#F5F5EE] rounded-lg p-4 border border-[#DCDCD4]">
        <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
          <span className="text-[11px] font-mono font-semibold uppercase tracking-wider text-[#4A4A45] flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-[#171717]" />
            Current Machine Operating Baseline
          </span>
          <span className="text-xs font-mono text-[#6B6B66]">
            Asset: <strong className="text-[#171717]">{data.machine_id}</strong> • Root Cause:{" "}
            <strong className="text-[#171717]">{data.root_cause}</strong>
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2.5 text-center">
          <div className="bg-[#FAFAF5] rounded-md p-2.5 border border-[#DCDCD4] shadow-2xs">
            <span className="text-[10px] font-mono uppercase text-[#6B6B66]">Current Risk</span>
            <div className="mt-1 flex justify-center">
              <RiskBadge riskLevel={current_state.risk_level} size="sm" />
            </div>
          </div>

          <div className="bg-[#FAFAF5] rounded-md p-2.5 border border-[#DCDCD4] shadow-2xs">
            <span className="text-[10px] font-mono uppercase text-[#6B6B66]">Failure Prob.</span>
            <p className="text-sm font-semibold text-[#171717] mt-1">
              {(current_state.failure_probability * 100).toFixed(0)}%
            </p>
          </div>

          <div className="bg-[#FAFAF5] rounded-md p-2.5 border border-[#DCDCD4] shadow-2xs">
            <span className="text-[10px] font-mono uppercase text-[#6B6B66]">Throughput</span>
            <p className="text-sm font-semibold text-[#171717] mt-1">
              {current_state.production}{" "}
              <span className="text-[10px] font-normal text-[#6B6B66]">u/h</span>
            </p>
          </div>

          <div className="bg-[#FAFAF5] rounded-md p-2.5 border border-[#DCDCD4] shadow-2xs">
            <span className="text-[10px] font-mono uppercase text-[#6B6B66]">Energy</span>
            <p className="text-sm font-semibold text-[#171717] mt-1">
              {current_state.energy}{" "}
              <span className="text-[10px] font-normal text-[#6B6B66]">kWh</span>
            </p>
          </div>

          <div className="bg-[#FAFAF5] rounded-md p-2.5 border border-[#DCDCD4] shadow-2xs">
            <span className="text-[10px] font-mono uppercase text-[#6B6B66]">Anomaly Status</span>
            <p className="text-xs font-semibold mt-1 truncate">
              {current_state.anomaly ? (
                <span className="text-[#9C382E]">Anomaly Active</span>
              ) : (
                <span className="text-[#2A6E3B]">Inlier Normal</span>
              )}
            </p>
          </div>

          <div className="bg-[#FAFAF5] rounded-md p-2.5 border border-[#DCDCD4] shadow-2xs">
            <span className="text-[10px] font-mono uppercase text-[#6B6B66]">Downtime Risk</span>
            <p className="text-xs font-semibold text-[#171717] mt-1 truncate" title={current_state.downtime_risk}>
              {current_state.downtime_risk}
            </p>
          </div>
        </div>
      </div>

      {/* 3. Decision Impact Hero Card */}
      <div className="rounded-xl border border-[#DCDCD4] bg-[#F5F5EE] p-5 sm:p-6 shadow-2xs">
        <div className="flex items-center justify-between pb-3 border-b border-[#DCDCD4] mb-4">
          <div className="flex items-center space-x-2">
            <Sparkles className="w-4 h-4 text-[#8B6E28]" />
            <span className="text-xs font-bold uppercase tracking-wider text-[#171717]">
              24-Hour Projected Decision Impact
            </span>
          </div>
          <span className="text-[11px] font-mono font-medium px-2 py-0.5 rounded bg-white text-[#4A4A45] border border-[#DCDCD4]">
            Comparative Scenario Differential
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          {/* Scenario A: Intervene Now (LEFT) */}
          <div className="bg-[#FAFAF5] rounded-lg p-4 border border-[#94C09A] flex flex-col justify-between h-full shadow-2xs">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-[#2A6E3B]">
                  SCENARIO A: INTERVENE NOW
                </span>
                <span className="px-2 py-0.5 text-[10px] font-mono font-semibold uppercase rounded bg-[#EDF5EE] text-[#2A6E3B] border border-[#94C09A]">
                  Controlled Recovery
                </span>
              </div>
              <p className="text-xs text-[#4A4A45] leading-relaxed">
                {assumptions.intervention_action}
              </p>
            </div>

            <div className="mt-4 pt-3 border-t border-[#DCDCD4] flex items-baseline justify-between">
              <span className="text-xs text-[#6B6B66]">Projected Risk Index (24h):</span>
              <span className="text-xl font-bold text-[#2A6E3B]">
                {intervene_now.projected_risk_index.toFixed(1)} / 100
              </span>
            </div>
          </div>

          {/* Scenario B: Do Nothing (RIGHT) */}
          <div className="bg-[#FAFAF5] rounded-lg p-4 border border-[#DE9E98] flex flex-col justify-between h-full shadow-2xs">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-[#9C382E]">
                  SCENARIO B: DO NOTHING
                </span>
                <span className="px-2 py-0.5 text-[10px] font-mono font-semibold uppercase rounded bg-[#FDF0EE] text-[#9C382E] border border-[#DE9E98]">
                  High Risk Exposure
                </span>
              </div>
              <p className="text-xs text-[#4A4A45] leading-relaxed">
                Continue operation without intervention. Unmitigated thermal, vibration, and friction progression.
              </p>
            </div>

            <div className="mt-4 pt-3 border-t border-[#DCDCD4] flex items-baseline justify-between">
              <span className="text-xs text-[#6B6B66]">Projected Risk Index (24h):</span>
              <span className="text-xl font-bold text-[#9C382E]">
                {do_nothing.projected_risk_index.toFixed(1)} / 100
              </span>
            </div>
          </div>
        </div>

        {/* Avoided Exposure Highlight Counters */}
        <div className="bg-[#FAFAF5] rounded-lg p-4 border border-[#DCDCD4]">
          <p className="text-[11px] font-mono font-medium uppercase tracking-wider text-[#6B6B66] mb-3 text-center sm:text-left">
            Estimated Operational Exposure Avoided by Intervening Now:
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-center">
            {/* 1. Production Loss Avoided */}
            <div className="bg-white rounded-md p-3 border border-[#DCDCD4]">
              <span className="text-[11px] font-medium text-[#6B6B66] block">Production Loss Avoided</span>
              <p className="text-2xl font-bold text-[#2A6E3B] mt-1 flex items-center justify-center gap-1">
                <TrendingDown className="w-5 h-5 text-[#2A6E3B]" />
                {estimated_difference.production_loss_avoided.toFixed(0)}{" "}
                <span className="text-xs font-normal text-[#6B6B66]">units*</span>
              </p>
              <span className="text-[10px] text-[#6B6B66]">Breakdown avoidance vs planned de-rate</span>
            </div>

            {/* 2. Energy Waste Avoided */}
            <div className="bg-white rounded-md p-3 border border-[#DCDCD4]">
              <span className="text-[11px] font-medium text-[#6B6B66] block">Energy Wastage Avoided</span>
              <p className="text-2xl font-bold text-[#171717] mt-1 flex items-center justify-center gap-1">
                <Zap className="w-5 h-5 text-[#8B6E28]" />
                {estimated_difference.energy_wastage_avoided.toFixed(0)}{" "}
                <span className="text-xs font-normal text-[#6B6B66]">kWh*</span>
              </p>
              <span className="text-[10px] text-[#6B6B66]">Friction &amp; thermal dissipation savings</span>
            </div>

            {/* 3. Downtime Exposure Avoided */}
            <div className="bg-white rounded-md p-3 border border-[#DCDCD4]">
              <span className="text-[11px] font-medium text-[#6B6B66] block">Downtime Exposure Avoided</span>
              <p className="text-2xl font-bold text-[#8B6E28] mt-1 flex items-center justify-center gap-1">
                <Clock className="w-5 h-5 text-[#8B6E28]" />
                {estimated_difference.downtime_exposure_avoided.toFixed(1)}{" "}
                <span className="text-xs font-normal text-[#6B6B66]">hours*</span>
              </p>
              <span className="text-[10px] text-[#6B6B66]">Critical outage risk reduction</span>
            </div>
          </div>

          <p className="text-[10px] text-[#6B6B66] mt-3 text-right">
            *Scenario estimate derived from configured intervention damping assumptions. Not guaranteed.
          </p>
        </div>
      </div>

      {/* 3.5. Qwen Scenario Explanation Callout */}
      {data.explanation && (
        <div className="rounded-lg border border-[#DCDCD4] bg-[#F5F5EE] p-4 text-xs text-[#171717]">
          <div className="flex items-center space-x-1.5 font-semibold text-[#171717] mb-1">
            <Sparkles className="w-3.5 h-3.5 text-[#6B6B66]" />
            <span className="uppercase tracking-wider text-[11px]">Operational Decision Explanation</span>
          </div>
          <p className="leading-relaxed text-[#4A4A45]">{data.explanation}</p>
        </div>
      )}

      {/* 4. Risk Trajectory Chart (Recharts) */}
      <div className="bg-[#FAFAF5] rounded-lg p-5 border border-[#DCDCD4]">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 mb-4 border-b border-[#DCDCD4] gap-2">
          <div>
            <h4 className="text-sm font-semibold text-[#171717] flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-[#4A4A45]" />
              24-Hour Projected Risk Index Trajectory
            </h4>
            <p className="text-xs text-[#6B6B66] mt-0.5">
              Comparison of hourly projected risk index (0 = Ideal, 100 = Imminent Outage)
            </p>
          </div>

          <div className="flex items-center space-x-3 text-xs">
            <span className="flex items-center gap-1.5 text-[#9C382E] font-medium">
              <span className="w-3 h-1 bg-[#C24134] rounded-full inline-block" />
              Do Nothing
            </span>
            <span className="flex items-center gap-1.5 text-[#2A6E3B] font-medium">
              <span className="w-3 h-1 bg-[#2A6E3B] rounded-full inline-block" />
              Intervene Now
            </span>
          </div>
        </div>

        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#DCDCD4" />
              <XAxis dataKey="hourLabel" stroke="#6B6B66" fontSize={11} tickLine={false} />
              <YAxis
                domain={[0, 100]}
                stroke="#6B6B66"
                fontSize={11}
                tickLine={false}
                label={{
                  value: "Risk Index",
                  angle: -90,
                  position: "insideLeft",
                  style: { fontSize: 10, fill: "#6B6B66" }
                }}
              />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (active && payload && payload.length) {
                    const dnVal = payload.find((p) => p.dataKey === "doNothingRisk")?.value;
                    const intVal = payload.find((p) => p.dataKey === "interveneRisk")?.value;
                    return (
                      <div className="bg-[#1F1F1D] text-white rounded-md p-3 text-xs shadow-lg border border-[#40403C] space-y-1">
                        <p className="font-semibold text-[#DCDCD4] pb-1 border-b border-[#40403C]">
                          Timeline: {label}
                        </p>
                        <p className="text-[#DE9E98] font-medium flex justify-between gap-4">
                          <span>Do Nothing:</span>
                          <span>{dnVal} / 100</span>
                        </p>
                        <p className="text-[#94C09A] font-medium flex justify-between gap-4">
                          <span>Intervene Now:</span>
                          <span>{intVal} / 100</span>
                        </p>
                        {dnVal !== undefined && intVal !== undefined && (
                          <p className="text-[#DCDCD4] text-[10px] pt-1 border-t border-[#40403C]">
                            Risk Reduction: {(Number(dnVal) - Number(intVal)).toFixed(1)} pts
                          </p>
                        )}
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <ReferenceLine
                y={70}
                stroke="#C24134"
                strokeDasharray="4 4"
                label={{
                  value: "Critical Threshold (70)",
                  position: "top",
                  fill: "#C24134",
                  fontSize: 10
                }}
              />
              <ReferenceLine
                y={40}
                stroke="#8B6E28"
                strokeDasharray="4 4"
                label={{
                  value: "Warning Threshold (40)",
                  position: "top",
                  fill: "#8B6E28",
                  fontSize: 10
                }}
              />

              <Line
                type="monotone"
                dataKey="doNothingRisk"
                name="Do Nothing"
                stroke="#C24134"
                strokeWidth={2.5}
                dot={{ r: 2 }}
                activeDot={{ r: 5 }}
              />
              <Line
                type="monotone"
                dataKey="interveneRisk"
                name="Intervene Now"
                stroke="#2A6E3B"
                strokeWidth={2.5}
                dot={{ r: 2 }}
                activeDot={{ r: 5 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 5. Impact Metrics Comparison Table / Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
        {/* Card 1: Production Impact */}
        <div className="bg-[#FAFAF5] border border-[#DCDCD4] rounded-lg p-4 shadow-2xs">
          <div className="flex items-center space-x-2 text-[#171717] font-semibold text-xs uppercase tracking-wider mb-2">
            <Package className="w-4 h-4 text-[#4A4A45]" />
            <span>Cumulative Production Loss (24h)</span>
          </div>
          <div className="space-y-1.5 text-xs text-[#4A4A45] mt-2">
            <div className="flex justify-between py-1 border-b border-[#DCDCD4]">
              <span>Do Nothing:</span>
              <span className="font-semibold text-[#9C382E]">
                {do_nothing.production_loss_units.toFixed(0)} units
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#DCDCD4]">
              <span>Intervene Now:</span>
              <span className="font-semibold text-[#171717]">
                {intervene_now.production_loss_units.toFixed(0)} units
              </span>
            </div>
            <div className="flex justify-between pt-1 font-semibold text-[#2A6E3B]">
              <span>Avoided Loss:</span>
              <span>↓ {estimated_difference.production_loss_avoided.toFixed(0)} units</span>
            </div>
          </div>
        </div>

        {/* Card 2: Energy Wastage */}
        <div className="bg-[#FAFAF5] border border-[#DCDCD4] rounded-lg p-4 shadow-2xs">
          <div className="flex items-center space-x-2 text-[#171717] font-semibold text-xs uppercase tracking-wider mb-2">
            <Zap className="w-4 h-4 text-[#8B6E28]" />
            <span>Cumulative Energy Waste (24h)</span>
          </div>
          <div className="space-y-1.5 text-xs text-[#4A4A45] mt-2">
            <div className="flex justify-between py-1 border-b border-[#DCDCD4]">
              <span>Do Nothing:</span>
              <span className="font-semibold text-[#9C382E]">
                {do_nothing.energy_wastage_kwh.toFixed(0)} kWh
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#DCDCD4]">
              <span>Intervene Now:</span>
              <span className="font-semibold text-[#171717]">
                {intervene_now.energy_wastage_kwh.toFixed(0)} kWh
              </span>
            </div>
            <div className="flex justify-between pt-1 font-semibold text-[#2A6E3B]">
              <span>Avoided Waste:</span>
              <span>↓ {estimated_difference.energy_wastage_avoided.toFixed(0)} kWh</span>
            </div>
          </div>
        </div>

        {/* Card 3: Downtime Exposure */}
        <div className="bg-[#FAFAF5] border border-[#DCDCD4] rounded-lg p-4 shadow-2xs">
          <div className="flex items-center space-x-2 text-[#171717] font-semibold text-xs uppercase tracking-wider mb-2">
            <Clock className="w-4 h-4 text-[#8B6E28]" />
            <span>Outage Risk Exposure (24h)</span>
          </div>
          <div className="space-y-1.5 text-xs text-[#4A4A45] mt-2">
            <div className="flex justify-between py-1 border-b border-[#DCDCD4]">
              <span>Do Nothing:</span>
              <span className="font-semibold text-[#9C382E]">
                {do_nothing.downtime_exposure_hours.toFixed(1)} hrs ({do_nothing.hours_above_critical}h critical)
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#DCDCD4]">
              <span>Intervene Now:</span>
              <span className="font-semibold text-[#171717]">
                {intervene_now.downtime_exposure_hours.toFixed(1)} hrs ({intervene_now.hours_above_critical}h critical)
              </span>
            </div>
            <div className="flex justify-between pt-1 font-semibold text-[#2A6E3B]">
              <span>Exposure Avoided:</span>
              <span>↓ {estimated_difference.downtime_exposure_avoided.toFixed(1)} hrs</span>
            </div>
          </div>
        </div>
      </div>

      {/* 6. Expandable Scenario Assumptions */}
      <div className="border border-[#DCDCD4] rounded-lg overflow-hidden bg-[#FAFAF5]">
        <button
          type="button"
          onClick={() => setShowAssumptions(!showAssumptions)}
          className="w-full flex items-center justify-between p-3.5 bg-[#F5F5EE] hover:bg-[#EFEFE8] transition text-left cursor-pointer"
        >
          <div className="flex items-center space-x-2 text-xs font-semibold text-[#171717]">
            <Info className="w-4 h-4 text-[#6B6B66]" />
            <span>Scenario assumptions &amp; simulation parameters</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-[11px] text-[#6B6B66]">Click to {showAssumptions ? "hide" : "inspect"}</span>
            {showAssumptions ? (
              <ChevronUp className="w-4 h-4 text-[#6B6B66]" />
            ) : (
              <ChevronDown className="w-4 h-4 text-[#6B6B66]" />
            )}
          </div>
        </button>

        {showAssumptions && (
          <div className="p-4 bg-[#FAFAF5] border-t border-[#DCDCD4] text-xs text-[#4A4A45] space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <strong className="text-[#171717] block">Root Cause Model:</strong>
                <span className="text-[#171717] font-medium">{assumptions.root_cause_profile}</span>
              </div>
              <div>
                <strong className="text-[#171717] block">Prescribed Action:</strong>
                <span>{assumptions.intervention_action}</span>
              </div>
              <div>
                <strong className="text-[#171717] block">Capacity De-rate:</strong>
                <span>{assumptions.load_reduction}</span>
              </div>
              <div>
                <strong className="text-[#171717] block">Trend Deceleration:</strong>
                <span>{assumptions.trend_damping}</span>
              </div>
              <div>
                <strong className="text-[#171717] block">Friction Waste Recovery:</strong>
                <span>{assumptions.energy_recovery}</span>
              </div>
              <div>
                <strong className="text-[#171717] block">Stabilized Output:</strong>
                <span>{assumptions.production_stabilization}</span>
              </div>
            </div>

            <div className="p-3 bg-[#FAF4E8] border border-[#E8DFC8] rounded-md text-[11px] text-[#8B6E28]">
              <strong>Operational Disclaimer:</strong> {assumptions.disclaimer} Projected risk indices and resource
              differentials are modeled estimates generated for operator decision support.
            </div>
          </div>
        )}
      </div>

      {/* 7. Decision Summary */}
      <div className="rounded-lg border border-[#94C09A] bg-[#EDF5EE] p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-[#1D4E29]">
        <div className="flex items-center space-x-2.5">
          <CheckCircle2 className="w-5 h-5 text-[#2A6E3B] shrink-0" />
          <p className="text-xs sm:text-sm font-semibold">
            Intervening now is projected to reduce operational exposure under the configured assumptions.
          </p>
        </div>
        <div className="text-[11px] font-mono shrink-0">
          Horizon: 24h • Mode: Deterministic Simulation
        </div>
      </div>
    </div>
  );
}
