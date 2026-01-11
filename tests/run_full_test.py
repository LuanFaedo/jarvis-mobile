import subprocess
import time
import os
import signal
import sys

print("--- INICIANDO SERVIDOR ---")
# Inicia app.py em background
server = subprocess.Popen([sys.executable, "app.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

try:
    print("Aguardando 10s para inicialização...")
    time.sleep(10)
    
    print("--- RODANDO TESTE DE SOCKET ---")
    res = subprocess.run([sys.executable, "test_socket.py"], capture_output=True, text=True)
    print("SAÍDA DO TESTE:")
    print(res.stdout)
    print("ERROS DO TESTE:")
    print(res.stderr)

finally:
    print("--- ENCERRANDO SERVIDOR ---")
    server.terminate()
    try:
        outs, errs = server.communicate(timeout=5)
        print("LOG DO SERVIDOR:")
        print(outs)
        print("ERROS DO SERVIDOR:")
        print(errs)
    except:
        server.kill()
