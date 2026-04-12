import requests
import json

url = "http://localhost:8000/analyze"
file_path = "test.sh"

try:
    with open(file_path, "rb") as f:
        print(f"File '{file_path}' opened successfully.")
        files = {"file": f}
        data = {"enable_network": "true"}
        
        print(f"Sending request to {url}...")
        response = requests.post(url, files=files, data=data)
        
        print(f"\nStatus Code: {response.status_code}")
        print("Response JSON:")
        print(json.dumps(response.json(), indent=2))
except FileNotFoundError:
    print(f"Error: {file_path} not found. Please create it first.")
except requests.exceptions.ConnectionError:
    print(f"Error: Could not connect to {url}. Is the FastAPI server running?")
