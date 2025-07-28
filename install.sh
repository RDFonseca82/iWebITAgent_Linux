#!/bin/bash

# install.sh para iwebit_agent
set -e

AGENT_PATH="/usr/local/bin/iwebit_agent.py"
SERVICE_PATH="/etc/systemd/system/iwebit_agent.service"
VERSION_FILE="/etc/iwebit_agent_version"

# Verifica dependências
apt update
apt install -y python3 python3-pip net-tools curl git
pip3 install psutil netifaces requests distro

# Cria diretórios necessários
mkdir -p /etc

# Baixa o script principal e o version.txt
curl -sSL https://raw.githubusercontent.com/RDFonseca82/iWebITAgent_Linux/main/iwebit_agent.py -o "$AGENT_PATH"
chmod +x "$AGENT_PATH"

curl -sSL https://raw.githubusercontent.com/RDFonseca82/iWebITAgent_Linux/main/version.txt -o "$VERSION_FILE"

# Cria o serviço systemd
cat > "$SERVICE_PATH" <<EOF
[Unit]
Description=Agente iWebIT Linux
After=network.target

[Service]
ExecStart=/usr/bin/python3 $AGENT_PATH
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF

# Ativa o serviço
systemctl daemon-reexec
systemctl daemon-reload
systemctl enable iwebit_agent.service
systemctl restart iwebit_agent.service

echo "Instalação concluída com sucesso."
echo "Edite /etc/sync_agent_idsync para definir o IdSync."
