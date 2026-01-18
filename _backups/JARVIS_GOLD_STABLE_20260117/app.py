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

# GLOBAIS
try:
    import qrcode
except ImportError:
    qrcode = None

LAST_USER_INPUT = {"text": "", "time": 0}
LAST_PROCESSED_TEXT = ""
LAST_PROCESSED_TIME = 0
LAST_RESPONSE_HASH = {"text": "", "time": 0}

# --- LOCK GLOBAL ANTI-CRASH (CONCORRÊNCIA) ---
import threading
COMMAND_LOCK = threading.Lock()
LAST_COMMAND_TIME = 0
COMMAND_COOLDOWN = 3.0  # Segundos de cooldown entre comandos

# --- Configurações Iniciais ---
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.environ['OMP_THREAD_LIMIT'] = '1'
os.environ['TESSDATA_PREFIX'] = os.path.join(BASE_DIR, "tessdata")

CAMINHO_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(CAMINHO_TESSERACT):
    pytesseract.pytesseract.tesseract_cmd = CAMINHO_TESSERACT

# Importa o módulo de memória SQLite com tratamento de erro
try:
    from memoria.db_memoria import (
        get_ou_criar_usuario,
        atualizar_resumo,
        atualizar_nome_preferido,
        adicionar_mensagem,
        get_ultimas_mensagens,
        contar_mensagens,
        get_mensagens_para_resumir,
        limpar_mensagens_antigas,
        salvar_fato,
        get_fatos,
        get_saldo,
        atualizar_saldo,
        adicionar_transacao,
        get_transacoes,
        limpar_memoria_usuario,
        salvar_diario_voz
    )
    print("[SISTEMA] Memória SQLite carregada com sucesso.")
except ImportError as e:
    print(f"[AVISO] Algumas funções de memória não foram encontradas: {e}")
    # Fallbacks vazios para não quebrar o código
    def adicionar_mensagem(*args, **kwargs): pass
    def get_ultimas_mensagens(*args, **kwargs): return []
    def salvar_diario_voz(*args, **kwargs): pass
    # ... outros se necessário

from iot.tv_controller import TVController
from sistema.automacao import pc
from sistema.web_search import pesquisar_web
from sistema.core import ManipuladorTotal

manipulador = ManipuladorTotal(BASE_DIR)

import requests

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:11434/v1")
API_KEY = "AAAAC3NzaC1lZDI1NTE5AAAAIJ9KfyhZeNo5E84kORaqKYu7gxopcvqT2hRabwJU/sXF"
MODELO_ATIVO = "gpt-oss:120b-cloud" # API Externa (NÃO ALTERAR)

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
KNOWLEDGE_FILE = os.path.join(BASE_DIR, "memoria/conhecimento.json")
CONFIG_FILE = os.path.join(BASE_DIR, "memoria/config_jarvis.json")

RESUMO_INTERVAL = 20
BUFFER_SIZE = 10
OFFSET_TEMPORAL = timedelta(hours=0)
MAX_CHAR_INPUT = 5000
MAX_AUDIO_CHARS = 1500

chats_ativos = {}
lock_chats = threading.Lock()

for folder in [AUDIO_DIR, HISTORY_DIR]:
    if not os.path.exists(folder): os.makedirs(folder)

app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, "templates"),
            static_folder=os.path.join(BASE_DIR, "static"),
            static_url_path='/static')
app.secret_key = 'jarvis_v11_ultra'
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")

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

