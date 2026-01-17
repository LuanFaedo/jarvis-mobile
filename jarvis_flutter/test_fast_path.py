import socketio
import time

sio = socketio.Client()
responses = []

@sio.on('bot_response')
def on_response(data):
    print(f"[SERVIDOR]: {data.get('text')}")
    responses.append(data.get('text'))

def run_test():
    try:
        sio.connect('http://localhost:5000')
        print("--- TESTE DE RESPOSTA RÁPIDA ---")
        
        # Simula falar apenas o nome
        print("Enviando apenas o gatilho: 'Jarvis'")
        sio.emit('active_command', {'text': 'Jarvis', 'user_id': 'Tester'})
        
        time.sleep(3)
        sio.disconnect()
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == '__main__':
    run_test()
