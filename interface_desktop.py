import os
import time
import webbrowser
import threading
import subprocess
import sys
from pycloudflared import try_cloudflare

# Tenta importar o app Flask do arquivo principal
try:
    from app import app, socketio, BASE_DIR
except ImportError as e:
    print(f"Erro ao importar o núcleo JARVIS: {e}")
    input("Pressione ENTER para sair...")
    sys.exit(1)

def open_browser():
    """Aguarda o servidor iniciar e abre o navegador em modo APP"""
    print("[INTERFACE] Aguardando servidor iniciar...")
    time.sleep(3) # Espera técnica
    
    url = "http://127.0.0.1:5000"
    
    # Tenta encontrar o Chrome ou Edge para abrir em modo 'app' (sem barra de endereços)
    # Isso dá a sensação de programa nativo
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    ]
    
    browser_path = None
    for path in chrome_paths:
        if os.path.exists(path):
            browser_path = path
            break
            
    if browser_path:
        print(f"[INTERFACE] Abrindo via: {browser_path}")
        try:
            subprocess.Popen([browser_path, f"--app={url}", "--start-maximized"])
        except Exception as e:
            print(f"[AVISO] Falha ao abrir modo app: {e}. Usando navegador padrão.")
            webbrowser.open(url)
    else:
        webbrowser.open(url)

if __name__ == '__main__':
    print("=========================================")
    print("   JARVIS - INTERFACE DE COMANDO TOTAL")
    print("=========================================")
    print("Iniciando cérebro e interface gráfica...")
    
    # Inicia a thread que abre o navegador
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Inicia o servidor Flask (Bloqueante)
    # allow_unsafe_werkzeug=True permite rodar em ambientes de dev/prod locais sem erro
    try:
        socketio.run(app, debug=False, port=5000, host='0.0.0.0', allow_unsafe_werkzeug=True)
    except Exception as e:
        print(f"ERRO FATAL: {e}")
        input("Pressione ENTER para fechar...")
