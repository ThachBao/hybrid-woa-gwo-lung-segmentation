"""
Quick test for history API
"""
import requests
import json

# Test /api/runs/list
print("Testing /api/runs/list...")
try:
    response = requests.get('http://localhost:5000/api/runs/list')
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Total runs: {data.get('total', 0)}")
        print(f"Runs: {len(data.get('runs', []))}")
        
        if data.get('runs'):
            print("\nFirst run:")
            print(json.dumps(data['runs'][0], indent=2))
    else:
        print(f"Error: {response.text}")
        
except requests.exceptions.ConnectionError:
    print("ERROR: Server is not running!")
    print("Please start server with: python -m src.ui.app")
except Exception as e:
    print(f"ERROR: {e}")
