import socket
import ssdpy
import json

# Portas comuns de TV Samsung
PORTS = [8001, 8002, 9110, 9119, 9197, 7678]

def check_port(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    result = sock.connect_ex((ip, port))
    sock.close()
    return result == 0

def scan_network():
    print("--- INICIANDO SCAN DE REDE (SSDP) ---")
    client = ssdpy.SSDPClient()
    devices = client.m_search(st='ssdp:all')
    
    samsung_devices = []
    
    for device in devices:
        usn = device.get('usn', '').lower()
        server = device.get('server', '').lower()
        location = device.get('location', '')
        
        if 'samsung' in usn or 'tizen' in server or 'samsung' in server:
            ip = location.split('//')[1].split(':')[0]
            print(f"[ENCONTRADO] Samsung Device em {ip}")
            
            open_ports = []
            for p in PORTS:
                if check_port(ip, p):
                    open_ports.append(p)
            
            print(f"   -> Portas Abertas: {open_ports}")
            samsung_devices.append({'ip': ip, 'ports': open_ports})

    # Se SSDP falhar, tenta scan direto no IP conhecido
    ip_conhecido = "192.168.3.140"
    print(f"\n--- VERIFICAÇÃO DIRETA NO IP {ip_conhecido} ---")
    open_ports = []
    for p in PORTS:
        if check_port(ip_conhecido, p):
            open_ports.append(p)
    print(f"   -> Portas Abertas: {open_ports}")
    
    if not samsung_devices and open_ports:
        samsung_devices.append({'ip': ip_conhecido, 'ports': open_ports})

    return samsung_devices

if __name__ == "__main__":
    scan_network()
