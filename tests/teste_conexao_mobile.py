# Teste de Conexão App Mobile -> Jarvis PC
import socketio
import time

sio = socketio.Client()

def testar_conexao_mobile():
    print("--- SIMULANDO APP MOBILE CONECTANDO ---")
    try:
        # Tenta conectar no servidor local
        sio.connect('http://localhost:5000')
        print(f"SUCESSO: Conectado ao Jarvis. SID: {sio.sid} ✅")
        
        # Simula envio de comando via Mobile
        print("Enviando comando de teste...")
        sio.emit('fala_usuario', {
            'text': 'Jarvis, teste de conexão via aplicativo mobile.',
            'user_id': 'Patrick_Mobile'
        })
        
        print("Aguardando resposta do servidor (3s)...")
        time.sleep(3)
        
        sio.disconnect()
        print("Desconectado. Teste concluído com sucesso. ✅")
        
    except Exception as e:
        print(f"FALHA: Não foi possível conectar ao Jarvis. Erro: {e} ❌")
        print("Nota: O servidor 'app.py' deve estar rodando na porta 5000.")

if __name__ == "__main__":
    testar_conexao_mobile()
