from flask import Flask, render_template, send_from_directory, request, jsonify, session, redirect, url_for, flash
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

# --- INTEGRAÇÃO SUPERVISOR (LOCAL OLLAMA) ---
# Substitui a API do Google (que deu erro 404) pelo Cérebro Local Potente
import requests

def consultar_gemini_nuvem(prompt):
    """
    Usa o Ollama Local como Supervisor Técnico.
    Simula uma 'Nuvem' mas roda localmente, garantindo funcionamento 100%.
    """
    print(f"[SUPERVISOR LOCAL] Analisando pedido: {prompt[:50]}...", flush=True)
    try:
        # Usa o modelo mais forte disponível (ou o ativo)
        modelo_supervisor = MODELO_ATIVO if MODELO_ATIVO else "gpt-oss:120b-cloud"
        
        payload = {
            "model": modelo_supervisor,
            "prompt": f"SYSTEM: Você é um Arquiteto de Software Sênior Python. O usuário precisa de um script ou comando. NÃO explique, apenas gere o código.\nPEDIDO: {prompt}",
            "stream": False,
            "options": {"temperature": 0.1} # Temperatura baixa para código preciso
        }
        
        resp = requests.post("http://127.0.0.1:11434/api/generate", json=payload, timeout=120)
        if resp.status_code == 200:
            return resp.json().get('response', '')
        else:
            return f"Erro no Supervisor Local: {resp.text}"
            
    except Exception as e:
        return f"Erro crítico no Supervisor: {e}"

load_dotenv()

# --- Módulo de Manipulação Total ---
from sistema.core import ManipuladorTotal
manipulador = ManipuladorTotal(os.path.dirname(os.path.abspath(__file__)))

# --- Sincronização de Tempo Real ---
OFFSET_TEMPORAL = timedelta(0)

def sincronizar_horario():
    global OFFSET_TEMPORAL
    try:
        print("[TIME] Sincronizando relógio com servidores globais...", flush=True)
        with urllib.request.urlopen("http://google.com", timeout=3) as conn:
            date_header = conn.headers['Date']
            data_real_utc = parsedate_to_datetime(date_header)
            data_sistema_utc = datetime.now(timezone.utc)
            OFFSET_TEMPORAL = data_real_utc - data_sistema_utc
            print(f"[TIME] Sincronizado! Desvio: {OFFSET_TEMPORAL.total_seconds():.2f}s", flush=True)
    except Exception as e:
        print(f"[TIME] Falha na sincronização online ({e}).", flush=True)

sincronizar_horario()

# --- Configurações de Pastas ---
# BASE_DIR já foi definido no topo
AUDIO_DIR = os.path.join(BASE_DIR, "audios")
HISTORY_DIR = os.path.join(BASE_DIR, "memoria")
CONFIG_FILE = os.path.join(HISTORY_DIR, "config_jarvis.json")
KNOWLEDGE_FILE = os.path.join(HISTORY_DIR, "memoria.json")

MAX_CHAR_INPUT = 1500
BUFFER_SIZE = 10
RESUMO_INTERVAL = 10

client = OpenAI(base_url="http://127.0.0.1:11434/v1", api_key="ollama")
MODELO_ATIVO = "gpt-oss:120b-cloud" # EXIGÊNCIA DO USUÁRIO (Melhor qualidade)
client_ollama = ollama.Client(host='http://127.0.0.1:11434')

