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
import netifaces

from datetime import datetime

# =================== CONFIG ===================
CONFIG_FILE = '/opt/iwebit_agent/iwebit_agent.conf'
# UNIQUEID_FILE = '/opt/iwebit_agent/uniqueid.conf'
VERSION = '1.0.38.1'
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
        # Verifica se está em ambiente gráfico
        has_gui = any([
            os.path.exists('/usr/bin/startx'),
            os.path.exists('/usr/bin/gnome-shell'),
            os.path.exists('/usr/bin/startplasma-x11'),
            os.path.exists('/usr/bin/lightdm'),
            os.path.exists('/usr/bin/gdm'),
            os.path.exists('/usr/bin/sddm'),
            os.environ.get('XDG_SESSION_TYPE') in ['x11', 'wayland'],
        ])

        return 92 if has_gui else 109  # 92 = Desktop, 109 = Server
    except:
        return 92  # Assumir Desktop por padrão


def get_physical_memory_info():
    try:
        output = subprocess.check_output(['dmidecode', '--type', '17'], text=True, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return []

    memory_blocks = output.split("Memory Device")
    memories = []

    def sanitize(value):
        return None if not value or value.strip().lower() == "unknown" else value.strip()

    for block in memory_blocks:
        if "Size: No Module Installed" in block:
            continue

        def extract(field):
            match = re.search(rf"{field}:\s*(.*)", block)
            return sanitize(match.group(1)) if match else None

        memory_info = {
            "BankLocator": extract("Bank Locator"),
            "Size": extract("Size"),
            "Speed": extract("Speed"),
            "ConfiguredClockSpeed": extract("Configured Clock Speed"),
            "Manufacturer": extract("Manufacturer"),
            "PartNumber": extract("Part Number"),
            "SerialNumber": extract("Serial Number")
        }

        memories.append(memory_info)

    return memories




def get_disk_info():
    disks = []
    partitions = psutil.disk_partitions(all=False)

    for part in partitions:
        try:
            usage = psutil.disk_usage(part.mountpoint)

            # Verificar se está encriptado
            try:
                lsblk_output = subprocess.check_output(['lsblk', '-no', 'TYPE', part.device], text=True).strip()
                encrypted = 'crypt' in lsblk_output or 'luks' in lsblk_output.lower()
            except Exception:
                encrypted = False

            # Buscar LABEL e UUID com blkid
            label = None
            uuid = None
            try:
                blkid_output = subprocess.check_output(['blkid', part.device], text=True).strip()
                for entry in blkid_output.split():
                    if entry.startswith("LABEL="):
                        label = entry.split('=')[1].strip('"')
                    elif entry.startswith("UUID="):
                        uuid = entry.split('=')[1].strip('"')
            except Exception:
                pass

            # Detectar se é SSD ou HDD (via /sys/block/*/queue/rotational)
            drive_type = "Unknown"
            try:
                base_device = os.path.basename(part.device).rstrip("0123456789")
                rotational_path = f"/sys/block/{base_device}/queue/rotational"
                if os.path.exists(rotational_path):
                    with open(rotational_path, 'r') as f:
                        is_rotational = f.read().strip()
                        drive_type = "HDD" if is_rotational == "1" else "SSD"
            except Exception:
                pass

            disks.append({
                'Device': part.device,
                'MountPoint': part.mountpoint,
                'FileSystem': part.fstype,
                'TotalSizeGB': round(usage.total / (1024 ** 3), 2),
                'UsedGB': round(usage.used / (1024 ** 3), 2),
                'FreeGB': round(usage.free / (1024 ** 3), 2),
                'PercentUsed': usage.percent,
                'Encrypted': encrypted,
                'Label': label,
                'UUID': uuid,
                'DriveType': drive_type
            })

        except PermissionError:
            continue  # Ignorar partições sem permissão
        except Exception as e:
            print(f"Erro ao processar {part.device}: {e}")
            continue

    return disks


def get_network_interfaces_info():
    interfaces = psutil.net_if_addrs()
    gateways = netifaces.gateways()

    def get_gateway_for_interface(iface):
        default_gateways = gateways.get('default', {})
        gw = default_gateways.get(netifaces.AF_INET)
        if gw and gw[1] == iface:
            return gw[0]
        return None

    def dhcp_enabled(iface):
        try:
            output = subprocess.check_output(['ps', 'aux'], text=True)
            for line in output.splitlines():
                if 'dhclient' in line and iface in line:
                    return True
        except Exception:
            pass
        return False

    result = []

    for iface, addrs in interfaces.items():
        ip_address = None
        subnet_mask = None
        mac_address = None

        for addr in addrs:
            if addr.family == socket.AF_PACKET:  # MAC address (Linux)
                mac_address = addr.address
            elif addr.family == socket.AF_INET:  # IPv4
                ip_address = addr.address
                subnet_mask = addr.netmask

        gateway = get_gateway_for_interface(iface)
        dhcp = dhcp_enabled(iface)

        result.append({
            'Interface': iface,
            'IPAddress': ip_address,
            'SubnetMask': subnet_mask,
            'MacAddress': mac_address,
            'Gateway': gateway,
            'DHCPEnable': dhcp
        })

    return result


def is_reboot_pending():
    # Verifica se o sistema Linux tem um reboot pendente. Retorna True se sim, False se não.

    reboot_files = [
        "/var/run/reboot-required",                  # Debian/Ubuntu
        "/run/reboot-required",                      # Alguns derivados
        "/var/run/reboot-required.pkgs",             # Ubuntu (detalhe)
        "/var/run/yum.pid",                          # RedHat/CentOS (durante atualização)
        "/var/run/dnf.pid"                           # Fedora/RHEL (atualizações pendentes)
    ]

    for path in reboot_files:
        if os.path.exists(path):
            return True

    # systemd way (algumas distros modernas)
    try:
        with open("/proc/1/comm") as f:
            if f.read().strip() == "systemd":
                result = os.system("needs-restarting -r > /dev/null 2>&1")
                if result == 1:
                    return True
    except:
        pass

    return False



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


import subprocess
import re

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

            # Exemplo:
            # bash/jammy 5.1-6ubuntu1.1 amd64 [upgradable from: 5.1-6ubuntu1]
            parts = line.split()
            if len(parts) < 4:
                continue

            name = parts[0].split('/')[0]
            new_version = parts[1]
            architecture = parts[2]
            installed_version = None
            origin = None
            release_date = None
            description = None

            match = re.search(r'\[upgradable from: (.+)\]', line)
            if match:
                installed_version = match.group(1)

            try:
                apt_show = subprocess.check_output(
                    ['apt-cache', 'show', name],
                    stderr=subprocess.DEVNULL
                ).decode()

                origin_match = re.search(r'^Origin:\s*(.+)', apt_show, re.MULTILINE)
                date_match = re.search(r'^Date:\s*(.+)', apt_show, re.MULTILINE)
                desc_match = re.search(r'^Description(?:-en)?:\s*(.+)', apt_show, re.MULTILINE)

                origin = origin_match.group(1) if origin_match else None
                release_date = date_match.group(1) if date_match else None
                description = desc_match.group(1) if desc_match else None

            except:
                pass

            updates.append({
                "Name": name,
                "InstalledVersion": installed_version or "NULL",
                "NewVersion": new_version,
                "Architecture": architecture,
                "Origin": origin or "NULL",
                "ReleaseDate": release_date or "NULL",
                "Description": description or "NULL"
            })

    except Exception as e:
        updates.append({"Error": str(e)})

    return updates

    
def check_for_updates():
    try:
        # Buscar script remoto
        remote = requests.get(UPDATE_URL, timeout=10).text
        with open(SCRIPT_PATH, 'r') as f:
            local = f.read()

        if remote.strip() != local.strip():
            log(f"Update disponível {VERSION}. A atualizar...")

            # Atualizar script principal
            with open(SCRIPT_PATH, 'w') as f:
                f.write(remote)
            os.chmod(SCRIPT_PATH, 0o755)
            log("Script principal atualizado.")

            # Verificar se ambiente gráfico está presente
            is_graphical = os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")

            if is_graphical:
                log("Ambiente desktop detetado. A verificar GUI...")
                # URLs dos componentes GUI
                gui_files = {
                    "iwebit_gui.py": "https://raw.githubusercontent.com/RDFonseca82/iWebITAgent_Linux/main/iwebit_gui.py",
                    "assets/iwebit_online.png": "https://intranet.iwebit.app/winsrv/iwebit_online.png",
                    "assets/iwebit_offline.png": "https://intranet.iwebit.app/winsrv/iwebit_offline.png",
                    "assets/iwebit_inactive.png": "https://intranet.iwebit.app/winsrv/iwebit_inactive.png"
                }

                base_path = "/opt/iwebit_agent"
                for filename, url in gui_files.items():
                    local_path = os.path.join(base_path, filename)
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)
                    try:
                        content = requests.get(url, timeout=10).content
                        with open(local_path, "wb") as f:
                            f.write(content)
                        log(f"[GUI] Atualizado: {filename}")
                    except Exception as e:
                        log(f"[GUI] Falha ao atualizar {filename}: {e}")

            # Reiniciar o agente com novo script
            log("A reiniciar o agente...")
            os.execv("/usr/bin/python3", ['python3', SCRIPT_PATH])

    except Exception as e:
        log(f"Falha na verificação de atualizações: {e}")
        

