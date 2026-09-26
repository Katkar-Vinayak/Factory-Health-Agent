"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Header } from "../../../components/Header";
import { RiskBadge } from "../../../components/RiskBadge";
import { SensorCard } from "../../../components/SensorCard";
import { SensorChart } from "../../../components/SensorChart";
import { AIAnalysis } from "../../../components/AIAnalysis";
import {
  Machine,
  SensorData,
  MachineAnalysis,
  MaintenanceRecord,
  ProductionRecord,
  NotificationItem
} from "../../../types";
import {
  getMachine,
  getMachineAnalysis,
  getSensorHistory,
  getMaintenanceHistory,
  getProductionHistory,
  getNotifications
} from "../../../lib/api";
import { ApprovalModal } from "../../../components/ApprovalModal";
import { authService } from "../../../lib/auth";
import {
  ArrowLeft,
  Cpu,
  Clock,
  Zap,
  Gauge,
  Thermometer,
  Activity,
  Layers,
  Factory,
  Wrench,
  Loader2,
  AlertTriangle,
  ServerCrash,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2
} from "lucide-react";

export default function MachineDetailsPage() {
  const params = useParams();
  const machineId = (params?.machine_id as string) || "";
  const router = useRouter();

  const [machine, setMachine] = useState<Machine | null>(null);
  const [latestSensor, setLatestSensor] = useState<SensorData | null>(null);
  const [analysis, setAnalysis] = useState<MachineAnalysis["analysis"] | null>(null);
  const [sensorHistory, setSensorHistory] = useState<SensorData[]>([]);
  const [maintenanceHistory, setMaintenanceHistory] = useState<MaintenanceRecord[]>([]);
  const [productionHistory, setProductionHistory] = useState<ProductionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [machineNotification, setMachineNotification] = useState<NotificationItem | null>(null);
  const [isApprovalOpen, setIsApprovalOpen] = useState(false);

  const fetchMachineNotification = async () => {
    try {
      const notifRes = await getNotifications({ machine_id: machineId });
      if (notifRes.notifications && notifRes.notifications.length > 0) {
        setMachineNotification(notifRes.notifications[0]);
      } else {
        setMachineNotification(null);
      }
    } catch {
      // non-critical
    }
  };

  useEffect(() => {
    if (!machineId) return;

    const loadData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [machineRes, analysisRes, sensorRes, maintRes, prodRes] = await Promise.all([
          getMachine(machineId),
          getMachineAnalysis(machineId).catch(() => null),
          getSensorHistory(machineId, 25).catch(() => []),
          getMaintenanceHistory(machineId).catch(() => []),
          getProductionHistory(machineId).catch(() => [])
        ]);

        setMachine(machineRes.metadata);
        setLatestSensor(machineRes.latest_sensor);
        if (analysisRes) {
          setAnalysis(analysisRes.analysis);
        }
        setSensorHistory(sensorRes);
        setMaintenanceHistory(maintRes);
        setProductionHistory(prodRes);

        await fetchMachineNotification();
      } catch (err: unknown) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("Failed to load machine telemetry data.");
        }
      } finally {
        setLoading(false);
      }
    };

    let isMounted = true;

    authService
      .getCurrentUser()
      .then((user) => {
        if (!isMounted) return;
        if (!user) {
          if (typeof document !== "undefined") {
            document.cookie = "access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
          }
          setLoading(false);
          router.replace("/login");
          return;
        }
        loadData();
      })
      .catch((err) => {
        if (!isMounted) return;
        setLoading(false);
        setError(err instanceof Error ? err.message : "Authentication session check failed.");
      });

    return () => {
      isMounted = false;
    };
  }, [machineId, router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F5F5EE] flex flex-col">
        <Header />
        <div className="flex-1 flex flex-col items-center justify-center p-8">
          <Loader2 className="w-8 h-8 animate-spin text-[#171717] mb-3" />
          <h2 className="text-base font-semibold text-[#171717]">Loading machine details...</h2>
          <p className="text-xs text-[#6B6B66] mt-1">
            Retrieving machine telemetry, maintenance records, and sensor history
          </p>
        </div>
      </div>
    );
  }

  if (error || !machine) {
    return (
      <div className="min-h-screen bg-[#F5F5EE] flex flex-col">
        <Header />
        <div className="flex-1 max-w-3xl mx-auto px-4 py-16 text-center">
          <div className="bg-[#FDF0EE] border border-[#DE9E98] rounded-xl p-8 text-[#9C382E]">
            <ServerCrash className="w-10 h-10 text-[#9C382E] mx-auto mb-3" />
            <h2 className="text-lg font-bold">Unable to Load Machine {machineId}</h2>
            <p className="text-xs sm:text-sm text-[#9C382E] mt-2">{error || "Machine not found."}</p>
            <div className="mt-6 flex justify-center space-x-3">
              <Link
                href="/"
                className="px-4 py-2 bg-[#171717] text-white rounded-md text-xs font-semibold hover:bg-[#262626] transition shadow-xs"
              >
                Back to Dashboard
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Derive risk level
  const hasAnalysis = Boolean(analysis);
  const prob = analysis?.failure_probability ?? 0.0;
  const isAnomaly = analysis?.anomaly ?? false;
  let riskLevel: "LOW" | "MEDIUM" | "HIGH" | "UNKNOWN" = "UNKNOWN";
  if (hasAnalysis) {
    if (isAnomaly || prob > 0.5) {
      riskLevel = "HIGH";
    } else if (prob > 0.3) {
      riskLevel = "MEDIUM";
    } else {
      riskLevel = "LOW";
    }
  }

  // Sensor status calculations
  const temp = latestSensor?.temperature_c ?? 46;
  const tempStatus = temp > 65 ? "critical" : temp > 55 ? "warning" : "normal";

  const vib = latestSensor?.vibration_mm_s ?? 1.8;
  const vibStatus = vib > 3.0 ? "critical" : vib > 2.5 ? "warning" : "normal";

  const press = latestSensor?.pressure_bar ?? 120;
  const pressStatus = press < 100 ? "critical" : press < 110 ? "warning" : "normal";

  const energy = latestSensor?.energy_consumption_kwh ?? 72;
  const energyStatus = energy > 88 ? "critical" : energy > 80 ? "warning" : "normal";

  const loadVal = latestSensor?.load_percent ?? 80;
  const loadStatus = loadVal > 90 ? "warning" : "normal";

  const prodVal = latestSensor?.production_output_units ?? 110;
  const prodStatus = prodVal < 90 ? "critical" : prodVal < 105 ? "warning" : "normal";

  return (
    <div className="min-h-screen bg-[#F5F5EE] flex flex-col">
      <Header />

      <main className="flex-1 max-w-[1500px] w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Navigation Breadcrumb */}
        <div>
          <Link
            href="/"
            className="inline-flex items-center text-xs font-semibold text-[#6B6B66] hover:text-[#171717] transition"
          >
            <ArrowLeft className="w-3.5 h-3.5 mr-1" />
            Back to Factory Dashboard
          </Link>
        </div>

        {/* Machine Identity Header Card */}
        <div className="bg-[#FAFAF5] rounded-xl border border-[#DCDCD4] p-6 sm:p-8 shadow-xs">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            <div>
              <div className="flex items-center space-x-2.5">
                <span className="font-mono text-xs font-bold px-2.5 py-1 rounded bg-[#171717] text-white">
                  {machine.machine_id}
                </span>
                <span className="text-xs px-2.5 py-0.5 rounded-full font-medium bg-[#F0F0EA] text-[#171717] border border-[#DCDCD4]">
                  {machine.criticality_level} Criticality
                </span>
                <span className="text-xs text-[#8C8C85]">
                  Installed: {machine.installation_date}
                </span>
              </div>
              <h2 className="text-2xl sm:text-3xl font-extrabold text-[#171717] tracking-tight mt-2">
                {machine.machine_name}
              </h2>
              <p className="text-xs sm:text-sm text-[#6B6B66] mt-1">
                Equipment Category: <strong className="text-[#171717] font-semibold">{machine.machine_type}</strong> • Rated Power:{" "}
                <strong className="text-[#171717] font-semibold">{machine.rated_power_kw} kW</strong>
              </p>
            </div>

            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 border-t lg:border-t-0 pt-4 lg:pt-0 border-[#DCDCD4]">
              <div className="text-right">
                <p className="text-xs font-medium text-[#6B6B66]">Current Health Assessment</p>
                <div className="mt-1 flex items-center justify-end space-x-2">
                  <RiskBadge riskLevel={riskLevel} size="lg" />
                </div>
              </div>

              <div className="bg-[#F5F5EE] border border-[#DCDCD4] rounded-xl p-3 text-center min-w-32">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-[#6B6B66]">
                  Failure Prob
                </p>
                {hasAnalysis ? (
                  <p
                    className={`text-xl font-bold font-mono mt-0.5 ${
                      prob > 0.5 ? "text-[#9C382E]" : "text-[#2A6E3B]"
                    }`}
                  >
                    {(prob * 100).toFixed(0)}%
                  </p>
                ) : (
                  <p className="text-xs font-medium text-[#6B6B66] mt-1">
                    Awaiting data
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Quick Info Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6 pt-6 border-t border-[#DCDCD4] text-xs">
            <div>
              <span className="text-[#6B6B66]">Operating Hours</span>
              <p className="font-semibold text-[#171717] font-mono text-sm mt-0.5">
                {machine.operating_hours.toLocaleString()} hrs
              </p>
            </div>
            <div>
              <span className="text-[#6B6B66]">Machine Age</span>
              <p className="font-semibold text-[#171717] font-mono text-sm mt-0.5">
                {machine.machine_age_years} years
              </p>
            </div>
            <div>
              <span className="text-[#6B6B66]">Past Maintenance Events</span>
              <p className="font-semibold text-[#171717] font-mono text-sm mt-0.5">
                {machine.maintenance_count} services
              </p>
            </div>
            <div>
              <span className="text-[#6B6B66]">Latest Telemetry Timestamp</span>
              <p className="font-mono text-[#171717] text-xs mt-0.5 truncate" title={latestSensor?.timestamp}>
                {latestSensor?.timestamp || "N/A"}
              </p>
            </div>
          </div>
        </div>

        {/* Machine-Specific Maintenance Approval State Banner */}
        {machineNotification && (machineNotification.status || "").toUpperCase() === "PENDING" && (
          <div className="bg-[#FAF4E8] border border-[#E8DFC8] rounded-xl p-5 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4 animate-fadeIn">
            <div className="flex items-start space-x-3.5">
              <div className="p-2.5 bg-[#8B6E28] text-white rounded-lg mt-0.5 shrink-0 shadow-xs">
                <ShieldAlert className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-[#5A4515]">
                    Critical Maintenance Alert — Awaiting Operator Approval
                  </span>
                  <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-[#EDE3CF] text-[#5A4515] font-semibold border border-[#D9CAAA]">
                    {machineNotification.notification_id}
                  </span>
                </div>
                <p className="text-xs font-bold text-[#171717] mt-1">
                  {machineNotification.title || "Critical Component Condition"} • {machineNotification.component} ({machineNotification.root_cause})
                </p>
                <p className="text-xs text-[#6B6B66] mt-0.5">
                  Failure Probability: {(Number(machineNotification.failure_probability) * 100).toFixed(0)}% • Prescribed actions awaiting operator sign-off
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={() => setIsApprovalOpen(true)}
              className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg font-semibold bg-[#8B6E28] hover:bg-[#735A1E] text-white text-xs shadow-xs transition cursor-pointer shrink-0 self-end sm:self-center"
            >
              <ShieldCheck className="w-4 h-4" />
              <span>REVIEW ACTION</span>
            </button>
          </div>
        )}

        {machineNotification && (machineNotification.status || "").toUpperCase() === "VERIFICATION_PENDING" && (
          <div className="bg-[#FAFAF5] border border-[#DCDCD4] rounded-xl p-5 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4 animate-fadeIn">
            <div className="flex items-start space-x-3.5">
              <div className="p-2.5 bg-[#171717] text-white rounded-lg shrink-0">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-[#171717]">
                    Maintenance Action: Verification Pending
                  </span>
                  <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-[#EAEAE0] text-[#171717] font-semibold border border-[#DCDCD4]">
                    {machineNotification.notification_id}
                  </span>
                </div>
                <p className="text-xs text-[#6B6B66] mt-1">
                  Software actions have been recorded. Physical machine recovery requires verified sensor telemetry.
                </p>
              </div>
            </div>

            <span className="text-xs font-medium px-3 py-1 rounded-full bg-[#EAEAE0] text-[#171717] border border-[#DCDCD4] shrink-0 self-end sm:self-center">
              Pending New Telemetry
            </span>
          </div>
        )}

        {/* 6 Sensor Cards Grid */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-bold text-[#171717]">
                Latest Sensor Telemetry Snapshot
              </h2>
              <p className="text-xs text-[#6B6B66]">
                Physical sensor measurements vs calibrated manufacturing thresholds
              </p>
            </div>
          </div>

          {!latestSensor ? (
            <div className="bg-[#FAFAF5] border border-[#DCDCD4] rounded-xl p-8 text-center text-[#6B6B66]">
              <Clock className="w-8 h-8 text-[#8C8C85] mx-auto mb-2" />
              <p className="text-sm font-semibold text-[#171717]">Awaiting Sensor Telemetry</p>
              <p className="text-xs text-[#6B6B66] mt-1 max-w-md mx-auto">
                No telemetry records found for this unit yet. Equipment is registered in the factory catalog awaiting live telemetry ingestion.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
              <SensorCard
                label="Temperature"
                value={latestSensor?.temperature_c}
                unit="°C"
                baseline="40 - 55°C"
                icon={Thermometer}
                status={tempStatus}
              />
              <SensorCard
                label="Vibration"
                value={latestSensor?.vibration_mm_s}
                unit="mm/s"
                baseline="< 2.5 mm/s"
                icon={Activity}
                status={vibStatus}
              />
              <SensorCard
                label="Pressure"
                value={latestSensor?.pressure_bar}
                unit="bar"
                baseline="115 - 125 bar"
                icon={Gauge}
                status={pressStatus}
              />
              <SensorCard
                label="Energy Consumption"
                value={latestSensor?.energy_consumption_kwh}
                unit="kWh"
                baseline="60 - 78 kWh"
                icon={Zap}
                status={energyStatus}
              />
              <SensorCard
                label="Load Factor"
                value={latestSensor?.load_percent}
                unit="%"
                baseline="75 - 85%"
                icon={Layers}
                status={loadStatus}
              />
              <SensorCard
                label="Production Output"
                value={latestSensor?.production_output_units}
                unit="units"
                baseline="110 - 120 units"
                icon={Factory}
                status={prodStatus}
              />
            </div>
          )}
        </div>

        {/* AI Factory Investigation Section (Hero / Focal Point) */}
        <AIAnalysis
          machineId={machine.machine_id}
          defaultTimestamp={latestSensor?.timestamp}
        />

        {/* Recharts Historical Telemetry */}
        <SensorChart
          sensorHistory={sensorHistory}
          productionHistory={productionHistory}
        />

        {/* Historical Maintenance Logs Table */}
        <div className="bg-[#FAFAF5] rounded-xl border border-[#DCDCD4] p-6 shadow-xs">
          <div className="flex items-center justify-between pb-4 mb-4 border-b border-[#DCDCD4]">
            <div>
              <h2 className="text-base font-bold text-[#171717] flex items-center">
                <Wrench className="w-5 h-5 mr-2 text-[#6B6B66]" />
                Historical Maintenance Records ({maintenanceHistory.length})
              </h2>
              <p className="text-xs text-[#6B6B66] mt-0.5">
                Past corrective repairs, part replacements, and preventive service logs
              </p>
            </div>
          </div>

          {maintenanceHistory.length === 0 ? (
            <p className="text-xs text-[#6B6B66] py-4 text-center">
              No historical maintenance records logged for this machine.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-[#DCDCD4] text-[#6B6B66] uppercase font-mono text-[11px] tracking-wider">
                    <th className="py-2.5 px-3">Date</th>
                    <th className="py-2.5 px-3">Type</th>
                    <th className="py-2.5 px-3">Component</th>
                    <th className="py-2.5 px-3">Description</th>
                    <th className="py-2.5 px-3 text-right">Downtime</th>
                    <th className="py-2.5 px-3 text-right">Cost</th>
                    <th className="py-2.5 px-3">Technician Notes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#EAEAE2]">
                  {maintenanceHistory.map((maint, idx) => (
                    <tr key={idx} className="hover:bg-[#F5F5EE]/70 transition">
                      <td className="py-2.5 px-3 font-mono text-[#171717] whitespace-nowrap">
                        {maint.maintenance_date}
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[11px] font-medium border ${
                            maint.maintenance_type === "Corrective"
                              ? "bg-[#FDF0EE] text-[#9C382E] border-[#DE9E98]"
                              : "bg-[#EDF5EE] text-[#2A6E3B] border-[#94C09A]"
                          }`}
                        >
                          {maint.maintenance_type}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 font-medium text-[#171717]">
                        {maint.component}
                      </td>
                      <td className="py-2.5 px-3 text-[#6B6B66] max-w-xs truncate" title={maint.description}>
                        {maint.description}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono font-medium text-[#171717]">
                        {maint.downtime_hours} hrs
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono font-medium text-[#171717]">
                        ${maint.maintenance_cost.toLocaleString()}
                      </td>
                      <td className="py-2.5 px-3 text-[#6B6B66] max-w-xs truncate" title={maint.technician_notes}>
                        {maint.technician_notes}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Human Approval Modal for Machine Details */}
        <ApprovalModal
          isOpen={isApprovalOpen}
          mode="accept"
          notification={machineNotification}
          onClose={() => setIsApprovalOpen(false)}
          onSuccess={() => {
            fetchMachineNotification();
          }}
        />
      </main>
    </div>
  );
}
