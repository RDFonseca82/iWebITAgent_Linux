✅ Pré-requisitos
Certifique-se de que o sistema tem os seguintes pacotes:

sudo apt update
sudo apt install -y git curl python3 python3-pip systemd


🚀 Passo a passo de instalação
1. Clone o repositório

git clone https://github.com/RDFonseca82/iWebITAgent_Linux.git
cd iWebITAgent_Linux


2. Torne o script de instalação executável

chmod +x install.sh


3. Execute o instalador

sudo ./install.sh

Durante a instalação será solicitado o IdSync (identificador da empresa ou cliente).
Ele será salvo em /etc/iwebit_agent.conf.


🔁 O que o install.sh faz:
Copia o script iwebit_agent.py para /usr/local/bin/
Cria e habilita o serviço iwebit_agent.service
Cria o arquivo de configuração /etc/iwebit_agent.conf
Gera o uniqueid (hash do IdSync + hostname)
Ativa o sistema de log em /var/log/iwebit_agent.log
Inicia o serviço automaticamente


▶️ Verificar se o serviço está rodando

sudo systemctl status iwebit_agent

Se estiver ativo, verá algo como:
Active: active (running)


📄 Configurações salvas
IdSync: /etc/iwebit_agent.conf
uniqueid: gerado automaticamente via SHA256
Log: /var/log/iwebit_agent.log
Versão: 1.0.0.0
