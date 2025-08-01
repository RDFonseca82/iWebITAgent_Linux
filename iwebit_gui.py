import os
import sys
import subprocess
import requests
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction, QMessageBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QTimer

APP_DIR = "/opt/iwebit_agent/"
ASSETS_DIR = os.path.join(APP_DIR, "assets")
LOG_FILE = "/var/log/iwebit_agent/iwebit_agent.log"
SERVICE_NAME = "iwebit_agent.service"

ICON_URLS = {
    "online": "https://intranet.iwebit.app/winsrv/iwebit_online.png",
    "offline": "https://intranet.iwebit.app/winsrv/iwebit_offline.png",
    "inactive": "https://intranet.iwebit.app/winsrv/iwebit_inactive.png"
}

ICON_FILES = {
    "online": os.path.join(ASSETS_DIR, "iwebit_online.png"),
    "offline": os.path.join(ASSETS_DIR, "iwebit_offline.png"),
    "inactive": os.path.join(ASSETS_DIR, "iwebit_inactive.png")
}

def update_icons():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    for name, url in ICON_URLS.items():
        local_path = ICON_FILES[name]
        try:
            remote = requests.get(url, timeout=5).content
            if os.path.exists(local_path):
                with open(local_path, 'rb') as f:
                    local = f.read()
                if local != remote:
                    with open(local_path, 'wb') as f:
                        f.write(remote)
            else:
                with open(local_path, 'wb') as f:
                    f.write(remote)
        except Exception:
            pass  # ignora erros silenciosamente

def get_icon():
    try:
        # Verifica se o serviço está ativo
        result = subprocess.run(
            ['systemctl', 'is-active', SERVICE_NAME],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
        status = result.stdout.decode().strip()
        if status == "active":
            # Testa conexão à internet
            try:
                requests.get("https://www.google.com", timeout=3)
                return QIcon(ICON_FILES["online"])
            except:
                return QIcon(ICON_FILES["offline"])
        else:
            return QIcon(ICON_FILES["inactive"])
    except:
        return QIcon(ICON_FILES["inactive"])

def show_logs():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            log_content = f.read()[-5000:]  # Mostra últimas linhas
    else:
        log_content = "Log não encontrado."

    msg = QMessageBox()
    msg.setWindowTitle("Logs do iWebIT Agent")
    msg.setTextInteractionFlags(Qt.TextSelectableByMouse)
    msg.setMinimumWidth(600)
    msg.setMinimumHeight(400)
    msg.setText(log_content)
    msg.exec_()

def restart_agent():
    subprocess.run(['systemctl', 'restart', SERVICE_NAME])
    QMessageBox.information(None, "Ressincronização", "O agente foi reiniciado com sucesso.")

def main():
    update_icons()
    app = QApplication(sys.argv)
    tray = QSystemTrayIcon()
    tray.setIcon(get_icon())
    tray.setVisible(True)

    # Atualiza ícone periodicamente
    def refresh_icon():
        tray.setIcon(get_icon())
    timer = QTimer()
    timer.timeout.connect(refresh_icon)
    timer.start(60000)  # a cada 60 segundos

    # Menu
    menu = QMenu()
    action_logs = QAction("Ver Logs")
    action_logs.triggered.connect(show_logs)
    menu.addAction(action_logs)

    action_restart = QAction("Ressincronizar")
    action_restart.triggered.connect(restart_agent)
    menu.addAction(action_restart)

    action_quit = QAction("Sair")
    action_quit.triggered.connect(app.quit)
    menu.addAction(action_quit)

    tray.setContextMenu(menu)
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
