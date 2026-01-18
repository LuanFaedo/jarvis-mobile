import socketio
import time
import sys

# Simulação de Cliente Socket.IO para Teste de Loop Contínuo

sio = socketio.Client()
LOOP_ATIVO = True

@sio.event
def connect():
    print("[TESTE] Conectado ao servidor.")
    # Envia comando inicial para iniciar sessão
    print("[TESTE] Enviando: 'Ola Jarvis'")
    sio.emit('active_command', {'user_id': 'Tester', 'text': 'Ola Jarvis'})

@sio.on('bot_response')
def on_response(data):
    global LOOP_ATIVO
    print(f"\n[JARVIS] {data.get('text')}")
    continuar = data.get('continue_conversation', False)
    print(f"[STATUS] Continuar Conversa? {continuar}")

    if continuar:
        print("[TESTE] Loop ativo. Enviando comando de PARADA em 2s...")
        time.sleep(2)
        sio.emit('active_command', {'user_id': 'Tester', 'text': 'Obrigado pare'})
    else:
        print("[TESTE] Loop encerrado corretamente pelo servidor.")
        LOOP_ATIVO = False
        sio.disconnect()

@sio.event
def disconnect():
    print("[TESTE] Desconectado.")

def run_test():
    try:
        sio.connect('http://localhost:5000')
        sio.wait()
    except Exception as e:
        print(f"[ERRO] {e}")

if __name__ == '__main__':
    run_test()
