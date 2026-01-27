import requests
import base64
import json

# Pequeno áudio WAV (silêncio) em base64 para teste
AUDIO_B64 = "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA="

url = "http://localhost:5000/api/whatsapp"
payload = {
    "sender": "TESTE_DIAGNOSTICO",
    "text": "",
    "chat_id": "TESTE_DIAGNOSTICO",
    "audio_data": AUDIO_B64
}

print("--- Enviando Requisição de Teste ---")
try:
    response = requests.post(url, json=payload, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Resposta: {response.text}")
except Exception as e:
    print(f"Erro na requisição: {e}")