def is_connected():
    try:
        subprocess.check_output(["ping", "-c", "1", "-W", "2", "iwebit.app"], stderr=subprocess.DEVNULL)
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

        # Verifica se a resposta é válida e em JSON
        try:
            data = response.json()
        except Exception:
            log("Nenhum script para executar.")
            return

        # Se não houver campo URL ou estiver vazio
        if not isinstance(data, dict) or 'URL' not in data or not data['URL']:
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

        if len(output) > 3000:
            output = output[:3000] + '... [truncado]'

        # Passo 4: Enviar resposta
        return_url = f'https://agent.iwebit.app/scripts/script_api.php?UniqueID={uniqueid}&ScriptRunned=1&Output={urllib.parse.quote_plus(output)}'
        log(f"Enviando saída do script para API. ({output})")
        requests.get(return_url, timeout=10)

        # Remover script após execução
        if script_path.startswith(script_dir):
            try:
                os.remove(script_path)
                log(f"Script removido após execução: {script_path}")
            except Exception as e:
                log(f"Erro ao remover script {script_path}: {e}")
        else:
            log(f"Caminho do script inválido, não removido: {script_path}")

    except Exception as e:
        log(f"Erro ao processar script remoto: {e}")




def check_and_run_updates():
    config = load_config()
    uniqueid = config.get('UniqueId', '0')    
    url = f"https://agent.iwebit.app/scripts/script_api.php?UniqueID={uniqueid}&LinuxUpdatesRun=1"
    try:
        response = requests.get(url, timeout=30)
        raw_data = response.text.strip()
        
        # Extrai cada bloco JSON separadamente com regex
        json_blocks = re.findall(r'\{.*?\}', raw_data)

        if not json_blocks:
            log("Nenhuma atualização Linux remota encontrada.")
            return

        log(f"{len(json_blocks)} atualizações remotas encontradas.")
        
        for block in json_blocks:
            try:
                update = json.loads(block)
                package = update.get("LinuxUpdateID")
                new_version = update.get("NewVersion")
                update_id = update.get("IdLinuxUpdateRun")

                log(f"Iniciando atualização do pacote '{package}' para versão '{new_version}'")

                # Tenta atualizar o pacote
                try:
                    result = subprocess.run(
                        ["apt-get", "install", "--only-upgrade", "-y", package],
                        capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        status = "Sucesso"
                        log(f"Atualização de '{package}' concluída com sucesso.")
                    else:
                        status = "Falhou"
                        log(f"Falha ao atualizar '{package}': {result.stderr.strip()}")
                except FileNotFoundError:
                    status = "Indisponivel"
                    log(f"Comando apt-get não disponível no sistema.")
                
                # Enviar resultado
                encoded_output = urllib.parse.quote_plus(status)
                response_url = (
                    f"https://agent.iwebit.app/scripts/script_api.php?"
                    f"UniqueID={uniqueid}&LinuxUpdateID={package}"
                    f"&NewVersion={urllib.parse.quote_plus(new_version)}"
                    f"&LinuxUpdatesRunned=1&Output={encoded_output}"
                )
                log(f"Enviando status '{status}' para API.")
                requests.get(response_url, timeout=20)

            except Exception as e:
                log(f"Erro ao processar bloco de atualização: {e}")
    except Exception as e:
        log(f"Erro ao verificar atualizações remotas: {e}")


def get_linux_errors_warnings(max_events=100):
    try:
        cmd = [
            "journalctl",
            "--no-pager",
            "-p", "3..4",
            "-n", str(max_events),
            "-o", "short-iso"
        ]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)

        events = []

        for line in result.stdout.splitlines():
            events.append({
                "Timestamp": line[:19],
                "Level": "ERROR/WARNING",
                "Message": line
            })

        return {
            "Source": "journalctl",
            "Events": events
        }

    except Exception as e:
        return {"Error": str(e)}


def get_kernel_events(max_events=50):
    cmd = [
        "journalctl",
        "--no-pager",
        "-k",
        "-n", str(max_events),
        "-o", "short-iso"
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)

    return {
        "Source": "Kernel",
        "Events": result.stdout.splitlines()
    }




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
        'Longitude': longitude,
        'RebootPending': is_reboot_pending()
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
            'CPU_Info': get_cpu_info(),
            'NetworkInfo': get_network_interfaces_info(),
            'DiskInfo': get_disk_info(),
            'MemoryInfo': get_physical_memory_info(),
            'RebootPending': is_reboot_pending(),
            'SystemErrorsWarnings': get_linux_errors_warnings(),
            'KernelEvents': get_kernel_events()           
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
            check_and_run_updates()
            last_remote_check = now

        check_for_updates()
        time.sleep(minimal_interval)
