"""
Local LLM Service for Factory Health & Response Agent
======================================================
Provides local open-source LLM explanations using Qwen models (Qwen/Qwen3-4B, Qwen/Qwen3-1.7B).
Uses Hugging Face Transformers, PyTorch, and Accelerate.
DOES NOT use OpenAI, Gemini, Anthropic, Ollama, or any paid/external API.

Architecture Role:
- The LLM is an INTERPRETATION and EXPLANATION layer only.
- It NEVER calculates or overrides failure probabilities, anomaly flags, sensor readings,
  deterministic RCA scores, or What-If simulation metrics.
- All numerical predictions remain strictly produced by the deterministic ML & RCA pipelines.
- Handles memory constraints gracefully: checks available RAM and GPU before loading.
  If resources are insufficient or if inference fails, seamlessly provides deterministic explanations.
- Filters out any hidden chain-of-thought (<think>...</think> tags).
"""

import os
import sys
import time
import re
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("factory_llm_service")

# Ensure huggingface cache doesn't fill restricted C: drive if E: is available
if os.path.exists("E:\\TKR"):
    default_hf_home = "E:\\TKR\\.cache\\huggingface"
    if "HF_HOME" not in os.environ:
        os.environ["HF_HOME"] = default_hf_home


def _get_system_memory() -> Dict[str, float]:
    """
    Retrieves system RAM metrics in GB using psutil or ctypes fallback.
    """
    try:
        import psutil
        mem = psutil.virtual_memory()
        return {
            "total_gb": round(mem.total / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2)
        }
    except Exception:
        try:
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ('dwLength', ctypes.c_ulong),
                    ('dwMemoryLoad', ctypes.c_ulong),
                    ('ullTotalPhys', ctypes.c_ulonglong),
                    ('ullAvailPhys', ctypes.c_ulonglong),
                    ('ullTotalPageFile', ctypes.c_ulonglong),
                    ('ullAvailPageFile', ctypes.c_ulonglong),
                    ('ullTotalVirtual', ctypes.c_ulonglong),
                    ('ullAvailVirtual', ctypes.c_ulonglong),
                    ('sullAvailExtendedVirtual', ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            return {
                "total_gb": round(stat.ullTotalPhys / (1024**3), 2),
                "available_gb": round(stat.ullAvailPhys / (1024**3), 2)
            }
        except Exception:
            return {"total_gb": 8.0, "available_gb": 4.0}


class LocalLLMService:
    """
    Singleton service managing local Qwen model loading, tokenizer reuse,
    conservative memory management, and deterministic explanation fallbacks.
    """
    _instance: Optional["LocalLLMService"] = None

    @classmethod
    def get_instance(cls) -> "LocalLLMService":
        if cls._instance is None:
            cls._instance = LocalLLMService()
        return cls._instance

    def __init__(self):
        self.primary_model: str = os.getenv("QWEN_MODEL_NAME", "Qwen/Qwen3-4B")
        self.fallback_model: str = os.getenv("QWEN_FALLBACK_MODEL", "Qwen/Qwen3-1.7B")
        self.enabled: bool = os.getenv("ENABLE_LOCAL_LLM", "true").lower() in ("true", "1", "yes")
        
        self.loaded: bool = False
        self.loaded_model: Optional[str] = None
        self.model = None
        self.tokenizer = None
        self.device: str = "cpu"
        self.last_latency_ms: int = 0
        self.status_message: str = ""
        self.hardware_info: Dict[str, Any] = {}
        
        # Check environment and attempt safe initialization
        self._initialize_service()

    def _initialize_service(self):
        """Inspects hardware resources and determines safe model loading parameters."""
        mem = _get_system_memory()
        self.hardware_info = {
            "total_ram_gb": mem["total_gb"],
            "available_ram_gb": mem["available_gb"],
            "cuda_available": False,
            "gpu_name": None,
            "vram_gb": 0.0
        }
        
        try:
            import torch
            if torch.cuda.is_available():
                self.hardware_info["cuda_available"] = True
                self.hardware_info["gpu_name"] = torch.cuda.get_device_name(0)
                self.hardware_info["vram_gb"] = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2)
                self.device = "cuda"
            else:
                self.device = "cpu"
        except Exception as e:
            logger.warning(f"PyTorch inspection warning: {e}")
            self.device = "cpu"

        if not self.enabled:
            self.loaded = False
            self.status_message = "Local LLM service disabled via configuration."
            return

        # RAM Safety Evaluation:
        # A 4B parameter model in float16 requires ~8 GB of memory. On CPU it requires ~10-12 GB RAM.
        # A 1.7B parameter model in float16 requires ~3.5 GB of memory. On CPU it requires ~4-5 GB RAM.
        # An 8 GB system or any system with < 4 GB available RAM cannot safely host these models
        # without OS paging freeze or OOM.
        avail_ram = self.hardware_info["available_ram_gb"]
        cuda_avail = self.hardware_info["cuda_available"]
        vram = self.hardware_info["vram_gb"]

        target_model = self.primary_model
        if cuda_avail and vram >= 6.0:
            target_model = self.primary_model
        elif avail_ram >= 9.0:
            target_model = self.primary_model
        elif avail_ram >= 4.0:
            target_model = self.fallback_model
        else:
            # Insufficient memory available to prevent crash
            self.loaded = False
            self.status_message = (
                f"Memory guard active: Available RAM ({avail_ram:.1f} GB) is below the 4.0 GB safe threshold "
                f"to load {self.primary_model} or {self.fallback_model} on CPU. Deterministic engine active."
            )
            return

        # Attempt to load target model if auto-download is enabled or model is cached
        # We test loading with explicit memory protection
        self._safe_load_model(target_model)

    def _safe_load_model(self, model_name: str):
        """Loads model and tokenizer with memory error containment."""
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForCausalLM

            logger.info(f"Checking/loading local model '{model_name}' on device '{self.device}'...")
            t0 = time.time()
            
            tokenizer = AutoTokenizer.from_pretrained(model_name, timeout=10)
            
            dtype = torch.float16 if self.device == "cuda" else torch.float32
            
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=dtype,
                low_cpu_mem_usage=True,
                device_map="auto" if self.device == "cuda" else None,
                timeout=10
            )
            if self.device == "cpu":
                model = model.to("cpu")
                
            model.eval()
            self.model = model
            self.tokenizer = tokenizer
            self.loaded = True
            self.loaded_model = model_name
            load_time = round(time.time() - t0, 2)
            self.status_message = f"Local model '{model_name}' successfully loaded into memory ({load_time}s on {self.device})."
            logger.info(self.status_message)
            
        except (torch.cuda.OutOfMemoryError if "torch" in sys.modules else Exception, MemoryError) as mem_err:
            self.loaded = False
            self.loaded_model = None
            self.model = None
            self.tokenizer = None
            self.status_message = f"Memory guard prevented crash while loading {model_name}: {str(mem_err)}. Deterministic engine active."
            logger.warning(self.status_message)
        except Exception as e:
            # Model download timeout or missing weights fallback
            self.loaded = False
            self.loaded_model = None
            self.model = None
            self.tokenizer = None
            self.status_message = f"Local model '{model_name}' not active ({str(e)}). Deterministic engine active."
            logger.info(self.status_message)

    def get_status(self) -> Dict[str, Any]:
        """Exposes detailed singleton status for API and frontend display."""
        return {
            "enabled": self.enabled,
            "provider": "local",
            "model": self.primary_model,
            "fallback_model": self.fallback_model,
            "loaded": self.loaded,
            "loaded_model": self.loaded_model if self.loaded else (self.primary_model if not self.status_message else None),
            "device": self.device,
            "latency_ms": self.last_latency_ms,
            "status_message": self.status_message or ("Model active" if self.loaded else "Deterministic engine active"),
            "hardware": self.hardware_info
        }

    @staticmethod
    def _clean_qwen_output(text: str) -> str:
        """
        Strips any hidden chain-of-thought reasoning tokens (<think>...</think>)
        to ensure no internal reasoning traces are exposed to operators.
        """
        if not text:
            return ""
        # Remove <think> ... </think> tags and contents
        cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        # Strip system / markdown wrapping
        cleaned = cleaned.replace("<|im_end|>", "").replace("<|im_start|>", "").strip()
        return cleaned

    def _run_local_inference(self, prompt: str, max_new_tokens: int = 250) -> Optional[str]:
        """Executes local inference with timing, memory protection, and chain-of-thought filtering."""
        if not self.loaded or not self.model or not self.tokenizer:
            return None

        try:
            import torch
            t0 = time.time()
            
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an industrial analysis explanation assistant. "
                        "The numerical analysis and root-cause diagnosis were already produced by a deterministic engineering system. "
                        "Do not recalculate, override, or invent analytical results. "
                        "Explain only the supplied evidence and conclusions. "
                        "Do not output hidden reasoning tags or chain-of-thought."
                    )
                },
                {"role": "user", "content": prompt}
            ]
            
            formatted_prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = self.tokenizer([formatted_prompt], return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=0.2,
                    do_sample=False,
                    pad_token_id=self.tokenizer.eos_token_id
                )
                
            input_len = inputs.input_ids.shape[1]
            generated_tokens = outputs[0][input_len:]
            raw_text = self.tokenizer.decode(generated_tokens, skip_special_tokens=True)
            
            self.last_latency_ms = int((time.time() - t0) * 1000)
            return self._clean_qwen_output(raw_text)
            
        except Exception as e:
            logger.warning(f"Local LLM inference error: {e}. Falling back to deterministic engine.")
            return None

    # =========================================================================
    # A. Investigation Explanation
    # =========================================================================
    def explain_investigation(
        self,
        machine_id: str,
        risk_level: str,
        failure_probability: float,
        anomaly: bool,
        abnormal_signals: List[str],
        trends: Dict[str, float],
        evidence: List[str]
    ) -> str:
        """
        Explains why the machine was flagged, summarizes evidence collected,
        and describes physical relationships between signals without inventing facts.
        """
        prompt = (
            f"Machine ID: {machine_id}\n"
            f"Risk Level: {risk_level}\n"
            f"Failure Probability: {failure_probability:.2f}\n"
            f"Anomaly Detected: {anomaly}\n"
            f"Abnormal Signals: {abnormal_signals}\n"
            f"Sensor Trends: {trends}\n"
            f"Evidence: {evidence}\n\n"
            "Explain in 2-3 concise sentences why the machine was flagged and describe the relationships "
            "between the observed signals. Do not invent extra facts."
        )

        llm_out = self._run_local_inference(prompt, max_new_tokens=150)
        if llm_out:
            return llm_out

        # High-Fidelity Deterministic Fallback
        vib_d = trends.get("vibration_change", 0.0)
        temp_d = trends.get("temperature_change", 0.0)
        energy_d = trends.get("energy_change", 0.0)
        
        if risk_level == "LOW":
            return (
                f"Machine {machine_id} was evaluated under nominal baseline parameters (Failure Probability: {failure_probability:.2f}). "
                f"No anomalous excursions or upward degradation trends were identified across sensor channels."
            )
            
        return (
            f"Machine {machine_id} was flagged as {risk_level} risk with a {failure_probability*100:.1f}% 24-hour failure probability "
            f"(Anomaly Status: {'Confirmed' if anomaly else 'Nominal'}). Telemetry indicates correlated signal degradation: "
            f"vibration delta of {vib_d:+.2f} mm/s, temperature drift of {temp_d:+.1f}°C, and energy variance of {energy_d:+.1f} kWh. "
            f"These coupled signals indicate progressive mechanical or thermal stress exceeding standard operating boundaries."
        )

    # =========================================================================
    # B. RCA Explanation
    # =========================================================================
    def explain_rca(
        self,
        machine_id: str,
        root_cause: str,
        confidence: float,
        candidate_scores: Dict[str, float],
        evidence: List[str],
        trends: Dict[str, float]
    ) -> Dict[str, str]:
        """
        Explains the deterministic RCA result, why the winning cause is supported,
        and why alternative causes received lower scores.
        NEVER overwrites root_cause, confidence, or candidate scores.
        """
        prompt = (
            f"Machine: {machine_id}\n"
            f"Diagnosed Root Cause: {root_cause} (Confidence: {confidence:.2f})\n"
            f"Candidate Scores: {candidate_scores}\n"
            f"Evidence: {evidence}\n"
            f"Trends: {trends}\n\n"
            "In 2 sentences, explain why the selected root cause is physically supported and why alternative "
            "causes scored lower based on the evidence. Respond in plain concise text."
        )

        llm_out = self._run_local_inference(prompt, max_new_tokens=180)
        if llm_out:
            return {
                "explanation": llm_out,
                "engine": f"local_qwen ({self.loaded_model})" if self.loaded else "deterministic"
            }

        # Deterministic Physics-Grounded Fallback
        sorted_candidates = sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)
        top_cause, top_score = sorted_candidates[0] if sorted_candidates else (root_cause, 0.0)
        runner_up = sorted_candidates[1] if len(sorted_candidates) > 1 else ("None", 0.0)
        
        explanation = (
            f"The deterministic RCA engine diagnosed '{root_cause}' with {confidence*100:.0f}% confidence "
            f"(Score: {top_score:.1f} pts) based on direct sensor signatures. "
            f"Alternative causes like '{runner_up[0]}' scored lower ({runner_up[1]:.1f} pts) because primary telemetry "
            f"exhibits characteristic subsystem-specific indicators rather than distributed mechanical/electrical faults."
        )
        return {
            "explanation": explanation,
            "engine": "deterministic"
        }

    # =========================================================================
    # C. Decision Explanation
    # =========================================================================
    def explain_decision(
        self,
        machine_id: str,
        root_cause: str,
        recommendation: Dict[str, Any],
        impact: Dict[str, Any]
    ) -> str:
        """
        Explains operational reasoning behind the deterministic recommendation,
        urgency, and expected benefit without altering the action plan.
        """
        action_name = recommendation.get("action", "Schedule Inspection")
        priority = recommendation.get("priority", "MEDIUM")
        urgency = impact.get("urgency", "MEDIUM")

        prompt = (
            f"Machine: {machine_id}\n"
            f"Root Cause: {root_cause}\n"
            f"Recommended Action: {action_name}\n"
            f"Priority: {priority}\n"
            f"Urgency: {urgency}\n\n"
            "In 2 concise sentences, explain the operational rationale for this recommendation and why prompt execution "
            "prevents downtime. Do not suggest different actions."
        )

        llm_out = self._run_local_inference(prompt, max_new_tokens=120)
        if llm_out:
            return llm_out

        # Deterministic Rationale Fallback
        return (
            f"Operational rationale: Executing '{action_name}' with {priority} priority directly addresses the "
            f"frictional and thermal degradation identified in the {root_cause.lower()} subsystem. Immediate action "
            f"stabilizes machine load, dampens ongoing wear trends, and mitigates the {urgency.lower()} urgency downtime exposure."
        )

    # =========================================================================
    # D. Final Report
    # =========================================================================
    def generate_final_report(self, state: Dict[str, Any]) -> str:
        """
        Synthesizes the entire structured analysis into a professional factory-health summary report.
        Clearly separates:
          - Observed Telemetry
          - Model Prediction
          - Deterministic RCA
          - Recommended Action
          - Operational Impact
        """
        machine_id = state.get("machine_id", "Unknown")
        timestamp = state.get("timestamp") or (state.get("sensor_data") or {}).get("timestamp", "Unknown")
        risk_level = state.get("risk_level", "UNKNOWN")
        ml_data = state.get("ml_analysis") or {}
        failure_prob = ml_data.get("failure_probability", 0.0)
        anomaly = ml_data.get("anomaly", False)
        
        root_cause_info = state.get("root_cause") or {}
        root_cause = root_cause_info.get("probable_root_cause", "None")
        confidence = root_cause_info.get("confidence", 0.0)
        candidate_scores = state.get("candidate_scores") or root_cause_info.get("candidate_scores") or {}
        
        evidence = state.get("evidence", [])
        impact = state.get("impact") or {}
        recommendation = state.get("recommendation") or {}
        action_title = recommendation.get("action", "Routine Monitoring")
        
        sensors = state.get("sensor_data") or {}
        vib = sensors.get("vibration_mm_s", 1.8)
        temp = sensors.get("temperature_c", 46.0)
        energy = sensors.get("energy_consumption_kwh", 72.0)
        press = sensors.get("pressure_bar", 120.0)

        prompt = (
            f"Create a concise 4-section executive factory health report for Machine {machine_id} at {timestamp}:\n"
            f"1. Telemetry: Vibration {vib} mm/s, Temp {temp}°C, Energy {energy} kWh, Pressure {press} bar\n"
            f"2. ML Assessment: {risk_level} Risk, Failure Probability {failure_prob:.2f}, Anomaly: {anomaly}\n"
            f"3. RCA: {root_cause} (Confidence: {confidence:.2f})\n"
            f"4. Action & Impact: {action_title} | Urgency: {impact.get('urgency', 'LOW')}\n\n"
            "Produce clean, professional markdown with no extra conversational text."
        )

        llm_out = self._run_local_inference(prompt, max_new_tokens=300)
        if llm_out:
            return llm_out

        # Deterministic Professional Report Fallback
        if risk_level == "LOW":
            return (
                f"### Executive Health Summary: Machine {machine_id}\n\n"
                f"**Observation Timestamp**: {timestamp}\n\n"
                f"- **Observed Data**: Vibration {vib:.2f} mm/s, Temperature {temp:.1f}°C, Energy {energy:.1f} kWh, Pressure {press:.1f} bar.\n"
                f"- **Model Prediction**: Evaluated as **LOW RISK** with a failure probability of {failure_prob:.2f}. No anomalies detected.\n"
                f"- **Deterministic RCA**: Telemetry parameters reside firmly within nominal design limits.\n"
                f"- **Operational Impact**: Standard production throughput maintained; zero downtime exposure.\n"
                f"- **Recommended Action**: Continue standard scheduled operational monitoring."
            )

        evidence_str = "\n".join([f"  - {e}" for e in evidence[:3]]) if evidence else "  - Subsystem telemetry variance detected."
        scores_str = ", ".join([f"{k}: {v:.1f} pts" for k, v in candidate_scores.items()]) if candidate_scores else "N/A"

        return (
            f"### Executive Health Assessment: Machine {machine_id}\n\n"
            f"**Observation Timestamp**: {timestamp}\n\n"
            f"#### 1. Observed Data & Telemetry Baseline\n"
            f"- **Telemetry Values**: Vibration: {vib:.2f} mm/s | Temperature: {temp:.1f}°C | Energy: {energy:.1f} kWh | Pressure: {press:.1f} bar\n"
            f"- **Observed Evidence**:\n{evidence_str}\n\n"
            f"#### 2. ML Prediction & Risk Assessment\n"
            f"- **Risk Classification**: **{risk_level} RISK**\n"
            f"- **24-Hour Failure Probability**: **{failure_prob*100:.1f}%** (Random Forest)\n"
            f"- **Isolation Forest Anomaly**: {'Outlier Anomaly Detected' if anomaly else 'Nominal Inlier'}\n\n"
            f"#### 3. Deterministic Root Cause Analysis\n"
            f"- **Diagnosed Root Cause**: **{root_cause}** (Confidence: {confidence*100:.0f}%)\n"
            f"- **Candidate Cause Scores**: {scores_str}\n\n"
            f"#### 4. Prescribed Action & Operational Impact\n"
            f"- **Recommended Action Plan**: **{action_title}**\n"
            f"- **Operational Impact**: Production: {impact.get('production_impact', 'Normal')} | Energy: {impact.get('energy_impact', 'Normal')}\n"
            f"- **Urgency**: {impact.get('urgency', 'MEDIUM')} priority intervention recommended."
        )

    # =========================================================================
    # E. What-If Simulator Explanation
    # =========================================================================
    def explain_what_if(self, sim: Dict[str, Any]) -> str:
        """
        Explains the already-calculated What-If scenario numbers.
        NEVER recalculates or modifies the simulation trajectory values.
        """
        machine_id = sim.get("machine_id", "Unknown")
        root_cause = sim.get("root_cause", "Mechanical Wear")
        int_res = sim.get("intervene_now", {})
        dn_res = sim.get("do_nothing", {})
        diff = sim.get("estimated_difference", {})
        
        dn_risk = dn_res.get("projected_risk_index", 100.0)
        int_risk = int_res.get("projected_risk_index", 20.0)
        prod_avoided = diff.get("production_loss_avoided", 0.0)
        energy_avoided = diff.get("energy_wastage_avoided", 0.0)
        dt_avoided = diff.get("downtime_exposure_avoided", 0.0)

        prompt = (
            f"Machine: {machine_id}\n"
            f"Root Cause: {root_cause}\n"
            f"Do Nothing: Risk Index {dn_risk}, Production Loss {dn_res.get('production_loss_units')} units, Downtime {dn_res.get('downtime_exposure_hours')} hrs\n"
            f"Intervene Now: Risk Index {int_risk}, Production Loss {int_res.get('production_loss_units')} units, Downtime {int_res.get('downtime_exposure_hours')} hrs\n"
            f"Avoided: {prod_avoided} units saved, {energy_avoided} kWh saved, {dt_avoided} hrs downtime avoided.\n\n"
            "Explain in 2 sentences why intervening now protects operations compared to doing nothing. "
            "Do not recalculate the numbers."
        )

        llm_out = self._run_local_inference(prompt, max_new_tokens=120)
        if llm_out:
            return llm_out

        # Deterministic Simulation Explanation Fallback
        return (
            f"Intervening now substantially reduces the projected 24-hour operational exposure because the modeled "
            f"corrective action dampens the degradation trend, maintaining a projected risk index of {int_risk:.1f} versus "
            f"{dn_risk:.1f} under unmitigated operation. Proactive intervention avoids an estimated {prod_avoided:.0f} units of "
            f"production loss, {energy_avoided:.1f} kWh in wasted energy, and {dt_avoided:.1f} hours of catastrophic downtime exposure."
        )


def get_llm_service() -> LocalLLMService:
    """Singleton accessor for LocalLLMService."""
    return LocalLLMService.get_instance()
