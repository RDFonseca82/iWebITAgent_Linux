#!/usr/bin/env python3

import os, sys, time, socket, json, uuid, subprocess, platform
import psutil, requests, netifaces
from datetime import datetime

# +++ CONFIGURAÇÃO +++
API_URL = "https://agent.iwebit.app/scripts/script_Linux.php"
AGENT_VERSION = "1.0.0.0"
INTERVAL_MINIMAL = 300    # 5 min
INTERVAL_FULL = 3600      # 60 min
UNIQUEID_FILE = "/etc/sync_agent_id"
IDSYNC_FILE = "/etc/sync_agent_idsync"
# +++ FIM CONFIGURAÇÃO +++

def get_user_input_idsync():
    if os.geteuid() != 0:
        print("Execute como root para salvar o IdSync."); sys.exit(1)
    if os.path.exists(IDSYNC_FILE):
        return open(IDSYNC_FILE).read().strip()
    IdSync = input("Digite o IdSync (identificador do cliente): ").strip()
    open(IDSYNC_FILE, "w").write(IdSync)
    return IdSync

def get_unique_id():
    if os.path.exists(UNIQUEID_FILE):
        return open(UNIQUEID_FILE).read().strip()
    uid = str(uuid.uuid4()); open(UNIQUEID_FILE, "w").write(uid)
    return uid

def get_mac_address():
    for iface in netifaces.interfaces():
        try:
            a = netifaces.ifaddresses(iface).get(netifaces.AF_LINK, [{}])[0].get('addr', '')
            if a and len(a.split(":")) == 6 and a != "00:00:00:00:00:00":
                return a
        except: pass
    return ""

def get_process_list():
    return [{"pid": p.info["pid"], "name": p.info["name"]} 
            for p in psutil.process_iter(attrs=["pid", "name"]) if p.info.get("name")]

def get_distribution():
    try:
        import distro
        return distro.name(pretty=True)
    except:
        return platform.platform()

def get_network_info():
    info = {"default_gateway": None, "dns": [], "interfaces": {}}
    try:
        gw = netifaces.gateways().get('default', {}).get(netifaces.AF_INET, [None])[0]
        info["default_gateway"] = gw
    except: pass
    try:
        with open('/etc/resolv.conf') as f:
            info["dns"] = [l.split()[1] for l in f if l.startswith("nameserver")]
    except: pass
    for iface in netifaces.interfaces():
        addrs = netifaces.ifaddresses(iface)
        ipv4 = addrs.get(netifaces.AF_INET, [{}])[0].get('addr')
        mac = addrs.get(netifaces.AF_LINK, [{}])[0].get('addr')
        if ipv4 or mac:
            info["interfaces"][iface] = {"ipv4": ipv4, "mac": mac}
    return info

def get_storage_info():
    parts = []
    for part in psutil.disk_partitions(all=False):
        try:
            u = psutil.disk_usage(part.mountpoint)
            parts.append({"device": part.device, "mountpoint": part.mountpoint, "fstype": part.fstype,
                          "total_gb": round(u.total/(1024**3),2), "used_gb": round(u.used/(1024**3),2),
                          "percent_used": u.percent})
        except: pass
    return parts

def check_firewall():
    try:
        o = subprocess.run(["ufw", "status"], stdout=subprocess.PIPE, text=True).stdout
        if "Status: active" in o: return "ufw active"
    except: pass
    try:
        if subprocess.run(["iptables","-L"], stdout=subprocess.PIPE).returncode == 0:
            return "iptables configured"
    except: pass
    return "none"

def check_ssh():
    try:
        o = subprocess.run(["ss","-tlnp"], stdout=subprocess.PIPE, text=True).stdout
        if "ssh" in o or ":22 " in o: return "ssh active"
    except: pass
    return "ssh not active"

def list_services():
    out = []
    try:
        o = subprocess.run(["systemctl","list-units","--type=service","--state=running","--no-legend","--no-pager"],
                            stdout=subprocess.PIPE, text=True).stdout
        for L in o.splitlines():
            s = L.split()[0]
            if s: out.append(s)
    except: pass
    return out

def list_installed_packages():
    try:
        o = subprocess.run(["dpkg-query","-W","-f=${binary:Package} ${Version}\n"], stdout=subprocess.PIPE, text=True)
        return o.stdout.splitlines()
    except:
        try:
            o = subprocess.run(["rpm","-qa"], stdout=subprocess.PIPE, text=True)
            return o.stdout.splitlines()
        except:
            return []

def list_pending_updates():
    try:
        o = subprocess.run(["apt","list","--upgradeable"], stdout=subprocess.PIPE, text=True).stdout
        return [l.split()[0]+" → "+l.split()[1] for l in o.splitlines() if "/upgradeable" in l]
    except: return []

def detect_device_type():
    try:
        out = subprocess.run(['systemctl', 'get-default'], stdout=subprocess.PIPE, text=True).stdout.strip()
        if out == "graphical.target":
            return 92  # workstation
        else:
            return 109  # servidor
    except:
        return 109  # fallback

def get_minimal(uniqueid, idsync):
    return {
        "uniqueid": uniqueid,
        "IdSync": idsync,
        "agent_version": AGENT_VERSION,
        "IdDeviceType": detect_device_type(),
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "FullSync": 0,
        "timestamp": datetime.utcnow().isoformat()
    }

def get_full(uniqueid, idsync):
    return {
        "uniqueid": uniqueid,
        "IdSync": idsync,
        "agent_version": AGENT_VERSION,
        "IdDeviceType": detect_device_type(),
        "hostname": socket.gethostname(),
        "ip_address": socket.gethostbyname(socket.gethostname()),
        "mac_address": get_mac_address(),
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent,
        "user": os.getenv("USER") or os.getenv("LOGNAME") or "",
        "timestamp": datetime.utcnow().isoformat(),
        "FullSync": 1,
        "processes": get_process_list(),
        "cpu_model": platform.processor(),
        "cpu_cores": psutil.cpu_count(logical=True),
        "kernel_version": platform.release(),
        "distribution": get_distribution(),
        "uptime_seconds": float(open('/proc/uptime').read().split()[0]) if os.path.exists('/proc/uptime') else None,
        "network": get_network_info(),
        "storage": get_storage_info(),
        "firewall_status": check_firewall(),
        "ssh_status": check_ssh(),
        "services": list_services(),
        "installed_packages": list_installed_packages(),
        "pending_updates": list_pending_updates()
    }

def send(data):
    try:
        resp = requests.post(API_URL, json=data, headers={"Content-Type":"application/json"}, timeout=30)
        resp.raise_for_status()
        print(f"[{datetime.now()}] Sent FullSync={data.get('FullSync')}")
    except Exception as e:
        print(f"Erro ao enviar: {e}")

def main():
    uid = get_unique_id(); idsync = get_user_input_idsync()
    last_full = last_min = time.time()
    while True:
        now = time.time()
        if now - last_full >= INTERVAL_FULL:
            send(get_full(uid, idsync)); last_full = now; last_min = now
        elif now - last_min >= INTERVAL_MINIMAL:
            send(get_minimal(uid, idsync)); last_min = now
        time.sleep(1)

if __name__=="__main__":
    main()
            
