"""
Sistema de Memória Jarvis com SQLite
- Buffer Recente: últimas N mensagens
- Resumo: atualizado periodicamente
- Fatos: memória permanente extraída automaticamente
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "jarvis_memoria.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Inicializa o banco de dados com as tabelas necessárias"""
    conn = get_connection()
    cursor = conn.cursor()

    # Tabela de usuários
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            nome_preferido TEXT DEFAULT NULL,
            resumo_conversa TEXT DEFAULT '',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabela de mensagens (buffer)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mensagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES usuarios(user_id)
        )
    """)

    # Tabela de fatos (memória permanente)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fatos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            tipo TEXT NOT NULL,
            chave TEXT NOT NULL,
            valor TEXT NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES usuarios(user_id),
            UNIQUE(user_id, tipo, chave)
        )
    """)

    # Tabela financeira
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS financeiro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            tipo TEXT NOT NULL,
            valor REAL NOT NULL,
            descricao TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES usuarios(user_id)
        )
    """)

    # Tabela de saldo
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS saldo (
            user_id TEXT PRIMARY KEY,
            valor REAL DEFAULT 0.0,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print("[DB] Banco de dados inicializado")

# ===================== USUÁRIOS =====================

def get_ou_criar_usuario(user_id: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM usuarios WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if not row:
        cursor.execute(
            "INSERT INTO usuarios (user_id, resumo_conversa) VALUES (?, ?)",
            (user_id, "Novo usuário iniciou conversa.")
        )
        conn.commit()
        cursor.execute("SELECT * FROM usuarios WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

    conn.close()
    return dict(row)

def atualizar_resumo(user_id: str, novo_resumo: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE usuarios SET resumo_conversa = ?, atualizado_em = ? WHERE user_id = ?",
        (novo_resumo, datetime.now(), user_id)
    )
    conn.commit()
    conn.close()

def atualizar_nome_preferido(user_id: str, nome: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE usuarios SET nome_preferido = ?, atualizado_em = ? WHERE user_id = ?",
        (nome, datetime.now(), user_id)
    )
    conn.commit()
    conn.close()

# ===================== MENSAGENS (BUFFER) =====================

def adicionar_mensagem(user_id: str, role: str, content: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO mensagens (user_id, role, content) VALUES (?, ?, ?)",
        (user_id, role, content)
    )
    conn.commit()
    conn.close()

def get_ultimas_mensagens(user_id: str, limite: int = 10) -> List[Dict]:
    """Retorna as últimas N mensagens do usuário"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT role, content FROM mensagens
           WHERE user_id = ?
           ORDER BY id DESC LIMIT ?""",
        (user_id, limite)
    )
    rows = cursor.fetchall()
    conn.close()
    # Inverte para ordem cronológica
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

def contar_mensagens(user_id: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM mensagens WHERE user_id = ?", (user_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_mensagens_para_resumir(user_id: str, offset: int, limite: int) -> List[Dict]:
    """Pega mensagens antigas para criar resumo"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT role, content FROM mensagens
           WHERE user_id = ?
           ORDER BY id ASC LIMIT ? OFFSET ?""",
        (user_id, limite, offset)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"role": r["role"], "content": r["content"]} for r in rows]

def limpar_mensagens_antigas(user_id: str, manter_ultimas: int = 10):
    """Remove mensagens antigas, mantendo apenas as últimas N"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """DELETE FROM mensagens WHERE user_id = ? AND id NOT IN (
            SELECT id FROM mensagens WHERE user_id = ? ORDER BY id DESC LIMIT ?
        )""",
        (user_id, user_id, manter_ultimas)
    )
    conn.commit()
    conn.close()

# ===================== FATOS (MEMÓRIA PERMANENTE) =====================

def salvar_fato(user_id: str, tipo: str, chave: str, valor: str):
    """Salva um fato na memória permanente (upsert)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO fatos (user_id, tipo, chave, valor) VALUES (?, ?, ?, ?)
           ON CONFLICT(user_id, tipo, chave) DO UPDATE SET valor = ?, criado_em = ?""",
        (user_id, tipo, chave, valor, valor, datetime.now())
    )
    conn.commit()
    conn.close()

def get_fatos(user_id: str, tipo: Optional[str] = None) -> List[Dict]:
    """Retorna fatos do usuário, opcionalmente filtrados por tipo"""
    conn = get_connection()
    cursor = conn.cursor()

    if tipo:
        cursor.execute(
            "SELECT tipo, chave, valor FROM fatos WHERE user_id = ? AND tipo = ?",
            (user_id, tipo)
        )
    else:
        cursor.execute(
            "SELECT tipo, chave, valor FROM fatos WHERE user_id = ?",
            (user_id,)
        )

    rows = cursor.fetchall()
    conn.close()
    return [{"tipo": r["tipo"], "chave": r["chave"], "valor": r["valor"]} for r in rows]

def remover_fato(user_id: str, tipo: str, chave: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM fatos WHERE user_id = ? AND tipo = ? AND chave = ?",
        (user_id, tipo, chave)
    )
    conn.commit()
    conn.close()

# ===================== FINANCEIRO =====================

def get_saldo(user_id: str) -> float:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM saldo WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row["valor"] if row else 0.0

def atualizar_saldo(user_id: str, novo_saldo: float):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO saldo (user_id, valor, atualizado_em) VALUES (?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET valor = ?, atualizado_em = ?""",
        (user_id, novo_saldo, datetime.now(), novo_saldo, datetime.now())
    )
    conn.commit()
    conn.close()

def adicionar_transacao(user_id: str, tipo: str, valor: float, descricao: str = ""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO financeiro (user_id, tipo, valor, descricao) VALUES (?, ?, ?, ?)",
        (user_id, tipo, valor, descricao)
    )
    conn.commit()
    conn.close()

def get_transacoes(user_id: str, limite: int = 20) -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT tipo, valor, descricao, criado_em FROM financeiro
           WHERE user_id = ? ORDER BY id DESC LIMIT ?""",
        (user_id, limite)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ===================== UTILIDADES =====================

def limpar_memoria_usuario(user_id: str):
    """Limpa toda a memória de um usuário"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM mensagens WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM fatos WHERE user_id = ?", (user_id,))
    cursor.execute("UPDATE usuarios SET resumo_conversa = 'Memória reiniciada.' WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# Inicializa o banco ao importar o módulo
init_database()
