#!/bin/bash

echo "==== iWebIT Agent - Instalação ===="

# Confirmar permissões
if [ "$EUID" -ne 0 ]; then
  echo "Por favor execute como root: sudo ./install.sh"
  exit 1
fi

# Solicitar o IdSync
read -p "Introduza o IdSync da máquina: " IDSYNC

# Diretórios
INSTALL_DIR="/opt/iwebit_agent"
LOG_DIR="/var/log/iwebit_agent"

# Criar diretórios
mkdir -p "$INSTALL_DIR"
mkdir -p "$LOG_DIR"

# Copiar ficheiros
cp iwebit_agent.py "$INSTALL_DIR/"
cp iwebit_agent.conf "$INSTALL_DIR/"
cp requirements.txt "$INSTALL_DIR/"

# Atualizar IdSync no ficheiro de configuração
sed -i "s/^IdSync = .*/IdSync = $IDSYNC/" "$INSTALL_DIR/iwebit_agent.conf"

# Gerar UniqueId persistente
HOSTNAME=$(hostname)
UNIQUE_ID=$(echo -n "${IDSYNC}_${HOSTNAME}" | sha256sum | awk '{print $1}')

# Atualizar ou adicionar UniqueId ao ficheiro de configuração
if grep -q "^UniqueId =" "$INSTALL_DIR/iwebit_agent.conf"; then
  sed -i "s/^UniqueId = .*/UniqueId = $UNIQUE_ID/" "$INSTALL_DIR/iwebit_agent.conf"
else
  echo "UniqueId = $UNIQUE_ID" >> "$INSTALL_DIR/iwebit_agent.conf"
fi

# Criar ficheiro do serviço
cat <<EOF > /etc/systemd/system/iwebit_agent.service
[Unit]
Description=iWebIT Agent
After=network.target

[Service]
ExecStart=/usr/bin/python3 /opt/iwebit_agent/iwebit_agent.py
WorkingDirectory=/opt/iwebit_agent/
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF

# Instalar dependências necessárias
echo "A instalar dependências..."
apt update
apt install -y python3 python3-psutil python3-requests curl

# Permissões
chmod +x "$INSTALL_DIR/iwebit_agent.py"

# Ativar o serviço
systemctl daemon-reexec
systemctl daemon-reload
systemctl enable iwebit_agent.service
systemctl restart iwebit_agent.service

echo "==== Instalação concluída ===="
echo "O serviço iwebit_agent está agora ativo e configurado."
