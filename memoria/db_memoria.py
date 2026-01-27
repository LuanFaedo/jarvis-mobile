"""
Sistema de Memória Jarvis com SQLite
- Buffer Recente: últimas N mensagens
- Resumo: atualizado periodicamente
- Fatos: memória permanente extraída automaticamente
"""

import sqlite3
import os
import shutil
from datetime import datetime
from typing import List, Dict, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "jarvis_memoria.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def fazer_backup_banco():
    """Cria uma cópia de segurança do banco de dados ao iniciar"""
    if os.path.exists(DB_PATH):
        backup_path = f"{DB_PATH}.bak"
        try:
            shutil.copy2(DB_PATH, backup_path)
            # print(f"[BACKUP] Banco de dados salvo em: {backup_path}")
        except Exception as e:
            print(f"[BACKUP] Falha: {e}")

def init_database():
    """Inicializa o banco de dados com as tabelas necessárias"""
    # Executa backup antes de qualquer operação
    fazer_backup_banco()

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

    # Tabela de Metas (Orçamento)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            categoria TEXT NOT NULL,
            valor_limite REAL NOT NULL,
            periodo TEXT DEFAULT 'mensal', -- 'mensal', 'semanal', 'anual'
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES usuarios(user_id),
            UNIQUE(user_id, categoria, periodo)
        )
    """)

    # Tabela de Objetivos (Cofrinhos)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS objetivos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            nome TEXT NOT NULL,
            valor_alvo REAL NOT NULL,
            valor_atual REAL DEFAULT 0.0,
            data_alvo DATE,
            status TEXT DEFAULT 'ativo', -- 'ativo', 'concluido', 'pausado'
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES usuarios(user_id)
        )
    """)

    # Tabela de Assinaturas (Recorrência)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assinaturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            nome TEXT NOT NULL,
            valor REAL NOT NULL,
            dia_vencimento INTEGER NOT NULL,
            ativo BOOLEAN DEFAULT 1,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES usuarios(user_id),
            UNIQUE(user_id, nome)
        )
    """)

    # Tabela de diário de voz (Gravação Integral)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS diario_voz (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT DEFAULT 'Patrick',
            texto TEXT NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

# ===================== METAS & OBJETIVOS =====================

def definir_meta(user_id: str, categoria: str, valor: float, periodo: str = 'mensal'):
    """Define ou atualiza uma meta de gastos"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO metas (user_id, categoria, valor_limite, periodo) VALUES (?, ?, ?, ?)
           ON CONFLICT(user_id, categoria, periodo) DO UPDATE SET valor_limite = ?""",
        (user_id, categoria, valor, periodo, valor)
    )
    conn.commit()
    conn.close()

def get_metas(user_id: str) -> List[Dict]:
    """Retorna todas as metas do usuário"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT categoria, valor_limite, periodo FROM metas WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def criar_objetivo(user_id: str, nome: str, valor_alvo: float, data_alvo: str = None):
    """Cria um novo objetivo financeiro (cofrinho)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO objetivos (user_id, nome, valor_alvo, data_alvo) VALUES (?, ?, ?, ?)",
        (user_id, nome, valor_alvo, data_alvo)
    )
    conn.commit()
    conn.close()

def atualizar_objetivo(user_id: str, nome_objetivo: str, valor_adicionado: float):
    """Adiciona valor a um objetivo existente pelo nome"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE objetivos SET valor_atual = valor_atual + ? WHERE nome = ? AND user_id = ?",
        (valor_adicionado, nome_objetivo, user_id)
    )
    conn.commit()
    conn.close()

def get_objetivos(user_id: str) -> List[Dict]:
    """Lista objetivos do usuário"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, valor_alvo, valor_atual, status FROM objetivos WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ===================== ASSINATURAS (RECORRÊNCIA) =====================

def adicionar_assinatura(user_id: str, nome: str, valor: float, dia_vencimento: int):
    """Adiciona ou atualiza uma assinatura recorrente"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO assinaturas (user_id, nome, valor, dia_vencimento) VALUES (?, ?, ?, ?)
           ON CONFLICT(user_id, nome) DO UPDATE SET valor = ?, dia_vencimento = ?, ativo = 1""",
        (user_id, nome, valor, dia_vencimento, valor, dia_vencimento)
    )
    conn.commit()
    conn.close()

def get_assinaturas(user_id: str) -> List[Dict]:
    """Lista assinaturas ativas"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT nome, valor, dia_vencimento FROM assinaturas WHERE user_id = ? AND ativo = 1 ORDER BY dia_vencimento ASC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def remover_assinatura(user_id: str, nome: str):
    """Desativa uma assinatura (soft delete)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE assinaturas SET ativo = 0 WHERE user_id = ? AND nome LIKE ?", (user_id, f"%{nome}%"))
    conn.commit()
    conn.close()

# ===================== UTILIDADES =====================

def limpar_memoria_usuario(user_id: str):
    """Limpa toda a memória de um usuário"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM mensagens WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM fatos WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM metas WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM objetivos WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM assinaturas WHERE user_id = ?", (user_id,))
    cursor.execute("UPDATE usuarios SET resumo_conversa = 'Memória reiniciada.' WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# ===================== DIÁRIO DE VOZ =====================

def salvar_diario_voz(texto: str, user_id: str = "Patrick"):
    """Salva áudio bruto no banco de dados"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO diario_voz (user_id, texto) VALUES (?, ?)",
        (user_id, texto)
    )
    conn.commit()
    conn.close()

# Inicializa o banco ao importar o módulo
init_database()