import requests
import json

payload = {
    "text": "Olá Jarvis",
    "sender": "Patrick",
    "chat_id": "5547999195027@c.us"
}

try:
    print("Enviando request...")
    res = requests.post("http://127.0.0.1:5000/api/whatsapp", json=payload)
    print(f"Status: {res.status_code}")
    print(f"Resp: {res.text}")
except Exception as e:
    print(f"Erro: {e}")
