
import os

path = '../app.py'

try:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Atualizar System Prompt (Humanização)
    # Procuramos o bloco onde o system_prompt é definido
    start_prompt = 'system_prompt = f"""VOCÊ É O JARVIS'
    end_prompt = '"""'
    
    idx_start = content.find(start_prompt)
    if idx_start != -1:
        # Encontra o fim do prompt
        idx_end = content.find(end_prompt, idx_start + 10)
        
        if idx_end != -1:
            new_prompt = '''system_prompt = f"""VOCÊ É J.A.R.V.I.S., UMA IA ASSISTENTE LEAL, ESPIRITUOSA E EFICIENTE.
DATA: {agora_br.strftime('%d/%m/%Y %H:%M')}. USUÁRIO MESTRE: {nome_usuario}.

=== SUA PERSONALIDADE ===
1. Você não é um robô chato. Você é o Jarvis. Tenha personalidade.
2. Use o contexto passivo (o que foi ouvido antes) para surpreender o usuário.
3. Se o usuário perguntar "o que eu disse?", responda com precisão usando o histórico.
4. Respostas curtas e diretas são melhores para chat por voz.

=== COMANDOS ===
- [[SEARCH: query]] -> Busca na internet.
- [[AUTO: comando | arg]] -> Automação PC.
- [[CMD: comando]] -> Terminal.

CONTEXTO:
{usuario['resumo_conversa']}
{fatos_texto}
{financas_contexto}
{info_iot if info_iot else ""}
{info_financeira if info_financeira else ""}
'''
            content = content[:idx_start] + new_prompt + content[idx_end:]
            print("Prompt do Sistema atualizado (Humanização).")

    # 2. Reforçar Variável Global e Anti-Spam
    # Se LAST_USER_INPUT não estiver no topo, adiciona.
    if 'LAST_USER_INPUT = {' not in content[:1000]: 
        content = content.replace('import qrcode', 'import qrcode\n\n# GLOBAIS\nLAST_USER_INPUT = {"text": "", "time": 0}\nLAST_RESPONSE_HASH = {"text": "", "time": 0}')
        print("Variáveis globais reinseridas.")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print("Correções do Backend aplicadas.")

except Exception as e:
    print(f"Erro: {e}")
