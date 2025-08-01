import sys
import os
import urllib.request
import hashlib
import subprocess
from PyQt5 import QtWidgets, QtGui, QtCore

ICON_URLS = {
    "online": "https://intranet.iwebit.app/winsrv/iwebit_online.png",
    "offline": "https://intranet.iwebit.app/winsrv/iwebit_offline.png",
    "inactive": "https://intranet.iwebit.app/winsrv/iwebit_inactive.png"
}

ASSETS_DIR = "/opt/iwebit_agent/assets"
LOG_FILE = "/var/log/iwebit_agent/iwebit_agent.log"
SERVICE_NAME = "iwebit_agent"

def get_icon_checksum(url):
    try:
        with urllib.request.urlopen(url) as response:
            return hashlib.md5(response.read()).hexdigest()
    except:
        return None

def update_icons():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    for name, url in ICON_URLS.items():
        local_path = os.path.join(ASSETS_DIR, f"iwebit_{name}.png")
        try:
            remote_checksum = get_icon_checksum(url)
            local_checksum = None
            if os.path.exists(local_path):
                with open(local_path, 'rb') as f:
                    local_checksum = hashlib.md5(f.read()).hexdigest()
            if local_checksum != remote_checksum:
                urllib.request.urlretrieve(url, local_path)
        except Exception as e:
            print(f"Erro ao verificar/baixar ícone {name}: {e}")

def is_service_active():
    try:
        status = subprocess.run(["systemctl", "is-active", SERVICE_NAME], stdout=subprocess.PIPE)
        return status.stdout.decode().strip() == "active"
    except:
        return False

def is_connected():
    try:
        subprocess.check_call(["ping", "-c", "1", "8.8.8.8"], stdout=subprocess.DEVNULL)
        return True
    except:
        return False

class IwebitTray(QtWidgets.QSystemTrayIcon):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.menu = QtWidgets.QMenu()

        self.logs_action = self.menu.addAction("Abrir logs")
        self.logs_action.triggered.connect(self.open_logs)

        self.quit_action = self.menu.addAction("Sair")
        self.quit_action.triggered.connect(QtWidgets.qApp.quit)

        self.setContextMenu(self.menu)

        self.update_icon()
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_icon)
        self.timer.start(60 * 1000)  # 1 minuto

    def open_logs(self):
        subprocess.Popen(["xdg-open", LOG_FILE])

    def update_icon(self):
        update_icons()
        if is_service_active():
            if is_connected():
                self.setIcon(QtGui.QIcon(os.path.join(ASSETS_DIR, "iwebit_online.png")))
                self.setToolTip("iWebIT Agent - Online")
            else:
                self.setIcon(QtGui.QIcon(os.path.join(ASSETS_DIR, "iwebit_offline.png")))
                self.setToolTip("iWebIT Agent - Sem internet")
        else:
            self.setIcon(QtGui.QIcon(os.path.join(ASSETS_DIR, "iwebit_inactive.png")))
            self.setToolTip("iWebIT Agent - Inativo")

def main():
    update_icons()
    app = QtWidgets.QApplication(sys.argv)
    tray = IwebitTray(app)
    tray.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
