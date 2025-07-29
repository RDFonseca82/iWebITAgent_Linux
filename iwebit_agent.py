#!/usr/bin/env python3

import os
import time
import json
import socket
import subprocess
import uuid
import requests
import platform
import datetime
import shutil
import hashlib
import sys

CONFIG_FILE = "/etc/iwebit_agent.conf"
LOG_FILE = "/var/log/iwebit_agent.log"
VERSION = "1.0.1.1"
SYNC_INTERVAL_FULL = 3600  # 60 minutos
SYNC_INTERVAL_MIN = 300    # 5 minutos
GITHUB_RAW_URL = "https://raw.githubusercontent.com/RDFonseca82/iWebITAgent_Linux/main/iwebit_agent.py"
LOCAL_SCRIPT_PATH = "/opt/iwebit_agent/iwebit_agent.py"

def log(message):
    if CONFIG.get("Log", "0") == "1":
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a") as logf:
            logf.write(f"[{timestamp}] {message}\n")

def get_config():
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    config[key] = value
    return config

def get_unique_id():
    idsync = CONFIG.get("IdSync", "")
    hostname = socket.gethostname()
    raw = f"{idsync}_{hostname}"
    return uuid.uuid5(uuid.NAMESPACE_DNS, raw).hex

def get_cpu_usage():
    return os.getloadavg()[0]

def get_memory_usage():
    try:
        with open('/proc/meminfo', 'r') as f:
            meminfo = f.read()
        total = int([x for x in meminfo.splitlines() if 'MemTotal' in x][0].split()[1])
        free = int([x for x in meminfo.splitlines() if 'MemAvailable' in x][0].split()[1])
        usage = ((total - free) / total) * 100
        return round(usage, 2)
    except:
        return None

def get_total_ram():
    try:
        with open('/proc/meminfo', 'r') as f:
            meminfo = f.read()
        total_kb = int([x for x in meminfo.splitlines() if 'MemTotal' in x][0].split()[1])
        return round(total_kb / 1024, 2)
    except:
        return None

def get_mac_address():
    try:
        output = subprocess.check_output("ip link", shell=True).decode()
        for line in output.splitlines():
            if "link/ether" in line:
                return line.strip().split()[1]
    except:
        return None

def get_process_list():
    try:
        output = subprocess.check_output(["ps", "-eo", "pid,comm,%cpu,%mem", "--sort=-%cpu"], text=True)
        lines = output.strip().splitlines()
        headers = lines[0].split()
        processes = []
        for line in lines[1:11]:
            values = line.split(None, len(headers)-1)
            proc = dict(zip(headers, values))
            processes.append(proc)
        return processes
    except:
        return []

def get_uptime():
    try:
        with open('/proc/uptime', 'r') as f:
            seconds = float(f.readline().split()[0])
            return str(datetime.timedelta(seconds=int(seconds)))
    except:
        return None

def get_last_boot():
    try:
        output = subprocess.check_output("who -b", shell=True).decode()
        return output.strip().split("boot")[1].strip()
    except:
        return None

def get_timezone():
    try:
        return time.tzname[0]
    except:
        return None

def get_hostname():
    return socket.gethostname()

def get_kernel_version():
    return platform.release()

def get_cpu_architecture():
    return platform.machine()

def get_logged_users_count():
    try:
        output = subprocess.check_output("who", shell=True).decode()
        return len(output.strip().splitlines())
    except:
        return None

def get_current_user():
    try:
        return os.getlogin()
    except:
        return None

def get_public_ip():
    try:
        return requests.get('https://api.ipify.org', timeout=5).text
    except:
        return None

def get_installed_packages():
    try:
        output = subprocess.check_output("dpkg -l", shell=True).decode()
        return output.strip().splitlines()[5:]
    except:
        return []

def get_pending_updates():
    try:
        output = subprocess.check_output("apt list --upgradable 2>/dev/null | tail -n +2", shell=True).decode()
        return output.strip().splitlines()
    except:
        return []

def get_location():
    try:
        response = requests.get("https://ipinfo.io/json", timeout=5)
        data = response.json()
        if "loc" in data:
            lat, lon = data["loc"].split(",")
            return lat, lon
    except:
        pass
    return None, None

def detect_device_type():
    try:
        output = subprocess.check_output("hostnamectl", shell=True).decode().lower()
        if "server" in output:
            return 109
        else:
            return 92
    except:
        return 92

def build_payload(full=True):
    lat, lon = get_location()
    payload = {
        "uniqueid": get_unique_id(),
        "IdSync": CONFIG.get("IdSync", ""),
        "FullSync": 1 if full else 0,
        "CPU": get_cpu_usage(),
        "Memory": get_memory_usage(),
        "Latitude": lat,
        "Longitude": lon
    }

    if full:
        payload.update({
            "MAC": get_mac_address(),
            "ProcessList": get_process_list(),
            "Uptime": get_uptime(),
            "LastBoot": get_last_boot(),
            "TimeZone": get_timezone(),
            "Hostname": get_hostname(),
            "KernelVersion": get_kernel_version(),
            "CPUArchitecture": get_cpu_architecture(),
            "NumLoggedUsers": get_logged_users_count(),
            "CurrentUser": get_current_user(),
            "PublicIP": get_public_ip(),
            "TotalRAM": get_total_ram(),
            "InstalledPackages": get_installed_packages(),
            "PendingUpdates": get_pending_updates(),
            "ScriptVersion": VERSION,
            "IdDeviceType": detect_device_type()
        })

    return payload

def send_data(payload):
    try:
        response = requests.post("https://agent.iwebit.app/scripts/script_linux.php",
                                 headers={"Content-Type": "application/json"},
                                 data=json.dumps(payload), timeout=10)
        log(f"Enviado com sucesso (FullSync={payload['FullSync']}): {response.status_code}")
    except Exception as e:
        log(f"Erro ao enviar dados: {str(e)}")

def file_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()

def check_for_update():
    if CONFIG.get("AutoUpdate", "0") != "1":
        return

    try:
        response = requests.get(GITHUB_RAW_URL, timeout=10)
        if response.status_code == 200:
            tmp_file = "/tmp/iwebit_agent_new.py"
            with open(tmp_file, "w") as f:
                f.write(response.text)

            if os.path.exists(LOCAL_SCRIPT_PATH):
                current_hash = file_hash(LOCAL_SCRIPT_PATH)
                new_hash = file_hash(tmp_file)

                if current_hash != new_hash:
                    log("Nova versão encontrada. Atualizando...")
                    shutil.copy2(tmp_file, LOCAL_SCRIPT_PATH)
                    os.chmod(LOCAL_SCRIPT_PATH, 0o755)
                    os.execv(sys.executable, ["python3", LOCAL_SCRIPT_PATH])
                else:
                    os.remove(tmp_file)
        else:
            log(f"Falha ao verificar atualização. Status: {response.status_code}")
    except Exception as e:
        log(f"Erro durante a verificação de update: {str(e)}")

def main_loop():
    last_full = 0
    while True:
        check_for_update()
        now = time.time()
        fullsync = (now - last_full >= SYNC_INTERVAL_FULL)
        payload = build_payload(full=fullsync)
        send_data(payload)
        if fullsync:
            last_full = now
        time.sleep(SYNC_INTERVAL_MIN)

if __name__ == "__main__":
    CONFIG = get_config()
    main_loop()
