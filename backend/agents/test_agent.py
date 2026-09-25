import os
import json
import pandas as pd
import sys

# Ensure UTF-8 output on Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.agent_service import run_factory_analysis

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
df = pd.read_csv(os.path.join(DATA_DIR, 'sensor_data.csv'), keep_default_na=False)

def format_output(scenario_name: str, result: dict):
    print("=" * 60)
    print(f" {scenario_name}")
    print("=" * 60)
    print(f"Machine ID:           {result.get('machine_id')}")
    print(f"Timestamp:            {result.get('timestamp')}")
    print(f"Risk Level:           {result.get('risk_level')}")
    print(f"Failure Probability:  {result.get('failure_probability'):.2f}")
    print(f"Anomaly Status:       {result.get('anomaly')}")
    print(f"Probable Root Cause:  {result.get('root_cause')}")
    print(f"Confidence:           {result.get('confidence')}")
    
    candidate_scores = result.get('candidate_scores')
    if candidate_scores:
        print(f"Candidate Scores:     {json.dumps(candidate_scores)}")
    
    print("\nEvidence:")
    evidence = result.get('evidence', [])
    if evidence:
        for idx, pt in enumerate(evidence, 1):
            print(f"  {idx}. {pt}")
    else:
        print("  None (Nominal operation)")
        
    impact = result.get('impact', {})
    print("\nOperational Impact:")
    print(f"  Production Impact:  {impact.get('production_impact', 'N/A')}")
    print(f"  Energy Impact:      {impact.get('energy_impact', 'N/A')}")
    print(f"  Downtime Risk:      {impact.get('downtime_risk', 'N/A')}")
    print(f"  Urgency:            {impact.get('urgency', 'N/A')}")
    
    print("\nRecommended Actions:")
    recommendations = result.get('recommendations', [])
    if recommendations:
        for rec in recommendations:
            print(f"  Primary Action:  {rec.get('action')}")
            print(f"  Priority:        {rec.get('priority')}")
            print(f"  Cost Impact:     {rec.get('estimated_cost_impact')}")
            print(f"  Details:         {rec.get('details')}")
            specific_actions = rec.get('recommended_actions', [])
            if specific_actions:
                print("  Action Steps:")
                for a in specific_actions:
                    print(f"    - {a}")
    else:
        print("  None (Continuous monitoring)")
        
    print("\nAgent Trace:")
    for step in result.get('agent_trace', []):
        print(f"  -> {step}")
        
    print("\nFinal Report Summary:")
    print(f"  {result.get('final_report')}")
    print("=" * 60 + "\n")


# 1. Normal Machine Selection (anomaly == 0 and failure_within_24h == 0)
normal_row = df[(df['anomaly'] == 0) & (df['failure_within_24h'] == 0)].iloc[0]
normal_machine = normal_row['machine_id']
normal_time = str(normal_row['timestamp'])

print("\nExecuting Regression Test on Normal Machine...")
result_normal = run_factory_analysis(normal_machine, normal_time)
format_output("SCENARIO 1: NORMAL MACHINE REGRESSION TEST", result_normal)

# 2. Pre-Failure Machine Selection (anomaly == 1 and failure_within_24h == 1)
# Note: Ground-truth labels are ONLY used here to locate an actual pre-failure record for testing.
# They are NOT passed into the workflow.
pre_failure_cases = [
    # M_003 at 2023-01-19 22:00:00 (Bearing Degradation pre-failure)
    ("M_003", "2023-01-19 22:00:00", "SCENARIO 2: PRE-FAILURE MACHINE TEST (M_003)"),
    # M_001 at 2023-01-12 02:00:00 (Motor Overheating pre-failure)
    ("M_001", "2023-01-12 02:00:00", "SCENARIO 3: PRE-FAILURE MACHINE TEST (M_001)")
]

for m_id, t_stamp, label in pre_failure_cases:
    print(f"Executing Pre-Failure Test on Machine {m_id} at {t_stamp}...")
    res = run_factory_analysis(m_id, t_stamp)
    format_output(label, res)
