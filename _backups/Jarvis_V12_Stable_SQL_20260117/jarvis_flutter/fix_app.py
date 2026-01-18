
import os

path = '../app.py'

try:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Correção Bruta: Remove os `n inseridos pelo PowerShell
    if '`n' in content:
        print("Detectado artefato do PowerShell (`n). Removendo...")
        content = content.replace('`n', '\n')

    # 2. Correção Lógica: Reescreve o handler active_command para garantir indentação correta
    # O código anterior tinha "import time; ct = ..." na mesma linha, o que é feio/frágil
    
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
    
    # Verifica se as chaves existem (proteção extra)
    if "text" not in LAST_USER_INPUT: LAST_USER_INPUT = {"text": "", "time": 0}
    
    if texto == LAST_USER_INPUT["text"] and (current_time - LAST_USER_INPUT["time"]) < 2.0:
        print(f"[DEBOUNCE] Ignorando comando duplicado: '{texto}'")
        return
        
    LAST_USER_INPUT = {"text": texto, "time": current_time}
    # -----------------------------------------------"""

    # Localiza onde substituir
    start_tag = "@socketio.on('active_command')"
    # O final do bloco problemático é onde começa o print do comando
    end_tag = 'print(f"[ACTIVE] Comando direto'

    idx_start = content.find(start_tag)
    idx_end = content.find(end_tag)

    if idx_start != -1 and idx_end != -1:
        print("Substituindo bloco corrompido pelo código limpo...")
        final_content = content[:idx_start] + new_handler + '\n    \n    ' + content[idx_end:]
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        print("Sucesso: app.py corrigido.")
    else:
        print(f"ERRO: Não achei os marcadores. Start: {idx_start}, End: {idx_end}")
        # Se falhou, salva pelo menos a remoção do `n
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

except Exception as e:
    print(f"Erro fatal: {e}")
