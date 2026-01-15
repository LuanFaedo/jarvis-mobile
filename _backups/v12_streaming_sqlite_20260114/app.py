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
from PIL import Image, ImageGrab, ImageOps, ImageEnhance # Adicionado ImageOps/Enhance para otimização
import mimetypes
import pytesseract # OCR Leve

# --- Configurações Iniciais (Definição Prioritária) ---
if getattr(sys, 'frozen', False):
    # Se estiver rodando como .exe (PyInstaller)
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Se estiver rodando como script .py
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Configuração "TURBO REAL" - Thread única evita overhead em imagens pequenas/médias
os.environ['OMP_THREAD_LIMIT'] = '1' 

# Configuração ESSENCIAL: Diz ao Tesseract onde estão os arquivos de idioma (.traineddata)
# Aponta para a pasta local do projeto onde baixamos o modelo 'fast'
os.environ['TESSDATA_PREFIX'] = os.path.join(BASE_DIR, "tessdata")

# Configuração do Tesseract (Caminho Padrão Windows)# Se você instalou em outro lugar, ajuste aqui.
CAMINHO_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(CAMINHO_TESSERACT):
    pytesseract.pytesseract.tesseract_cmd = CAMINHO_TESSERACT

# Importa o módulo de memória SQLite
from memoria.db_memoria import (
    get_ou_criar_usuario, atualizar_resumo, atualizar_nome_preferido,
    adicionar_mensagem, get_ultimas_mensagens, contar_mensagens,
    get_mensagens_para_resumir, limpar_mensagens_antigas,
    salvar_fato, get_fatos,
    get_saldo, atualizar_saldo, adicionar_transacao, get_transacoes,
    limpar_memoria_usuario
)

# Importa Controlador IoT
from iot.tv_controller import TVController

# Importa Módulo de Automação (God Mode)
from sistema.automacao import pc

# Importa Módulo de Busca Web
from sistema.web_search import pesquisar_web

# Importa Módulo de Manipulação de Sistema
from sistema.core import ManipuladorTotal

# Instancia o manipulador de arquivos/comandos
manipulador = ManipuladorTotal(BASE_DIR)

# --- INTEGRAÇÃO SUPERVISOR (LOCAL OLLAMA) ---
# Substitui a API do Google (que deu erro 404) pelo Cérebro Local Potente
import requests

# --- Configurações de API (LOCAL / CLOUD) ---
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:11434/v1")
# Para modelos no Ollama local, a API_KEY pode ser qualquer string ou vazia
API_KEY = "AAAAC3NzaC1lZDI1NTE5AAAAIJ9KfyhZeNo5E84kORaqKYu7gxopcvqT2hRabwJU/sXF" 
MODELO_ATIVO = "gpt-oss:120b-cloud"

client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
client_ollama = ollama.Client(host=API_BASE_URL.replace("/v1", ""))

def consultar_gemini_nuvem(prompt):
    """
    Supervisor Técnico. Tenta a Nuvem primeiro, fallback para local.
    """
    print(f"[SUPERVISOR] Consultando: {prompt[:50]}...", flush=True)
    try:
        payload = {
            "model": MODELO_ATIVO,
            "prompt": f"SYSTEM: Arquiteto Sênior. Gere apenas o código.\\nPEDIDO: {prompt}",
            "stream": False
        }
        # Tenta usar a mesma base_url configurada
        endpoint = API_BASE_URL.replace("/v1", "") + "/api/generate"
        resp = requests.post(endpoint, json=payload, timeout=60)
        if resp.status_code == 200:
            return resp.json().get('response', '')
    except Exception as e:
        print(f"[ERRO SUPERVISOR] {e}")
    return "Erro ao consultar supervisor."

# --- Configurações de Caminho ---
AUDIO_DIR = os.path.join(BASE_DIR, "audios")
HISTORY_DIR = os.path.join(BASE_DIR, "historico")
KNOWLEDGE_FILE = os.path.join(BASE_DIR, "memoria/conhecimento.json")
CONFIG_FILE = os.path.join(BASE_DIR, "memoria/config_jarvis.json")

# --- Parâmetros de Sistema ---
RESUMO_INTERVAL = 20
BUFFER_SIZE = 10
OFFSET_TEMPORAL = timedelta(hours=0)
MAX_CHAR_INPUT = 5000
MAX_AUDIO_CHARS = 1500  # ~2 minutos de áudio (aprox. 750 chars/min em PT-BR)

# --- Controle de Chats Simultâneos ---
chats_ativos = {}  # {user_id: {"processando": bool, "fila": [], "resultados": []}}
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

# --- Funções de Utilidade (Horário, etc) ---

def obter_horario_mundial(local="brasil"):
    """
    Retorna horário atual de diferentes fusos sem precisar de busca web.
    """
    from datetime import datetime, timezone, timedelta

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

    # Encontra o fuso mais próximo
    fuso_info = None
    for key, info in fusos.items():
        if key in local_lower:
            fuso_info = info
            break

    if not fuso_info:
        fuso_info = fusos["brasil"]  # Default: Brasil

    _, offset, nome = fuso_info

    # Calcula horário
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
    """
    Detecta se o usuário está perguntando sobre horário e extrai o local.
    IMPORTANTE: Só retorna se for REALMENTE sobre hora, não falsos positivos.
    """
    import unicodedata
    texto_lower = texto.lower()

    # Remove acentos para comparação mais robusta
    texto_sem_acento = ''.join(
        c for c in unicodedata.normalize('NFD', texto_lower)
        if unicodedata.category(c) != 'Mn'
    )

    # Palavras que indicam que NÃO é pergunta de hora
    exclusoes = ["criador", "quem", "pasta", "arquivo", "existe", "mostrar", "listar",
                 "abrir", "fechar", "deletar", "criar", "escrever", "codigo", "programa"]

    if any(ex in texto_sem_acento for ex in exclusoes):
        return None

    # Gatilhos ESPECÍFICOS de hora (mais restritivos)
    gatilhos_hora = [
        "que horas", "que hora", "que horario",
        "qual horario", "qual hora", "horas sao",
        "hora atual", "horario atual", "horas agora",
        "horario em", "hora em", "horas em"
    ]

    # Verifica se algum gatilho específico de hora existe
    encontrou_gatilho_hora = False
    for g in gatilhos_hora:
        g_sem_acento = ''.join(
            c for c in unicodedata.normalize('NFD', g)
            if unicodedata.category(c) != 'Mn'
        )
        if g_sem_acento in texto_sem_acento:
            encontrou_gatilho_hora = True
            break

    # Locais conhecidos
    locais = ["portugal", "lisboa", "brasil", "brasilia", "sao paulo",
              "nova york", "new york", "londres", "paris", "toquio", "tokyo", "china",
              "pequim", "dubai", "sydney", "utc"]

    # Verifica se menciona hora + local (padrão: "horário em Portugal")
    menciona_local = any(local in texto_sem_acento for local in locais)
    menciona_hora = any(h in texto_sem_acento for h in ["hora", "horario"])

    # SÓ retorna se: (gatilho específico) OU (menciona hora E menciona local)
    if not encontrou_gatilho_hora and not (menciona_hora and menciona_local):
        return None

    # Extrai local mencionado
    for local in locais:
        local_sem_acento = ''.join(
            c for c in unicodedata.normalize('NFD', local)
            if unicodedata.category(c) != 'Mn'
        )
        if local_sem_acento in texto_sem_acento:
            # Normaliza para chave padrão
            if local in ["brasilia"]:
                return "brasil"
            if local in ["toquio"]:
                return "tokyo"
            return local

    # Default para Brasil se não especificou local
    return "brasil"

