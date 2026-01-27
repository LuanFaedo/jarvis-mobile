import requests
import time
import json

BASE_URL = "http://127.0.0.1:5000/api/whatsapp"

messages = [
    {"sender": "Tester", "text": "Olá Jarvis", "chat_id": "test_chat_1"},
    {"sender": "Tester", "text": "Que horas são?", "chat_id": "test_chat_1"},
    {"sender": "Tester", "text": "Desenhe um gato futurista", "chat_id": "test_chat_1"},
    {"sender": "Tester", "text": "Pesquise sobre inteligência artificial", "chat_id": "test_chat_1"}
]

for msg in messages:
    print(f"Enviando: {msg['text']}")
    try:
        response = requests.post(BASE_URL, json=msg)
        print(f"Status: {response.status_code}")
        print(f"Resposta: {response.text}")
    except Exception as e:
        print(f"Erro ao enviar: {e}")
    time.sleep(5) # Aguarda 5 segundos entre mensagens para evitar spam block
