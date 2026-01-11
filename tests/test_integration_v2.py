import socketio
import time
import subprocess
import sys
import os
import requests
from threading import Thread

# Configuração
URL = 'http://127.0.0.1:5000'
sio = socketio.Client()
server_process = None

def is_server_running():
    try:
        requests.get(URL, timeout=1)
        return True
    except:
        return False

def start_server():
    global server_process
    print("[TESTE] Iniciando servidor app.py...")
    # Configura variáveis de ambiente para o teste
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    
    server_process = subprocess.Popen(
        [sys.executable, "app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )
    
    # Aguarda o servidor estar pronto lendo a saída
    start_time = time.time()
    while time.time() - start_time < 20:
        line = server_process.stdout.readline()
        if line:
            print(f"[SERVER LOG] {line.strip()}")
            if "Running on" in line or "Aguardando comandos" in line:
                print("[TESTE] Servidor detectado online!")
                return True
    return False

@sio.event
def connect():
    print("[SOCKET] Conectado!")
    msg = "Qual é o seu modelo de IA atual e o que você pode fazer?"
    print(f"[SOCKET] Enviando: '{msg}'")
    sio.emit('fala_usuario', {'text': msg})

@sio.event
def bot_msg(data):
    print("\n" + "="*40)
    print(f"[RESPOSTA JARVIS]: {data.get('data')}")
    print("="*40 + "\n")
    sio.disconnect()

@sio.event
def disconnect():
    print("[SOCKET] Desconectado.")

def run_test():
    if not is_server_running():
        if not start_server():
            print("[ERRO] Não foi possível iniciar o servidor.")
            return

    try:
        sio.connect(URL, wait_timeout=10)
        sio.wait()
    except Exception as e:
        print(f"[ERRO SOCKET] {e}")
    finally:
        if server_process:
            print("[TESTE] Encerrando servidor de teste...")
            server_process.terminate()

if __name__ == "__main__":
    run_test()
