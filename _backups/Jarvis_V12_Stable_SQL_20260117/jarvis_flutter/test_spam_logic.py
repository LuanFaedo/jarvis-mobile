import socketio
import time

sio = socketio.Client()

@sio.on('bot_response')
def on_response(data):
    print(f"[JARVIS RESPONDEU]: {data.get('text')}")

def run_test():
    try:
        sio.connect('http://localhost:5000')
        print("--- TESTE ANTI-SPAM JARVIS ---")
        
        # Simula envio rápido da mesma frase (Spam)
        print("\n[ENVIO 1] Ativando Jarvis...")
        sio.emit('active_command', {'text': 'Jarvis que horas são?', 'user_id': 'Mestre'})
        
        time.sleep(0.5) # Muito rápido
        
        print("[ENVIO 2] Enviando a MESMA frase (Deve ser bloqueado)...")
        sio.emit('active_command', {'text': 'Jarvis que horas são?', 'user_id': 'Mestre'})
        
        time.sleep(5) # Espera resposta do primeiro
        sio.disconnect()
        print("\n--- FIM DO TESTE ---")
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == '__main__':
    run_test()

