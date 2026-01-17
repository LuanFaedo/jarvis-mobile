# JARVIZ - Protocolo de Operação Total (GOD MODE)
*Última Atualização: 15 de Janeiro de 2026*

## 👑 RELAÇÃO MESTRE-SISTEMA
- **CRIADOR:** Patrick (Autoridade Suprema).
- **STATUS DO AGENTE:** Assistente Operacional Permanente.
- **GATILHO DE AÇÃO:** O Jarvis opera sob demanda imediata. A estrutura de comando padrão é: **"Jarvis, faça [comando]"**. 

## 🛡️ DIRETRIZES DE OPERAÇÃO E VALIDAÇÃO (CRÍTICO)

1.  **PROTOCOLO DE TESTE OBRIGATÓRIO:** 
    - Toda e qualquer alteração de código ou execução de comando deve ser **TESTADA IMEDIATAMENTE**.
    - O processo só pode ser considerado "finalizado" após a obtenção do **resultado correto e esperado**.
    - Se um teste falhar, o Jarvis deve realizar o auto-diagnóstico e corrigir o erro até que a validação passe com 100% de sucesso.
    - É PROIBIDO parar um processo baseado em "suposição" de funcionamento.

2.  **Execução > Explicação:** 
    - Se o Patrick pedir para "criar uma pasta", crie a pasta, teste se ela existe e diga "Feito".
    - Menos conversa, mais verificação técnica.

3.  **Backup Antes de Destruir:** 
    - Ao alterar arquivos de código críticos, sempre garanta que há uma versão anterior salva ou que a alteração é aditiva.

4.  **Proatividade e Correção:** 
    - Se perceber um erro no código ou no sistema, sugira a correção ou corrija automaticamente se for trivial, sempre validando após a alteração.


## ⚡ CAPACIDADES OPERACIONAIS REAIS


- **"Jarvis, faça a gestão das minhas contas":** Ele lê boletos via OCR e atualiza o banco de dados financeiro.


- **"Jarvis, faça o espelhamento do meu celular":** Ele inicia o protocolo SCRCPY e organiza a janela na tela.


- **"Jarvis, faça uma pesquisa sobre [assunto]":** Ele varre a web e entrega um resumo executivo direto.


- **"Jarvis, faça o controle da TV":** Ele interage via IoT para ligar/ajustar a televisão.


- **"Jarvis, fale comigo pelo celular":** Agora possui cliente Android nativo para comunicação via SocketIO.





---





## 🏗️ ARQUITETURA DE SUPORTE (V12.3)


- **Cérebro:** Flask (app.py) operando como o núcleo de processamento em modo Streaming.


- **Braços:** `ManipuladorTotal` (arquivos) e `AutomacaoPC` (interface).


- **Voz/Ouvido:** Interface Web com suporte a **Barge-In** (interrupção) e App Android (KivyMD).


- **Banco de Dados:** SQLite local (`jarvis_memoria.db`) com diário de voz integral e filtro de coerência.





## 📅 Histórico de Comandos do Criador


- **14/01/2026:** Implementada a filosofia de "Jarvis, faça algo".


- **14/01/2026:** [GEMINI] **Upgrade para V12.3 - Real-Time Streaming & Barge-In**:


  - Implementado **Streaming de Áudio**: O Jarvis começa a falar assim que a primeira sentença é gerada.


  - Implementado **Barge-In (Interrupção)**: O sistema detecta a Wake Word mesmo enquanto está falando e cala a boca imediatamente para ouvir o novo comando.


  - Criado **Diário de Voz em SQLite**: Gravação integral de todo áudio captado (após filtro de coerência) na tabela `diario_voz`.


  - **Ajuste de Voz Masculina**: Configurado ID 'AntonioNeural' com velocidade +20% para tom natural.


  - **Remoção de Dependências Externas**: O sistema agora é 100% autônomo, rodando inteiramente em `C:\WORD`.


  - **Correção Crítica WhatsApp**: Atualizada biblioteca para compatibilidade com a nova versão do WhatsApp Web.


  - **Lançamento Jarvis Mobile**: Criado projeto inicial em KivyMD (`/mobile`) para controle nativo via Android.


- **15/01/2026:** [CLAUDE] **Debug do Jarvis Mobile - App Crashando**:
  - **Problema identificado**: O APK instala corretamente mas fecha sozinho após abrir.
  - **ADB não detecta dispositivo**: WSL2 não passa USB diretamente, necessário usar ADB no Windows ou usbipd.
  - **Sistema de logging adicionado**: Modificado `main.py` (linhas 880-914) para salvar logs de crash em `/sdcard/jarvis_debug.log` e `/sdcard/jarvis_crash.log`.
  - **Possíveis causas de crash identificadas**:
    1. `MDIcon` dentro do `PulseMicButton` pode ter problemas de layout
    2. Incompatibilidade com KivyMD 1.2.0 (propriedades do `MDTextField` mudaram)
    3. Conflito entre `simple-websocket` e `websocket-client`
  - **Próximo passo**: Rebuildar APK e verificar logs no celular após crash.

