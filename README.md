✅ Pré-requisitos
Certifique-se de que o sistema tem os seguintes pacotes:

sudo apt update
sudo apt install -y git curl python3 python3-pip systemd


🚀 Passo a passo de instalação


git clone https://github.com/RDFonseca82/iWebITAgent_Linux.git

cd iWebITAgent_Linux

chmod +x install.sh

sudo ./install.sh

sudo systemctl status iwebit_agent


Durante a instalação será solicitado o IdSync (identificador da empresa ou cliente).



🚀 Desisntalar iWebItAgent


sudo systemctl stop iwebit_agent.service 2>/dev/null

sudo systemctl disable iwebit_agent.service 2>/dev/null

sudo rm -f /etc/systemd/system/iwebit_agent.service

sudo systemctl daemon-reload

sudo rm -rf /opt/iwebit_agent

sudo rm -rf /var/log/iwebit_agent



#Verificar versão

grep "VERSION" /opt/iwebit_agent/iwebit_agent.py


#Verificar o status do serviço

sudo systemctl status iwebit_agent 

