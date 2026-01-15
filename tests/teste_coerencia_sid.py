# Teste de Coerência de Contexto e SID
import threading
import time

class MockSocketIO:
    def emit(self, event, data, room=None):
        print(f"[MOCK EMIT] Evento: {event} | Room (SID): {room} | Data: {data}")

socketio = MockSocketIO()

def processar_streaming_mock(room_sid, texto):
    print(f"[THREAD] Iniciando processamento para: {room_sid}")
    # Simula o erro que aconteceria se usássemos emit()
    try:
        # Aqui no app real usaríamos socketio.emit
        socketio.emit('bot_msg_partial', {'data': 'Olá '}, room=room_sid)
        time.sleep(0.1)
        socketio.emit('bot_msg_partial', {'data': 'Mestre'}, room=room_sid)
        print("[THREAD] Sucesso ao emitir via SID. ✅")
    except Exception as e:
        print(f"[THREAD] Erro: {e} ❌")

def testar_fluxo_sid():
    print("--- INICIANDO TESTE DE FLUXO SID ---")
    
    # Simula o request.sid que o Flask daria
    mock_sid = "CLIENTE_ABC_123"
    texto_usuario = "Teste de streaming"
    
    print(f"[MAIN] Recebido comando. SID capturado: {mock_sid}")
    
    # Inicia a thread exatamente como no app.py
    t = threading.Thread(target=processar_streaming_mock, args=(mock_sid, texto_usuario))
    t.start()
    t.join()
    
    print("--- TESTE FINALIZADO ---")

if __name__ == "__main__":
    testar_fluxo_sid()