def processar_financas(user_id, texto):
    texto_lower = texto.lower()
    if any(p in texto_lower for p in ["atualize", "edite", "mude", "altere", "corrija"]): return None     
    valor_match = re.search(r'(?:R$|r$|$)\s?(\d+(?:[.,]\d+)?)', texto)
    if not valor_match: return None
    valor = float(valor_match.group(1).replace(',', '.'))
    tipo = "saida"
    if any(w in texto_lower for w in ["recebi", "ganhei", "entrada", "depósito"]): tipo = "entrada"      
    saldo_atual = get_saldo(user_id)
    novo_saldo = saldo_atual + valor if tipo == "entrada" else saldo_atual - valor
    atualizar_saldo(user_id, novo_saldo)
    adicionar_transacao(user_id, tipo, valor, texto[:50])
    return f"SISTEMA: {tipo.capitalize()} de R$ {valor:.2f} registrada. Saldo: R$ {novo_saldo:.2f}"

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
    info_iot = processar_comando_iot(user_id, texto)
    info_financeira = processar_financas(user_id, texto) 

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
    total_chats_ativos = len([c for c in chats_ativos.values() if c.get("processando", False)])

    system_prompt = f"""VOCÊ É J.A.R.V.I.S., UMA IA ASSISTENTE LEAL, ESPIRITUOSA E EFICIENTE.
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
"""

    msgs = [{"role": "system", "content": system_prompt}] + [{"role": m["role"], "content": m["content"]} for m in buffer_msgs] + [{"role": "user", "content": texto}]
    texto_lower = texto.lower()

    descricao_visual = ""
    imagem_b64 = None
    modo_leitura_texto = any(k in texto_lower for k in ["ler texto", "leia o texto", "extrair texto", "copiar texto", "o que está escrito"])

    if any(k in texto_lower for k in ["veja minha tela", "olhe minha tela", "o que está na tela", "leia a tela", "analise a tela"]) or (modo_leitura_texto and "tela" in texto_lower):
        print(f"[VISAO] Capturando tela (Modo Texto: {modo_leitura_texto})...", flush=True)
        if modo_leitura_texto:
            screenshot = ImageGrab.grab()
            resultado_ocr = extrair_texto_ocr(screenshot)
            descricao_visual = f"\n[SISTEMA OCR]: O usuário pediu para ler o texto da tela.\n{resultado_ocr}"
        else:
            imagem_b64 = capturar_tela_base64()
            if imagem_b64: descricao_visual = f"\n[SISTEMA VISUAL]: Descrição da tela: {analisar_imagem(imagem_b64)}"

    match_arq = re.search(r'([a-zA-Z]:\\(?:[^:<>"|?*]+)\.(?:png|jpg|jpeg|bmp|webp))', texto, re.IGNORECASE)
    if match_arq:
        caminho_img = match_arq.group(1)
        if os.path.exists(caminho_img):
            print(f"[VISAO] Processando arquivo: {caminho_img}", flush=True)
            if modo_leitura_texto:
                resultado_ocr = extrair_texto_ocr(caminho_img)
                descricao_visual += f"\n[SISTEMA OCR]: Texto extraído do arquivo '{caminho_img}':\n{resultado_ocr}"
            else:
                imagem_b64 = ler_imagem_local_base64(caminho_img)
                if imagem_b64: descricao_visual += f"\n[SISTEMA VISUAL]: Análise da imagem '{caminho_img}': {analisar_imagem(imagem_b64)}"

    if descricao_visual: texto += descricao_visual

    local_horario = detectar_pergunta_horario(texto)
    if local_horario:
        info = obter_horario_mundial(local_horario)
        try:
            h_str, m_str = info['horario'].split(':')
            h, m = int(h_str), int(m_str)
            lbl_h = "hora" if h == 1 else "horas"
            lbl_m = "minuto" if m == 1 else "minutos"
            msg_voz = f"{h} {lbl_h}"
            if m > 0: msg_voz += f" e {m} {lbl_m}"
            resposta_horario = f"Agora são {msg_voz} em {info['local']}."
        except: resposta_horario = f"Agora são {info['completo']}."

        if "brasil" in texto_lower and "portugal" in texto_lower:
            br = obter_horario_mundial("brasil")
            pt = obter_horario_mundial("portugal")
            resposta_horario = f"Brasil: {br['horario']} ({br['offset']})\nPortugal: {pt['horario']} ({pt['offset']})\nDiferença: 3 horas."

        adicionar_mensagem(user_id, "user", texto)
        adicionar_mensagem(user_id, "assistant", resposta_horario)
        return resposta_horario

    if any(k in texto_lower for k in ["espelhar celular", "espelhar tela", "abrir scrcpy", "tela do celular", "ver celular"]):
        threading.Thread(target=lambda: subprocess.Popen(os.path.join("scripts", "ESPELHAR_CELULAR.bat"), shell=True)).start()
        return "SISTEMA: Iniciando protocolo de espelhamento Android (SCRCPY)..."

    if any(k in texto_lower for k in ["limpar memoria", "limpar ram", "otimizar sistema"]):
        return f"SISTEMA: {manipulador.executar_comando_terminal('echo Limpeza solicitada...')}"

    if "tv" in texto_lower and any(k in texto_lower for k in ["ligar", "desligar", "volume", "mudo", "canal"]):
        res_iot = processar_comando_iot(user_id, texto)
        if res_iot: return res_iot

    MAX_CONTEXT_CHARS = 50000 
    total_chars = len(system_prompt) + len(texto) + sum(len(m['content']) for m in buffer_msgs)
    if total_chars > MAX_CONTEXT_CHARS:
        while len(buffer_msgs) > 0 and total_chars > MAX_CONTEXT_CHARS:
            msg_removida = buffer_msgs.pop(0) 
            total_chars -= len(msg_removida['content'])
        if total_chars > MAX_CONTEXT_CHARS:
            corte = total_chars - MAX_CONTEXT_CHARS + 1000
            system_prompt = system_prompt[:-corte] + "\n[...CONTEXTO TRUNCADO...]"

    msgs = [{"role": "system", "content": system_prompt}] + [{"role": m["role"], "content": m["content"]} for m in buffer_msgs] + [{"role": "user", "content": texto}]

    try:
        resp = client.chat.completions.create(model=MODELO_ATIVO, messages=msgs)
        res_txt = resp.choices[0].message.content
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
        return res_txt
    except Exception as e: return f"Erro: {e}"

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
    text_limpo = text
    for tag in ["[SISTEMA]", "[CMD]", "SISTEMA:", "Traceback", "Error:", "> Comando", "**RESULTADO DA BUSCA WEB:**", "[CONTEXTO_BUSCA_INTERNO]:"]:
        text_limpo = text_limpo.replace(tag, "")
    text_limpo = re.sub(r'```.*?```', '', text_limpo, flags=re.DOTALL) 
    text_limpo = re.sub(r'\[\[.*?\].*?\]\]', '', text_limpo) 
    text_limpo = re.sub(r'[^\w\s,.?!çáéíóúãõàêôüÇÁÉÍÓÚÃÕÀÊÔÜ]', '', text_limpo)
    text_limpo = text_limpo.strip()

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
    for tag in ["[SISTEMA]", "[CMD]", "SISTEMA:", "Traceback", "Error:", "> Comando", "**RESULTADO DA BUSCA WEB:**", "[CONTEXTO_BUSCA_INTERNO]:"]:
        text_limpo = text_limpo.replace(tag, "")
    text_limpo = re.sub(r'```.*?```', '', text_limpo, flags=re.DOTALL)
    text_limpo = re.sub(r'\[\[.*?\].*?\]\]', '', text_limpo)
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
    if not base64_data: return None
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path: AudioSegment.converter = ffmpeg_path
    try:
        audio_bytes = base64.b64decode(base64_data)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as t: t.write(audio_bytes); p = t.name
        wav = p + ".wav"
        try: AudioSegment.from_file(p).export(wav, format="wav")
        except: return "[ERRO AUDIO FORMATO]"
        r = sr.Recognizer()
        with sr.AudioFile(wav) as s: texto = r.recognize_google(r.record(s), language="pt-BR")
        if os.path.exists(p): os.remove(p)
        if os.path.exists(wav): os.remove(wav)
        return texto
    except: return None

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
    data = request.json
    sender = data.get('sender', 'Patrick')
    texto = data.get('text', '')
    chat_id = data.get('chat_id', sender) 

    with lock_chats:
        if chat_id not in chats_ativos: chats_ativos[chat_id] = {"processando": True, "fila": [], "resultados": []}
        else: chats_ativos[chat_id]["processando"] = True

    if data.get('audio_data'):
        trans = transcrever_audio(data['audio_data'])
        if trans: texto = f"{texto} {trans}".strip()

    if data.get('image_data'):
        try:
            img_bytes = base64.b64decode(data['image_data'])
            img = Image.open(io.BytesIO(img_bytes))
            texto_ocr = extrair_texto_ocr(img)
            if "ERRO" not in texto_ocr:
                if len(texto_ocr) > 1500: texto_ocr = texto_ocr[:1500] + "\n[...]"
                texto += f"\n[ANEXO IMAGEM - OCR]: {texto_ocr}\nINSTRUÇÃO: Extraia dados principais."
            else:
                desc_visual = analisar_imagem(data['image_data'])
                texto += f"\n[ANEXO IMAGEM - VISÃO]: {desc_visual}"
        except: pass

    res = gerar_resposta_jarvis(sender, texto)
    audios = gerar_multiplos_audios(res)

    with lock_chats:
        if chat_id in chats_ativos:
            chats_ativos[chat_id]["processando"] = False
            chats_ativos[chat_id]["resultados"].append({"response": res, "audios": audios, "timestamp": time.time()})

    return jsonify({"response": res, "audio_response": audios[0]["audio"] if audios else None, "audio_parts": audios, "total_parts": len(audios), "chat_id": chat_id})

