#!/usr/bin/env python3
import subprocess
import hashlib
import socket
import requests
import json
import time
import os

URL = "https://agent.iwebit.app/scripts/script_Linux.php"
CONFIG_PATH = "/etc/iwebit_agent.conf"
LOG_FILE = "/var/log/iwebit_agent.log"

def log(msg):
    config = read_config()
    if config.get("Log", "0") == "1":
        with open(LOG_FILE, "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")

def read_config():
    config = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            for line in f:
                line=line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k,v = line.split("=",1)
                    config[k.strip()] = v.strip()
    return config

def get_hostname():
    return socket.gethostname()

def get_mac():
    try:
        # Pega o MAC da primeira interface ativa (não loopback)
        result = subprocess.run("ip link show", shell=True, capture_output=True, text=True)
        lines = result.stdout.splitlines()
        for i in range(len(lines)):
            if "state UP" in lines[i]:
                # MAC está na linha anterior: "link/ether XX:XX:XX:XX:XX:XX"
                if i>0:
                    mac_line = lines[i-1].strip()
                    if "link/ether" in mac_line:
                        return mac_line.split()[1]
    except Exception as e:
        log(f"Erro ao obter MAC: {e}")
    return "00:00:00:00:00:00"

def get_cpu():
    try:
        result = subprocess.run("top -bn1 | grep '%Cpu'", shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except:
        return ""

def get_memory():
    try:
        result = subprocess.run("free -m", shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except:
        return ""

def get_processes():
    try:
        result = subprocess.run("ps aux", shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except:
        return ""

def get_packages():
    try:
        result = subprocess.run("dpkg -l", shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except:
        return ""

def get_updates():
    try:
        result = subprocess.run("apt list --upgradable 2>/dev/null", shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except:
        return ""

def get_device_type():
    # Simples heurística para distinguir servidor ou workstation
    try:
        result = subprocess.run("hostnamectl", shell=True, capture_output=True, text=True)
        output = result.stdout.lower()
        if "server" in output or "virtual" in output:
            return 109
    except:
        pass
    return 92

def generate_uniqueid(idsync, hostname):
    base = idsync + hostname
    return hashlib.sha256(base.encode("utf-8")).hexdigest()

def send_data(data):
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(URL, data=json.dumps(data), headers=headers, timeout=15)
        log(f"Envio OK, resposta: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        log(f"Erro no envio: {e}")
        return False

def main():
    config = read_config()
    if "IdSync" not in config:
        print("Falta configuração IdSync em /etc/iwebit_agent.conf")
        return

    idsync = config["IdSync"]
    log_flag = config.get("Log", "0")

    hostname = get_hostname()
    mac = get_mac()
    device_type = get_device_type()
    uniqueid = generate_uniqueid(idsync, hostname)
    version = "1.0.0.0"

    while True:
        # Minimal sync (FullSync=0)
        data_minimal = {
            "uniqueid": uniqueid,
            "mac": mac,
            "hostname": hostname,
            "cpu": get_cpu(),
            "memory": get_memory(),
            "FullSync": 0,
            "IdDeviceType": device_type,
            "version": version,
            "IdSync": idsync
        }
        send_data(data_minimal)
        time.sleep(5 * 60)  # 5 minutos

        # Full sync (FullSync=1)
        data_full = data_minimal.copy()
        data_full["FullSync"] = 1
        data_full["processes"] = get_processes()
        data_full["packages"] = get_packages()
        data_full["updates"] = get_updates()

        send_data(data_full)
        time.sleep(55 * 60)  # 55 minutos para totalizar 60 minutos entre full syncs

if __name__ == "__main__":
    main()
