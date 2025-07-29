#!/usr/bin/env python3
import os, time, json, subprocess, hashlib, base64, socket
import requests
from datetime import datetime

CONFIG_PATH = '/etc/iwebit_agent.conf'
LOG_PATH = '/var/log/iwebit_agent.log'
VERSION = '1.0.0.0'
API_URL = 'https://agent.iwebit.app/scripts/script_linux.php'

def load_config():
    config = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    config[key.strip()] = value.strip()
    return config

def write_log(message, log_enabled):
    if log_enabled:
        with open(LOG_PATH, 'a') as f:
            f.write(f"[{datetime.now()}] {message}\n")

def get_mac():
    try:
        output = subprocess.check_output("ip link", shell=True).decode()
        for line in output.splitlines():
            if 'link/ether' in line:
                return line.strip().split()[1]
    except:
        return ""
    return ""

def get_cpu():
    try:
        return subprocess.check_output("top -bn1 | head -5", shell=True).decode()
    except:
        return ""

def get_memory():
    try:
        return subprocess.check_output("free -m", shell=True).decode()
    except:
        return ""

def get_processes():
    try:
        return subprocess.check_output("ps aux", shell=True).decode()
    except:
        return ""

def get_installed_packages():
    try:
        return subprocess.check_output("dpkg -l", shell=True).decode()
    except:
        return ""

def get_pending_updates():
    try:
        return subprocess.check_output("apt list --upgradable 2>/dev/null", shell=True).decode()
    except:
        return ""

def get_device_type():
    try:
        output = subprocess.check_output("systemd-detect-virt", shell=True).decode().strip()
        return 109 if "none" in output else 92
    except:
        return 92

def generate_unique_id(idsync, hostname):
    raw = f"{idsync}{hostname}"
    return hashlib.sha256(raw.encode()).hexdigest()

def build_payload(config, fullsync=False):
    hostname = socket.gethostname()
    mac = get_mac()
    cpu = get_cpu()
    memory = get_memory()
    device_type = get_device_type()
    uniqueid = generate_unique_id(config['IdSync'], hostname)

    data = {
        "uniqueid": uniqueid,
        "mac": mac,
        "hostname": hostname,
        "cpu": cpu,
        "memory": memory,
        "FullSync": 1 if fullsync else 0,
        "IdDeviceType": device_type,
        "version": VERSION,
        "IdSync": config['IdSync']
    }

    if fullsync:
        data["processes"] = get_processes()
        data["packages"] = get_installed_packages()
        data["updates"] = get_pending_updates()

    return data

def main():
    config = load_config()
    if 'IdSync' not in config:
        return

    log_enabled = config.get('Log', '0') == '1'
    write_log("Agente iniciado", log_enabled)

    while True:
        current_time = int(time.time())
        fullsync = (current_time % 3600) < 5
        payload = build_payload(config, fullsync)
        try:
            headers = {'Content-Type': 'application/json'}
            response = requests.post(API_URL, headers=headers, json=payload)
            write_log(f"Sync enviada (Full: {payload['FullSync']}) - Status: {response.status_code}", log_enabled)
        except Exception as e:
            write_log(f"Erro ao enviar dados: {e}", log_enabled)

        time.sleep(300)

if __name__ == "__main__":
    main()
