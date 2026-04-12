#!/bin/bash
# Orchestration script to run inside the Docker sandbox

if [ ! -f "/sandbox_in/target" ]; then
    echo "Error: Target file /sandbox_in/target not found"
    exit 1
fi

# Copy the target file to a writable location to make it executable
cp /sandbox_in/target /tmp/target_file
chmod +x /tmp/target_file

# Start network capture
# -U makes tcpdump packet-buffered
# We ignore errors in case there's no network interface available
tcpdump -i any -n -w /sandbox_out/network.pcap -U 2>/dev/null &
TCPDUMP_PID=$!

# Give tcpdump a moment to initialize
sleep 1

# Execute the file under strace
# -f: Follow forks
# -y: Print paths associated with file descriptor arguments
# -e trace=...: Only trace specific system calls
# -o: Output file
# We use timeout to ensure it doesn't run forever
timeout 30 strace -f -y -e trace=open,openat,execve,connect -o /sandbox_out/trace.log /tmp/target_file

# Stop network capture gracefully
if kill -0 $TCPDUMP_PID 2>/dev/null; then
    kill -INT $TCPDUMP_PID
    wait $TCPDUMP_PID 2>/dev/null
fi

# Convert PCAP to readable text for easier parsing by the backend
# -nn: don't resolve hostnames or port names
tcpdump -r /sandbox_out/network.pcap -nn > /sandbox_out/network.txt 2>/dev/null || true

# Change permissions so the host backend can easily read/delete them if necessary
chmod 666 /sandbox_out/* 2>/dev/null || true

exit 0
