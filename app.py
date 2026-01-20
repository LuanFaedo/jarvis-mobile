import os
import sys

# --- PRIORIZAR DIRETÓRIO LOCAL ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from flask import Flask, render_template, send_from_directory, request, jsonify, session, redirect, url_for, flash
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from pycloudflared import try_cloudflare
from dotenv import load_dotenv
from openai import OpenAI
import edge_tts
import ollama
import asyncio
import os
import time
import threading
import sys
import json
import uuid
import re
import subprocess
import shutil
import sqlite3
import speech_recognition as sr
from pydub import AudioSegment
import io
import base64
import tempfile
from datetime import datetime, timedelta, timezone
from functools import wraps
import urllib.request
from email.utils import parsedate_to_datetime
from PIL import Image, ImageGrab, ImageOps, ImageEnhance
import mimetypes
import pytesseract
import hashlib
from difflib import SequenceMatcher

# Tenta importar FPDF para geração de relatórios
try:
    from fpdf import FPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("[AVISO] Biblioteca FPDF não instalada. Funcionalidade de PDF desativada.")

# GLOBAIS
try:
    import qrcode
except ImportError:
    qrcode = None

LAST_USER_INPUT = {"text": "", "time": 0}
LAST_PROCESSED_TEXT = ""
LAST_PROCESSED_TIME = 0
LAST_RESPONSE_HASH = {"text": "", "time": 0}
LAST_BOT_RESPONSE = "" # Armazena a última fala para evitar auto-escuta

# --- LOCK GLOBAL ANTI-CRASH (CONCORRÊNCIA) ---
COMMAND_LOCK = threading.Lock()
LAST_COMMAND_TIME = 0
COMMAND_COOLDOWN = 3.0

# --- Configurações Iniciais ---
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.environ['OMP_THREAD_LIMIT'] = '1'
os.environ['TESSDATA_PREFIX'] = os.path.join(BASE_DIR, "tessdata")

# Tesseract
CAMINHO_TESSERACT_PADRAO = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(CAMINHO_TESSERACT_PADRAO):
    pytesseract.pytesseract.tesseract_cmd = CAMINHO_TESSERACT_PADRAO
else:
    tess_path = shutil.which("tesseract")
    if tess_path:
        pytesseract.pytesseract.tesseract_cmd = tess_path

# Importa o módulo de memória SQLite
try:
    from memoria.db_memoria import (
        get_ou_criar_usuario, atualizar_resumo, atualizar_nome_preferido,
        adicionar_mensagem, get_ultimas_mensagens, contar_mensagens,
        get_mensagens_para_resumir, limpar_mensagens_antigas,
        salvar_fato, get_fatos,
        get_saldo, atualizar_saldo, adicionar_transacao, get_transacoes,
        limpar_memoria_usuario, salvar_diario_voz,
        definir_meta, get_metas, criar_objetivo, atualizar_objetivo, get_objetivos,
        adicionar_assinatura, get_assinaturas, remover_assinatura
    )
    print("[SISTEMA] Memória SQLite carregada com sucesso.")
except ImportError as e:
    print(f"[AVISO] Algumas funções de memória não foram encontradas: {e}")
    # Fallbacks básicos
    def adicionar_mensagem(*args, **kwargs): pass
    def get_ultimas_mensagens(*args, **kwargs): return []
    def salvar_diario_voz(*args, **kwargs): pass

from iot.tv_controller import TVController
from sistema.automacao import pc
from sistema.web_search import pesquisar_web
from sistema.core import ManipuladorTotal

manipulador = ManipuladorTotal(BASE_DIR)

# API
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:11434/v1")
API_KEY = "AAAAC3NzaC1lZDI1NTE5AAAAIJ9KfyhZeNo5E84kORaqKYu7gxopcvqT2hRabwJU/sXF"
MODELO_ATIVO = "gpt-oss:120b-cloud"

client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
client_ollama = ollama.Client(host=API_BASE_URL.replace("/v1", ""))

def consultar_gemini_nuvem(prompt):
    print(f"[SUPERVISOR] Consultando: {prompt[:50]}...", flush=True)
    try:
        payload = {
            "model": MODELO_ATIVO,
            "prompt": f"SYSTEM: Arquiteto Sênior. Gere apenas o código.\nPEDIDO: {prompt}",
            "stream": False
        }
        endpoint = API_BASE_URL.replace("/v1", "") + "/api/generate"
        resp = requests.post(endpoint, json=payload, timeout=60)
        if resp.status_code == 200:
            return resp.json().get('response', '')
    except Exception as e:
        print(f"[ERRO SUPERVISOR] {e}")
    return "Erro ao consultar supervisor."

AUDIO_DIR = os.path.join(BASE_DIR, "audios")
HISTORY_DIR = os.path.join(BASE_DIR, "historico")
STATIC_DIR = os.path.join(BASE_DIR, "static") # Ajustado para PDF
KNOWLEDGE_FILE = os.path.join(BASE_DIR, "memoria/conhecimento.json")
CONFIG_FILE = os.path.join(BASE_DIR, "memoria/config_jarvis.json")

RESUMO_INTERVAL = 20
BUFFER_SIZE = 10
OFFSET_TEMPORAL = timedelta(hours=0)
MAX_CHAR_INPUT = 5000
MAX_AUDIO_CHARS = 1500

chats_ativos = {}
lock_chats = threading.Lock()

for folder in [AUDIO_DIR, HISTORY_DIR, STATIC_DIR]:
    if not os.path.exists(folder): os.makedirs(folder)

app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, "templates"),
            static_folder=STATIC_DIR,
            static_url_path='/static')
app.secret_key = 'jarvis_v11_ultra'
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")

# --- Helper de Impressão Segura ---
def safe_print(text):
    try: print(text)
    except: pass

def obter_horario_mundial(local="brasil"):
    fusos = {
        "brasil": ("America/Sao_Paulo", -3, "Brasília"),
        "brasilia": ("America/Sao_Paulo", -3, "Brasília"),
        "são paulo": ("America/Sao_Paulo", -3, "São Paulo"),
        "sao paulo": ("America/Sao_Paulo", -3, "São Paulo"),
        "portugal": ("Europe/Lisbon", 0, "Lisboa"),
        "lisboa": ("Europe/Lisbon", 0, "Lisboa"),
        "nova york": ("America/New_York", -5, "Nova York"),
        "new york": ("America/New_York", -5, "Nova York"),
        "londres": ("Europe/London", 0, "Londres"),
        "paris": ("Europe/Paris", 1, "Paris"),
        "tóquio": ("Asia/Tokyo", 9, "Tóquio"),
        "tokyo": ("Asia/Tokyo", 9, "Tóquio"),
        "china": ("Asia/Shanghai", 8, "Pequim"),
        "pequim": ("Asia/Shanghai", 8, "Pequim"),
        "dubai": ("Asia/Dubai", 4, "Dubai"),
        "sydney": ("Australia/Sydney", 11, "Sydney"),
        "utc": ("UTC", 0, "UTC"),
    }
    local_lower = local.lower().strip()
    fuso_info = None
    for key, info in fusos.items():
        if key in local_lower:
            fuso_info = info
            break
    if not fuso_info: fuso_info = fusos["brasil"]
    _, offset, nome = fuso_info
    utc_now = datetime.now(timezone.utc)
    local_time = utc_now + timedelta(hours=offset)
    return {
        "local": nome,
        "horario": local_time.strftime("%H:%M"),
        "data": local_time.strftime("%d/%m/%Y"),
        "offset": f"UTC{'+' if offset >= 0 else ''}{offset}",
        "completo": f"{local_time.strftime('%H:%M')} do dia {local_time.strftime('%d/%m/%Y')} em {nome} ({f'UTC{'+' if offset >= 0 else ''}{offset}'})"
    }

