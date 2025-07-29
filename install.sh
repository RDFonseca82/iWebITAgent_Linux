#!/bin/bash

# iwebit_agent - Script de instalação
# https://github.com/RDFonseca82/iWebITAgent_Linux

AGENT_PATH="/usr/local/bin/iwebit_agent.py"
SERVICE_PATH="/etc/systemd/system/iwebit_agent.service"
CONFIG_PATH="/etc/iwebit_agent.conf"
LOG_FILE="/var/log/iwebit_agent.log"

echo "==============================="
echo " iWebIT Agent - Instalação"
echo "==============================="

# Verifica permissões
if [ "$EUID" -ne 0 ]; then
  echo "Por favor, execute como root"
  exit 1
fi

# Pergunta pelo IdSync
read -p "Introduza o IdSync da empresa: " IDSYNC

# Verifica se é válido
if [[ -z "$IDSYNC" ]]; then
  echo "IdSync inválido. Instalação cancelada."
  exit 1
fi

# Instala dependências
echo "Instalando dependências Python..."
apt update -y
apt install -y python3 python3-pip curl

# Cria o arquivo de configuração
echo "IdSync=${IDSYNC}" > "$CONFIG_PATH"
echo "Log=1" >> "$CONFIG_PATH"
chmod 600 "$CONFIG_PATH"
echo "Configuração salva em $CONFIG_PATH"

# Copia o script para o destino
cp iwebit_agent.py "$AGENT_PATH"
chmod +x "$AGENT_PATH"

# Cria o serviço systemd
cat <<EOF > "$SERVICE_PATH"
[Unit]
Description=iWebIT Agent
After=network.target

[Service]
ExecStart=/usr/bin/python3 $AGENT_PATH
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Habilita e inicia o serviço
systemctl daemon-reexec
systemctl daemon-reload
systemctl enable iwebit_agent.service
systemctl start iwebit_agent.service

# Mostra status
echo "Serviço instalado e iniciado:"
systemctl status iwebit_agent --no-pager

echo
echo "Logs em tempo real: sudo tail -f $LOG_FILE"
echo "Instalação concluída com sucesso!"
