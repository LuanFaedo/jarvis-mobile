import requests
import json
import time

def send_msg(text):
    url = "http://127.0.0.1:5000/api/whatsapp"
    payload = {
        "sender": "Patrick_Tester",
        "text": text
    }
    headers = {'Content-Type': 'application/json'}
    
    print(f"\n[TESTE] Enviando: '{text}'")
    try:
        start = time.time()
        response = requests.post(url, data=json.dumps(payload), headers=headers, timeout=60)
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            resp_text = data.get('response', '')
            print(f"[JARVIS ({duration:.2f}s)]: {resp_text}")
            return resp_text
        else:
            print(f"[ERRO HTTP] Status: {response.status_code}")
            return None
    except Exception as e:
        print(f"[ERRO CONEXÃO] {e}")
        return None

print("=== INICIANDO TESTE DE QUALIDADE JARVIS ===")

# Teste 1: Identidade e Contexto
r1 = send_msg("Quem é seu criador e qual sua missão?")

# Teste 2: Busca Web (Verificar se falha silenciosamente ou funciona)
r2 = send_msg("Qual a cotação do dólar hoje? Seja breve.")

print("\n=== FIM DO TESTE ===")
