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
import urllib.parse
import re
from datetime import datetime

# =================== CONFIG ===================
CONFIG_FILE = '/opt/iwebit_agent/iwebit_agent.conf'
# UNIQUEID_FILE = '/opt/iwebit_agent/uniqueid.conf'
VERSION = '1.0.20.1'
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

def get_cpu_info():
    info = {}

    try:
        # Arquitetura e bits
        info['Architecture'] = platform.machine()
        info['CPU_Bits'] = platform.architecture()[0]

        # Núcleos
        info['Physical_Cores'] = psutil.cpu_count(logical=False)
        info['Logical_Cores'] = psutil.cpu_count(logical=True)

        # Frequência
        freq = psutil.cpu_freq()
        if freq:
            info['CPU_Freq_Min_MHz'] = round(freq.min, 2)
            info['CPU_Freq_Max_MHz'] = round(freq.max, 2)
            info['CPU_Freq_Current_MHz'] = round(freq.current, 2)

        # Informações do /proc/cpuinfo
        with open('/proc/cpuinfo') as f:
            cpuinfo = f.read()

        # Primeiro processador listado
        first_proc = cpuinfo.split('\n\n')[0]

        # Modelo e fabricante
        model_match = re.search(r'model name\s+:\s+(.+)', first_proc)
        vendor_match = re.search(r'vendor_id\s+:\s+(.+)', first_proc)
        info['CPU_Model'] = model_match.group(1) if model_match else 'NULL'
        info['CPU_Vendor'] = vendor_match.group(1) if vendor_match else 'NULL'

        # Cache L2 ou L3 (opcional)
        cache_match = re.search(r'cache size\s+:\s+(.+)', first_proc)
        if cache_match:
            info['Cache'] = cache_match.group(1)

    except Exception as e:
        info['Error'] = str(e)

    return info

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
        return "NULL"

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
                    "InstallDate": "NULL"
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
                        "InstallDate": "NULL"
                    })
    except Exception as e:
        pass

    return software_list



def run_dmidecode(keyword):
    try:
        output = subprocess.check_output(['dmidecode', '-t', keyword], text=True, stderr=subprocess.DEVNULL)
        return output
    except subprocess.CalledProcessError:
        return ''
    except PermissionError:
        return 'Permission denied (requires sudo)'

def get_motherboard_info():
    output = run_dmidecode('baseboard')
    return {
        "Manufacturer": re.search(r'Manufacturer:\s*(.+)', output).group(1) if re.search(r'Manufacturer:\s*(.+)', output) else "NULL",
        "Model": re.search(r'Product Name:\s*(.+)', output).group(1) if re.search(r'Product Name:\s*(.+)', output) else "NULL",
        "SerialNumber": re.search(r'Serial Number:\s*(.+)', output).group(1) if re.search(r'Serial Number:\s*(.+)', output) else "NULL"
    }

def get_bios_info():
    output = run_dmidecode('bios')
    return {
        "BIOS_Manufacturer": re.search(r'Vendor:\s*(.+)', output).group(1) if re.search(r'Vendor:\s*(.+)', output) else "NULL",
        "BIOS_Version": re.search(r'Version:\s*(.+)', output).group(1) if re.search(r'Version:\s*(.+)', output) else "NULL",
        "BIOS_SerialNumber": re.search(r'Serial Number:\s*(.+)', output).group(1) if re.search(r'Serial Number:\s*(.+)', output) else "NULL",
        "BIOS_ReleaseDate": re.search(r'Release Date:\s*(.+)', output).group(1) if re.search(r'Release Date:\s*(.+)', output) else "NULL"
    }

def get_os_info():
    try:
        with open('/etc/os-release') as f:
            lines = f.readlines()
            info = {}
            for line in lines:
                if '=' in line:
                    k, v = line.strip().split('=', 1)
                    info[k] = v.strip('"')
            return {
                "OS_Name": info.get('PRETTY_NAME', 'NULL'),
                "OS_Version": info.get('VERSION', 'NULL'),
                "OS_ID": info.get('ID', 'NULL')
            }
    except:
        return {
            "OS_Name": platform.system(),
            "OS_Version": platform.version(),
            "OS_ID": "NULL"
        }

