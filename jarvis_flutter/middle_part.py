
    return "Base de conhecimento local não encontrada."

def extrair_fatos_da_mensagem(user_id: str, texto: str):
    prompt_extracao = f"Analise a mensagem do usuário e extraia FATOS para memória de longo prazo.\nTexto: \"{texto}\"\nRetorne APENAS um JSON puro lista de objetos: [{{"tipo": "...", "chave": "...", "valor": "..."}}]"
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
        prompt = f"ERRO CRÍTICO DE SISTEMA DETECTADO. TENTE OUTRA ESTRATÉGIA.\nERROS: {chr(10).join(erros_detectados)}\nOBJETIVO: Corrigir comando para Windows.\nRETORNE APENAS O COMANDO CORRIGIDO no formato [[CMD: ...]]."
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

    system_prompt = f"""VOCÊ É O JARVIS, UM ASSISTENTE FINANCEIRO AVANÇADO E CONTROLADOR DE SISTEMA COM ACESSO TOTAL (GOD MODE).
DATA: {agora_br.strftime('%d/%m/%Y %H:%M')}. USUÁRIO MESTRE: {nome_usuario}.

=== DIRETRIZES ===
1. ASSISTENTE FINANCEIRO: Gerencie o saldo de {nome_usuario}. Confirme gastos/ganhos.
2. ACESSO TOTAL: Manipule arquivos, pastas, processos.
3. SEJA DIRETO: Não peça permissão.
4. RESPOSTA CURTA: No WhatsApp, seja breve.

=== PROCESSAMENTO MULTI-CHAT ===
5. Chats simultâneos ativos: {total_chats_ativos}. Não espere.

=== COMANDOS ===
- [[SEARCH: query]] -> Busca na internet.
- [[AUTO: comando | arg]] -> Interface (abrir_programa, digitar, clicar, minimizar_tudo).     
- [[CMD: comando]] -> Terminal.
- [[READ: path]] / [[WRITE: path | content]] -> Arquivos.

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

    if any(k in texto_lower for k in ["veja minha tela", "olhe minha tela", "o que está na tela", "leia a tela", "analise a tela"]) or modo_leitura_texto and "tela" in texto_lower:
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

        res_txt = re.sub(r'\[CONTEXTO_BUSCA_INTERNO\]:.*?(?=\n|$)', '', res_txt, flags=re.DOTALL)
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
    text_limpo = re.sub(r'\[\[.*?\,\].*?\]\]', '', text_limpo) 
    text_limpo = re.sub(r'[^ -]', '', text_limpo) 
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
    text_limpo = re.sub(r'\[\[.*?\,\].*?\]\]', '', text_limpo)
    text_limpo = re.sub(r'[^ -]', '', text_limpo)   
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
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as t:
            t.write(audio_bytes); p = t.name
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
    user_id = data.get('user_id', 'Mestre')
    texto = data.get('text', '').strip()
    if not texto or len(texto) < 5: return
    texto_lower = texto.lower()
    if any(sw in texto_lower for sw in STOPWORDS_PASSIVAS): return
    print(f"[PASSIVE] Memorizando contexto: '{texto}'")
    adicionar_mensagem(user_id, "user", f"[CONTEXTO AMBIENTE]: {texto}")

@socketio.on('active_command')
@socketio.on('jarvis_command')
def handle_active_command(data):
    user_id = data.get('user_id', 'Mestre')
    texto = data.get('text', '')
    if not texto or len(texto.strip()) < 2: return
    print(f"[ACTIVE] Comando direto: '{texto}'", flush=True)
    resposta = gerar_resposta_jarvis(user_id, texto)
    audio_b64 = gerar_audio_b64(resposta)
    termos_fim = ['tchau', 'até logo', 'obrigado jarvis', 'encerrar', 'dormir']
    continuar = not any(t in resposta.lower() for t in termos_fim)
    emit('bot_response', {'text': resposta, 'audio': audio_b64, 'continue_conversation': continuar})
    try:
        audios = gerar_multiplos_audios(resposta)
        if audios and len(audios) > 1:
            emit('audio_parts_start', {'total': len(audios)})
            for part in audios:
                emit('play_audio_remoto', {'url': f"data:audio/mp3;base64,{part['audio']}", 'parte': part['parte'], 'total': part['total']})
            emit('audio_parts_end', {'total': len(audios)})
    except: pass

@socketio.on('message_text')
def handle_legacy_message_text(data):
    handle_web({'text': data.get('data'), 'user_id': 'LegacyUser'})

