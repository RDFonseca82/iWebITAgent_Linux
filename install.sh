##!/bin/bash

echo "🔧 A instalar o iWebIT Agent..."

INSTALL_DIR="/opt/iwebit_agent"
CONFIG_FILE="/etc/iwebit_agent.conf"
SERVICE_FILE="/etc/systemd/system/iwebit_agent.service"
AGENT_SCRIPT="iwebit_agent.py"
CONF_SCRIPT="iwebit_agent.conf"
SERVICE_SCRIPT="iwebit_agent.service"
LOG_FILE="/var/log/iwebit_agent.log"

# Perguntar IdSync ao utilizador
read -p "Por favor, introduza o IdSync (identificador da sincronização): " ID_SYNC

if [ -z "$ID_SYNC" ]; then
    echo "❌ IdSync não pode estar vazio. Abortando instalação."
    exit 1
fi

# Criar diretório de instalação
echo "📁 Criando diretório: $INSTALL_DIR"
sudo mkdir -p $INSTALL_DIR

# Copiar scripts para o diretório
echo "📄 Copiando scripts para $INSTALL_DIR"
sudo cp $AGENT_SCRIPT $INSTALL_DIR/
sudo chmod +x $INSTALL_DIR/$AGENT_SCRIPT

# Criar/atualizar ficheiro de configuração com o IdSync fornecido
echo "⚙️ Criando/atualizando ficheiro de configuração em $CONFIG_FILE"

sudo bash -c "cat > $CONFIG_FILE <<EOF
# Configuração do iWebIT Agent
IdSync=$ID_SYNC
Log=0
EOF
"

# Copiar serviço systemd
echo "🛠️ Instalando serviço systemd"
sudo cp $SERVICE_SCRIPT $SERVICE_FILE
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable iwebit_agent.service

# Criar ficheiro de log se não existir
if [ ! -f "$LOG_FILE" ]; then
    sudo touch $LOG_FILE
    sudo chmod 666 $LOG_FILE
fi

# Iniciar serviço
echo "🚀 A iniciar o serviço..."
sudo systemctl restart iwebit_agent.service

echo "✅ Instalação concluída com sucesso!"
echo "📌 O IdSync foi configurado como: $ID_SYNC"