# --- Gestão de Conhecimento ---

def carregar_base_conhecimento():
    if os.path.exists(KNOWLEDGE_FILE):
        try:
            with open(KNOWLEDGE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return "\n".join([str(i.get('content', ''))[:200] for i in data[:20]])
        except: pass
    return "Base de conhecimento local não encontrada."

# --- SISTEMA DE MEMÓRIA SQLite ---

def extrair_fatos_da_mensagem(user_id: str, texto: str):
    prompt_extracao = f"""Analise a mensagem do usuário e extraia FATOS para memória de longo prazo.\nTexto: "{texto}"\nRetorne APENAS um JSON puro lista de objetos: [{{"tipo": "...", "chave": "...", "valor": "..."}}]"""
    try:
        modelo_usado = MODELO_ATIVO if MODELO_ATIVO else "gpt-oss:120b-cloud"
        # Removido response_format para evitar erro 404/400 em APIs que não suportam
        resp = client.chat.completions.create(
            model=modelo_usado, 
            messages=[{"role": "user", "content": prompt_extracao}], 
            temperature=0
        )
        content = resp.choices[0].message.content
        # Limpa possível markdown de bloco de código
        content = content.replace("```json", "").replace("```", "").strip()
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
        usuario = get_ou_criar_usuario(user_id)
        msgs_para_resumir = get_mensagens_para_resumir(user_id, 0, total_msgs - BUFFER_SIZE)
        if msgs_para_resumir:
            limpar_mensagens_antigas(user_id, BUFFER_SIZE)

# --- Processamento Jarvis ---

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
    
    # Gatilhos Expandidos (Sua sugestão)
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
    
    # LISTA NEGRA DE SEGURANÇA REFINADA
    # Bloqueia apenas comandos destrutivos reais, permitindo "Format-Table" etc.
    COMANDOS_PROIBIDOS = ["format c:", "format d:", "del /s", "rm -rf", "shutdown /", "shutdown -"]

    # 0. Busca na Web (NOVO - Prioridade para dados externos)
    searches = re.findall(r'\[\[SEARCH: (.*?)\]\]', resposta_llm, re.DOTALL)
    for query in searches:
        print(f"[DEBUG] Processando busca: {query}", flush=True)
        try:
            res_busca = pesquisar_web(query.strip())
            if not res_busca or len(res_busca) < 5:
                # Silencia aviso, apenas loga
                print(f"[BUSCA VAZIA] '{query}' não retornou dados.", flush=True)
                res_busca = ""
        except Exception as e:
            print(f"[ERRO BUSCA SILENCIOSO] {e}", flush=True)
            res_busca = ""
            
        if res_busca:
            print(f"[DEBUG] Resultado Busca (primeiros 50 chars): {res_busca[:50]}...", flush=True)
            # NÃO mostra resultado bruto ao usuário - usa como contexto interno
            # O LLM vai processar e responder de forma natural
            output_extra += f"\n[CONTEXTO_BUSCA_INTERNO]: {res_busca[:500]}\n"

    # 1. Execução de Terminal
    cmds = re.findall(r'\[\[CMD: (.*?)\]\]', resposta_llm, re.DOTALL)
    for cmd in cmds:
        cmd_lower = cmd.lower()
        # Verifica se comando contém proibidos
        if any(p in cmd_lower for p in COMANDOS_PROIBIDOS):
            # Validação extra para evitar bloqueio de "format" em contextos seguros
            if "format" in cmd_lower and not any(x in cmd_lower for x in ["c:", "d:", "/fs:"]):
                pass # É seguro (provavelmente powershell formatting)
            else:
                output_extra += f"\n> **BLOQUEADO (SEGURANÇA):** `{cmd}`\n"; continue
        
        print(f"[ACAO] Executando: {cmd}...", flush=True)
        res = manipulador.executar_comando_terminal(cmd.strip())
        if "--- ERROS ---" in res:
            erros_detectados.append(f"Erro no comando '{cmd}': {res}")
            output_extra += f"\n> Falha em: `{cmd.strip()}`\n"
        else:
            output_extra += f"\n> Comando: `{cmd.strip()}`\n```powershell\n{res}\n```\n"
        
    # 2. Leitura
    reads = re.findall(r'\[\[READ: (.*?)\]\]', resposta_llm, re.DOTALL)
    for path in reads:
        content = manipulador.ler_arquivo(path.strip())
        output_extra += f"\n> Arquivo: `{path.strip()}`\n```python\n{content[:1000]}\n```\n"

    # 3. Automação de Desktop (God Mode)
    autos = re.findall(r'\[\[AUTO: (.*?)\]\]', resposta_llm, re.DOTALL)
    for acao_raw in autos:
        try:
            # Formato esperado: comando | argumento (ex: abrir_programa | chrome)
            partes = acao_raw.split("|")
            cmd_auto = partes[0].strip().lower()
            arg_auto = partes[1].strip() if len(partes) > 1 else ""
            
            print(f"[AUTO] Executando: {cmd_auto} -> {arg_auto}", flush=True)
            
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
        except Exception as e:
            output_extra += f"\n> [ERRO AUTO]: {e}\n"

    # ... (Escrita já foi corrigida no bloco anterior) ...

    # 4. Gemini Bridge (Nativa)
    asks = re.findall(r'\[\[ASK_GEMINI: (.*?)\]\]', resposta_llm, re.DOTALL)
    for pedido in asks:
        resposta_gemini = consultar_gemini_nuvem(pedido)
        output_extra += f"\n**GEMINI SUPERVISOR:**\n{resposta_gemini}\n"

    if erros_detectados and profundidade < 5: # Aumentado limite para 5 tentativas
        print(f"[AUTO-FIX] Tentativa {profundidade+1} de 5...", flush=True)
        prompt = f"""ERRO CRÍTICO DE SISTEMA DETECTADO. TENTE OUTRA ESTRATÉGIA.
        
ERROS ENCONTRADOS:
{chr(10).join(erros_detectados)}

SEU OBJETIVO: Corrigir o comando anterior para funcionar no Windows (cmd/powershell).
REGRAS:
1. Se o arquivo não existe, crie ele primeiro.
2. Use aspas em caminhos com espaços.
3. Se 'mkdir' falhou, verifique se a pasta já existe.
4. RETORNE APENAS O COMANDO CORRIGIDO no formato [[CMD: ...]].
"""
        resp = client.chat.completions.create(model=MODELO_ATIVO, messages=[{"role": "user", "content": prompt}])
        output_extra += f"\n\n[Correcao {profundidade+1}]:\n" + processar_comandos_sistema(resp.choices[0].message.content, user_id, profundidade + 1)

    return output_extra

def gerar_resposta_jarvis(user_id, texto):
    if len(texto) > MAX_CHAR_INPUT: texto = texto[:MAX_CHAR_INPUT] + "..."
    
    # --- PROCESSADORES DE COMANDO RÁPIDO ---
    info_iot = processar_comando_iot(user_id, texto)
    info_financeira = processar_financas(user_id, texto) # Adicionado processamento financeiro
    
    usuario = get_ou_criar_usuario(user_id)
    buffer_msgs = get_ultimas_mensagens(user_id, BUFFER_SIZE)
    
    # --- BUSCA DADOS DE CONTEXTO ---
    saldo_atual = get_saldo(user_id)
    fatos = get_fatos(user_id)
    base_conhecimento = carregar_base_conhecimento()

    # Formata fatos para o contexto
    fatos_texto = ""
    if fatos:
        fatos_texto = "ESTADO ATUAL E MEMÓRIA DE FATOS:\n" + "\n".join([f"- {f['chave']}: {f['valor']}" for f in fatos])
    
    # Preparação do Contexto Financeiro
    transacoes_db = get_transacoes(user_id, limite=10)
    financas_contexto = f"SALDO ATUAL: R$ {saldo_atual:.2f}\nÚLTIMAS TRANSAÇÕES:"
    if transacoes_db:
        for t in transacoes_db:
            financas_contexto += f"\n- {t['tipo'].upper()}: R$ {t['valor']:.2f} | {t['descricao']}"
    else:
        financas_contexto += "\n(Sem transações)"
    # -------------------------------------------

    nome_usuario = usuario.get('nome_preferido') or f"Usuário {str(user_id)[-4:]}"
    agora_br = (datetime.now(timezone.utc) + OFFSET_TEMPORAL).astimezone(timezone(timedelta(hours=-3)))
    
    # Conta chats ativos no momento
    total_chats_ativos = len([c for c in chats_ativos.values() if c.get("processando", False)])

    system_prompt = f"""VOCÊ É O JARVIS, UM ASSISTENTE FINANCEIRO AVANÇADO E CONTROLADOR DE SISTEMA COM ACESSO TOTAL (GOD MODE).
DATA: {agora_br.strftime('%d/%m/%Y %H:%M')}. USUÁRIO MESTRE: {nome_usuario}.

=== DIRETRIZES DE PERSONA E PODER ===
1. ASSISTENTE FINANCEIRO: Você gerencia o saldo de {nome_usuario}. Sempre que ele mencionar gastos ou ganhos, confirme se o sistema registrou.
2. ACESSO TOTAL: Você tem permissão para manipular arquivos, pastas, processos e a interface do Windows.
3. SEJA DIRETO: Não peça permissão. Execute e informe o resultado.
4. RESPOSTA CURTA: No WhatsApp, seja breve e eficiente.

=== PROCESSAMENTO MULTI-CHAT ===
5. MÚLTIPLOS CHATS SIMULTÂNEOS: Você pode estar processando VÁRIOS chats ao mesmo tempo ({total_chats_ativos} ativos agora).
   - Cada chat é independente e isolado.
   - Envie TODOS os resultados que você estiver processando.
   - Se uma resposta for longa (mais de 2 minutos de áudio), ela será automaticamente dividida em partes.
   - NÃO espere - processe e envie tudo imediatamente.
6. STREAMING DE RESULTADOS: Conforme você processa tarefas (buscas, comandos, análises), envie cada resultado assim que estiver pronto.

=== COMANDOS DISPONÍVEIS ===
- [[SEARCH: query]] -> Busca na internet.
- [[AUTO: comando | arg]] -> Controle de interface (abrir_programa, digitar, clicar, minimizar_tudo).
- [[CMD: comando]] -> Terminal (Powershell/CMD).
- [[READ: path]] / [[WRITE: path | content]] -> Manipulação de arquivos.

CONTEXTO ADICIONAL:
{usuario['resumo_conversa']}
{fatos_texto}
{financas_contexto}
{info_iot if info_iot else ""}
{info_financeira if info_financeira else ""}

REGRAS DE SEGURANÇA:
- NÃO APAGUE código funcional.
- Mantenha o foco na produtividade e segurança do Mestre Patrick.

=== REGRAS DE DESENVOLVIMENTO (OBRIGATÓRIAS) ===
7. NUNCA APAGAR COMANDOS: Ao modificar código, NUNCA delete funções ou comandos existentes. Apenas ALTERE se necessário ou ACRESCENTE novas funcionalidades.
8. TESTES OBRIGATÓRIOS: Antes de finalizar qualquer alteração de código, execute testes de sintaxe e imports.
9. DOCUMENTAR ALTERAÇÕES: Sempre atualize o arquivo memory.md com as mudanças realizadas (data, arquivo, o que mudou).
10. ABORDAGEM ADITIVA: Prefira adicionar código novo ao invés de substituir código existente.
"""

    msgs = [{"role": "system", "content": system_prompt}] + [{"role": m["role"], "content": m["content"]} for m in buffer_msgs] + [{"role": "user", "content": texto}]

    # --- FAST PATH: Comandos Rápidos (Bypass LLM) ---
    texto_lower = texto.lower()
    
    # --- INTEGRAÇÃO DE VISÃO (SCREENSHOT & ARQUIVOS) ---
    descricao_visual = ""
    imagem_b64 = None
    
    # Verifica intenção: Leitura de Texto (OCR) vs Entendimento Visual (Vision)
    modo_leitura_texto = any(k in texto_lower for k in ["ler texto", "leia o texto", "extrair texto", "copiar texto", "o que está escrito"])
    
    # 1. Gatilho para ver a tela
    if any(k in texto_lower for k in ["veja minha tela", "olhe minha tela", "o que está na tela", "leia a tela", "analise a tela"]) or modo_leitura_texto and "tela" in texto_lower:
        print(f"[VISAO] Capturando tela (Modo Texto: {modo_leitura_texto})...", flush=True)
        
        if modo_leitura_texto:
            # Rota Rápida: OCR na Tela
            screenshot = ImageGrab.grab()
            resultado_ocr = extrair_texto_ocr(screenshot)
            descricao_visual = f"\n[SISTEMA OCR]: O usuário pediu para ler o texto da tela.\n{resultado_ocr}"
        else:
            # Rota Lenta: Vision LLM
            imagem_b64 = capturar_tela_base64()
            if imagem_b64:
                descricao_visual = f"\n[SISTEMA VISUAL]: Descrição da tela: {analisar_imagem(imagem_b64)}"

    # 2. Gatilho para ver arquivo local
    match_arq = re.search(r'([a-zA-Z]:\\(?:[^:<>"|?*]+)\.(?:png|jpg|jpeg|bmp|webp))', texto, re.IGNORECASE)
    if match_arq:
        caminho_img = match_arq.group(1)
        if os.path.exists(caminho_img):
            print(f"[VISAO] Processando arquivo: {caminho_img}", flush=True)
            
            if modo_leitura_texto:
                # Rota Rápida: OCR em Arquivo
                resultado_ocr = extrair_texto_ocr(caminho_img)
                descricao_visual += f"\n[SISTEMA OCR]: Texto extraído do arquivo '{caminho_img}':\n{resultado_ocr}"
            else:
                # Rota Lenta: Vision LLM
                imagem_b64 = ler_imagem_local_base64(caminho_img)
                if imagem_b64:
                    descricao_visual += f"\n[SISTEMA VISUAL]: Análise da imagem '{caminho_img}': {analisar_imagem(imagem_b64)}"

    # Se houver descrição visual, anexa ao prompt do usuário para o Jarvis saber do que se trata
    if descricao_visual:
        texto += descricao_visual

    # 0. HORÁRIO MUNDIAL (Fast Path - Sem LLM, sem busca)
    local_horario = detectar_pergunta_horario(texto)
    if local_horario:
        info = obter_horario_mundial(local_horario)
        
        # Formatação Otimizada para Leitura TTS
        try:
            h_str, m_str = info['horario'].split(':')
            h, m = int(h_str), int(m_str)
            
            # Singular/Plural
            lbl_h = "hora" if h == 1 else "horas"
            lbl_m = "minuto" if m == 1 else "minutos"
            
            # Monta frase: "18 horas e 8 minutos" (Sem zero à esquerda)
            msg_voz = f"{h} {lbl_h}"
            if m > 0:
                msg_voz += f" e {m} {lbl_m}"
            
            resposta_horario = f"Agora são {msg_voz} em {info['local']}."
        except:
            # Fallback se falhar o parse
            resposta_horario = f"Agora são {info['completo']}."

        # Se perguntou de dois lugares, calcula ambos
        if "brasil" in texto_lower and "portugal" in texto_lower:
            br = obter_horario_mundial("brasil")
            pt = obter_horario_mundial("portugal")
            resposta_horario = f"Brasil: {br['horario']} ({br['offset']})\nPortugal: {pt['horario']} ({pt['offset']})\nDiferença: 3 horas."

        adicionar_mensagem(user_id, "user", texto)
        adicionar_mensagem(user_id, "assistant", resposta_horario)
        return resposta_horario

    # 1. Espelhamento Android (SCRCPY)
    if any(k in texto_lower for k in ["espelhar celular", "espelhar tela", "abrir scrcpy", "tela do celular", "ver celular"]):
        threading.Thread(target=lambda: subprocess.Popen(os.path.join("scripts", "ESPELHAR_CELULAR.bat"), shell=True)).start()
        return "SISTEMA: Iniciando protocolo de espelhamento Android (SCRCPY)..."
        
    # 2. Limpeza de Sistema
    if any(k in texto_lower for k in ["limpar memoria", "limpar ram", "otimizar sistema"]):
        return f"SISTEMA: {manipulador.executar_comando_terminal('echo Limpeza solicitada...')}" # Placeholder para lógica real se houver
        
    # 3. Comandos de TV (Prioridade Alta)
    if "tv" in texto_lower and any(k in texto_lower for k in ["ligar", "desligar", "volume", "mudo", "canal"]):
        res_iot = processar_comando_iot(user_id, texto)
        if res_iot: return res_iot

    # --- FIM FAST PATH ---

    # --- PROTEÇÃO DE CONTEXTO (TOKEN LIMIT SAFETY) ---
    MAX_CONTEXT_CHARS = 50000  # Limite seguro (~12k tokens) para evitar erro 400 (Limit 131k)
    
    # Estima tamanho total
    total_chars = len(system_prompt) + len(texto) + sum(len(m['content']) for m in buffer_msgs)
    
    if total_chars > MAX_CONTEXT_CHARS:
        print(f"[SAFETY] Contexto excedido ({total_chars} chars). Truncando...", flush=True)
        # 1. Reduz histórico agressivamente
        while len(buffer_msgs) > 0 and total_chars > MAX_CONTEXT_CHARS:
            msg_removida = buffer_msgs.pop(0) # Remove a mais antiga
            total_chars -= len(msg_removida['content'])
            
        # 2. Se ainda for grande, trunca a Base de Conhecimento do System Prompt
        if total_chars > MAX_CONTEXT_CHARS:
            corte = total_chars - MAX_CONTEXT_CHARS + 1000
            system_prompt = system_prompt[:-corte] + "\n[...CONTEXTO TRUNCADO...]"

    msgs = [{"role": "system", "content": system_prompt}] + [{"role": m["role"], "content": m["content"]} for m in buffer_msgs] + [{"role": "user", "content": texto}]

    try:
        resp = client.chat.completions.create(model=MODELO_ATIVO, messages=msgs)
        res_txt = resp.choices[0].message.content
        
        # OTIMIZAÇÃO 2: Só aciona o processador de sistema SE houver comandos detectados
        # Isso evita chamar o loop recursivo para conversas simples
        if "[[" in res_txt and "]]" in res_txt:
            output_sys = processar_comandos_sistema(res_txt, user_id)
            if output_sys: res_txt += f"\n\n--- SISTEMA ---\n{output_sys}"
        
        adicionar_mensagem(user_id, "user", texto)
        adicionar_mensagem(user_id, "assistant", res_txt)
        
        def bg_task():
            try:
                # OTIMIZAÇÃO 3: Não extrai fatos de respostas de OCR para economizar tokens/tempo
                if "[ANEXO IMAGEM" not in texto:
                    extrair_fatos_da_mensagem(user_id, texto)
                processar_memoria(user_id)
            except: pass
        threading.Thread(target=bg_task, daemon=True).start()

        # FILTRO FINAL: Remove tags internas antes de enviar ao usuário
        res_txt = re.sub(r'\[CONTEXTO_BUSCA_INTERNO\]:.*?(?=\n|$)', '', res_txt, flags=re.DOTALL)
        res_txt = res_txt.replace("--- SISTEMA ---", "").strip()

        return res_txt
    except Exception as e: return f"Erro: {e}"

# --- Áudio e Imagem ---

def dividir_texto_para_audio(texto, max_chars=MAX_AUDIO_CHARS):
    """
    Divide texto longo em segmentos menores para gerar múltiplos áudios.
    Tenta quebrar em pontos naturais (., !, ?, \n) para não cortar frases.
    Retorna lista de segmentos.
    """
    if len(texto) <= max_chars:
        return [texto]

    segmentos = []
    texto_restante = texto

    while len(texto_restante) > max_chars:
        # Procura ponto de corte natural dentro do limite
        ponto_corte = max_chars

        # Tenta encontrar fim de frase (. ! ? \n) antes do limite
        for delimitador in ['. ', '! ', '? ', '\n', ', ']:
            ultimo_delim = texto_restante[:max_chars].rfind(delimitador)
            if ultimo_delim > max_chars * 0.5:  # Pelo menos metade do segmento
                ponto_corte = ultimo_delim + len(delimitador)
                break

        segmento = texto_restante[:ponto_corte].strip()
        if segmento:
            segmentos.append(segmento)
        texto_restante = texto_restante[ponto_corte:].strip()

    # Adiciona o resto
    if texto_restante:
        segmentos.append(texto_restante)

    return segmentos

async def _tts_async(text, path):
    try:
        # Tenta ler do arquivo, mas define +20% como padrão seguro e agradável
        with open(CONFIG_FILE, 'r') as f: speed = json.load(f).get('velocidade', '+20%')
    except: speed = '+20%'
    
    # pt-BR-AntonioNeural é a voz masculina padrão de alta qualidade
    comm = edge_tts.Communicate(text, "pt-BR-AntonioNeural", rate=speed)
    await comm.save(path)

def gerar_audio_b64(text):
    if not text or len(text.strip()) == 0: return None
    
    # FILTRO INTELIGENTE: Remove tags técnicas mas FALA o conteúdo útil
    # Remove tags comuns de log/sistema para não serem lidas em voz alta
    text_limpo = text
    for tag in ["[SISTEMA]", "[CMD]", "SISTEMA:", "Traceback", "Error:", "> Comando", "**RESULTADO DA BUSCA WEB:**", "[CONTEXTO_BUSCA_INTERNO]:"]:
        text_limpo = text_limpo.replace(tag, "")

    # Limpa markdown e códigos para não bugar o áudio
    text_limpo = re.sub(r'```.*?```', '', text_limpo, flags=re.DOTALL) # Remove blocos de código
    text_limpo = re.sub(r'\[\[.*?\]\]', '', text_limpo) # Remove comandos [[CMD]]
    text_limpo = re.sub(r'[^\w\s,.?!çáéíóúãõàêôüÇÁÉÍÓÚÃÕÀÊÔÜ]', '', text_limpo) # Remove símbolos estranhos (Mantendo acentos)
    text_limpo = text_limpo.strip()

    if not text_limpo or len(text_limpo) < 2: return None # Se sobrou nada ou só 1 letra, ignora
    
    print(f"[AUDIO] Gerando voz para: {text_limpo[:50]}...", flush=True)

    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp: 
            path = tmp.name
        
        # GARANTE LOOP ISOLADO PARA CADA ÁUDIO
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            new_loop.run_until_complete(_tts_async(text_limpo, path))
        finally:
            new_loop.close()
            
        if os.path.exists(path) and os.path.getsize(path) > 100:
            with open(path, "rb") as f: 
                b64 = base64.b64encode(f.read()).decode('utf-8')
            os.remove(path)
            print(f"[AUDIO] SUCESSO: {len(b64)} bytes gerados.", flush=True)
            return b64
        else:
            print("[AUDIO] FALHA: Arquivo de áudio não foi gerado corretamente.", flush=True)
            return None
            
    except Exception as e:
        print(f"[ERRO CRÍTICO AUDIO]: {e}", flush=True)
        return None

def gerar_multiplos_audios(text):
    """
    Gera múltiplos áudios para textos longos (+2 min).
    Retorna lista de áudios em base64.
    """
    if not text or len(text.strip()) == 0:
        return []

    # Limpa o texto primeiro (mesma lógica do gerar_audio_b64)
    text_limpo = text
    for tag in ["[SISTEMA]", "[CMD]", "SISTEMA:", "Traceback", "Error:", "> Comando", "**RESULTADO DA BUSCA WEB:**", "[CONTEXTO_BUSCA_INTERNO]:"]:
        text_limpo = text_limpo.replace(tag, "")

    text_limpo = re.sub(r'```.*?```', '', text_limpo, flags=re.DOTALL)
    text_limpo = re.sub(r'\[\[.*?\]\]', '', text_limpo)
    text_limpo = re.sub(r'[^\w\s,.?!çáéíóúãõàêôüÇÁÉÍÓÚÃÕÀÊÔÜ]', '', text_limpo)
    text_limpo = text_limpo.strip()

    if not text_limpo or len(text_limpo) < 2:
        return []

    # Divide em segmentos
    segmentos = dividir_texto_para_audio(text_limpo)

    if len(segmentos) > 1:
        print(f"[AUDIO] Texto longo detectado. Dividindo em {len(segmentos)} partes...", flush=True)

    audios = []
    for i, segmento in enumerate(segmentos):
        print(f"[AUDIO] Gerando parte {i+1}/{len(segmentos)}: {segmento[:30]}...", flush=True)
        audio_b64 = gerar_audio_b64(segmento)
        if audio_b64:
            audios.append({
                "parte": i + 1,
                "total": len(segmentos),
                "audio": audio_b64
            })

    return audios

def transcrever_audio(base64_data):
    if not base64_data: return None
    print(f"[AUDIO] Recebido Base64 de {len(base64_data)} caracteres.", flush=True)

    # Tenta localizar FFmpeg no sistema
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        AudioSegment.converter = ffmpeg_path
    
    try:
        audio_bytes = base64.b64decode(base64_data)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as t: 
            t.write(audio_bytes)
            p = t.name
        
        wav = p + ".wav"
        print(f"[AUDIO] Convertendo {p} -> {wav}...", flush=True)
        
        # Conversão explícita com tratamento de erro
        try:
            AudioSegment.from_file(p).export(wav, format="wav")
        except Exception as e_conv:
            print(f"[ERRO CRITICO FFMPEG] Falha na conversão: {e_conv}")
            if os.path.exists(p): os.remove(p)
            return "[ERRO: O sistema não conseguiu processar o formato de áudio. Verifique se o FFmpeg está instalado.]"

        r = sr.Recognizer()
        with sr.AudioFile(wav) as s: 
            print("[AUDIO] Reconhecendo fala...", flush=True)
            texto = r.recognize_google(r.record(s), language="pt-BR")
            print(f"[AUDIO] Texto: {texto}", flush=True)
        
        if os.path.exists(p): os.remove(p)
        if os.path.exists(wav): os.remove(wav)
        return texto

    except sr.UnknownValueError: 
        print("[ERRO] Áudio não entendido (silêncio ou ruído).")
        return "[Áudio inaudível]"
    except Exception as e: 
        print(f"[ERRO GERAL AUDIO] {e}")
        return None

def analisar_imagem(base64_data):
    try:
        # Garante que o modelo existe (fallback se nao tiver vision)
        print("[VISAO] Analisando imagem com llama3.2-vision...", flush=True)
        response = client_ollama.generate(model='llama3.2-vision', prompt="Descreva esta imagem em detalhes (em português), focando no que é relevante para o usuário.", images=[base64_data], stream=False)
        desc = response['response']
        print(f"[VISAO] Resultado: {desc[:50]}...", flush=True)
        return desc
    except Exception as e: 
        print(f"[ERRO VISAO] {e}")
        return "[Erro ao processar imagem. Verifique se 'llama3.2-vision' está instalado no Ollama.]"

def capturar_tela_base64():
    try:
        screenshot = ImageGrab.grab()
        buffered = io.BytesIO()
        screenshot.save(buffered, format="JPEG", quality=70)
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    except Exception as e:
        print(f"[ERRO SCREENSHOT] {e}")
        return None

def ler_imagem_local_base64(caminho):
    try:
        with open(caminho.strip(), "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"[ERRO ARQUIVO IMAGEM] {e}")
        return None

def otimizar_imagem_para_ocr(img):
    """
    Pré-processamento LEVE para velocidade máxima.
    Apenas converte para escala de cinza e binariza.
    """
    # 1. Escala de Cinza (Essencial)
    img = ImageOps.grayscale(img)
    
    # 2. Reduz resolução SE for gigantesca (>3000px) para não travar CPU
    # Usa filtro NEAREST que é "feio" mas instantâneo
    if img.width > 3000:
        scale = 3000 / float(img.width)
        img = img.resize((3000, int(img.height * scale)), Image.NEAREST)

    return img

def extrair_texto_ocr(caminho_ou_imagem):
    try:
        if not os.path.exists(pytesseract.pytesseract.tesseract_cmd):
            return "ERRO: Tesseract OCR não encontrado."
        
        # Se for caminho string, abre a imagem
        img = Image.open(caminho_ou_imagem) if isinstance(caminho_ou_imagem, str) else caminho_ou_imagem
        
        # ETAPA 1: Pré-processamento (Otimização Visual)
        img = otimizar_imagem_para_ocr(img)
        
        # ETAPA 2: Configuração "Turbo" (Divide o trabalho)
        # --oem 1: Neural Net Fast (Mais rápido)
        # --psm 3: Auto-detectar blocos (padrão robusto)
        config_ocr = '--oem 1 --psm 3'
        
        # REMOVIDO: Não precisamos mais passar --tessdata-dir aqui
        # A variável de ambiente TESSDATA_PREFIX no topo do script já resolve isso.

        print("[OCR] Iniciando leitura rápida...", flush=True)
        texto = pytesseract.image_to_string(img, lang='por', config=config_ocr)
        
        if not texto.strip():
            return "[OCR] Nenhum texto detectado."
        return f"TEXTO EXTRAÍDO:\n{texto}"
    except Exception as e:
        return f"[ERRO OCR] Falha: {e}"

# --- Rotas ---

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/')
def index(): return render_template('index.html')

@app.route('/api/whatsapp', methods=['POST'])
def api_whatsapp():
    print("[API] Recebida nova requisição POST /api/whatsapp", flush=True)
    data = request.json
    sender = data.get('sender', 'Patrick')
    texto = data.get('text', '')
    chat_id = data.get('chat_id', sender)  # Identifica o chat específico

    # Registra chat ativo para processamento simultâneo
    with lock_chats:
        if chat_id not in chats_ativos:
            chats_ativos[chat_id] = {"processando": True, "fila": [], "resultados": []}
        else:
            chats_ativos[chat_id]["processando"] = True

    print(f"[MULTI-CHAT] Processando chat: {chat_id} | Chats ativos: {len(chats_ativos)}", flush=True)

    # 1. Processamento de Áudio
    if data.get('audio_data'):
        trans = transcrever_audio(data['audio_data'])
        if trans:
            # Se retornou mensagem de erro do sistema de áudio, avisa o usuário
            if "[ERRO" in trans or "[Áudio" in trans:
                texto = f"SISTEMA: O usuário enviou um áudio, mas ocorreu um erro: {trans}"
            else:
                print(f"[ZAP ÁUDIO]: {trans}")
                texto = f"{texto} {trans}".strip()
        else:
            texto = "SISTEMA: O usuário enviou um áudio vazio ou corrompido."

    # 2. Processamento de Imagem (OCR + Visão)
    if data.get('image_data'):
        try:
            start_ocr = time.time()
            # Decodifica Base64 para Imagem PIL
            img_bytes = base64.b64decode(data['image_data'])
            img = Image.open(io.BytesIO(img_bytes))

            # A) Tenta ler texto (OCR Rápido) - Prioridade para Contas/Boletos
            print("[ZAP] Iniciando OCR...", flush=True)
            texto_ocr = extrair_texto_ocr(img)

            if "ERRO" not in texto_ocr and "Nenhum texto" not in texto_ocr:
                # OTIMIZAÇÃO 1: Trunca texto gigante (evita processamento desnecessário de rodapés)
                if len(texto_ocr) > 1500:
                    texto_ocr = texto_ocr[:1500] + "\n[...corte para velocidade...]"

                texto += f"\n[ANEXO IMAGEM - OCR]: O usuário enviou uma imagem. Texto cru:\n{texto_ocr}\n\nINSTRUÇÃO: Extraia apenas: Data de Vencimento, Valor Total e Nome do Beneficiário/Empresa. Seja breve."
                print(f"[PERFORMANCE] OCR concluiu em {time.time() - start_ocr:.2f}s", flush=True)
            else:
                # B) Fallback para Visão
                print("[ZAP] OCR falhou. Usando Visão...", flush=True)
                desc_visual = analisar_imagem(data['image_data'])
                texto += f"\n[ANEXO IMAGEM - VISÃO]: {desc_visual}"

        except Exception as e:
            print(f"[ERRO ZAP IMG] Falha ao processar imagem: {e}")

    start_llm = time.time()
    res = gerar_resposta_jarvis(sender, texto)
    print(f"[PERFORMANCE] LLM concluiu em {time.time() - start_llm:.2f}s", flush=True)

    # Gera múltiplos áudios se a resposta for longa
    audios = gerar_multiplos_audios(res)

    # Marca chat como processado
    with lock_chats:
        if chat_id in chats_ativos:
            chats_ativos[chat_id]["processando"] = False
            chats_ativos[chat_id]["resultados"].append({
                "response": res,
                "audios": audios,
                "timestamp": time.time()
            })

    # Retorna resposta com múltiplos áudios
    return jsonify({
        "response": res,
        "audio_response": audios[0]["audio"] if audios else None,  # Compatibilidade
        "audio_parts": audios,  # Lista completa de áudios
        "total_parts": len(audios),
        "chat_id": chat_id
    })

# Importa Auditoria
from sistema.auditoria import registrar_input_usuario, gravar_diario_voz

@socketio.on('background_listen')
def handle_background_audio(data):
    """Recebe áudio bruto do ambiente e salva no diário, sem processar IA."""
    texto = data.get('text', '')
    if texto and len(texto.strip()) > 0:
        # Grava em thread separada para não bloquear
        threading.Thread(target=gravar_diario_voz, args=(texto,), daemon=True).start()

@socketio.on('fala_usuario')
def handle_web(data):
    user_id = data.get('user_id', 'Patrick')
    texto = data.get('text', '')
    sid = request.sid # Captura o ID da sessão atual
    
    # 1. Auditoria Imediata (Segurança de Dados)
    registrar_input_usuario(texto)
    print(f"[AUDITORIA] Input registrado: {texto[:50]}...", flush=True)

    # Função de background com SID injetado
    def processar_streaming(room_sid):
        # --- FAST PATHS (Sem Streaming) ---
        texto_lower = texto.lower()
        if detectar_pergunta_horario(texto) or \
           any(k in texto_lower for k in ["ligar tv", "desligar tv", "volume", "mudo"]) or \
           any(k in texto_lower for k in ["espelhar celular", "limpar memoria"]):
            
            res = gerar_resposta_jarvis(user_id, texto)
            socketio.emit('bot_msg', {'data': res}, room=room_sid)
            audio = gerar_audio_b64(res)
            if audio:
                socketio.emit('play_audio_remoto', {'url': f"data:audio/mp3;base64,{audio}"}, room=room_sid)
            return

        # --- SLOW PATH (LLM Streaming) ---
        print(f"[STREAM] Iniciando para SID: {room_sid}", flush=True)
        
        usuario = get_ou_criar_usuario(user_id)
        buffer_msgs = get_ultimas_mensagens(user_id, BUFFER_SIZE)
        saldo_atual = get_saldo(user_id)
        fatos = get_fatos(user_id)
        
        fatos_texto = "ESTADO ATUAL E MEMÓRIA DE FATOS:\n" + "\n".join([f"- {f['chave']}: {f['valor']}" for f in fatos]) if fatos else ""
        nome_usuario = usuario.get('nome_preferido') or "Mestre"
        agora_br = (datetime.now(timezone.utc) + timedelta(hours=-3)).strftime('%d/%m/%Y %H:%M')

        system_prompt = f"""VOCÊ É O JARVIS, ASSISTENTE OPERACIONAL (GOD MODE).
DATA: {agora_br}. MESTRE: {nome_usuario}.
ACESSO: Total (Shell, Arquivos, IoT).
OBJETIVO: Responda de forma direta e execute comandos.
CONTEXTO:
{fatos_texto}
SALDO: R$ {saldo_atual:.2f}
"""
        msgs = [{"role": "system", "content": system_prompt}] + \
               [{"role": m["role"], "content": m["content"]} for m in buffer_msgs] + \
               [{"role": "user", "content": texto}]

        try:
            stream = client.chat.completions.create(model=MODELO_ATIVO, messages=msgs, stream=True)
            
            frase_buffer = ""
            texto_completo = ""
            sentenca_idx = 0
            delimitadores = tuple(['.', '?', '!', '\n'])

            for chunk in stream:
                content = chunk.choices[0].delta.content or ""
                frase_buffer += content
                texto_completo += content
                
                # Emitindo via socketio.emit com room=sid
                socketio.emit('bot_msg_partial', {'data': content}, room=room_sid)

                if frase_buffer.strip().endswith(delimitadores) and len(frase_buffer) > 10:
                    sentenca_final = frase_buffer.strip()
                    audio_b64 = gerar_audio_b64(sentenca_final)
                    
                    if audio_b64:
                        socketio.emit('stream_audio_chunk', {
                            'audio': audio_b64, 
                            'index': sentenca_idx,
                            'text': sentenca_final
                        }, room=room_sid)
                        sentenca_idx += 1
                    
                    frase_buffer = ""

            if frase_buffer.strip():
                audio_b64 = gerar_audio_b64(frase_buffer)
                if audio_b64:
                    socketio.emit('stream_audio_chunk', {
                        'audio': audio_b64, 
                        'index': sentenca_idx,
                        'text': frase_buffer
                    }, room=room_sid)
            
            socketio.emit('bot_msg_end', {'full_text': texto_completo}, room=room_sid)
            adicionar_mensagem(user_id, "user", texto)
            adicionar_mensagem(user_id, "assistant", texto_completo)
            
            if "[[" in texto_completo:
                output_sys = processar_comandos_sistema(texto_completo, user_id)
                if output_sys:
                    socketio.emit('bot_msg', {'data': f"\n\n--- SISTEMA ---\n{output_sys}"}, room=room_sid)

            threading.Thread(target=lambda: processar_memoria(user_id), daemon=True).start()

        except Exception as e:
            print(f"[ERRO STREAM] {e}")
            socketio.emit('bot_msg', {'data': f"Erro no processamento: {e}"}, room=room_sid)

    # Inicia a thread passando o sid
    threading.Thread(target=processar_streaming, args=(sid,), daemon=True).start()

# --- Utilitários de Modelo ---
def get_installed_models():
    """Busca a lista real de modelos instalados no Ollama via HTTP Raw"""
    try:
        # Timeout agressivo (0.5s) para não travar a UI
        resp = requests.get("http://127.0.0.1:11434/api/tags", timeout=0.5)
        if resp.status_code == 200:
            data = resp.json()
            models = []
            for m in data.get('models', []):
                models.append(m.get('name', 'Modelo Desconhecido'))
            return models
    except: pass
    
    # Retorna cache rápido se falhar
    return ['qwen2.5-coder:32b', 'gpt-oss:120b-cloud', 'mistral', 'llama3', 'deepseek-r1']

@socketio.on('connect')
def handle_connect(*args, **kwargs): # Alterado para aceitar qualquer argumento
    print(f"[SOCKET] Cliente conectado. Detalhes: {args} {kwargs}", flush=True)
    emit('lista_modelos', {
        'modelos': get_installed_models(), 
        'atual': MODELO_ATIVO
    })

@socketio.on('listar_modelos')
def handle_models():
    emit('lista_modelos', {
        'modelos': get_installed_models(), 
        'atual': MODELO_ATIVO
    })

@socketio.on('trocar_modelo')
def handle_model_change(data):
    global MODELO_ATIVO
    MODELO_ATIVO = data.get('modelo')
    emit('log', {'data': f"Modelo: {MODELO_ATIVO}"})

if __name__ == '__main__':
    import logging
    # Silencia logs chatos
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    logging.getLogger('socketio').setLevel(logging.ERROR)
    logging.getLogger('engineio').setLevel(logging.ERROR)

    print("\n" * 2)
    print("=========================================")
    print("   JARVIS V12 - SISTEMA INTEGRADO")
    print("=========================================")
    
    # --- INICIALIZAÇÃO CLOUDFLARE (ACESSO REMOTO) ---
    print("[REDE] Iniciando Tunel Cloudflare...", flush=True)
    try:
        from pycloudflared import try_cloudflare
        # Tenta na porta 5000
        public_url_obj = try_cloudflare(port=5000)
        public_url = public_url_obj.tunnel
        print(f"\nACESSO REMOTO LIBERADO: {public_url}\n", flush=True)
        
        # Salva o link num arquivo para facil acesso
        link_path = os.path.join("docs", "LINK_JARVIS.txt")
        # Garante que a pasta existe
        if not os.path.exists("docs"): os.makedirs("docs")
        with open(link_path, "w") as f:
            f.write(public_url)
            
    except Exception as e:
        print(f"[REDE] Erro ao criar tunel: {e}", flush=True)

    def start_zap():
        zap_path = os.path.join(BASE_DIR, "jarvis-mcp-whatsapp")
        if os.path.exists(zap_path):
            subprocess.Popen(f'start cmd /k "cd /d {zap_path} && npm start"', shell=True)
    
    threading.Thread(target=start_zap, daemon=True).start()
    
    print("[SISTEMA] Servidor Online. Aguardando comandos...", flush=True)
    # Usa eventlet se disponivel para performance
    socketio.run(app, debug=False, port=5000, host='0.0.0.0', allow_unsafe_werkzeug=True)