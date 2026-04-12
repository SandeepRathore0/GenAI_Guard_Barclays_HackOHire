FROM ubuntu:22.04

# Install necessary tools
RUN apt-get update && \
    apt-get install -y strace tcpdump tree && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set up the sandbox directory
WORKDIR /sandbox

# Copy the orchestration script
COPY analyze.sh /sandbox/analyze.sh
RUN chmod +x /sandbox/analyze.sh

# The script will be the entrypoint
ENTRYPOINT ["/sandbox/analyze.sh"]
