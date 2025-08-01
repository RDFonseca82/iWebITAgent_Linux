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
ASSETS_DIR="$INSTALL_DIR/assets"

# Criar diretórios
mkdir -p "$INSTALL_DIR"
mkdir -p "$LOG_DIR"
mkdir -p "$ASSETS_DIR"

# Copiar ficheiros
cp iwebit_agent.py "$INSTALL_DIR/"
cp iwebit_agent.conf "$INSTALL_DIR/"
cp requirements.txt "$INSTALL_DIR/"

# Atualizar ou adicionar IdSync no ficheiro de configuração
if grep -q "^IdSync" "$INSTALL_DIR/iwebit_agent.conf"; then
  sed -i "s/^IdSync.*/IdSync = $IDSYNC/" "$INSTALL_DIR/iwebit_agent.conf"
else
  echo "IdSync = $IDSYNC" >> "$INSTALL_DIR/iwebit_agent.conf"
fi

# Gerar UniqueId persistente
HOSTNAME=$(hostname)
UNIQUE_ID=$(echo -n "${IDSYNC}_${HOSTNAME}" | sha256sum | awk '{print $1}')

# Atualizar ou adicionar UniqueId ao ficheiro de configuração
if grep -q "^UniqueId" "$INSTALL_DIR/iwebit_agent.conf"; then
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

# Verificar se sistema tem interface gráfica (X ou Wayland)
if command -v xhost >/dev/null || [ -n "$XDG_SESSION_TYPE" ]; then
  echo "Ambiente gráfico detetado. A instalar iwebit_gui..."

  # Copiar GUI
  cp iwebit_gui.py "$INSTALL_DIR/"
  chmod +x "$INSTALL_DIR/iwebit_gui.py"

  # Fazer download dos ícones
  echo "A transferir ícones..."
  curl -s -o "$ASSETS_DIR/iwebit_online.png" https://intranet.iwebit.app/winsrv/iwebit_online.png
  curl -s -o "$ASSETS_DIR/iwebit_offline.png" https://intranet.iwebit.app/winsrv/iwebit_offline.png
  curl -s -o "$ASSETS_DIR/iwebit_inactive.png" https://intranet.iwebit.app/winsrv/iwebit_inactive.png

  # Criar ficheiro .desktop para iniciar GUI no login
  DESKTOP_ENTRY="[Desktop Entry]
Type=Application
Exec=/usr/bin/python3 /opt/iwebit_agent/iwebit_gui.py
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=iWebIT Agent GUI
Comment=Monitorização iWebIT Systray"

  # Guardar em autostart do utilizador atual (caso exista $SUDO_USER)
  USER_HOME=$(eval echo ~${SUDO_USER})
  AUTOSTART_DIR="$USER_HOME/.config/autostart"
  mkdir -p "$AUTOSTART_DIR"
  echo "$DESKTOP_ENTRY" > "$AUTOSTART_DIR/iwebit_gui.desktop"
  chown -R "$SUDO_USER":"$SUDO_USER" "$AUTOSTART_DIR"

  echo "GUI instalado e configurado para iniciar com o sistema."
else
  echo "Ambiente gráfico não detetado. A instalação do GUI foi ignorada."
fi

echo "==== Instalação concluída ===="
echo "O serviço iwebit_agent está agora ativo e configurado."
