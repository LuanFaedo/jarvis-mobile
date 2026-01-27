const socket = io();

// DOM Elements
const chatContainer = document.getElementById('chat-container');
const textInput = document.getElementById('text-input');
const micBtn = document.getElementById('mic-btn');
const modelSelector = document.getElementById('model-selector');
const speedSelector = document.getElementById('speed-selector');
const statusBarText = document.getElementById('status-text');
const statusBarIndicator = document.getElementById('status-indicator');
const logOverlay = document.getElementById('log-overlay');
const logContent = document.getElementById('log-content');

let currentAudio = null;
let recognition = null;
let isProcessing = false;
let isMicActive = false;

// --- WAKE WORD VARIABLES ---
let silenceTimer = null;
let awakeTimer = null; 
let isAwake = false;   
let isSpeaking = false; // FLAG DE PROTEÇÃO CONTRA ECO (BLOQUEIO)
const SILENCE_DELAY = 2000;
const AWAKE_TIMEOUT = 10000;

// LISTA DE VARIAÇÕES FONÉTICAS (Fuzzy Matching)
const WAKE_WORDS = [
    "jarvis", "jarviz", "javis", "jarves", "javes", 
    "jarbas", "gervis", "yaris", "travis", "djarvis",
    "garvis", "jabes", "chaves", "jair" 
];

// --- MUTEX DE AUDIO (Modo Barge-In: Escuta Ativa) ---
const AudioMutex = {
    locked: false,
    
    lock: function() {
        if (this.locked) return;
        this.locked = true;
        isSpeaking = true;
        
        console.log("[MUTEX] 🟢 Iniciando fala (Microfone PERMANECE ATIVO para Barge-In)");
        
        // Em vez de parar, GARANTE que está escutando para poder ser interrompido
        if (!isMicActive && recognition) {
            try { 
                recognition.start(); 
                isMicActive = true;
                micBtn.classList.add('listening');
            } catch(e) { console.log("Erro ao ativar mic para barge-in:", e); }
        }
    },
    
    unlock: function() {
        if (!this.locked) return;
        console.log("[MUTEX] 🏁 Fala finalizada");
        this.locked = false;
        isSpeaking = false;
    }
};

// --- FUNÇÃO DE INTERRUPÇÃO (BARGE-IN) ---
function handleInterruption() {
    console.log("🛑 BARGE-IN DETECTADO! Interrompendo sistema...");
    
    // 1. Para o áudio atual imediatamente
    if (currentAudio) {
        currentAudio.pause();
        currentAudio.currentTime = 0;
        currentAudio = null;
    }
    
    // 2. Limpa a fila de áudios pendentes (Respostas longas)
    window.audioQueue = [];
    window.isPlayingQueue = false;
    
    // 3. Libera estado
    AudioMutex.unlock();
    isSpeaking = false;
    isAwake = true; // Já entra em modo de atenção
    
    // 4. Feedback Imediato
    addLog("⛔ INTERRUPÇÃO PELO USUÁRIO");
    setStatus("COMO POSSO AJUDAR?", "online");
    
    // 5. Resposta Sonora Local (Zero Latência)
    const utterance = new SpeechSynthesisUtterance("Pois não?");
    utterance.lang = "pt-BR";
    utterance.rate = 1.3;
    window.speechSynthesis.speak(utterance);
    
    // 6. Opcional: Avisar backend para parar streaming (se houvesse rota)
}

// --- AUDIO MGMT ---
function stopAudio() {
    if (currentAudio) {
        currentAudio.pause();
        currentAudio.currentTime = 0;
        currentAudio = null;
    }
    // Libera flags
    isSpeaking = false;
    AudioMutex.locked = false;
}

// --- UI HELPERS ---
function setStatus(text, type = 'online') {
    statusBarText.innerText = text.toUpperCase();
    statusBarIndicator.style.background = type === 'online' ? '#00ff00' : (type === 'busy' ? '#ffae00' : '#ff0000');
    statusBarIndicator.style.boxShadow = `0 0 5px ${statusBarIndicator.style.background}`;
}

