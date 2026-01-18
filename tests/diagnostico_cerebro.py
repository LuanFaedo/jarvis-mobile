import requests
import json
import time

def teste_cerebro():
    print("--- DIAGNÓSTICO CÉREBRO JARVIS ---")
    
    # 1. Teste Ollama Local
    print("\n1. Testando Ollama (http://127.0.0.1:11434)...")
    try:
        start = time.time()
        resp = requests.post('http://127.0.0.1:11434/api/generate', 
                             json={"model": "qwen2.5-coder:32b", "prompt": "Oi", "stream": False},
                             timeout=5)
        if resp.status_code == 200:
            print(f"   [OK] Ollama respondeu em {time.time()-start:.2f}s")
        else:
            print(f"   [ERRO] Status {resp.status_code}")
    except Exception as e:
        print(f"   [FALHA] Ollama indisponível: {e}")

    # 2. Teste Servidor Flask
    print("\n2. Testando Servidor Flask (http://127.0.0.1:5000)...")
    try:
        resp = requests.get('http://127.0.0.1:5000/')
        if resp.status_code == 200:
            print("   [OK] Servidor Web Online")
        else:
            print(f"   [ERRO] Servidor retornou {resp.status_code}")
    except:
        print("   [FALHA] Servidor Flask parece estar OFF. Reinicie 'python app.py'")

if __name__ == "__main__":
    teste_cerebro()
