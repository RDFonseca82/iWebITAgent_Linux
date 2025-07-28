#!/usr/bin/env python3

import os
import sys
import time
import socket
import json
import uuid
import subprocess
import platform
import psutil
import requests
import netifaces
from datetime import datetime

API_URL = "https://agent.iwebit.app/scripts/script_Linux.php"

INTERVAL_MINIMAL = 300    # 5 minutos
INTERVAL_FULL = 3600      # 60 minutos

UNIQUEID_FILE = "/etc/sync_agent_id"
IDSYNC_FILE = "/etc/sync_agent_idsync"

def get_user_input_idsync():
    if os.geteuid() != 0:
        print("Execute a instalação como root para salvar o IdSync.")
        sys.exit(1)
    if os.path.exists(IDSYNC_FILE):
        with open(IDSYNC_FILE, "r") as f:
            return f.read().strip()
    else:
        IdSync = input("Digite o IdSync para esta máquina (identificador do cliente): ").strip()
        with open(IDSYNC_FILE, "w") as f:
            f.write(IdSync)
        return IdSync

def get_unique_id():
    if os.path.exists(UNIQUEID_FILE):
        with open(UNIQUEID_FILE, "r") as f:
            return f.read().strip()
    else:
        unique_id = str(uuid.uuid4())
        with open(UNIQUEID_FILE, "w") as f:
            f.write(unique_id)
        return unique_id

def get_mac_address():
    for iface in netifaces.interfaces():
        try:
            addrs = netifaces.ifaddresses(iface)
            if netifaces.AF_LINK in addrs:
                addr = addrs[netifaces.AF_LINK][0]['addr']
                if addr and len(addr.split(":")) == 6 and addr != "00:00:00:00:00:00":
                    return addr
        except:
            continue
    return "00:00:00:00:00:00"

def get_process_list():
    procs = []
    for p in psutil.process_iter(attrs=["pid", "name"]):
        try:
            procs.append({"pid": p.info["pid"], "name": p.info["name"]})
        except:
            continue
    return procs

def get_cpu_info():
    try:
        return platform.processor()
    except:
        return ""

def get_cpu_count():
    return psutil.cpu_count(logical=True)

def get_kernel_version():
    return platform.release()

def get_distribution():
    try:
        import distro
        return distro.name(pretty=True)
    except ImportError:
        try:
            return " ".join(platform.linux_distribution())
        except:
            return "Unknown"

def get_uptime():
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
            return uptime_seconds
    except:
        return None

def get_network_info():
    info = {}
    try:
        gateways = netifaces.gateways()
        default_gateway = gateways.get('default', {}).get(netifaces.AF_INET, [None])[0]
        info['default_gateway'] = default_gateway
    except:
        info['default_gateway'] = None

    try:
        dns = []
        with open('/etc/resolv.conf', 'r') as f:
            for line in f:
                if line.startswith("nameserver"):
                    dns.append(line.split()[1])
        info['dns'] = dns
    except:
        info['dns'] = []

    try:
        interfaces = {}
        for iface in netifaces.interfaces():
            addresses = netifaces.ifaddresses(iface)
            ipv4 = addresses.get(netifaces.AF_INET, [{}])[0].get('addr', None)
            mac = addresses.get(netifaces.AF_LINK, [{}])[0].get('addr', None)
            if ipv4 or mac:
                interfaces[iface] = {"ipv4": ipv4, "mac": mac}
        info['interfaces'] = interfaces
    except:
        info['interfaces'] = {}

    return info

def get_storage_info():
    partitions = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            partitions.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total_gb": round(usage.total / (1024 ** 3), 2),
                "used_gb": round(usage.used / (1024 ** 3), 2),
                "percent_used": usage.percent
            })
        except:
            continue
    return partitions

def check_firewall():
    try:
        res = subprocess.run(['ufw', 'status'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if "Status: active" in res.stdout:
            return "ufw active"
    except:
        pass
    try:
        res = subprocess.run(['iptables', '-L'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            return "iptables configured"
    except:
        pass
    return "no firewall detected"

def check_ssh():
    try:
        res = subprocess.run(['ss', '-tlnp'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if 'ssh' in res.stdout or ':22 ' in res.stdout:
            return "ssh active"
    except:
        pass
    return "ssh not active"

def list_services():
    services = []
    try:
        res = subprocess.run(['systemctl', 'list-units', '--type=service', '--state=running', '--no-pager', '--no-legend'], stdout=subprocess.PIPE, text=True)
        for line in res.stdout.strip().split('\n'):
            parts = line.split()
            if parts:
                services.append(parts[0])
    except:
        pass
    return services

def list_packages():
    packages = []
    try:
        res = subprocess.run(['dpkg-query', '-W', '-f=${binary:Package}\n'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            packages = res.stdout.strip().split('\n')
    except:
        pass

    if not packages:
        try:
            res = subprocess.run(['rpm', '-qa'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0:
                packages = res.stdout.strip().split('\n')
        except:
            pass
    return packages

def get_minimal_data(uniqueid, idsync):
    return {
        "uniqueid": uniqueid,
        "IdSync": idsync,
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "FullSync": 0,
        "timestamp": datetime.utcnow().isoformat()
    }

def get_full_data(uniqueid, idsync):
    data = {
        "uniqueid": uniqueid,
        "IdSync": idsync,
        "hostname": socket.gethostname(),
        "ip_address": socket.gethostbyname(socket.gethostname()),
        "mac_address": get_mac_address(),
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent,
        "user": os.getenv("USER") or os.getenv("LOGNAME") or "unknown",
        "timestamp": datetime.utcnow().isoformat(),
        "FullSync": 1,

        "processes": get_process_list(),
        "cpu_model": get_cpu_info(),
        "cpu_cores": get_cpu_count(),
        "kernel_version": get_kernel_version(),
        "distribution": get_distribution(),
        "uptime_seconds": get_uptime(),
        "network": get_network_info(),
        "storage": get_storage_info(),
        "firewall_status": check_firewall(),
        "ssh_status": check_ssh(),
        "services": list_services(),
        "packages": list_packages()
    }
    return data

def send_info(data):
    try:
        headers = {"Content-Type": "application/json"}
        response = requests.post(API_URL, data=json.dumps(data), headers=headers, timeout=30)
        response.raise_for_status()
        print(f"[{datetime.now()}] Dados enviados com sucesso. FullSync={data.get('FullSync', 'N/A')}")
    except Exception as e:
        print(f"[{datetime.now()}] Falha ao enviar dados: {e}")

def main():
    uniqueid = get_unique_id()
    idsync = get_user_input_idsync()

    last_fullsync = 0
    last_minimal = 0

    while True:
        now = time.time()

        if now - last_fullsync >= INTERVAL_FULL:
            print("Executando sincronização FULL.")
            data = get_full_data(uniqueid, idsync)
            send_info(data)
            last_fullsync = now
            last_minimal = now  # evita enviar minimal logo após full

        elif now - last_minimal >= INTERVAL_MINIMAL:
            print("Executando sincronização MINIMAL.")
            data = get_minimal_data(uniqueid, idsync)
            send_info(data)
            last_minimal = now

        time.sleep(1)

if __name__ == "__main__":
    main()
