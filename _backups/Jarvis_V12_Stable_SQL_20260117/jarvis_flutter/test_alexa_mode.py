import socketio
import time

sio = socketio.Client()

@sio.on('bot_response')
def on_response(data):
    print(f"[RESPOSTA] {data.get('text', '')[:60]}... (Audio: {'SIM' if data.get('audio') else 'NAO'})")

try:
    sio.connect('http://localhost:5000')
    print("--- TESTE ALEXA MODE ---")
    
    # 1. Teste Gatilho Puro (Espera-se 'Pois não?')
    print("\n1. Enviando gatilho 'Jarvis'...")
    sio.emit('active_command', {'text': 'Jarvis', 'user_id': 'Tester'})
    time.sleep(2)
    
    # 2. Teste Comando Direto
    print("\n2. Enviando comando 'Jarvis que horas são'...")
    sio.emit('active_command', {'text': 'Jarvis que horas são', 'user_id': 'Tester'})
    time.sleep(3)
    
    # 3. Teste Duplicidade
    print("\n3. Teste Spam (2 envios rápidos)...")
    sio.emit('active_command', {'text': 'Teste', 'user_id': 'Tester'})
    sio.emit('active_command', {'text': 'Teste', 'user_id': 'Tester'})
    time.sleep(2)
    
    sio.disconnect()
    
except Exception as e:
    print(e)