@socketio.on('fala_usuario')
def handle_web(data):
    user_id = data.get('user_id', 'Patrick')
    res = gerar_resposta_jarvis(user_id, data.get('text'))
    emit('bot_msg', {'data': res})

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
    
    # --- FILTRO ANTI-SPAM GLOBAL (3s) ---
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

def classificar_intencao(texto):
    """
    Roteador Semântico: Decide o que fazer antes de fazer.
    Categorias:
    - COMANDO: Apenas para ações de HARDWARE/SISTEMA (abrir app, desligar, volume, mouse).
    - BUSCA: Informações externas, notícias, cotação.
    - CONVERSA: Horas, Data, Bate-papo, Perguntas gerais, Cálculos.
    """
    try:
        prompt_classificador = f"""
        Classifique a frase do usuário em [COMANDO], [BUSCA] ou [CONVERSA].
        
        Regras:
        - "Que horas são?", "Que dia é hoje?", "Quem é você?" -> [CONVERSA]
        - "Abra o Google", "Desligue o PC", "Aumente o volume" -> [COMANDO]
        - "Cotação do dólar", "Notícias de hoje", "Quem ganhou o jogo" -> [BUSCA]
        
        Frase: "{texto}"
        Categoria:"""
        
        resp = client.chat.completions.create(
            model=MODELO_ATIVO,
            messages=[{"role": "user", "content": prompt_classificador}],
            temperature=0.1,
            max_tokens=10
        )
        
        categoria = resp.choices[0].message.content.strip().upper()
        
        if "COMANDO" in categoria: return "COMANDO"
        if "BUSCA" in categoria: return "BUSCA"
        return "CONVERSA"
        
    except Exception as e:
        print(f"[ROTEADOR ERROR] {e}")
        return "CONVERSA"