for folder in [AUDIO_DIR, HISTORY_DIR]:
    if not os.path.exists(folder): os.makedirs(folder)

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"), static_folder=os.path.join(BASE_DIR, "static"))
app.secret_key = 'jarvis_v11_ultra'
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")

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
        resp = client.chat.completions.create(model=modelo_usado, messages=[{"role": "user", "content": prompt_extracao}], temperature=0, response_format={"type": "json_object"})
        dados = json.loads(resp.choices[0].message.content)
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
    # extrair_fatos_da_mensagem(user_id, texto) # Otimizado
    info_iot = processar_comando_iot(user_id, texto)
    usuario = get_ou_criar_usuario(user_id)
    buffer_msgs = get_ultimas_mensagens(user_id, BUFFER_SIZE)
    
    # --- BUSCA DADOS DE CONTEXTO (RESTURADO) ---
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
    
    system_prompt = f"""VOCÊ É O JARVIS. DATA: {agora_br.strftime('%d/%m/%Y %H:%M')}. USUÁRIO: {nome_usuario}.

=== DIRETRIZES DE PERSONALIDADE (MODO EXECUTIVO) ===
1. SEJA DIRETO: Não explique o comando que vai usar. Apenas use.
2. AÇÃO IMEDIATA: Se o usuário perguntar "Tenho o arquivo X?", NÃO PERGUNTE "Quer que eu procure?". PROCURE IMEDIATAMENTE com [[CMD: ...]].
3. SEM BUROCRACIA: Você tem acesso total. Não peça permissão para ler pastas ou listar arquivos.
4. RESPOSTA CURTA: Se for uma pergunta simples, resposta simples. Deixe textos longos APENAS para quando gerar código/scripts.
5. PROATIVIDADE: Se encontrar um caminho ambíguo, liste as opções encontradas em vez de perguntar "qual você quer?".

=== COMANDOS (USE SEM MEDO) ===
- [[CMD: python sistema/analise_disco.py]] -> USE ISTO para ver arquivos grandes/espaço em disco. (Muito mais rápido que PowerShell).
- [[CMD: dir C:\...]] -> Para listar/procurar arquivos comuns.
- [[READ: arquivo]] -> Para ler.
- [[WRITE: arquivo | conteudo]] -> Para criar scripts.
- [[ASK_GEMINI: ...]] -> Apenas se travar muito.

Memória Recente: {usuario['resumo_conversa']}

{fatos_texto}
{financas_contexto}
{info_iot if info_iot else ""}

CONHECIMENTO ADICIONAL:
{base_conhecimento[:500]}

INSTRUÇÕES FINAIS:
- Usuário perguntou -> Jarvis executa -> Jarvis mostra resultado.
- NUNCA diga "Vou executar um comando para...". Apenas execute e mostre o resultado.
- NÃO continue conversas anteriores sem pedido. Foco no comando ATUAL.
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
    match_arq = re.search(r'([a-zA-Z]:\\[^:<>"|?*]+\.(png|jpg|jpeg|bmp|webp))', texto, re.IGNORECASE)
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

    # 1. Espelhamento Android (SCRCPY)
    if any(k in texto_lower for k in ["espelhar celular", "espelhar tela", "abrir scrcpy", "tela do celular", "ver celular"]):
        threading.Thread(target=lambda: subprocess.Popen("ESPELHAR_CELULAR.bat", shell=True)).start()
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
        return res_txt
    except Exception as e: return f"Erro: {e}"

# --- Áudio e Imagem ---

async def _tts_async(text, path):
    try:
        with open(CONFIG_FILE, 'r') as f: speed = json.load(f).get('velocidade', '+0%')
    except: speed = '+0%'
    comm = edge_tts.Communicate(text, "pt-BR-AntonioNeural", rate=speed)
    await comm.save(path)

def gerar_audio_b64(text):
    if not text or len(text.strip()) == 0: return None
    
    # FILTRO INTELIGENTE: Não fala logs de sistema ou comandos técnicos
    if any(prefix in text for prefix in ["[SISTEMA]", "[CMD]", "[ERRO]", "SISTEMA:", "Traceback", "Error:", "> Comando"]):
        print(f"[AUDIO] Ignorado (Texto Técnico): {text[:30]}...", flush=True)
        return None

    # Limpa markdown e códigos para não bugar o áudio
    text_limpo = re.sub(r'```.*?```', '', text, flags=re.DOTALL) # Remove blocos de código
    text_limpo = re.sub(r'\[\[.*?\]\]', '', text_limpo) # Remove comandos [[CMD]]
    text_limpo = re.sub(r'[^\w\s,.?!]', '', text_limpo) # Remove símbolos estranhos
    text_limpo = text_limpo.strip()

    if not text_limpo: return None
    
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

def transcrever_audio(base64_data):
    try:
        audio_bytes = base64.b64decode(base64_data)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as t: t.write(audio_bytes); p = t.name
        wav = p + ".wav"
        AudioSegment.from_file(p).export(wav, format="wav")
        r = sr.Recognizer()
        with sr.AudioFile(wav) as s: texto = r.recognize_google(r.record(s), language="pt-BR")
        os.remove(p); os.remove(wav)
        return texto
    except sr.UnknownValueError: print("[ERRO] Áudio não entendido."); return None
    except Exception as e: print(f"[ERRO] Falha áudio: {e}"); return None

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

@app.route('/')
def index(): return render_template('index.html')

@app.route('/api/whatsapp', methods=['POST'])
def api_whatsapp():
    print("[API] Recebida nova requisição POST /api/whatsapp", flush=True)
    data = request.json
    sender = data.get('sender', 'Patrick')
    texto = data.get('text', '')
    
    # 1. Processamento de Áudio
    if data.get('audio_data'):
        trans = transcrever_audio(data['audio_data'])
        if trans:
            print(f"[ZAP ÁUDIO]: {trans}")
            texto = f"{texto} {trans}".strip()
            
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
    
    return jsonify({"response": res, "audio_response": gerar_audio_b64(res)})

@socketio.on('fala_usuario')
def handle_web(data):
    res = gerar_resposta_jarvis("Patrick", data.get('text'))
    emit('bot_msg', {'data': res})
    audio = gerar_audio_b64(res)
    if audio: emit('play_audio_remoto', {'url': f"data:audio/mp3;base64,{audio}"})

# --- Utilitários de Modelo ---
import requests 

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

@socketio.on('connect') # Dispara ao conectar
def handle_connect():
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
        with open("LINK_JARVIS.txt", "w") as f:
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