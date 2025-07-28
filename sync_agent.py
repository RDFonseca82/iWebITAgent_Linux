#!/usr/bin/env python3
import os
import time
import json
import uuid
import psutil
import netifaces
import platform
import socket
import subprocess
import requests
import distro

API_URL = "https://agent.iwebit.app/scripts/script_Linux.php"
SYNC_FILE = "/etc/sync_agent_uniqueid"
IDSYNC_FILE = "/etc/sync_agent_idsync"
VERSION_FILE = "/etc/iwebit_agent_version"
GITHUB_VERSION_URL = "https://raw.githubusercontent.com/RDFonseca82/iWebITAgent_Linux/main/version.txt"
AGENT_VERSION = "1.0.0.0"

def get_unique_id():
    if os.path.exists(SYNC_FILE):
        with open(SYNC_FILE, 'r') as f:
            return f.read().strip()
    unique_id = str(uuid.uuid4())
    with open(SYNC_FILE, 'w') as f:
        f.write(unique_id)
    return unique_id

def get_idsync():
    if os.path.exists(IDSYNC_FILE):
        with open(IDSYNC_FILE, 'r') as f:
            return f.read().strip()
    return ""

def get_mac_address():
    for iface in netifaces.interfaces():
        addrs = netifaces.ifaddresses(iface)
        if netifaces.AF_LINK in addrs:
            for addr in addrs[netifaces.AF_LINK]:
                mac = addr.get('addr')
                if mac and mac != '00:00:00:00:00:00':
                    return mac
    return "00:00:00:00:00:00"

def get_cpu_usage():
    return psutil.cpu_percent(interval=1)

def get_memory_usage():
    mem = psutil.virtual_memory()
    return mem.percent

def get_process_list():
    return [proc.info for proc in psutil.process_iter(['pid', 'name'])]

def get_installed_packages():
    try:
        output = subprocess.check_output(['dpkg', '-l']).decode()
        return output
    except Exception as e:
        return str(e)

def get_pending_updates():
    try:
        output = subprocess.check_output(['apt', 'list', '--upgradable']).decode()
        return output
    except Exception as e:
        return str(e)

def get_device_type():
    info = platform.uname()
    if 'server' in info.node.lower():
        return 109
    return 92

def get_network_info():
    interfaces = {}
    for iface in netifaces.interfaces():
        iface_data = {}
        addrs = netifaces.ifaddresses(iface)
        if netifaces.AF_INET in addrs:
            iface_data['ip'] = addrs[netifaces.AF_INET][0]['addr']
        if netifaces.AF_LINK in addrs:
            iface_data['mac'] = addrs[netifaces.AF_LINK][0]['addr']
        interfaces[iface] = iface_data
    return interfaces

def get_storage_info():
    disks = []
    for part in psutil.disk_partitions():
        usage = psutil.disk_usage(part.mountpoint)
        disks.append({
            'device': part.device,
            'mountpoint': part.mountpoint,
            'fstype': part.fstype,
            'total': usage.total,
            'used': usage.used,
            'free': usage.free,
            'percent': usage.percent
        })
    return disks

def get_firewall_status():
    try:
        output = subprocess.check_output(['ufw', 'status'], stderr=subprocess.DEVNULL).decode()
        return output
    except:
        return "ufw not installed or inaccessible"

def get_ssh_status():
    try:
        output = subprocess.check_output(['systemctl', 'is-active', 'ssh'], stderr=subprocess.DEVNULL).decode().strip()
        return output
    except:
        return "unknown"

def check_for_update():
    try:
        remote_version = requests.get(GITHUB_VERSION_URL, timeout=5).text.strip()
        if remote_version > AGENT_VERSION:
            os.system("curl -sSL https://raw.githubusercontent.com/RDFonseca82/iWebITAgent_Linux/main/iwebit_agent.py -o /usr/local/bin/iwebit_agent.py")
            os.system("systemctl restart iwebit_agent")
    except:
        pass

def sync(full=False):
    data = {
        "uniqueid": get_unique_id(),
        "idsync": get_idsync(),
        "mac_address": get_mac_address(),
        "cpu_usage": get_cpu_usage(),
        "memory_usage": get_memory_usage(),
        "fullsync": 1 if full else 0,
        "iddevicetype": get_device_type(),
        "agent_version": AGENT_VERSION,
    }

    if full:
        data.update({
            "process_list": json.dumps(get_process_list()),
            "network_info": json.dumps(get_network_info()),
            "storage_info": json.dumps(get_storage_info()),
            "firewall_status": get_firewall_status(),
            "ssh_status": get_ssh_status(),
            "installed_packages": get_installed_packages(),
            "pending_updates": get_pending_updates(),
        })

    try:
        requests.post(API_URL, data=data, timeout=10)
    except Exception as e:
        pass

def main():
    counter = 0
    while True:
        full = counter % 12 == 0
        check_for_update()
        sync(full=full)
        counter += 1
        time.sleep(300)  # 5 minutes

if __name__ == "__main__":
    main()