- **15/01/2026:** [CLAUDE CODE - Opus 4.5] **Setup Flutter + Build Jarvis Flutter**:
  - **Flutter SDK instalado**: Clonado em `C:\flutter` (stable branch 3.38.7)
  - **Extensão Flutter no VS Code**: Instalada com Dart SDK
  - **PATH configurado**: Flutter adicionado ao PATH do usuário Windows
  - **Kotlin atualizado**: Versão 1.9.23 → **2.1.0** em `android/settings.gradle.kts`
  - **APK Flutter gerado com sucesso**: `jarvis_flutter/build/app/outputs/flutter-apk/app-debug.apk`

  **Status do Ambiente (flutter doctor)**:
  - ✓ Flutter 3.38.7 (stable)
  - ✓ Windows 10 Pro 64-bit
  - ✓ Visual Studio Build Tools 2019
  - ✓ 3 dispositivos conectados
  - ⚠ Android cmdline-tools ausente (opcional)
  - ⚠ Chrome não encontrado (opcional para web)

  **Estrutura Completa do Projeto Escaneada**:
  ```
  jarvis-mobile/
  ├── app.py (1.452 linhas) - Backend Flask + SocketIO
  ├── mobile/ - App Kivy Android (v5.0)
  ├── jarvis_flutter/ - App Flutter Android (NOVO - build OK)
  ├── memoria/ - SQLite + configs JSON
  ├── sistema/ - Core, automação, web search
  ├── iot/ - Controle Samsung TV
  ├── templates/ - Interface web
  ├── g1-noticias/ - Scraper G1
  ├── jarvis-mcp-whatsapp/ - Integração WhatsApp (Node.js)
  └── tests/ - 35+ arquivos de teste
  ```

  **Tecnologias Ativas**:
  | Camada | Stack |
  |--------|-------|
  | Backend | Python, Flask, SocketIO, Ollama, OpenAI |
  | Mobile | Kivy (Python) + Flutter (Dart) |
  | Voz | Edge-TTS (AntonioNeural +20%) |
  | IoT | samsungtvws, wakeonlan |
  | Banco | SQLite (jarvis_memoria.db - 3.1 MB) |

- **15/01/2026:** [CLAUDE CODE - Opus 4.5] **Streaming TTS em Tempo Real V2**:
  - **Novo sistema de streaming implementado** em `app.py` (linhas 837-1089)
  - **Funções criadas**:
    1. `stream_llm_sentences(messages)` - Generator que faz yield de frases completas do LLM
    2. `stream_tts_audio_async(text)` - Async generator com edge-tts streaming nativo
    3. `stream_tts_audio_sync(text)` - Wrapper síncrono para threading
    4. `stream_text_to_audio(generator, socketio, sid)` - Orquestrador principal
    5. `processar_com_streaming_real(user_id, texto, sid)` - Handler completo

  - **Novos endpoints Socket.IO**:
    - `fala_usuario_v2` - Texto com streaming TTS real
    - `audio_stream_v2` - Áudio + transcrição + streaming TTS

  - **Eventos emitidos**:
    | Evento | Descrição |
    |--------|-----------|
    | `bot_msg_partial` | Texto parcial (cada sentença) |
    | `stream_audio_chunk` | Áudio MP3 da sentença (base64) |
    | `bot_msg_end` | Fim do streaming com texto completo |
    | `transcription` | Texto transcrito do áudio (v2) |

  - **Fluxo otimizado**:
    ```
    LLM Stream → Detecta Sentença → Edge-TTS Stream → Socket.IO Emit
         ↓              ↓                 ↓                ↓
      tokens      yield frase       yield chunks      IMEDIATO
    ```

  - **Benefícios**:
    - Latência reduzida: Áudio começa ~1-2s após primeira sentença
    - Edge-TTS streaming nativo (sem arquivo intermediário)
    - Threading para não bloquear servidor Flask
    - Compatível com endpoints antigos (v1)

  **Arquitetura do App Mobile (v5.0)**:
  - Interface estilo Iron Man HUD com tema Ciano Neon
  - Comunicação via SocketIO com servidor Flask
  - Gravação de áudio via MediaRecorder do Android
  - Dependências: `kivy==2.3.0`, `kivymd==1.2.0`, `python-socketio==5.11.1`, `pyjnius`
  - Target API: 34, Min API: 24
  - Arquiteturas: arm64-v8a, armeabi-v7a

