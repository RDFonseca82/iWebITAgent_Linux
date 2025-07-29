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
VERSION = '1.0.7.1'
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

def get_installed_packages():
    try:
        output = subprocess.check_output(['dpkg-query', '-W', '-f=${Package}\n']).decode()
        return output.strip().split('\n')
    except:
        return []

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
            'InstalledPackages': get_installed_packages(),
            'PendingUpdates': get_pending_updates()
        })

    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(API_URL, json=data, headers=headers)
        log(f"Data sent. Status code: {response.status_code}")
    except Exception as e:
        log(f"Failed to send data: {e}")

# =================== MAIN LOOP ===================
if __name__ == '__main__':
    full_interval = 60 * 60
    minimal_interval = 5 * 60
    last_fullsync = 0

    while True:
        now = time.time()
        if now - last_fullsync >= full_interval:
            log("Performing FULL sync")
            send_data(fullsync=True)
            last_fullsync = now
        else:
            log("Performing MINIMAL sync")
            send_data(fullsync=False)

        check_for_updates()
        time.sleep(minimal_interval)
