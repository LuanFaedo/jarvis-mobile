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

# ============================================================
# QR CODE PARA CONEXÃO RÁPIDA (Mobile App)
# ============================================================
def gerar_qrcode_conexao(url):
    """Gera QR Code para conexão rápida via app mobile"""
    if qrcode is None: return

    try:
        # Salva como imagem PNG (método principal)
        qr_img = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr_img.add_data(url)
        qr_img.make(fit=True)

        img = qr_img.make_image(fill_color="black", back_color="white")
        qr_path = os.path.join(BASE_DIR, "connect_qr.png")
        img.save(qr_path)

        # Header no terminal
        print("\n" + "="*55)
        print("       ESCANEIE COM O APP JARVIS MOBILE")
        print("="*55)

        # Tenta exibir ASCII no terminal (pode falhar em Windows)
        try:
            qr_ascii = qrcode.QRCode(version=1, box_size=1, border=1)
            qr_ascii.add_data(url)
            qr_ascii.make(fit=True)
            # Usa caracteres ASCII simples ao invés de Unicode
            matrix = qr_ascii.get_matrix()
            for row in matrix:
                line = ""
                for cell in row:
                    line += "##" if cell else "  "
                print(line)
        except:
            print("   [QR Code salvo como imagem]")

        print("="*55)
        print(f"   URL: {url}")
        print(f"   IMG: {qr_path}")
        print("="*55 + "\n")

        # Abre automaticamente no Windows
        if sys.platform == 'win32':
            os.startfile(qr_path)

    except Exception as e:
        print(f"[QR] Erro ao gerar QR Code: {e}")

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

        # Gera QR Code para conexão rápida via mobile
        gerar_qrcode_conexao(public_url)

    except Exception as e:
        print(f"[REDE] Erro ao criar tunel: {e}", flush=True)
        # Fallback: gera QR para URL local
        gerar_qrcode_conexao("http://localhost:5000")

    def start_zap():
        zap_path = os.path.join(BASE_DIR, "jarvis-mcp-whatsapp")
        if os.path.exists(zap_path):
            subprocess.Popen(f'start cmd /k "cd /d {zap_path} && npm start"', shell=True)

    # threading.Thread(target=start_zap, daemon=True).start()

    print("[SISTEMA] Servidor Online. Aguardando comandos...", flush=True)
    # Usa eventlet se disponivel para performance
    socketio.run(app, debug=False, port=5000, host='0.0.0.0', allow_unsafe_werkzeug=True)
