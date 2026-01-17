import socketio
import time

sio = socketio.Client()

try:
    sio.connect('http://localhost:5000')
    print("Conectado.")
    
    # 1. Primeiro comando (Válido)
    print("Enviando comando 1...")
    sio.emit('active_command', {'text': 'Teste Spam', 'user_id': 'Tester'})
    time.sleep(0.5)
    
    # 2. Segundo comando igual (Deve ser bloqueado como SPAM)
    print("Enviando comando 2 (Duplicado)...")
    sio.emit('active_command', {'text': 'Teste Spam', 'user_id': 'Tester'})
    
    time.sleep(2)
    sio.disconnect()
except Exception as e:
    print(e)