@socketio.on('active_command')
def handle_active_command(data):
    global LAST_USER_INPUT, LAST_COMMAND_TIME
    
    user_id = data.get('user_id', 'Mestre')
    text = data.get('text', '').strip()
    
    if not text: return

    # Filtros de Duplicidade e Spam
    tempo_atual = time.time()
    if text == LAST_USER_INPUT["text"] and (tempo_atual - LAST_USER_INPUT["time"] < 3.0):
        print(f"[SPAM IGNORADO] '{text}'")
        return

    LAST_USER_INPUT = {"text": text, "time": tempo_atual}
    print(f"\n[COMANDO RECEBIDO] {user_id}: {text}")

    # Memória
    try: adicionar_mensagem(user_id, "user", text)
    except: pass

    # Roteamento
    socketio.emit('status_update', {'status': 'ANALISANDO INTENÇÃO...'})
    intencao = classificar_intencao(text)
    print(f"[ROTEADOR] Intenção detectada: {intencao}")
    socketio.emit('intent_detected', {'intent': intencao})

    resposta_final = ""
    
    # Execução
    if intencao == "COMANDO":
        socketio.emit('status_update', {'status': 'PROCESSANDO AÇÃO...'})
        # Prompt Híbrido: Ação + Fala
        prompt_sistema = f"""
        O usuário solicitou uma ação de sistema: "{text}".
        1. Identifique qual ação executar (abrir, fechar, volume, etc).
        2. Responda APENAS com uma frase curta e natural confirmando que vai fazer (ex: "Abrindo o navegador agora", "Aumentando o volume").
        Não gere código ou JSON aqui, apenas a resposta falada.
        """
        resposta_final = gerar_resposta_llm(user_id, prompt_sistema, usar_memoria=False)
        
        # Dispara a automação real em background (via thread separada para não travar a fala)
        socketio.start_background_task(processar_automacao_silenciosa, text)
        
    elif intencao == "BUSCA":
        socketio.emit('status_update', {'status': 'PESQUISANDO NA WEB...'})
        resumo_busca = pesquisar_web(text)
        prompt_busca = f"Baseado nesta pesquisa: '{resumo_busca}', responda à pergunta do usuário: '{text}'. Seja direto e falado."
        resposta_final = gerar_resposta_llm(user_id, prompt_busca)
        
    else: # CONVERSA
        socketio.emit('status_update', {'status': 'PENSANDO...'})
        if "hora" in text.lower():
            hora_atual = datetime.now().strftime("%H:%M")
            prompt_extra = f" (Dica de contexto: Agora são {hora_atual})"
            resposta_final = gerar_resposta_llm(user_id, text + prompt_extra, usar_memoria=True)
        else:
            resposta_final = gerar_resposta_llm(user_id, text, usar_memoria=True)

    # Envio da Resposta
    if resposta_final:
        try: adicionar_mensagem(user_id, "assistant", resposta_final)
        except: pass
        
        # Correção: Usar a função existente gerar_audio_b64 que já retorna o base64
        audio_b64 = gerar_audio_b64(resposta_final)
        
        socketio.emit('bot_response', {
            'text': resposta_final,
            'audio': audio_b64, 
            'continue_conversation': True
        })

