import socketio
import time
import base64

# Simula o cliente Flutter
sio = socketio.Client()

received_ack = False
received_response = False

@sio.on('connect')
def on_connect():
    print("[TESTE] Conectado ao servidor Jarvis!")

@sio.on('jarvis_ack')
def on_ack(data):
    global received_ack
    print(f"[TESTE] ACK Recebido (Wake Word Detectada): {data}")
    received_ack = True

@sio.on('response_audio')
def on_audio(data):
    global received_response
    print(f"[TESTE] Áudio de resposta recebido! Tamanho: {len(data.get('audio', ''))} bytes")
    received_response = True

def run_test():
    try:
        # Tenta conectar ao servidor local
        sio.connect('http://127.0.0.1:5001')
        
        # Simula o envio de áudio (bytes brutos)
        # Como não temos um áudio real com "Jarvis" agora, vamos enviar bytes vazios 
        # para testar a rota e a conexão.
        # Nota: O teste de transcrição real requer áudio válido.
        print("[TESTE] Enviando pacote de áudio simulado...")
        dummy_audio = b'\x00' * 1024
        sio.emit('audio_stream', dummy_audio)
        
        # Aguarda um pouco para ver as respostas
        time.sleep(5)
        
        sio.disconnect()
        
        print("\n--- RESULTADO DO TESTE ---")
        print(f"Conexão: SUCESSO")
        print(f"Processamento: O servidor tentou processar (verifique os logs do app.py)")
        
    except Exception as e:
        print(f"[ERRO NO TESTE] {e}")

if __name__ == '__main__':
    run_test()