def get_bios_last_upgrade_date():
    try:
        output = subprocess.check_output(['stat', '/sys/class/dmi/id/bios_date'], text=True)
        match = re.search(r'Modify:\s(.+)', output)
        if match:
            return match.group(1)
    except:
        pass
    return "Unknown"


def get_pending_updates():
    updates = []

    try:
        output = subprocess.check_output(
            ['apt', 'list', '--upgradeable'],
            stderr=subprocess.DEVNULL
        ).decode().splitlines()

        for line in output:
            if not line or '/' not in line or line.startswith("Listing..."):
                continue

            # Exemplo de linha:
            # bash/jammy 5.1-6ubuntu1.1 amd64 [upgradable from: 5.1-6ubuntu1]
            parts = line.split()
            if len(parts) < 4:
                continue

            name = parts[0].split('/')[0]
            new_version = parts[1]
            architecture = parts[2]
            installed_version = None
            origin = None

            match = re.search(r'\[upgradable from: (.+)\]', line)
            if match:
                installed_version = match.group(1)

            # Pegar origem do repositório e data (limitado)
            try:
                apt_show = subprocess.check_output(['apt-cache', 'show', name], stderr=subprocess.DEVNULL).decode()
                origin_match = re.search(r'^Origin:\s*(.+)', apt_show, re.MULTILINE)
                date_match = re.search(r'^Date:\s*(.+)', apt_show, re.MULTILINE)

                origin = origin_match.group(1) if origin_match else None
                release_date = date_match.group(1) if date_match else None
            except:
                origin = None
                release_date = None

            updates.append({
                "Name": name,
                "InstalledVersion": installed_version or "NULL",
                "NewVersion": new_version,
                "Architecture": architecture,
                "Origin": origin or "NULL",
                "ReleaseDate": release_date or "NULL"
            })

    except Exception as e:
        updates.append({"Error": str(e)})

    return updates
    

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


def check_and_run_remote_scripts():
    config = load_config()
    uniqueid = config.get('UniqueId', '0')
    script_dir = '/opt/iwebit_agent/scripts'
    os.makedirs(script_dir, exist_ok=True)

    try:
        # Passo 1: Verifica se há script para executar
        check_url = f'https://agent.iwebit.app/scripts/script_api.php?UniqueID={uniqueid}&ScriptRun=1'
        response = requests.get(check_url, timeout=10)
        data = response.json()

        if 'URL' not in data or not data['URL']:
            log("Nenhum script remoto para executar.")
            return

        script_url = data['URL']
        script_name = os.path.basename(urllib.parse.urlparse(script_url).path)
        script_path = os.path.join(script_dir, script_name)

        # Passo 2: Baixar script
        log(f"Baixando script de: {script_url}")
        script_resp = requests.get(script_url, timeout=10)
        with open(script_path, 'w') as f:
            f.write(script_resp.text)
        os.chmod(script_path, 0o755)

        # Passo 3: Executar script
        log(f"Executando script: {script_path}")
        result = subprocess.run([script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
        output = result.stdout.decode(errors='ignore').strip()

        # Limitar tamanho da resposta, se necessário
        if len(output) > 3000:
            output = output[:3000] + '... [truncado]'

        # Passo 4: Enviar resposta
        encoded_output = urllib.parse.quote_plus(output)
        return_url = f'https://agent.iwebit.app/scripts/script_api.php?UniqueID={uniqueid}&ScriptRunned=1&Output={encoded_output}'
        log(f"Enviando saída do script para API.")
        requests.get(return_url, timeout=10)

    except Exception as e:
        log(f"Erro ao processar script remoto: {e}")



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
            'PendingUpdates': get_pending_updates(),
            'BiosUpgrade': get_bios_last_upgrade_date(),
            'OS_Info': get_os_info(),
            'Bios_Info': get_bios_info(),
            'MB_Info': get_motherboard_info(),
            'CPU_Info': get_cpu_info()
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
            check_and_run_remote_scripts()
            last_remote_check = now

        check_for_updates()
        time.sleep(minimal_interval)
