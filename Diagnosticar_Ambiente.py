import sys
import os
import importlib.util

print("=== DIAGNÓSTICO DE AMBIENTE PYTHON ===")
print(f"Executável Python: {sys.executable}")
print(f"Versão: {sys.version}")
print(f"Diretório de Trabalho: {os.getcwd()}")
print("\n--- CAMINHOS DO SISTEMA (sys.path) ---")
for p in sys.path:
    print(f"- {p}")

print("\n--- TESTE DE IMPORTAÇÃO ---")
libs = ['samsungtvws', 'wakeonlan', 'websocket', 'flask', 'socketio']
for lib in libs:
    try:
        spec = importlib.util.find_spec(lib)
        if spec:
            print(f"[OK] {lib} encontrado em: {spec.origin}")
        else:
            print(f"[FALHA] {lib} NÃO ENCONTRADO!")
    except ImportError:
        print(f"[ERRO] Falha ao tentar importar {lib}")
    except Exception as e:
        print(f"[ERRO] {lib}: {e}")

print("\n=== FIM DO DIAGNÓSTICO ===")

