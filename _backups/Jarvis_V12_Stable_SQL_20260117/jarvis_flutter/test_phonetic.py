import socketio
import time

sio = socketio.Client()

@sio.on('bot_response')
def on_response(data):
    print(f"\n[JARVIS RESPONDEU]: {data.get('text')}")
    if data.get('audio'):
        print(f"[AUDIO]: Gerado ({len(data.get('audio'))} bytes)")

def run_test():
    try:
        sio.connect('http://localhost:5000')
        print("--- TESTE DE SENSIBILIDADE E MEMÓRIA ---")

        # 1. Simula conversa de fundo (Contexto Passivo)
        print("\n[APP] Enviando contexto: 'Vou comprar uma moto amanhã'")
        sio.emit('passive_log', {'text': 'Vou comprar uma moto amanhã', 'user_id': 'Mestre'})
        time.sleep(1)

        # 2. Simula ativação pelo gatilho 'já vi' (Ativo)
        # O App detecta 'já vi', limpa a frase e manda o comando
        print("[APP] Detectado gatilho 'já vi'. Enviando comando...")
        sio.emit('active_command', {'text': 'já vi o que eu disse que ia fazer amanhã?', 'user_id': 'Mestre'})
        
        time.sleep(5) # Espera o Llama processar
        sio.disconnect()
        print("\n--- FIM DO TESTE ---")

    except Exception as e:
        print(f"Erro no teste: {e}")

if __name__ == '__main__':
    run_test()
