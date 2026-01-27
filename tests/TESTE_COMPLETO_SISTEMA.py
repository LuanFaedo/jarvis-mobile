import socketio
import time
import sys

# Cores para o terminal (Simples)
GREEN = ''
RED = ''
CYAN = ''
YELLOW = ''
RESET = ''

sio = socketio.Client()
test_results = {"img": False, "stop": False, "echo": False}
last_bot_response = ""

@sio.event
def connect():
    print("[✓] Conectado ao Servidor Jarvis!")

@sio.on('bot_msg')
def on_message(data):
    global last_bot_response
    print(f"[BOT MSG] {data.get('data','')}")
    last_bot_response = data.get('data','')
    
    if "[[GEN_IMG:" in last_bot_response:
        print("[✓] SUCESSO: Tag de imagem detectada!")
        test_results["img"] = True

@sio.on('bot_response')
def on_response(data):
    global last_bot_response
    print(f"[BOT RESPONSE] {data.get('text','')}")
    last_bot_response = data.get('text','')
    
    if "[[GEN_IMG:" in last_bot_response:
        print("[✓] SUCESSO: Tag de imagem detectada!")
        test_results["img"] = True

@sio.on('force_stop_playback')
def on_stop(data):
    print("[EVENTO] force_stop_playback recebido!")
    test_results["stop"] = True

def run_test():
    try:
        print("Tentando conectar em localhost:5000...")
        sio.connect('http://localhost:5000', wait_timeout=5)
    except Exception as e:
        print(f"[X] Erro: Servidor offline ou recusou conexao. Detalhe: {e}")
        return

    print("\n--- TESTE 1: GERAÇÃO DE IMAGEM (META AI) ---")
    sio.emit('active_command', {'user_id': 'Tester', 'text': 'Gere uma imagem de um cachorro voando'})
    time.sleep(15) # Aguarda resposta (LLM pode demorar)

    print("\n--- TESTE 2: BARGE-IN (PARADA) ---")
    sio.emit('active_command', {'user_id': 'Tester', 'text': 'Jarvis pare'})
    time.sleep(2)

    print("\n--- TESTE 3: FILTRO DE ECO ---")
    if last_bot_response:
        print(f"Simulando eco da frase: '{last_bot_response[:30]}...'")
        sio.emit('active_command', {'user_id': 'Tester', 'text': last_bot_response})
        print("Mensagem de eco enviada.")
    else:
        print("Não houve resposta anterior para testar eco.")
    
    time.sleep(2)
    
    print("\n--- RELATÓRIO FINAL ---")
    print(f"IMAGEM TAG: {'✅ PASSOU' if test_results['img'] else '❌ FALHOU'}")
    print(f"BARGE-IN:   {'✅ PASSOU' if test_results['stop'] else '❌ FALHOU'}")
    
    sio.disconnect()

if __name__ == "__main__":
    run_test()