function addMsg(role, text) {
    const div = document.createElement('div');
    div.className = `msg ${role}`;
    div.innerHTML = text.replace(/\n/g, '<br>');
    chatContainer.appendChild(div);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function toggleLogs() {
    logOverlay.classList.toggle('active');
}

function addLog(msg) {
    const div = document.createElement('div');
    div.innerText = `[${new Date().toLocaleTimeString()}] ${msg}`;
    logContent.appendChild(div);
    logContent.scrollTop = logContent.scrollHeight;
}

function changeModel() {
    const modelo = modelSelector.value;
    socket.emit('trocar_modelo', { modelo: modelo });
    addLog(`Solicitada troca para: ${modelo}`);
}

// --- HISTORY MGMT ---
let commandHistory = [];
let historyIndex = -1;

function addToHistory(text) {
    if (text && text.trim() !== "") {
        if (commandHistory.length === 0 || commandHistory[commandHistory.length - 1] !== text) {
            commandHistory.push(text);
        }
        historyIndex = commandHistory.length;
    }
}

window.addEventListener('error', function(e) {
    if (e.target.tagName === 'IMG' || e.target.tagName === 'LINK' || e.target.tagName === 'SCRIPT') {
        addLog(`ERRO 404: Falha ao carregar recurso: ${e.target.src || e.target.href}`);
    }
}, true);

// --- CORE ACTIONS ---
function sendText(text = null) {
    const messageToSend = text || textInput.value.trim();
    if (messageToSend) {
        addToHistory(messageToSend);
        stopAudio();
        addMsg('user', messageToSend);
        socket.emit('fala_usuario', { text: messageToSend });
        textInput.value = "";
        textInput.blur();
        setStatus('processando...', 'busy');
        isProcessing = true;
        
        // Desativa modo Awake após enviar comando
        isAwake = false;
        clearTimeout(awakeTimer);
    }
}

// --- VOICE RECOGNITION ENGINE ---
function initSpeechRecognition() {
    try {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.lang = 'pt-BR';
        recognition.continuous = true; 
        recognition.interimResults = true; 

        recognition.onstart = () => {
            isMicActive = true;
            micBtn.classList.add('listening');
            setStatus(isAwake ? 'OUVINDO COMANDO...' : 'ESCUTANDO (Diga "Jarvis")...', 'busy');
            addLog("Microfone ativado. Aguardando Wake Word...");
        };

        recognition.onend = () => {
            if (isMicActive) {
                console.log("Reiniciando reconhecimento...");
                try { recognition.start(); } catch(e){}
            } else {
                micBtn.classList.remove('listening');
                setStatus('AGUARDANDO COMANDO', 'online');
            }
        };

        recognition.onresult = (event) => {
            clearTimeout(silenceTimer);

            let interimTranscript = '';
            let finalTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript;
                } else {
                    interimTranscript += event.results[i][0].transcript;
                }
            }
            
            const currentText = (finalTranscript || interimTranscript).trim();
            const lowerText = currentText.toLowerCase();
            
            // --- LÓGICA DE BARGE-IN (INTERRUPÇÃO) ---
            if (isSpeaking) {
                // Verifica se ouviu "Jarvis" ou variações ENQUANTO fala
                const detectedWord = WAKE_WORDS.find(word => lowerText.includes(word));
                
                if (detectedWord) {
                    console.log(`[BARGE-IN] Gatilho '${detectedWord}' detectado durante fala!`);
                    handleInterruption();
                    // Limpa o reconhecimento para não processar "Jarvis" como comando novamente
                    textInput.value = "";
                    recognition.stop(); 
                    return;
                }
                
                // Se não for Jarvis, ignora (considera ECO da própria voz)
                console.log(`[ECO FILTER] Ignorando '${currentText}' durante fala.`);
                return; 
            }

            console.log(`[DEBUG MIC - POPULANDO]: ${currentText}`); 
            textInput.value = currentText;
            
            // Inicia Timer de Silêncio
            silenceTimer = setTimeout(() => {
                if (textInput.value.trim() !== "") {
                    processVoiceCommand(textInput.value);
                    recognition.stop(); 
                }
            }, SILENCE_DELAY);
        };

    } catch (e) {
        alert("Navegador sem suporte a voz.");
        addLog("Erro Speech: " + e.message);
    }
}

