"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Header } from "../components/Header";
import { SummaryCard } from "../components/SummaryCard";
import { MachineCard } from "../components/MachineCard";
import { MachineWithStatus } from "../types";
import { getMachines, getMachineAnalysis } from "../lib/api";
import AddMachineModal from "../components/AddMachineModal";
import { ActionHistoryTable } from "../components/ActionHistoryTable";
import { authService } from "../lib/auth";
import {
  Cpu,
  ShieldCheck,
  AlertTriangle,
  AlertOctagon,
  Search,
  Filter,
  RefreshCw,
  Loader2,
  ServerCrash,
  Plus,
  ChevronDown
} from "lucide-react";

export default function DashboardPage() {
  const router = useRouter();
  const [machines, setMachines] = useState<MachineWithStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [healthFilter, setHealthFilter] = useState<"ALL" | "HEALTHY" | "WARNING" | "CRITICAL">("ALL");
  const [criticalityFilter, setCriticalityFilter] = useState<"ALL" | "HIGH" | "MEDIUM" | "LOW">("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [displayCount, setDisplayCount] = useState<number>(10);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [actionTrigger, setActionTrigger] = useState(0);


  const loadDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const rawMachines = await getMachines();
      if (!Array.isArray(rawMachines)) {
        throw new Error("Invalid machine registry response received from server.");
      }

      // Fetch analyses for all machines in parallel to compute actual health counts
      const enriched = await Promise.all(
        rawMachines.map(async (m) => {
          try {
            const analysisData = await getMachineAnalysis(m.machine_id);
            const prob = analysisData?.analysis?.failure_probability ?? 0.0;
            const isAnomaly = Boolean(analysisData?.analysis?.anomaly);

            let riskLevel: "LOW" | "MEDIUM" | "HIGH" | "UNKNOWN" = "LOW";
            if (isAnomaly || prob > 0.5) {
              riskLevel = "HIGH";
            } else if (prob > 0.3) {
              riskLevel = "MEDIUM";
            }

            return {
              metadata: m,
              latest_sensor: analysisData?.sensors,
              analysis: {
                anomaly: isAnomaly,
                failure_probability: prob,
                risk_level: riskLevel
              }
            };
          } catch {
            return {
              metadata: m,
              latest_sensor: undefined,
              analysis: {
                anomaly: false,
                failure_probability: 0.0,
                risk_level: "UNKNOWN" as const
              }
            };
          }
        })
      );

      setMachines(enriched);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Failed to load factory machines from backend.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
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
        loadDashboardData();
      })
      .catch((err) => {
        if (!isMounted) return;
        setLoading(false);
        setError(err instanceof Error ? err.message : "Authentication session check failed.");
      });

    return () => {
      isMounted = false;
    };
  }, [router]);

  // Compute live counts derived strictly from actual backend analysis and metadata
  const totalCount = machines.length;
  const healthyCount = machines.filter(
    (m) => m.analysis?.risk_level === "LOW"
  ).length;
  const warningCount = machines.filter(
    (m) => m.analysis?.risk_level === "MEDIUM"
  ).length;
  const criticalCount = machines.filter(
    (m) => m.analysis?.risk_level === "HIGH"
  ).length;

  // Filter machines based on health status, criticality level, and search query
  const filteredMachines = machines.filter((m) => {
    // 1. Health Status filter (driven by summary cards)
    const risk = m.analysis?.risk_level || "UNKNOWN";
    if (healthFilter === "HEALTHY" && risk !== "LOW") return false;
    if (healthFilter === "WARNING" && risk !== "MEDIUM") return false;
    if (healthFilter === "CRITICAL" && risk !== "HIGH") return false;

    // 2. Criticality Level filter (driven by Criticality: All / High / Medium / Low buttons)
    const critLevel = (m.metadata.criticality_level || "").toUpperCase();
    if (criticalityFilter === "HIGH" && critLevel !== "HIGH") return false;
    if (criticalityFilter === "MEDIUM" && critLevel !== "MEDIUM") return false;
    if (criticalityFilter === "LOW" && critLevel !== "LOW") return false;

    // 3. Search query filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchId = m.metadata.machine_id.toLowerCase().includes(q);
      const matchName = m.metadata.machine_name.toLowerCase().includes(q);
      const matchType = m.metadata.machine_type.toLowerCase().includes(q);
      return matchId || matchName || matchType;
    }

    return true;
  });

  // Limit visible machines based on selected display count while keeping complete fleet data intact
  const visibleMachines = filteredMachines.slice(0, displayCount);

  return (
    <div className="min-h-screen bg-[#F5F5EE] flex flex-col">
      <Header
        onActionComplete={() => {
          setActionTrigger((prev) => prev + 1);
          loadDashboardData();
        }}
      />

      <main className="flex-1 max-w-[1500px] w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Editorial Hero Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 pb-5 border-b border-[#DCDCD4]">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xs font-bold uppercase tracking-wider text-[#6B6B66]">
                Plant Operations Overview
              </span>
              <span className="text-[#DCDCD4]">•</span>
              <span className="text-xs font-mono font-medium text-[#1E4D2B]">
                Telemetry Stream Active
              </span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold text-[#171717] tracking-tight mt-1">
              Factory Operations Overview
            </h1>
          </div>

          <div className="flex items-center gap-2.5 self-start sm:self-auto">
            <button
              onClick={() => setIsAddModalOpen(true)}
              className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-[#171717] hover:bg-[#262626] active:scale-98 text-white shadow-2xs transition cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add New Machine</span>
            </button>

            <button
              onClick={loadDashboardData}
              disabled={loading}
              className="inline-flex items-center space-x-2 px-3.5 py-2 rounded-lg text-xs font-semibold bg-[#FAFAF5] hover:bg-[#EFEFE8] border border-[#DCDCD4] text-[#171717] shadow-2xs transition disabled:opacity-50 cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-[#171717]" : "text-[#6B6B66]"}`} />
              <span>Refresh Telemetry</span>
            </button>
          </div>
        </div>

        {/* Dynamic Summary Cards Header */}
        <div className="mb-2.5 flex items-center justify-between">
          <p className="text-xs font-medium text-[#6B6B66] flex items-center">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#1E4D2B] mr-2" />
            Status computed from latest calibrated telemetry snapshot
          </p>
          <span className="text-[11px] text-[#8C8C85] hidden sm:inline">
            Select card to filter fleet by health status
          </span>
        </div>

        {/* Exactly 4 Symmetrical Summary Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <SummaryCard
            title="Total Machines"
            count={totalCount}
            subtitle="Active fleet monitored"
            icon={Cpu}
            variant="default"
            isActive={healthFilter === "ALL"}
            onClick={() => setHealthFilter("ALL")}
          />
          <SummaryCard
            title="Healthy"
            count={healthyCount}
            subtitle="Nominal operating state"
            icon={ShieldCheck}
            variant="healthy"
            isActive={healthFilter === "HEALTHY"}
            onClick={() => setHealthFilter((prev) => (prev === "HEALTHY" ? "ALL" : "HEALTHY"))}
          />
          <SummaryCard
            title="Warning"
            count={warningCount}
            subtitle="Elevated telemetry drift"
            icon={AlertTriangle}
            variant="warning"
            isActive={healthFilter === "WARNING"}
            onClick={() => setHealthFilter((prev) => (prev === "WARNING" ? "ALL" : "WARNING"))}
          />
          <SummaryCard
            title="Critical"
            count={criticalCount}
            subtitle="Pre-failure / High risk"
            icon={AlertOctagon}
            variant="critical"
            isActive={healthFilter === "CRITICAL"}
            onClick={() => setHealthFilter((prev) => (prev === "CRITICAL" ? "ALL" : "CRITICAL"))}
          />
        </div>

        {/* Machine Fleet Section Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3.5">
          <div className="flex items-center space-x-2">
            <h2 className="text-base sm:text-lg font-bold text-[#171717] tracking-tight">
              Factory Floor Machine Fleet
            </h2>
            <span className="text-xs text-[#8C8C85]">•</span>
            <span className="text-xs text-[#6B6B66] font-medium">
              {filteredMachines.length} {filteredMachines.length === 1 ? "machine" : "machines"} matching
            </span>
          </div>

          <div className="flex items-center space-x-1.5 text-xs self-start sm:self-auto">
            <label htmlFor="fleet-display-count" className="text-xs text-[#6B6B66] font-medium whitespace-nowrap">
              Show:
            </label>
            <div className="relative">
              <select
                id="fleet-display-count"
                aria-label="Machines to show"
                value={displayCount}
                onChange={(e) => setDisplayCount(Number(e.target.value))}
                className="appearance-none bg-white border border-[#DCDCD4] text-[#171717] text-xs font-semibold rounded-md pl-3 pr-7 py-1.5 shadow-2xs focus:outline-hidden focus:border-[#171717] cursor-pointer hover:bg-[#F5F5EE] transition"
              >
                {[10, 20, 30, 40, 50].map((num) => (
                  <option key={num} value={num}>
                    {num}
                  </option>
                ))}
              </select>
              <ChevronDown className="w-3.5 h-3.5 text-[#6B6B66] pointer-events-none absolute right-2 top-1/2 -translate-y-1/2" />
            </div>
          </div>
        </div>

        {/* Filter and Search Bar */}
        <div className="bg-[#FAFAF5] rounded-xl border border-[#DCDCD4] p-3.5 mb-6 shadow-2xs flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#8C8C85]" />
            <input
              type="text"
              placeholder="Search by Machine ID (e.g. M_001), name, or type..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 rounded-lg text-xs bg-[#F5F5EE] border border-[#DCDCD4] focus:outline-hidden focus:border-[#171717] focus:bg-white text-[#171717] placeholder:text-[#8C8C85] transition"
            />
          </div>

          <div className="flex items-center space-x-1.5 overflow-x-auto pb-1 md:pb-0 text-xs">
            <Filter className="w-3.5 h-3.5 text-[#8C8C85] mr-1 shrink-0" />
            <span className="text-xs font-semibold text-[#171717] mr-1 select-none">Criticality:</span>
            {(
              [
                { key: "ALL", label: "All" },
                { key: "HIGH", label: "High" },
                { key: "MEDIUM", label: "Medium" },
                { key: "LOW", label: "Low" },
              ] as const
            ).map(({ key, label }) => {
              const isActive = criticalityFilter === key;
              return (
                <button
                  key={key}
                  type="button"
                  id={`fleet-filter-${key.toLowerCase()}`}
                  onClick={() => setCriticalityFilter(key)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer whitespace-nowrap border ${
                    isActive
                      ? "bg-[#171717] text-white border-[#171717] shadow-2xs"
                      : "bg-[#FAFAF5] text-[#555550] border-[#DCDCD4] hover:bg-[#EFEFE8] hover:text-[#171717]"
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className="bg-[#FDF0EE] border border-[#F2C2BD] rounded-xl p-8 text-center text-[#9E2A2B] my-8">
            <ServerCrash className="w-10 h-10 mx-auto mb-3 text-[#9E2A2B]" />
            <h2 className="text-base font-bold">Unable to Connect to Industrial Backend</h2>
            <p className="text-xs text-[#9E2A2B]/80 mt-1 max-w-lg mx-auto">{error}</p>
            <button
              onClick={loadDashboardData}
              className="mt-4 px-4 py-2 bg-[#9E2A2B] hover:bg-[#852324] text-white text-xs font-semibold rounded-lg shadow-2xs transition"
            >
              Retry Connection
            </button>
          </div>
        )}

        {/* Loading State */}
        {loading && !error && (
          <div className="py-20 text-center">
            <Loader2 className="w-8 h-8 animate-spin text-[#171717] mx-auto mb-3" />
            <p className="text-sm font-semibold text-[#171717]">Loading machine data...</p>
            <p className="text-xs text-[#6B6B66] mt-1">
              Fetching machine registry, current sensors, and ML anomaly predictions
            </p>
          </div>
        )}

        {/* Machine Grid */}
        {!loading && !error && (
          <>
            {filteredMachines.length === 0 ? (
              <div className="bg-[#FAFAF5] border border-[#DCDCD4] rounded-xl p-12 text-center text-[#6B6B66]">
                <p className="text-sm font-semibold text-[#171717]">
                  {criticalityFilter !== "ALL"
                    ? `No ${criticalityFilter.toLowerCase()}-criticality machines found.`
                    : healthFilter !== "ALL"
                    ? `No ${healthFilter.toLowerCase()}-status machines found.`
                    : "No machines found."}
                </p>
                <p className="text-xs mt-1">Try adjusting your search query, criticality filter, or health status selection.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
                {visibleMachines.map((machine) => (
                  <MachineCard key={machine.metadata.machine_id} machine={machine} />
                ))}
              </div>
            )}

            {/* Action History Audit Trail Section */}
            <div className="mt-8">
              <ActionHistoryTable refreshTrigger={actionTrigger} />
            </div>
          </>
        )}

        {/* Add Machine Modal */}
        <AddMachineModal
          isOpen={isAddModalOpen}
          onClose={() => setIsAddModalOpen(false)}
          onSuccess={() => {
            loadDashboardData();
          }}
        />
      </main>
    </div>
  );
}
