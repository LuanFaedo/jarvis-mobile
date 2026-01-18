
import os

path = '../app.py'

try:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Bloco antigo (Passive + Active)
    # Vou identificar pelo passive_log e substituir até o Active terminar
    
    start_marker = "@socketio.on('passive_log')"
    end_marker = "audio_b64 = gerar_audio_b64(resposta)"
    
    idx_start = content.find(start_marker)
    idx_end = content.find(end_marker)
    
    if idx_start != -1 and idx_end != -1:
        new_block = """@socketio.on('passive_log')
def handle_passive_log(data):
    user_id = data.get('user_id', 'Mestre')
    texto = data.get('text', '').strip()
    if not texto or len(texto) < 5: return
    texto_lower = texto.lower()
    if any(sw in texto_lower for sw in STOPWORDS_PASSIVAS): return
    print(f"[PASSIVE] Memorizando contexto: '{texto}'")
    
    # Executa gravação em background para liberar o socket imediatamente
    threading.Thread(target=adicionar_mensagem, args=(user_id, "user", f"[CONTEXTO AMBIENTE]: {texto}")).start()

@socketio.on('active_command')
@socketio.on('jarvis_command')
def handle_active_command(data):
    global LAST_RESPONSE_HASH, LAST_USER_INPUT
    user_id = data.get('user_id', 'Mestre')
    texto = data.get('text', '')
    
    if not texto or len(texto.strip()) < 2: return

    # --- FILTRO DE INPUT DUPLICADO (Debounce 2s) ---
    import time
    current_time = time.time()
    
    if "text" not in LAST_USER_INPUT: LAST_USER_INPUT = {"text": "", "time": 0}
    
    if texto == LAST_USER_INPUT["text"] and (current_time - LAST_USER_INPUT["time"]) < 2.0:
        print(f"[DEBOUNCE] Ignorando comando duplicado: '{texto}'")
        return
        
    LAST_USER_INPUT = {"text": texto, "time": current_time}
    
    print(f"[ACTIVE] Comando direto: '{texto}'", flush=True)
    resposta = gerar_resposta_jarvis(user_id, texto)
    
    # --- ANTI-DUPLICIDADE TTS (1.0s) ---
    import hashlib
    resp_hash = hashlib.md5(resposta.encode('utf-8')).hexdigest()
    if resp_hash == LAST_RESPONSE_HASH["text"] and (current_time - LAST_RESPONSE_HASH["time"]) < 1.0:
        print(f"[DUPLICIDADE] Bloqueando TTS repetido (1s limit).")
        return
    LAST_RESPONSE_HASH = {"text": resp_hash, "time": current_time}
    # -----------------------------------
    
    """
        # Monta o arquivo final
        final_content = content[:idx_start] + new_block + content[idx_end:]
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        print("Sucesso: Handlers atualizados.")
    else:
        print("Marcadores não encontrados.")

except Exception as e:
    print(f"Erro: {e}")