def processar_automacao_silenciosa(comando_texto):
    """Tenta executar o comando no sistema sem gerar fala extra"""
    try:
        from sistema.automacao import automacao_rapida
        automacao_rapida(comando_texto)
    except Exception as e:
        print(f"[AUTOMACAO BG] Erro: {e}")

def gerar_resposta_llm(user_id, prompt, usar_memoria=True):
    # Função auxiliar para centralizar chamada ao LLM
    # (Lógica original de processamento movida para cá para limpeza)
    try:
        contexto = ""
        if usar_memoria:
            hist = get_ultimas_mensagens(user_id, 5)
            contexto = f"Histórico: {hist}\n"
        
        full_prompt = f"{contexto}Usuário: {prompt}"
        
        resp = client.chat.completions.create(
            model=MODELO_ATIVO,
            messages=[
                {"role": "system", "content": "Você é o Jarvis. Responda de forma curta, direta e eficiente."},
                {"role": "user", "content": full_prompt}
            ]
        )
        return resp.choices[0].message.content
    except Exception as e:
        print(f"[LLM ERROR] {e}")
        return "Desculpe, tive um erro neural."

# (MANTENDO O RESTO DO CÓDIGO INALTERADO ONDE POSSÍVEL)
# ... active_command anterior será substituído ...