function processVoiceCommand(fullText) {
    if (!fullText) return;

    // --- GRAVAÇÃO INTEGRAL (DIÁRIO DE VOZ) ---
    // Envia tudo o que ouviu para o servidor salvar no log, independente de ser comando
    socket.emit('background_listen', { text: fullText });

    const lowerText = fullText.toLowerCase();
    
    // LÓGICA 1: Modo "Awake" (Já estava prestando atenção)
    // Aceita QUALQUER COISA como comando direto
    if (isAwake) {
        addLog(`[MODO ATENTO] Comando recebido: "${fullText}"`);
        sendText(fullText); 
        return;
    }

    // LÓGICA 2: Detecção de Wake Word (Com Tolerância Fonética)
    // Verifica se alguma das variações existe na frase
    const detectedWord = WAKE_WORDS.find(word => lowerText.includes(word));

    if (detectedWord) {
        addLog(`Wake Word detectada (${detectedWord}) em: "${fullText}"`);

        // Separa o comando: pega tudo que vem DEPOIS da palavra chave
        // Ex: "Jarviz abre o youtube" -> " abre o youtube"
        const parts = lowerText.split(detectedWord);
        // Pega a última parte para garantir (caso fale "Jarvis... Jarvis...")
        let command = parts[parts.length - 1].trim();

        if (command.length > 0) {
            // Caso A: "Jarvis [comando]" (Tudo junto)
            addLog(`Comando direto extraído: "${command}"`);
            sendText(command);
        } else {
            // Caso B: Apenas "Jarvis" (Pausa)
            addLog("Apenas Wake Word. Entrando em modo ATENÇÃO.");
            playSystemSound("estou_aqui");
            
            // ATIVA O MODO ALEXA (FLUXO CONTÍNUO)
            isAwake = true;
            setStatus("DIGA O COMANDO AGORA...", "busy");
            
            // Timer de segurança (10s para falar o comando)
            clearTimeout(awakeTimer);
            awakeTimer = setTimeout(() => {
                if (isAwake) {
                    isAwake = false;
                    addLog("Timeout de atenção. Voltando a standby.");
                    setStatus('AGUARDANDO "JARVIS"', 'online');
                    playSystemSound("timeout"); // Opcional
                }
            }, AWAKE_TIMEOUT);
        }
        
        textInput.value = "";
    } else {
        console.log(`[IGNORADO - STANDBY]: "${fullText}"`);
    }
}

function playSystemSound(type) {
    if (type === "estou_aqui") {
        setStatus('ESTOU AQUI', 'online');
        // Feedback sonoro rápido
        const utterance = new SpeechSynthesisUtterance("Estou aqui");
        utterance.lang = "pt-BR";
        utterance.rate = 1.2; // Um pouco mais rápido
        window.speechSynthesis.speak(utterance);
    }
}

function toggleMic() {
    if (!recognition) initSpeechRecognition();

    if (isMicActive) {
        isMicActive = false;
        isAwake = false; // Reseta flag ao desligar
        recognition.stop();
        addLog("Microfone desativado manualmente.");
    } else {
        recognition.start();
        addLog("Iniciando escuta...");
    }
}

// --- SOCKET LISTENERS ---

// NOVO: Escuta comando de parada forçada (Barge-in do Servidor)
socket.on('force_stop_playback', (data) => {
    console.log("[SERVER] Comando de SILÊNCIO recebido.");
    handleInterruption();
    addLog("🔇 Silêncio forçado pelo servidor.");
});

socket.on('lista_modelos', (data) => {
    modelSelector.innerHTML = "";
    if (data.modelos && data.modelos.length > 0) {
        data.modelos.forEach(modelo => {
            const option = document.createElement('option');
            option.value = modelo;
            option.text = modelo;
            if (modelo === data.atual) option.selected = true;
            modelSelector.appendChild(option);
        });
    }
});

// Mensagem completa (Legacy/FastPath) ou Sistema
socket.on('bot_msg', (data) => {
    isProcessing = false;
    setStatus('ONLINE', 'online');
    
    // Tratamento de Imagem (Meta AI Tag)
    let texto = data.data;
    if (texto.includes('[[GEN_IMG:')) {
        texto = texto.replace(/\[\[GEN_IMG:(.*?)\]\]/g, '<div class="img-generating"><i class="fa-solid fa-palette"></i> Gerando imagem: "$1"...</div>');
    }
    
    addMsg('assistant', texto);
});