def detectar_pergunta_horario(texto):
    import unicodedata
    texto_lower = texto.lower()
    texto_sem_acento = ''.join(c for c in unicodedata.normalize('NFD', texto_lower) if unicodedata.category(c) != 'Mn')
    exclusoes = ["criador", "quem", "pasta", "arquivo", "existe", "mostrar", "listar", "abrir", "fechar", "deletar", "criar", "escrever", "codigo", "programa"]
    if any(ex in texto_sem_acento for ex in exclusoes): return None
    gatilhos_hora = ["que horas", "que hora", "que horario", "qual horario", "qual hora", "horas sao", "hora atual", "horario atual", "horas agora", "horario em", "hora em", "horas em"]
    encontrou_gatilho_hora = False
    for g in gatilhos_hora:
        g_sem_acento = ''.join(c for c in unicodedata.normalize('NFD', g) if unicodedata.category(c) != 'Mn')
        if g_sem_acento in texto_sem_acento:
            encontrou_gatilho_hora = True
            break
    locais = ["portugal", "lisboa", "brasil", "brasilia", "sao paulo", "nova york", "new york", "londres", "paris", "toquio", "tokyo", "china", "pequim", "dubai", "sydney", "utc"]
    menciona_local = any(local in texto_sem_acento for local in locais)
    menciona_hora = any(h in texto_sem_acento for h in ["hora", "horario"])
    if not encontrou_gatilho_hora and not (menciona_hora and menciona_local): return None
    for local in locais:
        local_sem_acento = ''.join(c for c in unicodedata.normalize('NFD', local) if unicodedata.category(c) != 'Mn')
        if local_sem_acento in texto_sem_acento:
            if local in ["brasilia"]: return "brasil"
            if local in ["toquio"]: return "tokyo"
            return local
    return "brasil"

