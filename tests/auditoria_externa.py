# Auditoria de Banco de Dados Externo
import sys
import os
import sqlite3

# Configura path para o módulo externo
EXTERNAL_PATH = r"D:\compartilhado\Projetos\jarvis01\jarvizsql-FINANEIRO-ZAP"
sys.path.insert(0, EXTERNAL_PATH)

# Caminho direto do banco (para sqlite3)
DB_FILE = os.path.join(EXTERNAL_PATH, "memoria", "jarvis_memoria.db")

def auditar_banco():
    print(f"--- AUDITORIA DO BANCO: {DB_FILE} ---\n")
    
    if not os.path.exists(DB_FILE):
        print("ERRO: Arquivo de banco de dados não encontrado.")
        return

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # 1. Usuários
    print(">>> USUÁRIOS CADASTRADOS:")
    try:
        cur.execute("SELECT user_id, nome_preferido, criado_em FROM usuarios")
        users = cur.fetchall()
        for u in users:
            print(f"- ID: {u['user_id']} | Nome: {u['nome_preferido']} | Criado: {u['criado_em']}")
    except Exception as e: print(f"Erro ao ler usuários: {e}")

    # 2. Saldo Financeiro
    print("\n>>> SALDOS:")
    try:
        cur.execute("SELECT user_id, valor FROM saldo")
        saldos = cur.fetchall()
        for s in saldos:
            print(f"- User: {s['user_id']} | Saldo: R$ {s['valor']:.2f}")
    except Exception as e: print(f"Erro ao ler saldo: {e}")

    # 3. Últimas 5 Mensagens
    print("\n>>> ÚLTIMAS MENSAGENS (Geral):")
    try:
        cur.execute("SELECT user_id, role, content, criado_em FROM mensagens ORDER BY id DESC LIMIT 5")
        msgs = cur.fetchall()
        for m in msgs:
            preview = m['content'][:50].replace('\n', ' ')
            print(f"[{m['criado_em']}] {m['user_id']} ({m['role']}): {preview}...")
    except Exception as e: print(f"Erro ao ler mensagens: {e}")

    conn.close()

if __name__ == "__main__":
    auditar_banco()
