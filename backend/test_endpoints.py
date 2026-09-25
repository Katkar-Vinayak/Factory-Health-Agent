import requests
import json

def test_api():
    base_url = "http://127.0.0.1:8000/api"
    
    endpoints = [
        "/health",
        "/machines",
        "/machines/M_001",
        "/machines/M_010/analysis",
        "/machines/M_010/maintenance",
        "/machines/M_010/production",
    ]
    
    for ep in endpoints:
        print(f"Testing {ep}...")
        try:
            resp = requests.get(base_url + ep)
            print(f"Status Code: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    print(f"Returned a list of {len(data)} items. First item:")
                    print(json.dumps(data[0] if len(data) > 0 else [], indent=2))
                else:
                    print(json.dumps(data, indent=2))
            else:
                print(resp.text)
        except Exception as e:
            print(f"Error: {e}")
        print("-" * 40)
        
test_api()
