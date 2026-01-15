# Teste de Gravação de Diário no SQLite
import sys
import os
sys.path.append(os.getcwd())

import memoria.db_memoria as db
from sistema.auditoria import gravar_diario_voz
import sqlite3

def testar_db_voz():
    print("--- TESTE DE DIÁRIO DE VOZ (SQLite) ---")
    texto_teste = "Teste de gravação no banco de dados SQLite."
    
    # 1. Gravar via Auditoria
    print("Gravando...")
    gravar_diario_voz(texto_teste)
    
    # 2. Ler via DB Direto
    print("Lendo do banco...")
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM diario_voz ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    
    if row:
        print(f"ID: {row['id']}")
        print(f"User: {row['user_id']}")
        print(f"Texto: {row['texto']}")
        print(f"Criado em: {row['criado_em']}")
        
        if row['texto'] == texto_teste:
            print("SUCESSO: Dados conferem. ✅")
        else:
            print("ERRO: Texto divergente. ❌")
    else:
        print("ERRO: Nenhum dado encontrado. ❌")

if __name__ == "__main__":
    testar_db_voz()
