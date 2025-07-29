#!/usr/bin/env python3

import os
import sys
import time
import json
import logging
import requests
import socket
import subprocess
import hashlib
from datetime import datetime

# ====================
# Configurações
# ====================
API_URL = "https://agent.iwebit.app/scripts/script_Linux.php"
UNIQUE_ID_FILE = "/etc/iwebit_agent_id"
CONFIG_FILE = "/etc/iwebit_agent.conf"
VERSION = "1.0.0.0"
LOG = 1  # 1 = ativo, 0 = desativo
LOG_FILE = "/var/log/iwebit_agent.log"

# ====================
# Logging
# ====================
if LOG:
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logging.debug("Logging ativado.")
else:
    logging.basicConfig(level=logging.CRITICAL)

def log_info(msg): logging.info(msg) if LOG else None
def log_error(msg): logging.error(msg) if LOG else None

# ====================
# Funções Utilitárias
# ====================
def get_hostname():
    try:
        return socket.gethostname()
    except:
        return "unknown"

def get_idsync():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                for line in f:
                    if line.startswith("IdSync="):
                        return line.strip().split("=")[1]
    except Exception as e:
        log_error(f"Erro ao ler IdSync: {e}")
    return "0"

def generate_unique_id():
    try:
        hostname = get_hostname()
        idsync = get_idsync()
        combined = f"{idsync}-{hostname}"
        unique_id = hashlib.sha256(combined.encode()).hexdigest()
        return unique_id
    except Exception as e:
        log_error(f"Erro ao gerar unique ID: {e}")
        return "unknown"

def get_mac_address():
    try:
        result = subprocess.check_output("ip link show", shell=True).decode()
        for line in result.splitlines():
            if "link/ether" in line:
                return line.strip().split()[1]
    except Exception as e:
        log_error(f"Erro ao obter MAC address: {e}")
    return "00:00:00:00:00:00"

def get_cpu_mem():
    try:
        cpu = subprocess.check_output("top -bn1 | grep '%Cpu'", shell=True).decode()
        mem = subprocess.check_output("free -m", shell=True).decode()
        return {"cpu": cpu.strip(), "memory": mem.strip()}
    except Exception as e:
        log_error(f"Erro ao obter CPU/Memória: {e}")
        return {}

def get_processes():
    try:
        ps = subprocess.check_output("ps aux", shell=True).decode()
        return ps.strip()
    except Exception as e:
        log_error(f"Erro ao obter processos: {e}")
        return ""

def get_installed_packages():
    try:
        result = subprocess.check_output("dpkg -l", shell=True).decode()
        return result
    except Exception as e:
        log_error(f"Erro ao obter pacotes: {e}")
        return ""

def get_pending_updates():
    try:
        result = subprocess.check_output("apt list --upgradable 2>/dev/null", shell=True).decode()
        return result
    except Exception as e:
        log_error(f"Erro ao obter atualizações pendentes: {e}")
        return ""

def is_server():
    try:
        result = subprocess.check_output("systemctl list-units --type=service", shell=True).decode()
        return "apache2" in result or "nginx" in result or "mysql" in result
    except:
        return False

# ====================
# Função principal
# ====================
def sync(full_sync=False):
    try:
        unique_id = generate_unique_id()
        mac = get_mac_address()
        cpu_mem = get_cpu_mem()

        payload = {
            "uniqueid": unique_id,
            "mac": mac,
            "hostname": get_hostname(),
            "cpu": cpu_mem.get("cpu", ""),
            "memory": cpu_mem.get("memory", ""),
            "FullSync": 1 if full_sync else 0,
            "IdDeviceType": 109 if is_server() else 92,
            "version": VERSION,
            "IdSync": get_idsync()
        }

        if full_sync:
            payload["processes"] = get_processes()
            payload["packages"] = get_installed_packages()
            payload["updates"] = get_pending_updates()

        log_info(f"Enviando dados: FullSync={payload['FullSync']}")
        response = requests.post(API_URL, data=payload, timeout=30)
        log_info(f"Resposta: {response.status_code} - {response.text.strip()}")
    except Exception as e:
        log_error(f"Erro durante sincronização: {e}")

# ====================
# Loop principal
# ====================
def main():
    counter = 0
    while True:
        full = (counter % 12 == 0)
        sync(full_sync=full)
        counter += 1
        time.sleep(300)

if __name__ == "__main__":
    main()
