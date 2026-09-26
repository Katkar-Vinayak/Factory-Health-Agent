"use client";

import React, { useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  AreaChart,
  Area
} from "recharts";
import { SensorData, ProductionRecord } from "../types";
import { Thermometer, Activity, Zap, TrendingUp, Grid, Layers } from "lucide-react";

interface SensorChartProps {
  sensorHistory: SensorData[];
  productionHistory: ProductionRecord[];
}

export function SensorChart({ sensorHistory, productionHistory }: SensorChartProps) {
  const [activeTab, setActiveTab] = useState<"all" | "temperature" | "vibration" | "energy" | "production">("all");

  const formatTime = (ts?: string) => {
    if (!ts) return "";
    try {
      const parts = ts.split(" ");
      if (parts.length >= 2) {
        return parts[1].slice(0, 5); // HH:mm
      }
      return ts.slice(11, 16);
    } catch {
      return ts;
    }
  };

  const sensorChartData = sensorHistory.map((item) => ({
    time: formatTime(item.timestamp),
    timestamp: item.timestamp,
    temperature: item.temperature_c,
    vibration: item.vibration_mm_s,
    energy: item.energy_consumption_kwh,
    pressure: item.pressure_bar,
    load: item.load_percent,
    production: item.production_output_units
  }));

  const prodChartData =
    productionHistory.length > 0
      ? productionHistory.map((item) => ({
          time: formatTime(item.timestamp),
          timestamp: item.timestamp,
          production: item.production_output,
          target: item.production_target,
          efficiency: item.efficiency_percent
        }))
      : sensorChartData.map((item) => ({
          time: item.time,
          timestamp: item.timestamp,
          production: item.production,
          target: 120,
          efficiency: 100
        }));

  if (sensorHistory.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-500">
        No historical sensor telemetry available for this machine.
      </div>
    );
  }

  return (
    <div className="bg-[#FAFAF5] rounded-xl border border-[#DCDCD4] p-5 shadow-2xs">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#DCDCD4]">
        <div>
          <h2 className="text-base font-bold text-[#171717] flex items-center">
            <Activity className="w-5 h-5 mr-2 text-[#171717]" />
            Historical Telemetry &amp; Trends
          </h2>
          <p className="text-xs text-[#6B6B66] mt-0.5">
            Real chronological telemetry observations ({sensorHistory.length} sensor readings,{" "}
            {productionHistory.length} production logs)
          </p>
        </div>

        {/* View Switcher */}
        <div className="flex items-center space-x-1 bg-[#ECECE5] p-1 rounded-lg self-start sm:self-center text-xs">
          <button
            onClick={() => setActiveTab("all")}
            className={`px-3 py-1.5 rounded-md font-medium transition cursor-pointer ${
              activeTab === "all"
                ? "bg-[#171717] text-white shadow-2xs"
                : "text-[#6B6B66] hover:text-[#171717]"
            }`}
          >
            <Grid className="w-3.5 h-3.5 inline mr-1" />
            All 4 Charts
          </button>
          <button
            onClick={() => setActiveTab("temperature")}
            className={`px-3 py-1.5 rounded-md font-medium transition cursor-pointer ${
              activeTab === "temperature"
                ? "bg-[#171717] text-white shadow-2xs"
                : "text-[#6B6B66] hover:text-[#171717]"
            }`}
          >
            Temp
          </button>
          <button
            onClick={() => setActiveTab("vibration")}
            className={`px-3 py-1.5 rounded-md font-medium transition cursor-pointer ${
              activeTab === "vibration"
                ? "bg-[#171717] text-white shadow-2xs"
                : "text-[#6B6B66] hover:text-[#171717]"
            }`}
          >
            Vib
          </button>
          <button
            onClick={() => setActiveTab("energy")}
            className={`px-3 py-1.5 rounded-md font-medium transition cursor-pointer ${
              activeTab === "energy"
                ? "bg-[#171717] text-white shadow-2xs"
                : "text-[#6B6B66] hover:text-[#171717]"
            }`}
          >
            Energy
          </button>
          <button
            onClick={() => setActiveTab("production")}
            className={`px-3 py-1.5 rounded-md font-medium transition cursor-pointer ${
              activeTab === "production"
                ? "bg-[#171717] text-white shadow-2xs"
                : "text-[#6B6B66] hover:text-[#171717]"
            }`}
          >
            Production
          </button>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 1. Temperature Over Time */}
        {(activeTab === "all" || activeTab === "temperature") && (
          <div
            className={`border border-[#DCDCD4] rounded-xl p-4 bg-[#F5F5EE]/70 ${
              activeTab === "temperature" ? "lg:col-span-2" : ""
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-2">
                <div className="p-1.5 bg-[#FDF0EE] text-[#9E2A2B] rounded-md">
                  <Thermometer className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-[#171717]">
                    1. Operating Temperature Over Time
                  </h3>
                  <span className="text-[11px] text-[#6B6B66]">Unit: °C (Normal baseline ~46°C)</span>
                </div>
              </div>
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-[#FDF0EE] text-[#9E2A2B] border border-[#F2C2BD]">
                Threshold: 60°C
              </span>
            </div>
            <div className="h-56 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={sensorChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="tempGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#9E2A2B" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#9E2A2B" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#DCDCD4" />
                  <XAxis dataKey="time" tick={{ fontSize: 11, fill: "#6B6B66" }} />
                  <YAxis domain={["auto", "auto"]} tick={{ fontSize: 11, fill: "#6B6B66" }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#171717",
                      border: "1px solid #333",
                      borderRadius: "8px",
                      color: "#FAFAF5",
                      fontSize: "12px"
                    }}
                    formatter={(val: any) => [`${val} °C`, "Temperature"]}
                    labelFormatter={(label, items) => items[0]?.payload?.timestamp || label}
                  />
                  <ReferenceLine
                    y={60}
                    stroke="#9E2A2B"
                    strokeDasharray="4 4"
                    label={{ value: "Warning Threshold", fill: "#9E2A2B", fontSize: 10, position: "top" }}
                  />
                  <Area
                    type="monotone"
                    dataKey="temperature"
                    stroke="#9E2A2B"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#tempGradient)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* 2. Vibration Over Time */}
        {(activeTab === "all" || activeTab === "vibration") && (
          <div
            className={`border border-[#DCDCD4] rounded-xl p-4 bg-[#F5F5EE]/70 ${
              activeTab === "vibration" ? "lg:col-span-2" : ""
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-2">
                <div className="p-1.5 bg-[#FAF4E8] text-[#8C5E14] rounded-md">
                  <Activity className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-[#171717]">
                    2. Vibration Over Time
                  </h3>
                  <span className="text-[11px] text-[#6B6B66]">Unit: mm/s (Normal baseline ~1.8 mm/s)</span>
                </div>
              </div>
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-[#FAF4E8] text-[#8C5E14] border border-[#EADBB8]">
                Critical: 3.0 mm/s
              </span>
            </div>
            <div className="h-56 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={sensorChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="vibGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#8C5E14" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#8C5E14" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#DCDCD4" />
                  <XAxis dataKey="time" tick={{ fontSize: 11, fill: "#6B6B66" }} />
                  <YAxis domain={["auto", "auto"]} tick={{ fontSize: 11, fill: "#6B6B66" }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#171717",
                      border: "1px solid #333",
                      borderRadius: "8px",
                      color: "#FAFAF5",
                      fontSize: "12px"
                    }}
                    formatter={(val: any) => [`${val} mm/s`, "Vibration"]}
                    labelFormatter={(label, items) => items[0]?.payload?.timestamp || label}
                  />
                  <ReferenceLine
                    y={3.0}
                    stroke="#8C5E14"
                    strokeDasharray="4 4"
                    label={{ value: "Fault Limit", fill: "#8C5E14", fontSize: 10, position: "top" }}
                  />
                  <Area
                    type="monotone"
                    dataKey="vibration"
                    stroke="#8C5E14"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#vibGradient)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* 3. Energy Consumption Over Time */}
        {(activeTab === "all" || activeTab === "energy") && (
          <div
            className={`border border-[#DCDCD4] rounded-xl p-4 bg-[#F5F5EE]/70 ${
              activeTab === "energy" ? "lg:col-span-2" : ""
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-2">
                <div className="p-1.5 bg-[#FAF4E8] text-[#8C5E14] rounded-md">
                  <Zap className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-[#171717]">
                    3. Energy Consumption Over Time
                  </h3>
                  <span className="text-[11px] text-[#6B6B66]">Unit: kWh (Nominal ~72 kWh)</span>
                </div>
              </div>
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-[#FAF4E8] text-[#8C5E14] border border-[#EADBB8]">
                Surge Limit: 88 kWh
              </span>
            </div>
            <div className="h-56 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={sensorChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#DCDCD4" />
                  <XAxis dataKey="time" tick={{ fontSize: 11, fill: "#6B6B66" }} />
                  <YAxis domain={["auto", "auto"]} tick={{ fontSize: 11, fill: "#6B6B66" }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#171717",
                      border: "1px solid #333",
                      borderRadius: "8px",
                      color: "#FAFAF5",
                      fontSize: "12px"
                    }}
                    formatter={(val: any) => [`${val} kWh`, "Energy Draw"]}
                    labelFormatter={(label, items) => items[0]?.payload?.timestamp || label}
                  />
                  <ReferenceLine
                    y={88}
                    stroke="#8C5E14"
                    strokeDasharray="4 4"
                    label={{ value: "Surge Alert", fill: "#8C5E14", fontSize: 10, position: "top" }}
                  />
                  <Line
                    type="monotone"
                    dataKey="energy"
                    stroke="#8C5E14"
                    strokeWidth={2}
                    dot={{ r: 2 }}
                    activeDot={{ r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* 4. Production Output Over Time */}
        {(activeTab === "all" || activeTab === "production") && (
          <div
            className={`border border-[#DCDCD4] rounded-xl p-4 bg-[#F5F5EE]/70 ${
              activeTab === "production" ? "lg:col-span-2" : ""
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-2">
                <div className="p-1.5 bg-[#EDF5EE] text-[#1E4D2B] rounded-md">
                  <TrendingUp className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-[#171717]">
                    4. Production Output Over Time
                  </h3>
                  <span className="text-[11px] text-[#6B6B66]">Unit: Units Produced vs Target (120 units)</span>
                </div>
              </div>
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-[#EDF5EE] text-[#1E4D2B] border border-[#C8E0CD]">
                Target: 120 Units
              </span>
            </div>
            <div className="h-56 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={prodChartData}
                  margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="prodGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#1E4D2B" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#1E4D2B" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#DCDCD4" />
                  <XAxis dataKey="time" tick={{ fontSize: 11, fill: "#6B6B66" }} />
                  <YAxis domain={["auto", "auto"]} tick={{ fontSize: 11, fill: "#6B6B66" }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#171717",
                      border: "1px solid #333",
                      borderRadius: "8px",
                      color: "#FAFAF5",
                      fontSize: "12px"
                    }}
                    formatter={(val: any) => [`${val} units`, "Production Output"]}
                    labelFormatter={(label, items) => items[0]?.payload?.timestamp || label}
                  />
                  <ReferenceLine
                    y={120}
                    stroke="#1E4D2B"
                    strokeDasharray="4 4"
                    label={{ value: "Quota Target", fill: "#1E4D2B", fontSize: 10, position: "top" }}
                  />
                  <Area
                    type="monotone"
                    dataKey="production"
                    stroke="#1E4D2B"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#prodGradient)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
