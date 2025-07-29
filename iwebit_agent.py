#!/usr/bin/env python3
import os
import platform
import psutil
import socket
import json
import time
import subprocess
import hashlib
import requests
import shutil
from datetime import datetime

# =================== CONFIG ===================
CONFIG_FILE = '/opt/iwebit_agent/iwebit_agent.conf'
# UNIQUEID_FILE = '/opt/iwebit_agent/uniqueid.conf'
VERSION = '1.0.14.1'
LOG_ENABLED = True
LOG_FILE = '/var/log/iwebit_agent/iwebit_agent.log'
UPDATE_URL = 'https://raw.githubusercontent.com/RDFonseca82/iWebITAgent_Linux/main/iwebit_agent.py'
SCRIPT_PATH = '/opt/iwebit_agent/iwebit_agent.py'
API_URL = 'https://agent.iwebit.app/scripts/script_linux.php'

# =================== LOGGING ===================
def log(message):
    if LOG_ENABLED:
        with open(LOG_FILE, 'a') as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")

# =================== CONFIG LOAD ===================
def load_config():
    global LOG_ENABLED
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
    LOG_ENABLED = config.get('Log', '0') == '1'
    return config


# =================== DATA COLLECTION ===================
def get_cpu_usage():
    return psutil.cpu_percent(interval=1)

def get_memory_usage():
    return psutil.virtual_memory().percent

def get_total_memory():
    return round(psutil.virtual_memory().total / (1024**3), 2)

def get_mac_address():
    for interface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == psutil.AF_LINK:
                return addr.address
    return '00:00:00:00:00:00'

def get_process_list():
    return [p.info for p in psutil.process_iter(attrs=['pid', 'name', 'username'])]

def get_hostname():
    return socket.gethostname()

def get_uptime():
    return int(time.time() - psutil.boot_time())

def get_last_boot():
    return datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M:%S')

def get_timezone():
    return time.tzname[0]

def get_kernel_version():
    return platform.release()

def get_architecture():
    return platform.machine()

def get_logged_users():
    return len(psutil.users())

def get_current_user():
    try:
        import getpass
        return getpass.getuser()
    except Exception:
        return "unknown"

def get_public_ip():
    try:
        return requests.get('https://api.ipify.org').text
    except:
        return 'Unavailable'

def get_location():
    try:
        res = requests.get('https://ipinfo.io/json').json()
        loc = res.get('loc', '0,0').split(',')
        return loc[0], loc[1]
    except:
        return '0', '0'

def get_device_type():
    try:
        output = subprocess.check_output(['systemd-detect-virt']).decode().strip()
        return 109 if output == 'none' else 92
    except:
        return 92

def get_all_installed_software():
    software_list = []

    # --------------------- DPKG (APT) ---------------------
    try:
        output = subprocess.check_output(
            ['dpkg-query', '-W', '-f=${Package}\t${Version}\t${Installed-Size}\t${Status}\n'],
            stderr=subprocess.DEVNULL
        ).decode().strip().split('\n')

        for line in output:
            parts = line.split('\t')
            if len(parts) >= 2:
                name = parts[0]
                version = parts[1]
                identifier = name
                software_list.append({
                    "Name": name,
                    "Version": version,
                    "Identifier": identifier,
                    "InstallDate": "Unknown"
                })
    except Exception as e:
        pass

    # --------------------- SNAP ---------------------
    try:
        snap_output = subprocess.check_output(['snap', 'list'], stderr=subprocess.DEVNULL).decode().strip().split('\n')[1:]
        for line in snap_output:
            parts = line.split()
            if len(parts) >= 4:
                name = parts[0]
                version = parts[1]
                install_date = parts[-1]  # Última coluna costuma ser data
                software_list.append({
                    "Name": name,
                    "Version": version,
                    "Identifier": name,
                    "InstallDate": install_date
                })
    except Exception as e:
        pass

    # --------------------- FLATPAK ---------------------
    try:
        flatpak_output = subprocess.check_output(
            ['flatpak', 'list', '--columns=application,version,installation'],
            stderr=subprocess.DEVNULL
        ).decode().strip().split('\n')

        for line in flatpak_output:
            if '\t' in line:
                parts = line.split('\t')
                if len(parts) >= 2:
                    app_id = parts[0]
                    version = parts[1] or "Unknown"
                    software_list.append({
                        "Name": app_id,
                        "Version": version,
                        "Identifier": app_id,
                        "InstallDate": "Unknown"
                    })
    except Exception as e:
        pass

    return software_list

def get_pending_updates():
    try:
        output = subprocess.check_output(['apt', 'list', '--upgradeable'], stderr=subprocess.DEVNULL).decode()
        return [line.split('/')[0] for line in output.splitlines() if '/' in line]
    except:
        return []

