#!/bin/bash

echo "Instalando iWebIT Agent..."

if [ "$(id -u)" -ne 0 ]; then
    echo "Execute como root."
    exit 1
fi

apt update -y
apt install -y python3 python3-pip curl

cp iwebit_agent.py /usr/local/bin/iwebit_agent.py
chmod +x /usr/local/bin/iwebit_agent.py

echo -n "Digite o IdSync para esta instalação: "
read IDSYNC

mkdir -p /etc
echo "IdSync=$IDSYNC" > /etc/iwebit_agent.conf
echo "Log=1" >> /etc/iwebit_agent.conf
chmod 600 /etc/iwebit_agent.conf

cat >/etc/systemd/system/iwebit_agent.service <<EOF
[Unit]
Description=iWebIT Agent
After=network.target

[Service]
ExecStart=/usr/bin/python3 /usr/local/bin/iwebit_agent.py
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable iwebit_agent
systemctl start iwebit_agent

echo "Instalação concluída e serviço iniciado."
echo "Logs em /var/log/iwebit_agent.log"
