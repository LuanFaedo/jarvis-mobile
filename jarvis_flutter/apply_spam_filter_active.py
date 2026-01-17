
import os

path = '../app.py'

try:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Bloco Active Command
    start_tag = "def process_active_command_bg(data):"
    end_tag = "print(f\"[ACTIVE] Comando recebido" # Marcador seguro
    
    idx_start = content.find(start_tag)
    idx_end = content.find(end_tag)
    
    if idx_start != -1 and idx_end != -1:
        new_logic = """def process_active_command_bg(data):
    global LAST_RESPONSE_HASH, LAST_PROCESSED_TEXT, LAST_PROCESSED_TIME
    
    user_id = data.get('user_id', 'Mestre')
    texto = data.get('text', '').strip()
    
    if not texto or len(texto) < 2: return

    # --- FILTRO ANTI-SPAM GLOBAL (3s) ---
    import time
    current_time = time.time()
    
    if texto == LAST_PROCESSED_TEXT and (current_time - LAST_PROCESSED_TIME) < 3.0:
        print(f"[SPAM ATIVO] Bloqueado: '{texto}'")
        return
        
    LAST_PROCESSED_TEXT = texto
    LAST_PROCESSED_TIME = current_time
    # ------------------------------------

    """
        final_content = content[:idx_start] + new_logic + content[idx_end:]
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        print("Filtro Ativo aplicado.")
    else:
        print("Erro Active.")

except Exception as e:
    print(e)

