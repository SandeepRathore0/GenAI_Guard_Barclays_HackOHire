#!/bin/bash
echo "Hello from sandbox!"
cat /etc/passwd > /dev/null
ping -c 1 8.8.8.8 > /dev/null
