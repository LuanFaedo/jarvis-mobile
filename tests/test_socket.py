import socketio
import time
import sys

# Cria cliente SocketIO
sio = socketio.Client()

@sio.event
def connect():
    print("[TESTE] Conectado ao servidor Jarvis!")
    # Envia mensagem assim que conectar
    print("[TESTE] Enviando mensagem: 'Quem é você?'")
    sio.emit('fala_usuario', {'text': 'Quem é você e qual seu modelo?'})

@sio.event
def bot_msg(data):
    print(f"\n[TESTE] Resposta do Jarvis: {data.get('data')}")
    print("[TESTE] Teste concluído com sucesso.")
    sio.disconnect()

@sio.event
def disconnect():
    print("[TESTE] Desconectado.")

def run_test():
    try:
        sio.connect('http://localhost:5000')
        sio.wait()
    except Exception as e:
        print(f"[TESTE] Erro ao conectar: {e}")

if __name__ == '__main__':
    run_test()
