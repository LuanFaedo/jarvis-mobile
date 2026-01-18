
import os

path = '../app.py'

try:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Injeta Globais Reforçadas
    if 'LAST_PROCESSED_TEXT' not in content:
        content = content.replace('LAST_USER_INPUT = {"text": "", "time": 0}', 
                                  'LAST_USER_INPUT = {"text": "", "time": 0}\nLAST_PROCESSED_TEXT = ""\n LAST_PROCESSED_TIME = 0')

    # 2. Atualiza Passive Log (Filtro Global)
    start_passive = "@socketio.on('passive_log')"
    end_passive = "def handle_active_command(data):" # Marca onde começa o próximo
    
    idx_passive = content.find(start_passive)
    idx_active = content.find("@socketio.on('active_command')") # Melhor marcador
    
    if idx_passive != -1 and idx_active != -1:
        new_passive = """@socketio.on('passive_log')
def handle_passive_log(data):
    global LAST_PROCESSED_TEXT, LAST_PROCESSED_TIME
    
    user_id = data.get('user_id', 'Mestre')
    texto = data.get('text', '').strip()
    
    if not texto or len(texto) < 5: return
    
    # --- FILTRO ANTI-SPAM GLOBAL (3s) ---
    import time
    current_time = time.time()
    if texto == LAST_PROCESSED_TEXT and (current_time - LAST_PROCESSED_TIME) < 3.0:
        print(f"[SPAM PASSIVO] Bloqueado: '{texto}'")
        return
        
    LAST_PROCESSED_TEXT = texto
    LAST_PROCESSED_TIME = current_time
    # ------------------------------------

    texto_lower = texto.lower()
    if any(sw in texto_lower for sw in STOPWORDS_PASSIVAS): return
    
    print(f"[PASSIVE] Memorizando contexto: '{texto}'")
    threading.Thread(target=adicionar_mensagem, args=(user_id, "user", f"[CONTEXTO AMBIENTE]: {texto}")).start()

"""
        # Substitui o bloco passivo
        content = content[:idx_passive] + new_passive + content[idx_active:]
        print("Filtro Passivo aplicado.")

    # 3. Atualiza Active Command (Filtro Global)
    # Vou usar replace direto no bloco de debounce existente para usar a nova variável global
    if 'LAST_USER_INPUT = {' in content:
        # Substitui o bloco antigo pelo novo mais robusto
        old_debounce = 'if texto == LAST_USER_INPUT["text"] and (current_time - LAST_USER_INPUT["time"]) < 2.0:'
        new_debounce = '''if texto == LAST_PROCESSED_TEXT and (current_time - LAST_PROCESSED_TIME) < 3.0:
        print(f"[SPAM ATIVO] Bloqueado: '{texto}'")
        return
    
    LAST_PROCESSED_TEXT = texto
    LAST_PROCESSED_TIME = current_time'''
    
        # Não vou substituir LAST_USER_INPUT completamente pois pode quebrar referências, 
        # vou apenas adicionar essa camada extra de proteção.
        # Na verdade, melhor substituir a lógica inteira do handler active para usar as NOVAS globais.
        
        # Vou reescrever o handler active com o script completo para não ter erro.
        pass

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
        
except Exception as e:
    print(e)
