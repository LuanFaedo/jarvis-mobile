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
    // Converte quebras de linha em <br> para exibição correta
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

// --- MONITOR DE ERROS 404 ---
window.addEventListener('error', function(e) {
    if (e.target.tagName === 'IMG' || e.target.tagName === 'LINK' || e.target.tagName === 'SCRIPT') {
        addLog(`ERRO 404: Falha ao carregar recurso: ${e.target.src || e.target.href}`);
    }
}, true);

// --- CORE ACTIONS ---
function sendText() {
    const text = textInput.value.trim();
    if (text) {
        addToHistory(text);
        stopAudio();
        addMsg('user', text);
        socket.emit('fala_usuario', { text: text });
        textInput.value = "";
        textInput.blur();
        setStatus('processando...', 'busy');
        isProcessing = true;
    }
}

function toggleMic() {
    if (!recognition) {
        try {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.lang = 'pt-BR';
            recognition.continuous = false;
            recognition.interimResults = false;

            recognition.onstart = () => {
                micBtn.classList.add('listening');
                setStatus('ouvindo...', 'busy');
            };

            recognition.onend = () => {
                micBtn.classList.remove('listening');
                setStatus('AGUARDANDO COMANDO', 'online');
                recognition = null;
            };

            recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                textInput.value = transcript;
                sendText();
            };

            recognition.start();
        } catch (e) {
            alert("Seu navegador não suporta reconhecimento de voz.");
            addLog("Erro SpeechRecognition: " + e.message);
        }
    } else {
        recognition.stop();
        recognition = null;
    }
}

// --- SOCKET LISTENERS (O QUE FALTAVA!) ---

// 1. Receber lista de IAs
socket.on('lista_modelos', (data) => {
    console.log("Recebendo modelos:", data);
    modelSelector.innerHTML = ""; // Limpa lista anterior
    
    if (data.modelos && data.modelos.length > 0) {
        data.modelos.forEach(modelo => {
            const option = document.createElement('option');
            option.value = modelo;
            option.text = modelo;
            if (modelo === data.atual) option.selected = true;
            modelSelector.appendChild(option);
        });
        addLog(`Lista de modelos atualizada: ${data.modelos.length} IAs.`);
    } else {
        const option = document.createElement('option');
        option.text = "Nenhum modelo detectado";
        modelSelector.appendChild(option);
    }
});

// 2. Receber resposta do Bot
socket.on('bot_msg', (data) => {
    isProcessing = false;
    setStatus('ONLINE', 'online');
    addMsg('assistant', data.data);
    addLog("Resposta recebida do servidor.");
});

// 3. Tocar Áudio
socket.on('play_audio_remoto', (data) => {
    stopAudio();
    try {
        currentAudio = new Audio(data.url);
        currentAudio.onerror = (e) => {
            addLog("ERRO DE ÁUDIO: Falha ao carregar ou tocar o arquivo gerado.");
            setStatus('ERRO DE ÁUDIO', 'error');
        };
        currentAudio.onended = () => {
            micBtn.classList.remove('listening'); 
        };
        currentAudio.play().catch(e => {
            addLog("AUTOPLAY BLOQUEADO: Clique na tela para permitir áudio.");
        });
    } catch (e) {
        addLog("Erro ao criar objeto de áudio: " + e.message);
    }
});

// 4. Logs do Servidor
socket.on('log', (data) => {
    addLog("[SERVER] " + data.data);
});

function resetMemory() {
    if (confirm("Tem certeza que deseja resetar toda a memória do Jarvis? Isso é irreversível.")) {
        socket.emit('fala_usuario', { text: "SISTEMA: LIMPAR MINHA MEMÓRIA AGORA" });
        addLog("Solicitado reset de memória...");
    }
}

// --- INIT ---
document.addEventListener('DOMContentLoaded', () => {
    // Requisição inicial de modelos
    socket.emit('listar_modelos');
    
    // Polling de modelos a cada 30s
    setInterval(() => {
        socket.emit('listar_modelos');
    }, 30000);

    // Key Events
    textInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            sendText();
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            if (commandHistory.length > 0) {
                if (historyIndex > 0) historyIndex--;
                textInput.value = commandHistory[historyIndex];
            }
        } else if (e.key === "ArrowDown") {
            e.preventDefault();
            if (historyIndex < commandHistory.length - 1) {
                historyIndex++;
                textInput.value = commandHistory[historyIndex];
            } else {
                historyIndex = commandHistory.length;
                textInput.value = "";
            }
        }
    });

    // Retry de segurança
    setTimeout(() => {
        if (modelSelector.options.length <= 1) {
            console.log("Tentando forçar recarga de modelos...");
            socket.emit('listar_modelos');
        }
    }, 2000);

    addLog("Interface V12 carregada e corrigida.");
});
