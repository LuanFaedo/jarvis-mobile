import socketio
import time

sio = socketio.Client()

@sio.event
def connect():
    print("[HTML TEST] Conectado ao servidor SocketIO!")
    print("[HTML TEST] Enviando: 'Ola Jarvis, status do sistema?'")
    sio.emit('active_command', {'user_id': 'WebUser', 'text': 'Ola Jarvis, status do sistema?'})

@sio.on('bot_response')
def on_response(data):
    print("\n[RESPOSTA RECEBIDA]")
    print(f"Texto: {data.get('text')}")
    print(f"Tem Áudio? {'Sim' if data.get('audio') else 'Não'}")
    print(f"Continuar? {data.get('continue_conversation')}")
    sio.disconnect()

@sio.event
def disconnect():
    print("[HTML TEST] Desconectado.")

try:
    sio.connect('http://localhost:5000', wait_timeout=10)
    sio.wait()
except Exception as e:
    print(f"[ERRO] Não foi possível conectar: {e}")
