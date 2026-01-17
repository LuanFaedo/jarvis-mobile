
import os

path = '../app.py'

try:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Garante que as globais existam no topo (logo após os imports iniciais)
    globals_init = '\n# --- GLOBAIS DE CONTROLE ---\nLAST_RESPONSE_HASH = {"text": "", "time": 0}\nLAST_USER_INPUT = {"text": "", "time": 0}\n'
    
    if 'LAST_USER_INPUT =' not in content:
        # Insere após o primeiro bloco de imports
        content = content.replace('import qrcode', 'import qrcode' + globals_init)

    # 2. Substitui o bloco do handler active_command completo
    start_tag = "@socketio.on('active_command')"
    end_tag = "audio_b64 = gerar_audio_b64(resposta)"
    
    # Re-localiza o bloco (considerando possíveis alterações de texto)
    idx_start = content.find(start_tag)
    idx_end = content.find(end_tag)

    if idx_start != -1 and idx_end != -1:
        new_handler = """@socketio.on('active_command')
@socketio.on('jarvis_command')
def handle_active_command(data):
    global LAST_RESPONSE_HASH, LAST_USER_INPUT
    user_id = data.get('user_id', 'Mestre')
    texto = data.get('text', '')
    
    if not texto or len(texto.strip()) < 2: return

    # --- FILTRO DE INPUT DUPLICADO (Debounce 2s) ---
    import time
    current_time = time.time()
    
    if texto == LAST_USER_INPUT["text"] and (current_time - LAST_USER_INPUT["time"]) < 2.0:
        print(f"[SPAM DETECTADO] Ignorando comando duplicado: {texto}")
        return
        
    LAST_USER_INPUT = {"text": texto, "time": current_time}
    
    print(f"[ACTIVE] Comando direto: '{texto}'", flush=True)
    resposta = gerar_resposta_jarvis(user_id, texto)
    
    # --- ANTI-DUPLICIDADE TTS (1.0s) ---
    import hashlib
    resp_hash = hashlib.md5(resposta.encode('utf-8')).hexdigest()
    if resp_hash == LAST_RESPONSE_HASH["text"] and (current_time - LAST_RESPONSE_HASH["time"]) < 1.0:
        print(f"[DUPLICIDADE] Bloqueando TTS repetido.")
        return
    LAST_RESPONSE_HASH = {"text": resp_hash, "time": current_time}
    """
        final_content = content[:idx_start] + new_handler + content[idx_end:]
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        print("Correção de NameError e Debounce aplicada.")
    else:
        print("Erro: Não foi possível localizar o handler para substituição.")

except Exception as e:
    print(f"Erro fatal no script de correção: {e}")