def carregar_base_conhecimento():
    if os.path.exists(KNOWLEDGE_FILE):
        try:
            with open(KNOWLEDGE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return "\n".join([str(i.get('content', ''))[:200] for i in data[:20]])
        except: pass
    return "Base de conhecimento local não encontrada."

def extrair_fatos_da_mensagem(user_id: str, texto: str):
    prompt_extracao = f"""Analise a mensagem do usuário e extraia FATOS para memória de longo prazo.
Texto: "{texto}"\nRetorne APENAS um JSON puro lista de objetos: [{{"tipo": "...", "chave": "...", "valor": "..."}}]"""
    try:
        modelo_usado = MODELO_ATIVO if MODELO_ATIVO else "gpt-oss:120b-cloud"
        resp = client.chat.completions.create(model=modelo_usado, messages=[{"role": "user", "content": prompt_extracao}], temperature=0)
        content = resp.choices[0].message.content.replace("```json", "").replace("```", "").strip()
        dados = json.loads(content)
        lista_fatos = dados if isinstance(dados, list) else dados.get('fatos', [])
        if isinstance(lista_fatos, list):
            for fato in lista_fatos:
                if 'chave' in fato and 'valor' in fato:
                    chave = fato['chave'].lower().replace(" ", "_")
                    salvar_fato(user_id, fato.get('tipo', 'geral'), chave, str(fato['valor']))
                    if chave in ['nome', 'nome_preferido', 'apelido']: atualizar_nome_preferido(user_id, str(fato['valor']))
    except: pass

def processar_memoria(user_id: str):
    total_msgs = contar_mensagens(user_id)
    if total_msgs >= RESUMO_INTERVAL * 2:
        get_ou_criar_usuario(user_id)
        msgs_para_resumir = get_mensagens_para_resumir(user_id, 0, total_msgs - BUFFER_SIZE)
        if msgs_para_resumir: limpar_mensagens_antigas(user_id, BUFFER_SIZE)

# --- SISTEMA FINANCEIRO AVANÇADO (V12) ---
def processar_financas(user_id, texto):
    texto_lower = texto.lower()

    # === METAS ===
    if "definir meta" in texto_lower or "criar meta" in texto_lower:
        match_valor = re.search(r'(?:R$|r$|\$)?\s?(\d+(?:[.,]\d+)?)', texto)
        categoria = ""
        match_para = re.search(r'para\s+([a-zA-Zçãõáéíóú\s]+)', texto_lower)
        if match_para: categoria = match_para.group(1).strip().split()[0].title()
        if not categoria:
            match_de = re.search(r'meta (?:de|em)\s+([a-zA-Zçãõáéíóú]+)', texto_lower)
            if match_de: categoria = match_de.group(1).title()

        if match_valor and categoria:
            valor = float(match_valor.group(1).replace(',', '.'))
            definir_meta(user_id, categoria, valor)
            return f"✅ Meta de **{categoria}** definida: R$ {valor:.2f} /mês."

    # === OBJETIVOS ===
    if "novo objetivo" in texto_lower or "criar objetivo" in texto_lower or "criar cofrinho" in texto_lower:
        match_valor = re.search(r'(?:valor|de|meta)\s?(?:R$|r$|\$)?\s?(\d+(?:[.,]\d+)?)', texto_lower)
        try:
            palavras_chave = ["objetivo", "cofrinho", "meta"]
            inicio = -1
            for p in palavras_chave:
                idx = texto_lower.find(p)
                if idx != -1:
                    inicio = idx + len(p); break
            
            if inicio != -1:
                fim = texto_lower.find("valor")
                if fim == -1: fim = len(texto_lower)
                nome = texto[inicio:fim].strip().title().replace("De", "").replace("Para", "").strip()
                if match_valor and nome:
                    valor = float(match_valor.group(1).replace(',', '.'))
                    criar_objetivo(user_id, nome, valor)
                    return f"🆕 Novo Objetivo Criado: **{nome}** (Alvo: R$ {valor:.2f})."
        except: pass

    # === VISUALIZAÇÃO ===
    if "ver metas" in texto_lower or "minhas metas" in texto_lower:
        metas = get_metas(user_id)
        if not metas: return "Você ainda não definiu metas."
        res = "📊 **Suas Metas:**\n"
        for m in metas: res += f"- {m['categoria']}: R$ {m['valor_limite']:.2f}\n"
        return res

    if "ver objetivos" in texto_lower or "meus objetivos" in texto_lower:
        objs = get_objetivos(user_id)
        if not objs: return "Você não tem objetivos."
        res = "🆕 **Seus Objetivos:**\n"
        for o in objs:
            perc = (o['valor_atual'] / o['valor_alvo']) * 100 if o['valor_alvo'] > 0 else 0
            res += f"- {o['nome']}: R$ {o['valor_atual']:.2f} / {o['valor_alvo']:.2f} ({perc:.1f}%)\n"
        return res

    # === ASSINATURAS ===
    if "assinatura" in texto_lower or "conta fixa" in texto_lower:
        if any(x in texto_lower for x in ["remover", "cancelar", "apagar"]):
            return "SISTEMA: Função de remover assinatura ainda em desenvolvimento."
        
        match_valor = re.search(r'(?:R$|r$|\$)?\s?(\d+(?:[.,]\d+)?)', texto)
        match_dia = re.search(r'dia\s+(\d{1,2})', texto_lower)
        
        try:
            inicio = texto_lower.find("assinatura") + 10
            fim = len(texto_lower)
            if match_valor and match_valor.start() > inicio: fim = min(fim, match_valor.start())
            if match_dia and match_dia.start() > inicio: fim = min(fim, match_dia.start())
            nome = texto[inicio:fim].strip().title().replace("De", "").replace("Da", "").strip()
            
            if match_valor and match_dia and nome:
                valor = float(match_valor.group(1).replace(',', '.'))
                dia = int(match_dia.group(1))
                adicionar_assinatura(user_id, nome, valor, dia)
                return f"📅 Assinatura Registrada: **{nome}** (R$ {valor:.2f}, Dia {dia})."
        except: pass

    # === REMOÇÃO DE TRANSAÇÃO ===
    termos_remocao = ["apagar", "apague", "remover", "remova", "excluir", "exclua", "deletar"]
    if any(t in texto_lower for t in termos_remocao):
        valor_match = re.search(r'(?:R$|r$|\$)\s?(\d+(?:[.,]\d+)?)', texto)
        conn = sqlite3.connect(os.path.join("memoria", "jarvis_memoria.db"))
        cursor = conn.cursor()
        deleted_count = 0
        if valor_match:
            valor = float(valor_match.group(1).replace(',', '.'))
            cursor.execute("DELETE FROM financeiro WHERE user_id = ? AND valor BETWEEN ? AND ?", (user_id, valor - 0.1, valor + 0.1))
            deleted_count = cursor.rowcount
        conn.commit()
        # Recalcula
        cursor.execute("SELECT SUM(CASE WHEN tipo='entrada' THEN valor ELSE -valor END) FROM financeiro WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        novo_saldo = res[0] if res[0] else 0.0
        cursor.execute("UPDATE saldo SET valor = ?, atualizado_em = ? WHERE user_id = ?", (novo_saldo, datetime.now(), user_id))
        conn.commit(); conn.close()
        if deleted_count > 0: return f"SISTEMA: {deleted_count} transação(ões) removida(s). Novo Saldo: R$ {novo_saldo:.2f}"

    # === TRANSAÇÃO PADRÃO ===
    if any(p in texto_lower for p in ["atualize", "edite", "mude", "altere", "corrija", "formato"]): return None
    valor_match = re.search(r'(?:R$|r$|$)\s?(\d+(?:[.,]\d+)?)', texto)
    if not valor_match: return None
    
    valor = float(valor_match.group(1).replace(',', '.'))
    tipo = "saida"
    if any(w in texto_lower for w in ["recebi", "ganhei", "entrada", "depósito", "salário"]): tipo = "entrada"
    
    # Check duplicação (5min)
    conn = sqlite3.connect(os.path.join("memoria", "jarvis_memoria.db"))
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM financeiro WHERE user_id = ? AND valor = ? AND tipo = ? AND criado_em > datetime('now', '-5 minutes')", (user_id, valor, tipo))
    if cursor.fetchone():
        conn.close()
        return f"SISTEMA: Transação de R$ {valor:.2f} ignorada (duplicada)."
    conn.close()

    saldo_atual = get_saldo(user_id)
    novo_saldo = saldo_atual + valor if tipo == "entrada" else saldo_atual - valor
    atualizar_saldo(user_id, novo_saldo)
    adicionar_transacao(user_id, tipo, valor, texto[:50])
    return f"SISTEMA: {tipo.capitalize()} de R$ {valor:.2f} registrada. Saldo: R$ {novo_saldo:.2f}"

# --- PDF GENERATOR ---
def limpar_pdfs_antigos(manter_ultimos=5):
    try:
        pdf_dir = STATIC_DIR
        pdfs = [f for f in os.listdir(pdf_dir) if f.startswith("Extrato_") and f.endswith(".pdf")]
        if len(pdfs) > manter_ultimos:
            pdfs_com_data = [(f, os.path.getmtime(os.path.join(pdf_dir, f))) for f in pdfs]
            pdfs_ordenados = sorted(pdfs_com_data, key=lambda x: x[1], reverse=True)
            for pdf_antigo, _ in pdfs_ordenados[manter_ultimos:]:
                try: os.remove(os.path.join(pdf_dir, pdf_antigo))
                except: pass
    except: pass

def gerar_pdf_financeiro(user_id):
    print(f"[PDF] Iniciando geração para {user_id}...")
    if not PDF_AVAILABLE: return None
    limpar_pdfs_antigos(10)

    try:
        transacoes = get_transacoes(user_id, limite=100)
        # Categorização simples para V12 Mobile
        cc_itens = []
        total_cc = 0
        
        transacoes_cronologicas = sorted(transacoes, key=lambda x: x['criado_em'])
        for t in transacoes_cronologicas:
            desc = str(t.get('descricao', 'Sem descrição')).encode('latin-1', 'replace').decode('latin-1')
            tipo = str(t.get('tipo', 'saida')).lower()
            valor = float(t.get('valor', 0.0))
            raw_date = t.get('criado_em', '')
            if hasattr(raw_date, 'strftime'): data_str = raw_date.strftime("%d/%m")
            else: data_str = str(raw_date)[8:10] + "/" + str(raw_date)[5:7]
            
            item = {"data": data_str, "desc": desc, "valor": valor, "tipo": tipo}
            cc_itens.append(item)
            if tipo == 'entrada': total_cc += valor
            else: total_cc -= valor

        pdf = FPDF()
        pdf.add_page()
        pdf.set_fill_color(0, 0, 0)
        pdf.rect(0, 0, 210, 40, 'F')
        pdf.set_font("Arial", 'B', 18)
        pdf.set_text_color(0, 255, 234)
        pdf.set_xy(10, 10)
        pdf.cell(190, 10, txt="RELATÓRIO FINANCEIRO JARVIS", ln=True, align='C')
        
        pdf.set_font("Arial", 'I', 11)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(10, 22)
        pdf.cell(190, 8, txt="Resumo Mobile", ln=True, align='C')
        pdf.ln(20)

        # Tabela
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(30, 8, "DATA", 1, 0, 'C')
        pdf.cell(110, 8, "DESCRIÇÃO", 1, 0, 'L')
        pdf.cell(50, 8, "VALOR", 1, 1, 'C')
        
        pdf.set_font("Arial", size=10)
        for it in cc_itens:
            pdf.cell(30, 8, it['data'], 1, 0, 'C')
            pdf.cell(110, 8, it['desc'], 1, 0, 'L')
            if it['tipo'] == 'entrada': pdf.set_text_color(0, 150, 0)
            else: pdf.set_text_color(180, 0, 0)
            pdf.cell(50, 8, f"R$ {it['valor']:.2f}", 1, 1, 'C')
            pdf.set_text_color(0, 0, 0)

        pdf.ln(10)
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(190, 10, f"SALDO ATUAL: R$ {total_cc:,.2f}", 0, 1, 'C')

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Extrato_{timestamp}.pdf"
        filepath = os.path.join(STATIC_DIR, filename)
        pdf.output(filepath)
        return filename
    except Exception as e:
        print(f"[PDF] Erro: {e}")
        return None

def processar_comando_iot(user_id, texto):
    if not TVController: return None
    texto_lower = texto.lower()
    acao = None
    nums = [int(s) for s in re.findall(r'\b\d+\b', texto)]
    quantidade = nums[0] if nums else 1

    if any(x in texto_lower for x in ["ligar tv", "liga a tv", "ligue a tv", "acender tv", "ligar teve", "liga a teve", "liga tv", "ligue tv", "liga teve"]): acao = "ligar"
    elif any(x in texto_lower for x in ["desligar tv", "desliga a tv", "desligue a tv", "apagar tv", "apaga a tv", "desligar teve", "desliga tv", "desligue tv", "apaga tv", "desliga teve"]): acao = "desligar"    
    elif "digite" in texto_lower or "escreva" in texto_lower: acao = "type"; quantidade = texto_lower.replace("digite", "").strip()
    elif "abrir" in texto_lower:
        acao = "open_app"
        for app in ["youtube", "netflix", "spotify"]:
            if app in texto_lower: quantidade = app; break

    gatilhos_up = ["aumentar volume", "aumenta o volume", "aumente o volume", "sobe o volume", "subir o volume", "mais volume", "volume mais", "aumentar som", "aumenta o som", "sobe o som", "mais som"]
    gatilhos_down = ["abaixar volume", "abaixa o volume", "baixe o volume", "baixa o volume", "diminuir volume", "diminua o volume", "desce o volume", "menos volume", "volume menos", "abaixar som", "baixe o som", "menos som", "diminua o som"]

    if any(g in texto_lower for g in gatilhos_up): acao = "vol_up"; quantidade = 5 if not nums else nums[0]
    elif any(g in texto_lower for g in gatilhos_down): acao = "vol_down"; quantidade = 5 if not nums else nums[0]
    elif "mudo" in texto_lower or "silenciar" in texto_lower: acao = "mute"
    elif "cima" in texto_lower: acao = "up"
    elif "baixo" in texto_lower: acao = "down"
    elif "esquerda" in texto_lower: acao = "left"
    elif "direita" in texto_lower: acao = "right"
    elif "ok" in texto_lower or "confirmar" in texto_lower: acao = "enter"
    elif "voltar" in texto_lower: acao = "back"
    elif "home" in texto_lower: acao = "home"

    if not acao: return None
    fatos = get_fatos(user_id)
    tv_ip = next((f['valor'] for f in fatos if f['chave'] in ['tv_ip', 'ip_tv']), None)
    tv_mac = next((f['valor'] for f in fatos if f['chave'] in ['tv_mac', 'mac_tv']), None)
    if not tv_ip: return "SISTEMA: Preciso do IP da TV primeiro."

    controller = TVController(tv_ip, tv_mac)
    return f"SISTEMA: {getattr(controller, acao)(quantidade) if acao in ['vol_up', 'vol_down', 'up', 'down', 'left', 'right', 'type_text', 'open_app'] else getattr(controller, acao)()}"

def processar_comandos_sistema(resposta_llm, user_id, profundidade=0):
    if profundidade > 3: return "\n[SISTEMA] Limite de auto-correção atingido."
    output_extra = ""
    erros_detectados = []
    COMANDOS_PROIBIDOS = ["format c:", "format d:", "del /s", "rm -rf", "shutdown /", "shutdown -"]       

    searches = re.findall(r'\[\[SEARCH: (.*?)\]\]', resposta_llm, re.DOTALL)
    for query in searches:
        print(f"[DEBUG] Processando busca: {query}", flush=True)
        try:
            res_busca = pesquisar_web(query.strip())
            if not res_busca or len(res_busca) < 5: res_busca = ""
        except: res_busca = ""
        if res_busca: output_extra += f"\n[CONTEXTO_BUSCA_INTERNO]: {res_busca[:500]}\n"

    cmds = re.findall(r'\[\[CMD: (.*?)\]\]', resposta_llm, re.DOTALL)
    for cmd in cmds:
        cmd_lower = cmd.lower()
        if any(p in cmd_lower for p in COMANDOS_PROIBIDOS):
            if not ("format" in cmd_lower and not any(x in cmd_lower for x in ["c:", "d:", "/fs:"])):
                output_extra += f"\n> **BLOQUEADO (SEGURANÇA):** `{cmd}`\n"; continue

        print(f"[ACAO] Executando: {cmd}...", flush=True)
        res = manipulador.executar_comando_terminal(cmd.strip())
        if "--- ERROS ---" in res:
            erros_detectados.append(f"Erro no comando '{cmd}': {res}")
            output_extra += f"\n> Falha em: `{cmd.strip()}`\n"
        else:
            output_extra += f"\n> Comando: `{cmd.strip()}`\n```powershell\n{res}\n```\n"

    reads = re.findall(r'\[\[READ: (.*?)\]\]', resposta_llm, re.DOTALL)
    for path in reads:
        content = manipulador.ler_arquivo(path.strip())
        output_extra += f"\n> Arquivo: `{path.strip()}`\n```python\n{content[:1000]}\n```\n"

    autos = re.findall(r'\[\[AUTO: (.*?)\]\]', resposta_llm, re.DOTALL)
    for acao_raw in autos:
        try:
            partes = acao_raw.split("|")
            cmd_auto = partes[0].strip().lower()
            arg_auto = partes[1].strip() if len(partes) > 1 else ""
            res_auto = "Comando desconhecido."
            if cmd_auto == "abrir_programa": res_auto = pc.abrir_programa(arg_auto)
            elif cmd_auto == "fechar_programa": res_auto = pc.fechar_programa(arg_auto)
            elif cmd_auto == "minimizar_tudo": res_auto = pc.minimizar_tudo()
            elif cmd_auto == "digitar": res_auto = pc.digitar(arg_auto)
            elif cmd_auto == "pressionar": res_auto = pc.pressionar(arg_auto)
            elif cmd_auto == "mover_mouse":
                coords = arg_auto.split(",")
                if len(coords) == 2: res_auto = pc.mover_mouse(int(coords[0]), int(coords[1]))
            elif cmd_auto == "clicar": res_auto = pc.clicar()
            output_extra += f"\n> [AUTO]: {res_auto}\n"
        except Exception as e: output_extra += f"\n> [ERRO AUTO]: {e}\n"

    asks = re.findall(r'\[\[ASK_GEMINI: (.*?)\]\]', resposta_llm, re.DOTALL)
    for pedido in asks:
        resposta_gemini = consultar_gemini_nuvem(pedido)
        output_extra += f"\n**GEMINI SUPERVISOR:**\n{resposta_gemini}\n"

    if erros_detectados and profundidade < 5:
        print(f"[AUTO-FIX] Tentativa {profundidade+1} de 5...", flush=True)
        prompt = f"""ERRO CRÍTICO DE SISTEMA DETECTADO. TENTE OUTRA ESTRATÉGIA.
ERROS: {chr(10).join(erros_detectados)}
OBJETIVO: Corrigir comando para Windows.
RETORNE APENAS O COMANDO CORRIGIDO no formato [[CMD: ...]]."""
        resp = client.chat.completions.create(model=MODELO_ATIVO, messages=[{"role": "user", "content": prompt}])
        output_extra += f"\n\n[Correcao {profundidade+1}]:\n" + processar_comandos_sistema(resp.choices[0].message.content, user_id, profundidade + 1)

    return output_extra

def gerar_resposta_jarvis(user_id, texto):
    if len(texto) > MAX_CHAR_INPUT: texto = texto[:MAX_CHAR_INPUT] + "..."
    
    try:
        info_iot = processar_comando_iot(user_id, texto)
    except Exception as e:
        print(f"[ERRO IOT] {e}")
        info_iot = None

    try:
        info_financeira = processar_financas(user_id, texto)
    except Exception as e:
        print(f"[ERRO FINANCAS] {e}")
        info_financeira = None

    usuario = get_ou_criar_usuario(user_id)
    buffer_msgs = get_ultimas_mensagens(user_id, BUFFER_SIZE)
    saldo_atual = get_saldo(user_id)
    fatos = get_fatos(user_id)
    
    fatos_texto = ""
    if fatos: fatos_texto = "ESTADO ATUAL E MEMÓRIA DE FATOS:\n" + "\n".join([f"- {f['chave']}: {f['valor']}" for f in fatos])

    transacoes_db = get_transacoes(user_id, limite=10)
    financas_contexto = f"SALDO ATUAL: R$ {saldo_atual:.2f}\nÚLTIMAS TRANSAÇÕES:"
    if transacoes_db:
        for t in transacoes_db: financas_contexto += f"\n- {t['tipo'].upper()}: R$ {t['valor']:.2f} | {t['descricao']}"
    else: financas_contexto += "\n(Sem transações)"

    nome_usuario = usuario.get('nome_preferido') or f"Usuário {str(user_id)[-4:]}"
    agora_br = (datetime.now(timezone.utc) + OFFSET_TEMPORAL).astimezone(timezone(timedelta(hours=-3)))   
    
    system_prompt = f"""VOCÊ É J.A.R.V.I.S., UMA IA ASSISTENTE LEAL, ESPIRITUOSA E EFICIENTE.
DATA: {agora_br.strftime('%d/%m/%Y %H:%M')}. USUÁRIO MESTRE: {nome_usuario}.

=== SUA PERSONALIDADE ===
1. Você não é um robô chato. Você é o Jarvis. Tenha personalidade.
2. Use o contexto passivo (o que foi ouvido antes) para surpreender o usuário.
3. Se o usuário perguntar "o que eu disse?", responda com precisão usando o histórico.
4. Respostas curtas e diretas são melhores para chat por voz.

=== FINANÇAS (V12) ===
- Você tem acesso total ao banco de dados.
- Se o usuário pedir PDF/Relatório: Responda "Gerando seu relatório agora..." para ativar a trigger.

CONTEXTO:
{usuario['resumo_conversa']}
{fatos_texto}
{financas_contexto}
{info_iot if info_iot else ""}
{info_financeira if info_financeira else ""}
"""

    msgs = [{"role": "system", "content": system_prompt}] + [{"role": m["role"], "content": m["content"]} for m in buffer_msgs] + [{"role": "user", "content": texto}]
    texto_lower = texto.lower()

    # --- Visão e Arquivos (Simplificado) ---
    descricao_visual = ""
    imagem_b64 = None
    if any(k in texto_lower for k in ["ler tela", "o que está na tela"]):
        imagem_b64 = capturar_tela_base64()
        if imagem_b64: descricao_visual = f"\n[SISTEMA VISUAL]: Descrição da tela: {analisar_imagem(imagem_b64)}"
    if descricao_visual: texto += descricao_visual

    # --- Resposta Horário ---
    local_horario = detectar_pergunta_horario(texto)
    if local_horario:
        info = obter_horario_mundial(local_horario)
        try:
            h_str, m_str = info['horario'].split(':')
            h = int(h_str)
            m = int(m_str)
            lbl_h = "hora" if h == 1 else "horas"
            lbl_m = "minuto" if m == 1 else "minutos"
            msg_voz = f"{h} {lbl_h}"
            if m > 0:
                msg_voz += f" e {m} {lbl_m}"
            res = f"São {msg_voz}."
        except:
            res = f"Agora são {info['horario']}."
            
        adicionar_mensagem(user_id, "user", texto)
        adicionar_mensagem(user_id, "assistant", res)
        return {"text": res, "pdf": None}

    # --- IOT Return ---
    if "tv" in texto_lower and info_iot:
         return {"text": info_iot, "pdf": None}

    # --- LLM ---
    try:
        resp = client.chat.completions.create(model=MODELO_ATIVO, messages=msgs)
        res_txt = resp.choices[0].message.content
        
        # --- PDF TRIGGER ---
        pdf_gerado = None
        user_quer_pdf = any(x in texto_lower for x in ["pdf", "relatório", "extrato"])
        ia_diz_pdf = any(x in res_txt.lower() for x in ["gerando", "enviando", "segue"]) and "pdf" in res_txt.lower()
        
        if user_quer_pdf or ia_diz_pdf:
            pdf_gerado = gerar_pdf_financeiro(user_id)
            if pdf_gerado: res_txt += "\n\n📄 [Relatório Anexado]"

        if "[[" in res_txt and "]]" in res_txt:
            output_sys = processar_comandos_sistema(res_txt, user_id)
            if output_sys: res_txt += f"\n\n--- SISTEMA ---\n{output_sys}"

        adicionar_mensagem(user_id, "user", texto)
        adicionar_mensagem(user_id, "assistant", res_txt)

        def bg_task():
            try:
                if "[ANEXO IMAGEM" not in texto: extrair_fatos_da_mensagem(user_id, texto)
                processar_memoria(user_id)
            except: pass
        threading.Thread(target=bg_task, daemon=True).start()

        res_txt = re.sub(r'\n[CONTEXTO_BUSCA_INTERNO]:.*?(?=\n|$)', '', res_txt, flags=re.DOTALL)
        res_txt = res_txt.replace("--- SISTEMA ---", "").strip()
        
        return {"text": res_txt, "pdf": pdf_gerado}
    except Exception as e: return {"text": f"Erro: {e}", "pdf": None}

def dividir_texto_para_audio(texto, max_chars=MAX_AUDIO_CHARS):
    if len(texto) <= max_chars: return [texto]
    segmentos = []
    texto_restante = texto
    while len(texto_restante) > max_chars:
        ponto_corte = max_chars
        for delimitador in ['. ', '! ', '? ', '\n', ', ']:
            ultimo_delim = texto_restante[:max_chars].rfind(delimitador)
            if ultimo_delim > max_chars * 0.5:
                ponto_corte = ultimo_delim + len(delimitador)
                break
        segmento = texto_restante[:ponto_corte].strip()
        if segmento: segmentos.append(segmento)
        texto_restante = texto_restante[ponto_corte:].strip()
    if texto_restante: segmentos.append(texto_restante)
    return segmentos

async def _tts_async(text, path):
    try:
        with open(CONFIG_FILE, 'r') as f: speed = json.load(f).get('velocidade', '+0%')
    except: speed = '+0%'
    comm = edge_tts.Communicate(text, "pt-BR-AntonioNeural", rate=speed)
    await comm.save(path)

def gerar_audio_b64(text):
    if not text or len(text.strip()) == 0: return None
    
    # --- SANITIZAÇÃO DE ÁUDIO AGRESSIVA ---
    text_limpo = text
    # Remove tags de sistema
    for tag in ["[SISTEMA]", "[CMD]", "SISTEMA:", "Traceback", "Error:", "> Comando", "**RESULTADO DA BUSCA WEB:**", "[CONTEXTO_BUSCA_INTERNO]"]:
        text_limpo = text_limpo.replace(tag, "")
    
    # Remove Markdown e Códigos
    text_limpo = re.sub(r'```.*?```', '', text_limpo, flags=re.DOTALL) 
    text_limpo = re.sub(r'\[\[.*?\]\]', '', text_limpo)
    
    # Substitui quebras de linha por pausas
    text_limpo = text_limpo.replace("\n", ". ")
    
    # Mantém APENAS letras, números e pontuação básica
    text_limpo = re.sub(r'[^\w\s,.?!çáéíóúãõàêôüÇÁÉÍÓÚÃÕÀÊÔÜ\-]', '', text_limpo)
    
    # Remove espaços duplos
    text_limpo = re.sub(r'\s+', ' ', text_limpo).strip()

    if not text_limpo or len(text_limpo) < 2: return None 
    print(f"[AUDIO] Gerando voz para: {text_limpo[:50]}...", flush=True)

    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp: path = tmp.name
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try: new_loop.run_until_complete(_tts_async(text_limpo, path))
        finally: new_loop.close()

        if os.path.exists(path) and os.path.getsize(path) > 100:
            with open(path, "rb") as f: b64 = base64.b64encode(f.read()).decode('utf-8')
            os.remove(path)
            return b64
        else: return None
    except Exception as e: 
        print(f"[ERRO CRÍTICO AUDIO]: {e}", flush=True)
        return None

def gerar_multiplos_audios(text):
    if not text or len(text.strip()) == 0: return []
    text_limpo = text
    for tag in ["[SISTEMA]", "[CMD]", "SISTEMA:", "Traceback", "Error:", "> Comando", "**RESULTADO DA BUSCA WEB:**", "[CONTEXTO_BUSCA_INTERNO]"]:
        text_limpo = text_limpo.replace(tag, "")
    text_limpo = re.sub(r'```.*?```', '', text_limpo, flags=re.DOTALL)
    text_limpo = re.sub(r'\[\[.*?\]\]', '', text_limpo)
    text_limpo = re.sub(r'[^\w\s,.?!çáéíóúãõàêôüÇÁÉÍÓÚÃÕÀÊÔÜ]', '', text_limpo)   
    text_limpo = text_limpo.strip()

    if not text_limpo or len(text_limpo) < 2: return []
    segmentos = dividir_texto_para_audio(text_limpo)
    if len(segmentos) > 1: print(f"[AUDIO] Texto longo. {len(segmentos)} partes...", flush=True)      
    audios = []
    for i, segmento in enumerate(segmentos):
        audio_b64 = gerar_audio_b64(segmento)
        if audio_b64:
            audios.append({"parte": i + 1, "total": len(segmentos), "audio": audio_b64})
    return audios

def transcrever_audio(base64_data):
    if not base64_data: 
        print("[AUDIO] Erro: Dados base64 vazios.")
        return None
    
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        AudioSegment.converter = ffmpeg_path
    else:
        print("[AUDIO] AVISO: FFmpeg não encontrado no PATH. Transcrição pode falhar.")

    temp_p = None
    temp_wav = None
    
    try:
        audio_bytes = base64.b64decode(base64_data)
        # WhatsApp usa OGG/Opus. Vamos salvar como .ogg primeiro.
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as t:
            t.write(audio_bytes)
            temp_p = t.name
        
        temp_wav = temp_p + ".wav"
        
        print(f"[AUDIO] Convertendo {temp_p} para WAV...", flush=True)
        try:
            audio = AudioSegment.from_file(temp_p)
            audio.export(temp_wav, format="wav")
        except Exception as conv_err:
            print(f"[AUDIO] Erro na conversão para WAV: {conv_err}")
            return "[ERRO AUDIO FORMATO]"

        r = sr.Recognizer()
        with sr.AudioFile(temp_wav) as source:
            print("[AUDIO] Reconhecendo fala (Google API)...", flush=True)
            audio_data = r.record(source)
            texto = r.recognize_google(audio_data, language="pt-BR")
            print(f"[AUDIO] Transcrição Sucesso: '{texto}'")
            return texto
    except sr.UnknownValueError:
        print("[AUDIO] Google não entendeu o áudio (silêncio ou ruído).")
        return None
    except sr.RequestError as e:
        print(f"[AUDIO] Erro no serviço de transcrição: {e}")
        return None
    except Exception as e:
        print(f"[AUDIO] Erro inesperado na transcrição: {e}")
        return None
    finally:
        # Limpeza de arquivos temporários
        try:
            if temp_p and os.path.exists(temp_p): os.remove(temp_p)
            if temp_wav and os.path.exists(temp_wav): os.remove(temp_wav)
        except: pass

def analisar_imagem(base64_data):
    try:
        response = client_ollama.generate(model='llama3.2-vision', prompt="Descreva esta imagem em detalhes (em português), focando no que é relevante para o usuário.", images=[base64_data], stream=False)     
        return response['response']
    except Exception as e: return "[Erro ao processar imagem. Verifique se 'llama3.2-vision' está instalado no Ollama.]"

def capturar_tela_base64():
    try:
        screenshot = ImageGrab.grab()
        buffered = io.BytesIO()
        screenshot.save(buffered, format="JPEG", quality=70)
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    except: return None

def ler_imagem_local_base64(caminho):
    try:
        with open(caminho.strip(), "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except: return None

def otimizar_imagem_para_ocr(img):
    img = ImageOps.grayscale(img)
    if img.width > 3000:
        scale = 3000 / float(img.width)
        img = img.resize((3000, int(img.height * scale)), Image.NEAREST)
    return img

def extrair_texto_ocr(caminho_ou_imagem):
    try:
        if not os.path.exists(pytesseract.pytesseract.tesseract_cmd): return "ERRO: Tesseract OCR não encontrado."
        img = Image.open(caminho_ou_imagem) if isinstance(caminho_ou_imagem, str) else caminho_ou_imagem  
        img = otimizar_imagem_para_ocr(img)
        return f"TEXTO EXTRAÍDO:\n{pytesseract.image_to_string(img, lang='por', config='--oem 1 --psm 3')}"
    except Exception as e: return f"[ERRO OCR] Falha: {e}"

# --- Rotas ---

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/')
def index(): return render_template('index.html')

@app.route('/api/whatsapp', methods=['POST'])
def api_whatsapp():
    try:
        print("\n[WHATSAPP API] --- Nova Requisição ---", flush=True)
        data = request.json
        if not data:
            return jsonify({"error": "No JSON data"}), 400

        sender = data.get('sender', 'Patrick')
        texto = data.get('text', '')
        chat_id = data.get('chat_id', sender)
        
        print(f"[WHATSAPP API] Sender: {sender} | ChatID: {chat_id}", flush=True)
        print(f"[WHATSAPP API] Texto Base: '{texto}'", flush=True)

        with lock_chats:
            if chat_id not in chats_ativos: chats_ativos[chat_id] = {"processando": True, "fila": [], "resultados": []}
            else: chats_ativos[chat_id]["processando"] = True

        if data.get('audio_data'):
            trans = transcrever_audio(data['audio_data'])
            if trans: texto = f"{texto} {trans}".strip()
            else: 
                 if not texto.strip(): texto = "SISTEMA: Áudio recebido mas não entendido."

        if not texto.strip() and not data.get('image_data'):
             return jsonify({"response": "🔇 Não consegui ouvir nada.", "chat_id": chat_id})

        if data.get('image_data'):
            try:
                img_bytes = base64.b64decode(data['image_data'])
                img = Image.open(io.BytesIO(img_bytes))
                texto_ocr = extrair_texto_ocr(img)
                if "ERRO" not in texto_ocr:
                    if len(texto_ocr) > 1500: texto_ocr = texto_ocr[:1500] + "\n[...]"
                    texto += f"\n[ANEXO IMAGEM - OCR]: {texto_ocr}"
                else:
                    desc_visual = analisar_imagem(data['image_data'])
                    texto += f"\n[ANEXO IMAGEM - VISÃO]: {desc_visual}"
            except Exception as e:
                print(f"[WHATSAPP API] Erro ao processar imagem: {e}", flush=True)

        print(f"[WHATSAPP API] Gerando resposta...", flush=True)
        
        # CHAMA BRAIN (Retorna DICT agora)
        resultado = gerar_resposta_jarvis(sender, texto)
        
        # Normaliza resultado
        if isinstance(resultado, dict):
            res_txt = resultado.get('text', '...')
            pdf_anexo = resultado.get('pdf')
        else:
            res_txt = str(resultado)
            pdf_anexo = None

        if not res_txt or not res_txt.strip(): res_txt = "..."

        print(f"[WHATSAPP API] Resposta: {len(res_txt)} chars. PDF: {pdf_anexo}", flush=True)
        
        audios = gerar_multiplos_audios(res_txt)

        with lock_chats:
            if chat_id in chats_ativos:
                chats_ativos[chat_id]["processando"] = False
                chats_ativos[chat_id]["resultados"].append({"response": res_txt, "audios": audios, "timestamp": time.time()})

        # JSON Final
        response_data = {
            "response": res_txt,
            "audio_response": audios[0]["audio"] if audios else None,
            "audio_parts": audios,
            "total_parts": len(audios),
            "chat_id": chat_id
        }
        
        # Anexo PDF (Base64)
        if pdf_anexo:
            pdf_path = os.path.join(STATIC_DIR, pdf_anexo)
            if os.path.exists(pdf_path):
                try:
                    with open(pdf_path, "rb") as f: response_data["attachment"] = base64.b64encode(f.read()).decode('utf-8')
                    response_data["attachment_name"] = pdf_anexo
                except: pass

        return jsonify(response_data)
    except Exception as e:
        print(f"[WHATSAPP API] ERRO CRÍTICO: {e}", flush=True)
        import traceback; traceback.print_exc()
        return jsonify({"response": "Erro interno no servidor Jarvis.", "error": str(e)}), 500

@socketio.on('fala_usuario')
def handle_web(data):
    # Identificação Única de Sessão (Web/Mobile)
    # Se o cliente mandar user_id, usa. Se não, usa o ID da sessão do socket (único por aba/conexão)
    user_id = data.get('user_id')
    if not user_id or user_id == "Patrick":
        # Prefixo 'web_' para diferenciar visualmente no banco
        user_id = f"web_{request.sid[:8]}" 
    
    print(f"[WEB/SOCKET] Processando mensagem de: {user_id}")
    
    resultado = gerar_resposta_jarvis(user_id, data.get('text'))
    
    if isinstance(resultado, dict):
        res_txt = resultado.get('text', '')
        pdf_anexo = resultado.get('pdf')
    else:
        res_txt = str(resultado)
        pdf_anexo = None

    emit('bot_msg', {'data': res_txt})
    if pdf_anexo:
        emit('bot_msg', {'data': f"<a href='/static/{pdf_anexo}' target='_blank'>📄 Baixar Relatório PDF</a>"})

STOPWORDS_PASSIVAS = [
    "sous-titres", "subtitles", "legendas", "amara.org", "comunidade", 
    "fale agora", "ouvindo", "nenhuma fala", "tente novamente", "teclado"
]

@socketio.on('passive_log')
def handle_passive_log(data):
    global LAST_PROCESSED_TEXT, LAST_PROCESSED_TIME
    user_id = data.get('user_id', 'Mestre')
    texto = data.get('text', '').strip()
    if not texto or len(texto) < 5: return
    
    current_time = time.time()
    if texto == LAST_PROCESSED_TEXT and (current_time - LAST_PROCESSED_TIME) < 3.0: return
    LAST_PROCESSED_TEXT = texto
    LAST_PROCESSED_TIME = current_time
    
    texto_lower = texto.lower()
    if any(sw in texto_lower for sw in STOPWORDS_PASSIVAS): return
    print(f"[PASSIVE] Memorizando: '{texto}'")
    threading.Thread(target=adicionar_mensagem, args=(user_id, "user", f"[CONTEXTO AMBIENTE]: {texto}")).start()

def classificar_intencao(texto):
    try:
        resp = client.chat.completions.create(
            model=MODELO_ATIVO,
            messages=[{"role": "user", "content": f"Classifique a frase em [COMANDO], [BUSCA] ou [CONVERSA]. Frase: {texto}"}],
            max_tokens=10
        )
        cat = resp.choices[0].message.content.strip().upper()
        if "COMANDO" in cat: return "COMANDO"
        if "BUSCA" in cat: return "BUSCA"
        return "CONVERSA"
    except: return "CONVERSA"

@socketio.on('active_command')
def handle_active_command(data):
    global LAST_USER_INPUT, LAST_COMMAND_TIME, LAST_BOT_RESPONSE
    user_id = data.get('user_id', 'Mestre')
    text = data.get('text', '').strip()
    if not text: return

    # --- 1. Lógica de "Barge-in" (Interrupção) ---
    texto_lower = text.lower()
    comandos_parada = ["pare", "parar", "silêncio", "silencio", "stop", "chega", "fique quieto"]
    
    # Se disser APENAS "Jarvis", ou comandos de parada
    if texto_lower == "jarvis" or any(cmd == texto_lower for cmd in comandos_parada) or "jarvis, pare" in texto_lower:
        print(f"[INTERRUPÇÃO] Comando de parada recebido: {text}")
        socketio.emit('force_stop_playback', {'user_id': user_id}) # Cliente deve tratar isso parando o player
        return

    # --- 2. Cancelamento de Eco (Auto-escuta) ---
    if LAST_BOT_RESPONSE:
        ratio = SequenceMatcher(None, texto_lower, LAST_BOT_RESPONSE.lower()).ratio()
        if ratio > 0.85: # 85% de similaridade
            print(f"[ECO DETECTADO] Ignorando entrada (Similaridade: {ratio:.2f}): '{text}'")
            return
        # Verifica se o texto ouvido está contido na última resposta (comum em ecos parciais)
        if len(text) > 15 and text.lower() in LAST_BOT_RESPONSE.lower():
             print(f"[ECO PARCIAL] Ignorando entrada contida na resposta anterior: '{text}'")
             return

    tempo_atual = time.time()
    if text == LAST_USER_INPUT["text"] and (tempo_atual - LAST_USER_INPUT["time"] < 3.0): return
    LAST_USER_INPUT = {"text": text, "time": tempo_atual}
    print(f"\n[COMANDO RECEBIDO] {user_id}: {text}")

    try: adicionar_mensagem(user_id, "user", text)
    except: pass

    socketio.emit('status_update', {'status': 'PROCESSANDO...'})
    
    # Se o usuário falou algo novo enquanto o bot falava, forçamos parada do áudio anterior também
    socketio.emit('force_stop_playback', {'user_id': user_id})

    resultado = gerar_resposta_jarvis(user_id, text)
    
    if isinstance(resultado, dict): res_txt = resultado['text']
    else: res_txt = str(resultado)

    # Atualiza a memória de eco
    LAST_BOT_RESPONSE = res_txt

    if res_txt:
        try: adicionar_mensagem(user_id, "assistant", res_txt)
        except: pass
        audio_b64 = gerar_audio_b64(res_txt)
        try:
            socketio.emit('bot_response', {'text': res_txt, 'audio': audio_b64, 'continue_conversation': True})
        except Exception as e_sock:
            print(f"[AVISO] Falha ao enviar resposta ao cliente (conexão perdida?): {e_sock}")

def processar_automacao_silenciosa(comando_texto):
    try:
        from sistema.automacao import automacao_rapida
        automacao_rapida(comando_texto)
    except Exception as e: print(f"[AUTOMACAO BG] Erro: {e}")

# --- Utilitários de Modelo ---
import requests

def get_installed_models():
    try:
        resp = requests.get("http://127.0.0.1:11434/api/tags", timeout=0.5)
        if resp.status_code == 200:
            return [m.get('name', '?') for m in resp.json().get('models', [])]
    except: pass
    return ['gpt-oss:120b-cloud']

@socketio.on('connect') 
def handle_connect():
    emit('lista_modelos', {'modelos': get_installed_models(), 'atual': MODELO_ATIVO})

@socketio.on('listar_modelos')
def handle_models():
    emit('lista_modelos', {'modelos': get_installed_models(), 'atual': MODELO_ATIVO})

@socketio.on('trocar_modelo')
def handle_model_change(data):
    global MODELO_ATIVO
    MODELO_ATIVO = data.get('modelo')
    emit('log', {'data': f"Modelo: {MODELO_ATIVO}"})

def gerar_qrcode_conexao(url):
    if qrcode is None: return
    try:
        qr_img = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr_img.add_data(url); qr_img.make(fit=True)
        img = qr_img.make_image(fill_color="black", back_color="white")
        qr_path = os.path.join(BASE_DIR, "connect_qr.png")
        img.save(qr_path)
        if sys.platform == 'win32': os.startfile(qr_path)
    except: pass

if __name__ == '__main__':
    import logging
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    logging.getLogger('socketio').setLevel(logging.ERROR)
    logging.getLogger('engineio').setLevel(logging.ERROR)

    print("\n" * 2)
    print("=========================================")
    print("   JARVIS V12 - SISTEMA INTEGRADO")
    print("=========================================")

    print("[REDE] Iniciando Tunel Cloudflare...", flush=True)
    try:
        from pycloudflared import try_cloudflare
        public_url_obj = try_cloudflare(port=5000)
        public_url = public_url_obj.tunnel
        print(f"\nACESSO REMOTO LIBERADO: {public_url}\n", flush=True)

        if not os.path.exists("docs"): os.makedirs("docs")
        with open(os.path.join("docs", "LINK_JARVIS.txt"), "w") as f: f.write(public_url)
        gerar_qrcode_conexao(public_url)
    except:
        print("[REDE] Fallback Local", flush=True)
        gerar_qrcode_conexao("http://localhost:5000")

    def start_zap():
        print("[SISTEMA] Disparando integração WhatsApp...", flush=True)
        try:
            subprocess.Popen(["cmd", "/c", "start", "INICIAR_WHATSAPP.bat"], shell=True, cwd=BASE_DIR)
        except Exception as e: print(f"[ERRO] Falha Zap: {e}")

    threading.Thread(target=start_zap, daemon=True).start()
    print("[SISTEMA] Servidor Online.", flush=True)
    socketio.run(app, debug=False, port=5000, host='0.0.0.0', allow_unsafe_werkzeug=True)