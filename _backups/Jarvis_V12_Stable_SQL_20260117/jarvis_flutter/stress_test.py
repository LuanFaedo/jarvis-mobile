import socketio
import time
import random

sio = socketio.Client()
logs = []

@sio.on('bot_response')
def on_response(data):
    msg = f"[RESPOSTA] {data.get('text', '')[:50]}... (Audio: {'SIM' if data.get('audio') else 'NAO'})"
    print(msg)
    logs.append(msg)

def run_stress():
    try:
        sio.connect('http://localhost:5000')
        print("--- INICIO STRESS TEST ---")
        
        # 1. Fase Passiva (Contexto)
        frases = ["Estou testando o sistema", "O processador está esquentando", "Preciso comprar café"]
        for f in frases:
            print(f"Enviando passivo: {f}")
            sio.emit('passive_log', {'text': f, 'user_id': 'Tester'})
            time.sleep(1) # Simula fala natural

        # 2. Fase Ativa (Pergunta)
        print("Enviando comando ativo...")
        sio.emit('active_command', {'text': 'Jarvis, o que eu preciso comprar?', 'user_id': 'Tester'})
        time.sleep(5) # Espera resposta

        # 3. Teste de Duplicidade (Envio rápido)
        print("Testando filtro de duplicidade...")
        sio.emit('active_command', {'text': 'Jarvis que horas são?', 'user_id': 'Tester'})
        time.sleep(0.5)
        sio.emit('active_command', {'text': 'Jarvis que horas são?', 'user_id': 'Tester'})
        time.sleep(3)

        # 4. Teste de Ruído
        print("Testando ruído...")
        sio.emit('active_command', {'text': 'a', 'user_id': 'Tester'}) # Deve ser ignorado
        sio.emit('passive_log', {'text': '...', 'user_id': 'Tester'}) # Deve ser ignorado
        
        time.sleep(2)
        sio.disconnect()
        print("--- FIM TESTE ---")

    except Exception as e:
        print(f"Erro: {e}")

if __name__ == '__main__':
    run_stress()