def check_for_updates():
    try:
        remote = requests.get(UPDATE_URL).text
        with open(SCRIPT_PATH, 'r') as f:
            local = f.read()
        if remote.strip() != local.strip():
            log(f"Update available {VERSION}. Updating...")
            with open(SCRIPT_PATH, 'w') as f:
                f.write(remote)
            os.chmod(SCRIPT_PATH, 0o755)
            log(f"Update {VERSION} applied. Restarting agent...")
            os.execv(SCRIPT_PATH, ['python3', SCRIPT_PATH])
    except Exception as e:
        log(f"Auto-update failed: {e}")

def is_connected():
    try:
        subprocess.check_output(["ping", "-c", "1", "-W", "2", "8.8.8.8"], stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False


# =================== SYNC ===================
def send_data(fullsync):
    config = load_config()
    # log(f"Config loaded in send_data: {config}")  # <-- linha para debug
    idsync = config.get('IdSync', '0')
    hostname = get_hostname()
    uniqueid = config.get('UniqueId', '0')
    # log(f"UniqueId read: '{uniqueid}'")  # <-- linha para debug
    latitude, longitude = get_location()
    current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    debug_enabled = config.get('Debug', '0') == '1'

    data = {
        'IdSync': idsync,
        'uniqueid': uniqueid,
        'Hostname': hostname,
        'AgentVersion': VERSION,
        'DateTime': current_datetime,
        'FullSync': 1 if fullsync else 0,
        'CPUUsage': get_cpu_usage(),
        'MemoryUsage': get_memory_usage(),
        'CurrentUser': get_current_user(),
        'Latitude': latitude,
        'Longitude': longitude
    }

    if fullsync:
        data.update({
            'MACAddress': get_mac_address(),
            'ProcessList': get_process_list(),
            'Uptime': get_uptime(),
            'LastBoot': get_last_boot(),
            'TimeZone': get_timezone(),
            'DateTime': current_datetime,
            'Hostname': hostname,
            'KernelVersion': get_kernel_version(),
            'CPUArchitecture': get_architecture(),
            'NumLoggedUsers': get_logged_users(),
            'CurrentUser': get_current_user(),
            'PublicIP': get_public_ip(),
            'TotalRAM': get_total_memory(),
            'IdDeviceType': get_device_type(),
            'AgentVersion': VERSION,
            'InstalledSoftware': get_all_installed_software(),
            'PendingUpdates': get_pending_updates()
        })

    # Salvar JSON se Debug=1
    if debug_enabled:
        try:
            with open('/opt/iwebit_agent/iwebit_send.json', 'w') as json_file:
                json.dump(data, json_file, indent=4)
            log("Debug ativo: JSON enviado salvo em iwebit_send.json")
        except Exception as e:
            log(f"Erro ao gravar JSON de debug: {e}")
            
    
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(API_URL, json=data, headers=headers)
        log(f"Data sent. Status code: {response.status_code}")
    except Exception as e:
        log(f"Failed to send data: {e}")

# =================== CHECK REMOTE ACTIONS ===================
def check_remote_actions():
    config = load_config()
    uniqueid = config.get('UniqueId', '0')
    if uniqueid == '0' or not uniqueid:
        log("UniqueId não definido, pulando verificação de ações remotas.")
        return

    try:
        url = f"https://agent.iwebit.app/scripts/script_api.php?UniqueID={uniqueid}"
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            log(f"Falha ao obter ações remotas. Código HTTP: {response.status_code}")
            return

        data = response.json()
        reboot = str(data.get('OperatingSystem_Reboot', '0')) == '1'
        shutdown = str(data.get('OperatingSystem_ShutDown', '0')) == '1'

        if reboot:
            log("Comando remoto recebido: REBOOT")
            os.system('reboot')
        elif shutdown:
            log("Comando remoto recebido: SHUTDOWN")
            os.system('shutdown now')
        else:
            log("Nenhuma ação remota necessária.")

    except Exception as e:
        log(f"Erro ao verificar ações remotas: {e}")


# =================== MAIN LOOP ===================
if __name__ == '__main__':
    full_interval = 60 * 60
    minimal_interval = 5 * 60
    last_fullsync = 0
    last_remote_check = 0
    remote_check_interval = 2 * 60  # 2 minutos

    # Aguarda até haver conexão
    while not is_connected():
        log("Sem acesso à internet. Aguardando conexão...")
        time.sleep(30)

    log("Conexão com a internet estabelecida. Iniciando agente.")


    while True:
        if not is_connected():
            log("Sem conexão com a internet. Pulando execução...")
            time.sleep(minimal_interval)
            continue
        
        now = time.time()
        
        if now - last_fullsync >= full_interval:
            log("Performing FULL sync")
            send_data(fullsync=True)
            last_fullsync = now
        else:
            log("Performing MINIMAL sync")
            send_data(fullsync=False)

        if now - last_remote_check >= remote_check_interval:
            check_remote_actions()
            last_remote_check = now

        check_for_updates()
        time.sleep(minimal_interval)
