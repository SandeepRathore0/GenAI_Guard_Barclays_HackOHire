# File Analysis Sandbox

A secure system using Docker and Python FastAPI to analyze unknown files. It monitors file accesses, process executions, and network activities using `strace` and `tcpdump`.

## Prerequisites
- Python 3.8+
- Docker installed and running

## Setup Instructions

1. **Build the Sandbox Docker Image**
   ```bash
   docker build -t sandbox-image .
   ```

2. **Install Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the API Server**
   ```bash
   uvicorn main:app --reload
   ```
   The API will be available at `http://localhost:8000`.

## API Usage

The API provides a single `/analyze` POST endpoint.

### Example Request

```bash
# Create a test script
echo '#!/bin/bash' > test.sh
echo 'cat /etc/passwd > /dev/null' >> test.sh
echo 'ping -c 1 8.8.8.8 > /dev/null' >> test.sh
chmod +x test.sh

# Analyze the file (enable_network is optional, default false)
curl -X POST -F "file=@test.sh" -F "enable_network=true" http://localhost:8000/analyze
```

### Example Response
```json
{
  "files_accessed": [
    "/etc/passwd"
  ],
  "processes": [
    "/bin/cat",
    "/bin/ping"
  ],
  "network_calls": [
    "8.8.8.8:8"
  ],
  "risk_score": 8
}
```

## Security Limits Imposed
- **No privileges**: The container runs without the `--privileged` flag.
- **Resource Limits**: CPU is limited to 1 core, and memory is capped at 256MB.
- **Network Optional**: Network access is completely disabled (`network_mode="none"`) unless `enable_network=true` is passed.
- **Read-Only Input**: The uploaded file is mounted strictly as read-only.
- **Ephemeral Run**: Containers are instantly removed after the execution completes.
