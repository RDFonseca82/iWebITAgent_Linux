#!/bin/bash
set -e
REPO="https://github.com/RDFonseca82/iWebITAgent_Linux.git"
DIR="/opt/iwebit-agent"
apt_install() { apt-get update && apt-get install -y python3-pip git; }
pip_install() { pip3 install --upgrade psutil requests netifaces distro; }

if [ -d "$DIR" ]; then cd "$DIR" && git pull; else git clone "$REPO" "$DIR"; fi
if command -v apt-get >/dev/null; then apt_install; fi
pip_install
cp "$DIR/sync_agent.py" /usr/local/bin/; chmod +x /usr/local/bin/sync_agent.py
cp "$DIR/iwebit_agent.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable iwebit_agent.service
systemctl restart iwebit_agent.service
echo "Instalação concluída — agente versão ${1:-1.0.0.0}"
