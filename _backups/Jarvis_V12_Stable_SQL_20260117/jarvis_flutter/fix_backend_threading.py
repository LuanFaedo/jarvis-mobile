import os

path = '../app.py'

try:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Identifica o handler antigo para substituir
    start_tag = "@socketio.on('active_command')"
    end_tag = "audio_b64 = gerar_audio_b64(resposta)"
    
    # Precisamos achar o final real da função antiga.
    # O end_tag acima pode estar no meio.
    # Vamos substituir até o início do próximo handler ou helper.
    # No arquivo atual, depois de handle_active_command vem handle_legacy_message_text
    
    real_end_tag = "@socketio.on('message_text')"
    
    idx_start = content.find(start_tag)
    idx_end = content.find(real_end_tag)
    
    if idx_start != -1 and idx_end != -1:
        new_handler = """@socketio.on('active_command')
@socketio.on('jarvis_command')
def handle_active_command(data):
    # Executa em background para liberar o socket e evitar AssertionError
    socketio.start_background_task(process_active_command_bg, data)

def process_active_command_bg(data):
    global LAST_RESPONSE_HASH, LAST_USER_INPUT
    
    user_id = data.get('user_id', 'Mestre')
    texto = data.get('text', '').strip()
    
    if not texto or len(texto) < 2: return

    # --- FILTRO DE INPUT DUPLICADO (Debounce 2s) ---
    import time
    current_time = time.time()
    if "text" not in LAST_USER_INPUT: LAST_USER_INPUT = {"text": "", "time": 0}
    
    if texto == LAST_USER_INPUT["text"] and (current_time - LAST_USER_INPUT["time"]) < 2.0:
        print(f"[DEBOUNCE] Ignorando comando duplicado: '{texto}'")
        return
    LAST_USER_INPUT = {"text": texto, "time": current_time}
    # -----------------------------------------------

    print(f"[ACTIVE] Comando recebido: '{texto}'", flush=True)

    # --- FILTRO DE GATILHO PURO (Resposta Rápida) ---
    triggers = ["jarvis", "javis", "chaves", "garvis", "assistente", "já vi", "jair"]
    texto_lower = texto.lower()
    
    # Se o texto for APENAS um gatilho (ex: "Jarvis"), responde rápido
    if texto_lower in triggers:
        print("[FAST] Apenas gatilho detectado. Respondendo 'Pois não?'.")
        resposta = "Pois não?"
        audio_b64 = gerar_audio_b64(resposta)
        socketio.emit('bot_response', {'text': resposta, 'audio': audio_b64, 'continue_conversation': True})
        return

    # --- PROCESSAMENTO LLM (Normal) ---
    resposta = gerar_resposta_jarvis(user_id, texto)
    
    # Anti-Duplicidade TTS
    import hashlib
    resp_hash = hashlib.md5(resposta.encode('utf-8')).hexdigest()
    if "text" not in LAST_RESPONSE_HASH: LAST_RESPONSE_HASH = {"text": "", "time": 0}
    
    if resp_hash == LAST_RESPONSE_HASH["text"] and (current_time - LAST_RESPONSE_HASH["time"]) < 1.0:
        print("[DUPLICIDADE] Bloqueando TTS repetido.")
        return
    LAST_RESPONSE_HASH = {"text": resp_hash, "time": current_time}
    
    audio_b64 = gerar_audio_b64(resposta)
    termos_fim = ['tchau', 'até logo', 'obrigado jarvis', 'encerrar', 'dormir']
    continuar = not any(t in resposta.lower() for t in termos_fim)
    
    socketio.emit('bot_response', {'text': resposta, 'audio': audio_b64, 'continue_conversation': continuar})
    
    # Áudio Longo
    try:
        audios = gerar_multiplos_audios(resposta)
        if audios and len(audios) > 1:
            socketio.emit('audio_parts_start', {'total': len(audios)})
            for part in audios:
                socketio.emit('play_audio_remoto', {'url': f"data:audio/mp3;base64,{part['audio']}", 'parte': part['parte'], 'total': part['total']})
            socketio.emit('audio_parts_end', {'total': len(audios)})
    except: pass

"""
        final_content = content[:idx_start] + new_handler + content[idx_end:]
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        print("Backend corrigido com Threading e Filtro de Gatilho.")
    else:
        print("Erro: Marcadores não encontrados.")

except Exception as e:
    print(f"Erro fatal: {e}")