#!/bin/bash

echo "🔧 A instalar o iWebIT Agent..."

# Caminhos
INSTALL_DIR="/opt/iwebit_agent"
CONFIG_FILE="/etc/iwebit_agent.conf"
SERVICE_FILE="/etc/systemd/system/iwebit_agent.service"
AGENT_SCRIPT="iwebit_agent.py"
CONF_SCRIPT="iwebit_agent.conf"
SERVICE_SCRIPT="iwebit_agent.service"
LOG_FILE="/var/log/iwebit_agent.log"

# Cria diretório
echo "📁 Criando diretório: $INSTALL_DIR"
sudo mkdir -p $INSTALL_DIR

# Copia scripts
echo "📄 Copiando scripts para $INSTALL_DIR"
sudo cp $AGENT_SCRIPT $INSTALL_DIR/
sudo chmod +x $INSTALL_DIR/$AGENT_SCRIPT

# Copia config
echo "⚙️ Instalando configuração para $CONFIG_FILE"
if [ ! -f "$CONFIG_FILE" ]; then
    sudo cp $CONF_SCRIPT $CONFIG_FILE
    echo "🔐 Por favor edite o ficheiro /etc/iwebit_agent.conf e defina o IdSync antes de iniciar o agente."
else
    echo "⚠️ Ficheiro de configuração já existe, não será substituído."
fi

# Copia serviço systemd
echo "🛠️ Instalando serviço systemd"
sudo cp $SERVICE_SCRIPT $SERVICE_FILE
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable iwebit_agent.service

# Cria log (opcional)
if [ ! -f "$LOG_FILE" ]; then
    sudo touch $LOG_FILE
    sudo chmod 666 $LOG_FILE
fi

# Inicia serviço
echo "🚀 A iniciar o serviço..."
sudo systemctl restart iwebit_agent.service

echo "✅ Instalação completa!"
echo "📌 Edita o ficheiro /etc/iwebit_agent.conf para configurares o IdSync antes da primeira execução real."
