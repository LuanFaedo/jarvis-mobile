# --- HANDLER PARA FLUTTER APP (Memória Contínua) ---

# Lista de palavras para ignorar (alucinações comuns do STT em silêncio)
STOPWORDS_PASSIVAS = [
    "sous-titres", "subtitles", "legendas", "amara.org", "comunidade", 
    "fale agora", "ouvindo", "nenhuma fala", "tente novamente", "teclado"
]

@socketio.on('passive_log')
def handle_passive_log(data):
    """
    Recebe áudio ambiente/contexto, salva no banco, mas NÃO responde.
    Isso permite que o Jarvis 'lembre' do que foi falado antes do comando.
    """
    user_id = data.get('user_id', 'Mestre')
    texto = data.get('text', '').strip()

    # 1. Filtro de Ruído e Stopwords
    if not texto or len(texto) < 5: return
    
    texto_lower = texto.lower()
    if any(sw in texto_lower for sw in STOPWORDS_PASSIVAS):
        print(f"[PASSIVE] Ignorando alucinação: '{texto}'")
        return

    # 2. Salva no histórico como contexto (sem disparar LLM)
    # Prefixamos com [AMBIENTE] para o LLM saber que não foi uma ordem direta
    print(f"[PASSIVE] Memorizando contexto: '{texto}'")
    adicionar_mensagem(user_id, "user", f"[CONTEXTO AMBIENTE]: {texto}")


@socketio.on('active_command')
@socketio.on('jarvis_command') # Mantém compatibilidade
def handle_active_command(data):
    """Processa comandos diretos (quando 'Jarvis' é detectado)"""
    user_id = data.get('user_id', 'Mestre')
    texto = data.get('text', '')
    trigger_type = data.get('trigger_type', 'voice')
    
    # --- FILTRO DE SEGURANÇA ---
    if not texto or len(texto.strip()) < 2: return
        
    print(f"[ACTIVE] Comando direto: '{texto}'", flush=True)

    # O 'gerar_resposta_jarvis' já puxa as últimas mensagens do banco via 'get_ultimas_mensagens'.
    # Como o 'passive_log' salvou as falas anteriores lá, o contexto já está montado automaticamente!
    
    resposta = gerar_resposta_jarvis(user_id, texto)

    # Gera áudio e responde
    audio_b64 = gerar_audio_b64(resposta)
    termos_fim = ['tchau', 'até logo', 'obrigado jarvis', 'encerrar', 'dormir']
    continuar = not any(t in resposta.lower() for t in termos_fim)

    emit('bot_response', {
        'text': resposta,
        'audio': audio_b64,
        'continue_conversation': continuar
    })

    # Tratamento de áudios longos (multi-partes)
    try:
        audios = gerar_multiplos_audios(resposta)
        if audios and len(audios) > 1:
            emit('audio_parts_start', {'total': len(audios)})
            for part in audios:
                emit('play_audio_remoto', {
                    'url': f"data:audio/mp3;base64,{part['audio']}", 
                    'parte': part['parte'], 
                    'total': part['total']
                })
            emit('audio_parts_end', {'total': len(audios)})
    except: pass
