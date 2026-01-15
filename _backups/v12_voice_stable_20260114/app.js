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
let awakeTimer = null; // Timer para resetar o modo "atenção"
let isAwake = false;   // FLAG DE ATENÇÃO (Ouvindo comando sequencial)
const SILENCE_DELAY = 2000; // 2 segundos de silêncio para processar
const AWAKE_TIMEOUT = 10000; // 10 segundos esperando comando após "Estou aqui"

// LISTA DE VARIAÇÕES FONÉTICAS (Fuzzy Matching)
const WAKE_WORDS = [
    "jarvis", "jarviz", "javis", "jarves", "javes", 
    "jarbas", "gervis", "yaris", "travis", "djarvis"
];

// --- AUDIO MGMT ---
function stopAudio() {
    if (currentAudio) {
        currentAudio.pause();
        currentAudio.currentTime = 0;
        currentAudio = null;
    }
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
            
            // Debug imediato da população de dados
            const currentText = (finalTranscript || interimTranscript);
            console.log(`[DEBUG MIC - POPULANDO]: ${currentText}`); 
            textInput.value = currentText;
            
            // Inicia Timer de Silêncio
            silenceTimer = setTimeout(() => {
                if (textInput.value.trim() !== "") {
                    processVoiceCommand(textInput.value);
                    // Reinicia buffer
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

socket.on('bot_msg', (data) => {
    isProcessing = false;
    setStatus('ONLINE', 'online');
    addMsg('assistant', data.data);
});

socket.on('play_audio_remoto', (data) => {
    // Lógica unificada para fila ou áudio único
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
    if (!window.audioQueue || window.audioQueue.length === 0) return;
    if (window.isPlayingQueue) return;

    window.isPlayingQueue = true;
    playNextInQueue();
}

function playNextInQueue() {
    if (window.audioQueue.length === 0) {
        window.isPlayingQueue = false;
        return;
    }
    const nextAudio = window.audioQueue.shift();
    stopAudio();
    currentAudio = new Audio(nextAudio.url);
    currentAudio.onended = () => playNextInQueue();
    currentAudio.play().catch(e => playNextInQueue());
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
