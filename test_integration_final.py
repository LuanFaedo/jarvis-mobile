import requests
import json
import time

URL = "http://localhost:5000/api/whatsapp"
PAYLOAD = {
    "sender": "TESTER_BOT",
    "text": "Olá Jarvis, teste de conexão final.",
    "chat_id": "TEST_CHAT_001"
}

print(f"--- TESTANDO API INTEGRADA ---")
print(f"Alvo: {URL}")

try:
    start = time.time()
    resp = requests.post(URL, json=PAYLOAD, timeout=120)
    duration = time.time() - start
    
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Tempo: {duration:.2f}s")
        print(f"Resposta Jarvis: {data.get('response')}")
        
        audios = data.get('audio_parts', [])
        print(f"Áudios gerados: {len(audios)}")
        if audios:
            print("Audio B64 detectado (OK)")
    else:
        print(f"Erro na requisição: {resp.text}")

except Exception as e:
    print(f"Falha ao conectar na API Flask: {e}")
    print("DICA: Verifique se o INICIAR_JARVIS.bat está rodando!")
