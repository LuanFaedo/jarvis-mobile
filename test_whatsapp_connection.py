import requests
import base64
import json

url = "http://localhost:5000/api/whatsapp"

payload = {
    "sender": "TesteDebug",
    "text": "Olá Jarvis, teste de conexão.",
    "chat_id": "TesteDebug"
}

print(f"Enviando para {url}...")

try:
    response = requests.post(url, json=payload, timeout=30)
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("--- Resposta Recebida ---")
        print(f"Texto: {data.get('response')}")
        audio_parts = data.get('audio_parts', [])
        print(f"Áudios: {len(audio_parts)}")
        print("SUCESSO: O servidor está respondendo corretamente.")
    else:
        print(f"ERRO: Servidor retornou código {response.status_code}")
        print(response.text)

except requests.exceptions.ConnectionError:
    print("ERRO CRÍTICO: Falha na conexão. O servidor (app.py ou server.py) está rodando?")
except Exception as e:
    print(f"ERRO: {e}")
