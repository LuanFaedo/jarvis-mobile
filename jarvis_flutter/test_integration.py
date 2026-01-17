import socketio
import time

sio = socketio.Client()

@sio.on('bot_response')
def on_response(data):
    print(f"\n[TESTE] Resposta do Jarvis: {data['text']}")

def test():
    try:
        sio.connect('http://localhost:5000')
        print("[TESTE] Conectado ao Servidor.")
        
        # Teste 1: Envio Passivo (Não deve gerar resposta sonora)
        print("[TESTE] Enviando log passivo...")
        sio.emit('passive_log', {'text': 'Estou pensando em comprar uma moto BMW'})
        time.sleep(1)
        
        # Teste 2: Comando Ativo (Deve usar o contexto acima)
        print("[TESTE] Enviando comando ativo...")
        sio.emit('active_command', {'text': 'Jarvis, qual foi a marca de moto que eu acabei de falar?'})
        
        time.sleep(5) # Espera resposta do LLM
        sio.disconnect()
    except Exception as e:
        print(f"[ERRO NO TESTE] {e}")

if __name__ == '__main__':
    test()
