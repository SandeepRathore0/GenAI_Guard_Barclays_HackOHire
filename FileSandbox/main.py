import os
import shutil
import tempfile
import re
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from pydantic import BaseModel
import docker
import PyPDF2
from docx import Document
from bs4 import BeautifulSoup

app = FastAPI(title="File Analysis Sandbox API")
client = docker.from_env()

class SandboxResult(BaseModel):
    files_accessed: List[str]
    processes: List[str]
    network_calls: List[str]
    risk_score: int
    extracted_text: Optional[str] = None

DOCKER_IMAGE_NAME = "sandbox-image"

def extract_text_from_file(file_path: str, filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    text = ""
    try:
        if ext == ".pdf":
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
        elif ext == ".docx":
            doc = Document(file_path)
            for para in doc.paragraphs:
                text += para.text + "\n"
        elif ext in [".html", ".htm"]:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                soup = BeautifulSoup(f, "html.parser")
                text = soup.get_text(separator="\n")
    except Exception as e:
        print(f"Error parsing {filename}: {e}")
    
    # Limit text to 5000 characters to prevent overwhelming LLM
    return text[:5000].strip()

def parse_logs(output_dir: str) -> SandboxResult:
    trace_log_path = os.path.join(output_dir, "trace.log")
    network_log_path = os.path.join(output_dir, "network.txt")

    files_accessed = set()
    processes = set()
    network_calls = set()

    # Parse trace.log
    if os.path.exists(trace_log_path):
        with open(trace_log_path, 'r', errors='ignore') as f:
            for line in f:
                # Example execve: 123 execve("/bin/cat", ["cat", "/etc/passwd"], 0x7ffd...) = 0
                if "execve(" in line:
                    match = re.search(r'execve\("([^"]+)"', line)
                    if match:
                        processes.add(match.group(1))
                
                # Example open/openat: 123 openat(AT_FDCWD, "/etc/passwd", O_RDONLY) = 3
                if "open(" in line or "openat(" in line:
                    match = re.search(r'(?:open|openat)\([^,"]*"?([^"]+)"', line)
                    if match:
                        # Filter out common shared libraries and standard files to reduce noise
                        path = match.group(1)
                        if not path.startswith('/lib') and not path.startswith('/usr/lib') and path not in ['/dev/null', '/etc/ld.so.cache']:
                            files_accessed.add(path)

    # Parse network.txt
    if os.path.exists(network_log_path):
        with open(network_log_path, 'r', errors='ignore') as f:
            for line in f:
                # Example line: 12:34:56.789101 IP 10.0.0.2.12345 > 8.8.8.8.53: UDP, length 33
                # We extract the destination IP and port
                match = re.search(r'IP\s+(?:[\d\.]+)(?:\.\d+)?\s+>\s+([\d\.]+)(?:\.(\d+))?:', line)
                if match:
                    ip = match.group(1)
                    port = match.group(2)
                    if port:
                        network_calls.add(f"{ip}:{port}")
                    else:
                        network_calls.add(ip)

    # Compute a simple risk score
    risk_score = 0
    if network_calls:
        risk_score += 3
    
    # Sensitive file accesses
    sensitive_files = ['/etc/passwd', '/etc/shadow', '/root']
    for sf in sensitive_files:
        if any(sf in f for f in files_accessed):
            risk_score += 5
            break
            
    # Suspicious processes
    suspicious_procs = ['/bin/sh', '/bin/bash', '/usr/bin/wget', '/usr/bin/curl', '/usr/bin/nc', 'nc', 'curl', 'wget']
    for sp in suspicious_procs:
        if any(sp in p for p in processes):
            risk_score += 4
            break

    return SandboxResult(
        files_accessed=sorted(list(files_accessed)),
        processes=sorted(list(processes)),
        network_calls=sorted(list(network_calls)),
        risk_score=min(10, risk_score)
    )

@app.post("/analyze", response_model=SandboxResult)
async def analyze_file(file: UploadFile = File(...), enable_network: bool = Form(False)):
    # 1. Ensure docker image exists
    try:
        client.images.get(DOCKER_IMAGE_NAME)
    except docker.errors.ImageNotFound:
        raise HTTPException(status_code=500, detail=f"Docker image '{DOCKER_IMAGE_NAME}' not found. Please build it first.")

    # 2. Create temporary directories
    temp_dir = tempfile.mkdtemp(prefix="sandbox_")
    input_dir = os.path.join(temp_dir, "input")
    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    try:
        # 3. Save uploaded file
        target_path = os.path.join(input_dir, "target")
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Extract text if it's a known document type
        extracted_text = extract_text_from_file(target_path, file.filename)

        # 4. Run Docker Container
        volumes = {
            os.path.abspath(input_dir): {'bind': '/sandbox_in', 'mode': 'ro'},
            os.path.abspath(output_dir): {'bind': '/sandbox_out', 'mode': 'rw'}
        }

        try:
            client.containers.run(
                DOCKER_IMAGE_NAME,
                detach=False,
                remove=True, # Automatically remove container after execution
                network_mode="bridge" if enable_network else "none",
                privileged=False,
                mem_limit="256m",
                memswap_limit="256m",
                nano_cpus=1000000000, # 1 CPU core
                volumes=volumes,
                user="root", # Needed for tcpdump, but bounded by privileged=False
                environment={"TARGET_FILENAME": file.filename}
            )
        except docker.errors.ContainerError as e:
            # Container exited with non-zero code (e.g., timeout or script failure)
            # We still want to parse the logs!
            pass
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Docker execution failed: {str(e)}")

        # 5. Extract and parse logs
        result = parse_logs(output_dir)
        if extracted_text:
            result.extracted_text = extracted_text
        return result

    finally:
        # 6. Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
