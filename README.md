✅ Pré-requisitos
Certifique-se de que o sistema tem os seguintes pacotes:

sudo apt update
sudo apt install -y git curl python3 python3-pip systemd

----------------------------------------------------------------------------

🚀 Passo a passo de instalação


git clone https://github.com/RDFonseca82/iWebITAgent_Linux.git

cd iWebITAgent_Linux

chmod +x install.sh

sudo ./install.sh

sudo systemctl status iwebit_agent


Durante a instalação será solicitado o IdSync (identificador da empresa ou cliente).


-------------------------------------------------------------------------------------

🚀 Desisntalar iWebItAgent


sudo systemctl stop iwebit_agent.service 2>/dev/null

sudo systemctl disable iwebit_agent.service 2>/dev/null

sudo rm -f /etc/systemd/system/iwebit_agent.service

sudo systemctl daemon-reload

sudo rm -rf /opt/iwebit_agent

sudo rm -rf /var/log/iwebit_agent


----------------------------------------------------------------------------------------

# Verificar versão do Agente

grep "VERSION" /opt/iwebit_agent/iwebit_agent.py

----------------------------------------------------------------------------------------

# Ativar logs

Editar o ficheiro /opt/iwebit_agent/iwebit_agent.conf

Alterar o valor Log = 1

Ver os logs em /var/log/iwebit_agent/iwebit_agent.log


----------------------------------------------------------------------------------------

# Ativar Debug JSON

Editar o ficheiro /opt/iwebit_agent/iwebit_agent.conf

Alterar o valor Debug = 1

Ver o ficheiro JSON a ser enviado em /opt/iwebit_agent/iwebit_send.json

----------------------------------------------------------------------------------------

#Verificar o status do serviço

sudo systemctl status iwebit_agent 

