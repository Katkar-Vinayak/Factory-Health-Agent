"use client";

import React, { useState } from "react";
import { NewMachineInput, AddMachineResponse } from "../types";
import { addMachine } from "../lib/api";

interface AddMachineModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (newMachineId: string) => void;
}

const MACHINE_TYPES = [
  "CNC Lathe",
  "Milling Machine",
  "Industrial Press",
  "Welding Robot",
  "Packaging Line"
];

const STEPS = [
  "Registering machine in authoritative catalog...",
  "Generating telemetry & operational history...",
  "Retraining ML anomaly & failure models...",
  "Updating factory dashboard live..."
];

export default function AddMachineModal({
  isOpen,
  onClose,
  onSuccess
}: AddMachineModalProps) {
  const [name, setName] = useState("");
  const [type, setType] = useState("CNC Lathe");
  const [age, setAge] = useState<number | "">(3);
  const [power, setPower] = useState<number | "">(100);
  const [installDate, setInstallDate] = useState(
    new Date().toISOString().split("T")[0]
  );
  const [opHours, setOpHours] = useState<number | "">(5000);
  const [maintCount, setMaintCount] = useState<number | "">(5);
  const [criticality, setCriticality] = useState<"Low" | "Medium" | "High">("Medium");

  const [loading, setLoading] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMessage(null);

    // Client-side validations
    if (!name.trim()) {
      setError("Machine name is required.");
      return;
    }
    if (!type.trim()) {
      setError("Machine type is required.");
      return;
    }
    if (age === "" || Number(age) < 0) {
      setError("Machine age must be 0 or greater.");
      return;
    }
    if (power === "" || Number(power) <= 0) {
      setError("Rated power must be greater than 0 kW.");
      return;
    }
    if (!installDate) {
      setError("Installation date is required.");
      return;
    }
    if (opHours === "" || Number(opHours) < 0) {
      setError("Operating hours must be 0 or greater.");
      return;
    }
    if (maintCount === "" || Number(maintCount) < 0) {
      setError("Maintenance count must be 0 or greater.");
      return;
    }

    const payload: NewMachineInput = {
      machine_name: name.trim(),
      machine_type: type.trim(),
      machine_age_years: Number(age),
      rated_power_kw: Number(power),
      installation_date: installDate,
      operating_hours: Number(opHours),
      maintenance_count: Math.floor(Number(maintCount)),
      criticality_level: criticality
    };

    setLoading(true);
    setCurrentStepIndex(0);

    // Realistic UI progress simulation through the 4 backend phases
    const stepInterval = setInterval(() => {
      setCurrentStepIndex((prev) => (prev < STEPS.length - 1 ? prev + 1 : prev));
    }, 1200);

    try {
      const response: AddMachineResponse = await addMachine(payload);
      clearInterval(stepInterval);
      setCurrentStepIndex(3);
      setSuccessMessage(response.message || `Machine ${response.machine_id} added successfully.`);

      setTimeout(() => {
        setLoading(false);
        onSuccess(response.machine_id);
        onClose();
      }, 1000);
    } catch (err: unknown) {
      clearInterval(stepInterval);
      setLoading(false);
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("An unexpected error occurred while adding machine.");
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="relative w-full max-w-xl bg-[#FAFAF5] border border-[#DCDCD4] rounded-xl shadow-xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#DCDCD4] bg-[#FAFAF5]">
          <div>
            <h2 className="text-base sm:text-lg font-bold text-[#171717] tracking-tight flex items-center gap-2">
              <span className="flex h-2 w-2 rounded-full bg-[#171717]" />
              Add New Machine
            </h2>
            <p className="text-xs text-[#6B6B66] mt-0.5">
              Registers machine, generates realistic telemetry &amp; retrains ML models.
            </p>
          </div>
          <button
            onClick={onClose}
            disabled={loading}
            className="text-[#6B6B66] hover:text-[#171717] p-1 rounded hover:bg-[#EFEFE8] transition-colors disabled:opacity-50 cursor-pointer"
            aria-label="Close modal"
          >
            ✕
          </button>
        </div>

        {/* Content / Form */}
        <form onSubmit={handleSubmit} className="p-5 sm:p-6 space-y-4">
          {/* Machine ID notice badge */}
          <div className="flex items-center justify-between px-3.5 py-2 bg-[#F5F5EE] border border-[#DCDCD4] rounded-md text-xs">
            <span className="text-[#6B6B66] font-medium">Machine ID:</span>
            <span className="text-[#171717] font-mono font-medium bg-white px-2 py-0.5 rounded border border-[#DCDCD4]">
              Automatically assigned (Sequential M_xxx)
            </span>
          </div>

          {error && (
            <div className="p-3 bg-[#FDF0EE] border border-[#DE9E98] rounded-md text-xs text-[#9C382E]">
              {error}
            </div>
          )}

          {successMessage && (
            <div className="p-3 bg-[#EDF5EE] border border-[#94C09A] rounded-md text-xs text-[#1D4E29] flex items-center gap-2">
              <span className="text-[#2A6E3B]">✓</span> {successMessage}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {/* Machine Name */}
            <div>
              <label className="block text-xs font-semibold text-[#171717] mb-1">
                Machine Name *
              </label>
              <input
                type="text"
                required
                disabled={loading}
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. CNC Lathe 24"
                className="w-full px-3 py-1.5 bg-white border border-[#DCDCD4] rounded-md text-xs text-[#171717] placeholder-[#A8A89F] focus:outline-hidden focus:border-[#171717] transition-all disabled:opacity-50"
              />
            </div>

            {/* Machine Type */}
            <div>
              <label className="block text-xs font-semibold text-[#171717] mb-1">
                Machine Type *
              </label>
              <select
                disabled={loading}
                value={type}
                onChange={(e) => setType(e.target.value)}
                className="w-full px-3 py-1.5 bg-white border border-[#DCDCD4] rounded-md text-xs text-[#171717] focus:outline-hidden focus:border-[#171717] transition-all disabled:opacity-50"
              >
                {MACHINE_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>

            {/* Machine Age (Years) */}
            <div>
              <label className="block text-xs font-semibold text-[#171717] mb-1">
                Machine Age (Years) *
              </label>
              <input
                type="number"
                step="0.1"
                min="0"
                required
                disabled={loading}
                value={age}
                onChange={(e) => setAge(e.target.value === "" ? "" : Number(e.target.value))}
                className="w-full px-3 py-1.5 bg-white border border-[#DCDCD4] rounded-md text-xs text-[#171717] focus:outline-hidden focus:border-[#171717] transition-all disabled:opacity-50"
              />
            </div>

            {/* Rated Power (kW) */}
            <div>
              <label className="block text-xs font-semibold text-[#171717] mb-1">
                Rated Power (kW) *
              </label>
              <input
                type="number"
                step="1"
                min="1"
                required
                disabled={loading}
                value={power}
                onChange={(e) => setPower(e.target.value === "" ? "" : Number(e.target.value))}
                className="w-full px-3 py-1.5 bg-white border border-[#DCDCD4] rounded-md text-xs text-[#171717] focus:outline-hidden focus:border-[#171717] transition-all disabled:opacity-50"
              />
            </div>

            {/* Installation Date */}
            <div>
              <label className="block text-xs font-semibold text-[#171717] mb-1">
                Installation Date *
              </label>
              <input
                type="date"
                required
                disabled={loading}
                value={installDate}
                onChange={(e) => setInstallDate(e.target.value)}
                className="w-full px-3 py-1.5 bg-white border border-[#DCDCD4] rounded-md text-xs text-[#171717] focus:outline-hidden focus:border-[#171717] transition-all disabled:opacity-50"
              />
            </div>

            {/* Criticality Level */}
            <div>
              <label className="block text-xs font-semibold text-[#171717] mb-1">
                Criticality Level *
              </label>
              <select
                disabled={loading}
                value={criticality}
                onChange={(e) => setCriticality(e.target.value as "Low" | "Medium" | "High")}
                className="w-full px-3 py-1.5 bg-white border border-[#DCDCD4] rounded-md text-xs text-[#171717] focus:outline-hidden focus:border-[#171717] transition-all disabled:opacity-50"
              >
                <option value="Low">Low</option>
                <option value="Medium">Medium</option>
                <option value="High">High</option>
              </select>
            </div>

            {/* Operating Hours */}
            <div>
              <label className="block text-xs font-semibold text-[#171717] mb-1">
                Operating Hours *
              </label>
              <input
                type="number"
                min="0"
                required
                disabled={loading}
                value={opHours}
                onChange={(e) => setOpHours(e.target.value === "" ? "" : Number(e.target.value))}
                className="w-full px-3 py-1.5 bg-white border border-[#DCDCD4] rounded-md text-xs text-[#171717] focus:outline-hidden focus:border-[#171717] transition-all disabled:opacity-50"
              />
            </div>

            {/* Maintenance Count */}
            <div>
              <label className="block text-xs font-semibold text-[#171717] mb-1">
                Maintenance Count *
              </label>
              <input
                type="number"
                min="0"
                required
                disabled={loading}
                value={maintCount}
                onChange={(e) => setMaintCount(e.target.value === "" ? "" : Number(e.target.value))}
                className="w-full px-3 py-1.5 bg-white border border-[#DCDCD4] rounded-md text-xs text-[#171717] focus:outline-hidden focus:border-[#171717] transition-all disabled:opacity-50"
              />
            </div>
          </div>

          {/* Loading Progress State */}
          {loading && (
            <div className="mt-3.5 p-3 bg-[#F5F5EE] border border-[#DCDCD4] rounded-md">
              <div className="flex items-center gap-2.5">
                <div className="h-3.5 w-3.5 border-2 border-[#171717] border-t-transparent rounded-full animate-spin" />
                <span className="text-xs text-[#171717] font-medium">
                  {STEPS[currentStepIndex]}
                </span>
              </div>
              <div className="w-full bg-[#DCDCD4] h-1.5 rounded-full mt-2 overflow-hidden">
                <div
                  className="bg-[#171717] h-full rounded-full transition-all duration-700"
                  style={{ width: `${((currentStepIndex + 1) / STEPS.length) * 100}%` }}
                />
              </div>
            </div>
          )}

          {/* Footer Actions */}
          <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-[#DCDCD4]">
            <button
              type="button"
              disabled={loading}
              onClick={onClose}
              className="px-4 py-2 bg-white hover:bg-[#F5F5EE] border border-[#DCDCD4] text-[#4A4A45] text-xs font-medium rounded-md transition-colors disabled:opacity-50 cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2 bg-[#171717] hover:bg-[#262626] text-white text-xs font-semibold rounded-md shadow-xs transition-all disabled:opacity-50 flex items-center gap-2 cursor-pointer"
            >
              {loading ? (
                <>
                  <span className="h-3.5 w-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Processing...
                </>
              ) : (
                "+ Register Machine"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
