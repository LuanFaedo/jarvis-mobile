
import os

path = '../app.py'

try:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Limpa as globais no topo
    import re
    content = re.sub(r'LAST_USER_INPUT = \{.*?\}', 'LAST_USER_INPUT = {"text": "", "time": 0}', content)
    content = re.sub(r'LAST_PROCESSED_TEXT = .*', 'LAST_PROCESSED_TEXT = ""', content)
    content = re.sub(r'\s*LAST_PROCESSED_TIME = .*', '\nLAST_PROCESSED_TIME = 0', content)

    # 2. Corrige o Handler Passive Log (Reescrevendo o bloco inteiro para garantir indentação)
    passive_start = "@socketio.on('passive_log')"
    # Encontra o início da próxima função para saber onde parar
    next_func = "@socketio.on('active_command')"
    
    idx_p = content.find(passive_start)
    idx_a = content.find(next_func)
    
    if idx_p != -1 and idx_a != -1:
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
    
    texto_lower = texto.lower()
    if any(sw in texto_lower for sw in STOPWORDS_PASSIVAS): return
    print(f"[PASSIVE] Memorizando contexto: '{texto}'")
    threading.Thread(target=adicionar_mensagem, args=(user_id, "user", f"[CONTEXTO AMBIENTE]: {texto}")).start()

"""
        content = content[:idx_p] + new_passive + content[idx_a:]

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Correção de indentação e lógica concluída.")

except Exception as e:
    print(f"Erro no reparo: {e}")
