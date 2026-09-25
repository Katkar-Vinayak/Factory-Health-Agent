import sys
import os
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services import agent_service
from services import simulation_service
from services.llm_service import get_llm_service

def test_singleton_status():
    print("\n--- 1. Testing Singleton LLM Status ---")
    svc = get_llm_service()
    status = svc.get_status()
    print("LLM Status:", json.dumps(status, indent=2))
    assert status["provider"] == "local"
    assert status["model"] == "Qwen/Qwen3-4B"
    assert "hardware" in status
    print("PASS: Singleton status verified")

def test_healthy_machine():
    print("\n--- 2. Testing Healthy Machine (M_001 nominal) ---")
    res = agent_service.run_factory_analysis("M_001", "2023-01-01 00:00:00")
    print(f"Machine: {res['machine_id']}, Risk: {res['risk_level']}, Prob: {res['failure_probability']:.2f}")
    print("Final Report snippet:", res["final_report"][:150])
    assert res["risk_level"] == "LOW"
    assert res["final_report"] != ""
    assert res["llm_status"] is not None
    print("PASS: Healthy machine analysis verified")

def test_critical_machine_m003():
    print("\n--- 3. Testing Critical Machine M_003 (Bearing Degradation) ---")
    res = agent_service.run_factory_analysis("M_003", "2023-01-19 22:00:00")
    print(f"Machine: {res['machine_id']}, Risk: {res['risk_level']}, Prob: {res['failure_probability']:.2f}")
    print(f"Diagnosed Root Cause: {res['root_cause']} (Confidence: {res['confidence']})")
    print("Candidate Scores:", res["candidate_scores"])
    print("Evidence Points:", len(res["evidence"]))
    print("Investigation Explanation snippet:", str(res.get("investigation_explanation"))[:120])
    print("RCA Explanation snippet:", str(res.get("rca_explanation"))[:120])
    print("Decision Explanation snippet:", str(res.get("decision_explanation"))[:120])
    print("Final Report:\n", res["final_report"][:300])

    assert res["risk_level"] == "HIGH"
    assert res["root_cause"] == "Bearing Degradation"
    assert res["confidence"] > 0.5
    assert len(res["evidence"]) >= 3
    assert len(res["recommendations"]) > 0
    assert res["recommendations"][0]["action"] == "Schedule Bearing Inspection and Reduce Machine Load"
    print("PASS: M_003 Bearing Degradation verified with deterministic authority")

def test_critical_machine_m010():
    print("\n--- 4. Testing Machine M_010 ---")
    res = agent_service.run_factory_analysis("M_010")
    print(f"Machine: {res['machine_id']}, Risk: {res['risk_level']}, Prob: {res['failure_probability']:.2f}")
    print(f"Root Cause: {res['root_cause']}")
    assert res["risk_level"] in ("LOW", "MEDIUM", "HIGH")
    assert res["final_report"] != ""
    print("PASS: M_010 analysis verified")

def test_what_if_simulator():
    print("\n--- 5. Testing What-If Simulator with Explanation ---")
    sim = simulation_service.run_what_if_simulation("M_003", "2023-01-19 22:00:00")
    print(f"Machine: {sim['machine_id']}, Root Cause: {sim['root_cause']}")
    print(f"Do Nothing Risk: {sim['do_nothing']['projected_risk_index']}, Loss: {sim['do_nothing']['production_loss_units']}")
    print(f"Intervene Risk: {sim['intervene_now']['projected_risk_index']}, Loss: {sim['intervene_now']['production_loss_units']}")
    print("Avoided Production Loss:", sim["estimated_difference"]["production_loss_avoided"])
    print("Simulation Explanation:\n", sim.get("explanation"))

    assert "explanation" in sim
    assert sim["estimated_difference"]["production_loss_avoided"] > 0
    assert sim["do_nothing"]["projected_risk_index"] > sim["intervene_now"]["projected_risk_index"]
    print("PASS: What-If simulation verified")

def test_invalid_machine_id():
    print("\n--- 6. Testing Invalid Machine ID ---")
    from services import machine_service
    machine = machine_service.get_machine("M_999_INVALID")
    assert machine is None
    print("PASS: Invalid machine correctly rejected")

if __name__ == "__main__":
    test_singleton_status()
    test_healthy_machine()
    test_critical_machine_m003()
    test_critical_machine_m010()
    test_what_if_simulator()
    test_invalid_machine_id()
    print("\n==============================================")
    print("ALL QWEN INTEGRATION BACKEND TESTS PASSED 100%")
    print("==============================================")