// STREAMING DE TEXTO (Efeito Digitação)
let currentMsgDiv = null;
socket.on('bot_msg_partial', (data) => {
    if (!currentMsgDiv) {
        currentMsgDiv = document.createElement('div');
        currentMsgDiv.className = 'msg assistant streaming';
        chatContainer.appendChild(currentMsgDiv);
    }
    // Converte quebras de linha e adiciona texto
    currentMsgDiv.innerHTML += data.data.replace(/\n/g, '<br>');
    chatContainer.scrollTop = chatContainer.scrollHeight;
});

socket.on('bot_msg_end', (data) => {
    if (currentMsgDiv) {
        currentMsgDiv.classList.remove('streaming');
        currentMsgDiv = null; // Reseta para próxima mensagem
    }
    isProcessing = false;
    setStatus('ONLINE', 'online');
});

// STREAMING DE ÁUDIO (Chunk Playback)
socket.on('stream_audio_chunk', (data) => {
    // Adiciona na fila de áudio
    if (!window.audioQueue) window.audioQueue = [];
    
    // Constrói objeto compatível
    const chunkData = {
        url: `data:audio/mp3;base64,${data.audio}`,
        parte: data.index,
        texto: data.text
    };
    
    window.audioQueue.push(chunkData);
    
    // Se não estiver tocando nada, começa IMEDIATAMENTE
    if (!window.isPlayingQueue) {
        console.log("[STREAM] Iniciando playback do primeiro chunk...");
        processAudioQueue();
    } else {
        console.log(`[STREAM] Chunk ${data.index} enfileirado.`);
    }
});

socket.on('play_audio_remoto', (data) => {
    // Lógica unificada para fila ou áudio único (Legacy)
    if (data.parte) {
        if (!window.audioQueue) window.audioQueue = [];
        window.audioQueue.push(data);
        window.audioQueue.sort((a, b) => a.parte - b.parte);
    } else {
        playSingleAudio(data.url);
    }
});

socket.on('audio_parts_start', (data) => {
    window.audioQueue = [];
    window.isPlayingQueue = false;
});

socket.on('audio_parts_end', () => {
    processAudioQueue();
});

function playSingleAudio(url) {
    stopAudio();
    currentAudio = new Audio(url);
    currentAudio.play().catch(e => console.log(e));
}

function processAudioQueue() {
    if (!window.audioQueue || window.audioQueue.length === 0) {
        window.isPlayingQueue = false;
        
        // FIM DA FILA: LIBERA O MICROFONE (UNLOCK MUTEX)
        if (AudioMutex.locked) {
             AudioMutex.unlock();
             addLog("✅ Fala concluída.");
        }
        return;
    }
    
    window.isPlayingQueue = true; 

    const nextAudio = window.audioQueue.shift();
    if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
    }

    // INÍCIO DA FALA: BLOQUEIA MICROFONE (LOCK MUTEX)
    if (!AudioMutex.locked) {
        AudioMutex.lock();
        addLog("🔊 Bot falando... (Microfone Pausado)");
    }

    currentAudio = new Audio(nextAudio.url);
    
    currentAudio.onended = () => {
        // Verifica se ainda tem áudio na fila
        if (window.audioQueue.length > 0) {
            // Continua falando, mantém Lock
            setTimeout(() => processAudioQueue(), 200);
        } else {
            // FIM DA FILA: LIBERA O MICROFONE
            AudioMutex.unlock();
            addLog("✅ Fala concluída.");
            window.isPlayingQueue = false;
        }
    };
    
    currentAudio.onerror = (e) => {
        console.log("Erro no chunk de áudio, pulando...", e);
        processAudioQueue();
    };
    
    currentAudio.play().catch(e => {
        console.log("Autoplay block ou erro", e);
        processAudioQueue();
    });
}


socket.on('log', (data) => {
    addLog("[SERVER] " + data.data);
});

function resetMemory() {
    if (confirm("Resetar memória?")) {
        socket.emit('fala_usuario', { text: "SISTEMA: LIMPAR MINHA MEMÓRIA AGORA" });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    socket.emit('listar_modelos');
    setInterval(() => socket.emit('listar_modelos'), 30000);
    textInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") sendText();
    });
});