def process_active_command_bg(data):
    """Processa comando em background thread - THREAD-SAFE"""
    global LAST_RESPONSE_HASH, LAST_PROCESSED_TEXT, LAST_PROCESSED_TIME

    user_id = data.get('user_id', 'Mestre')
    texto = data.get('text', '').strip()

    if not texto or len(texto) < 2: return

    # --- FILTRO TEXTO DUPLICADO ---
    current_time = time.time()
    if texto == LAST_PROCESSED_TEXT and (current_time - LAST_PROCESSED_TIME) < 2.0:
        return
    LAST_PROCESSED_TEXT = texto
    LAST_PROCESSED_TIME = current_time

    print(f"[ACTIVE] Comando recebido: '{texto}'", flush=True)

    # --- LÓGICA DE PARADA (STOP WORDS) ---
    STOP_WORDS = ["pare", "parar", "silêncio", "chega", "obrigado", "tchau", "dormir", "encerrar"]
    texto_lower = texto.lower()

    if any(w in texto_lower for w in STOP_WORDS):
        print("[SESSÃO] Comando de parada detectado.")
        socketio.start_background_task(_enviar_resposta_com_audio, "Entendido. Standby.", False)
        return

    # --- LÓGICA DE GATILHO RÁPIDO ---
    triggers = ["jarvis", "javis", "chaves", "garvis", "assistente", "já vi", "jair"]
    if texto_lower in triggers:
        socketio.start_background_task(_enviar_resposta_com_audio, "Pois não?", True)
        return

    # --- PROCESSAMENTO IA ---
    resposta = gerar_resposta_jarvis(user_id, texto)

    # Filtro de resposta duplicada
    resp_hash = hashlib.md5(resposta.encode('utf-8')).hexdigest()
    if resp_hash == LAST_RESPONSE_HASH["text"] and (current_time - LAST_RESPONSE_HASH["time"]) < 1.0:
        return
    LAST_RESPONSE_HASH = {"text": resp_hash, "time": current_time}

    # --- LOOP INFINITO: SEMPRE CONTINUA A MENOS QUE MANDE PARAR ---
    socketio.start_background_task(_enviar_resposta_com_audio, resposta, True)

def _enviar_resposta_com_audio(resposta, continuar):
    """Gera e envia áudio em background - evita crash de concorrência"""
    try:
        audio_b64 = gerar_audio_b64(resposta)
        socketio.emit('bot_response', {'text': resposta, 'audio': audio_b64, 'continue_conversation': continuar})

        # Áudio em partes (para respostas longas)
        audios = gerar_multiplos_audios(resposta)
        if audios and len(audios) > 1:
            socketio.emit('audio_parts_start', {'total': len(audios)})
            for part in audios:
                socketio.emit('play_audio_remoto', {
                    'url': f"data:audio/mp3;base64,{part['audio']}",
                    'parte': part['parte'],
                    'total': part['total']
                })
            socketio.emit('audio_parts_end', {'total': len(audios)})
    except Exception as e:
        print(f"[ERRO AUDIO BG] {e}", flush=True)
        # Mesmo com erro no áudio, envia texto
        socketio.emit('bot_response', {'text': resposta, 'audio': None, 'continue_conversation': continuar})

@socketio.on('message_text')
def handle_legacy_message_text(data):
    handle_web({'text': data.get('data'), 'user_id': 'LegacyUser'})

# --- Utilitários de Modelo ---
import requests

def get_installed_models():
    try:
        resp = requests.get("http://127.0.0.1:11434/api/tags", timeout=0.5)
        if resp.status_code == 200:
            return [m.get('name', '?') for m in resp.json().get('models', [])]
    except: pass
    return ['qwen2.5-coder:32b', 'gpt-oss:120b-cloud', 'mistral', 'llama3', 'deepseek-r1']

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
    except Exception as e: print(f"[QR] Erro: {e}")

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
        zap_path = os.path.join(BASE_DIR, "jarvis-mcp-whatsapp")
        if os.path.exists(zap_path): subprocess.Popen(f'start cmd /k "cd /d {zap_path} && npm start"', shell=True)

    # threading.Thread(target=start_zap, daemon=True).start()
    print("[SISTEMA] Servidor Online. Aguardando comandos...", flush=True)
    socketio.run(app, debug=False, port=5000, host='0.0.0.0', allow_unsafe_werkzeug=True)
