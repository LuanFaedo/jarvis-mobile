// Teste de Robustez Fonética Atualizado

let isAwake = false;
// Copiando a lista exata do app.js
const WAKE_WORDS = [
    "jarvis", "jarviz", "javis", "jarves", "javes", 
    "jarbas", "gervis", "yaris", "travis", "djarvis",
    "garvis", "jabes", "chaves", "jair"
];

function sendText(cmd) {
    console.log(`[AÇÃO]: Enviando comando -> "${cmd}"`);
    isAwake = false;
}

function playSystemSound(type) {
    if (type === "estou_aqui") console.log(`[FEEDBACK]: "Estou aqui" (Modo Atento Ativado)`);
}

function processVoiceCommand(fullText) {
    console.log(`\nEntrada: "${fullText}"`);
    const lowerText = fullText.toLowerCase();
    
    if (isAwake) {
        console.log("[MODO ATENTO]: Capturando comando sequencial...");
        sendText(fullText);
        return;
    }

    const detectedWord = WAKE_WORDS.find(word => lowerText.includes(word));

    if (detectedWord) {
        console.log(`[GATILHO]: Detectado via variação "${detectedWord}"`);
        const parts = lowerText.split(detectedWord);
        let command = parts[parts.length - 1].trim();

        if (command.length > 0) {
            sendText(command);
        } else {
            playSystemSound("estou_aqui");
            isAwake = true;
        }
    } else {
        console.log("[IGNORADO]: Nenhuma palavra-chave detectada.");
    }
}

// --- BATERIA DE TESTES ---
processVoiceCommand("Garvis"); // Nova palavra
processVoiceCommand("Jarbas"); // Palavra existente
processVoiceCommand("Djarvis"); // Palavra existente
processVoiceCommand("Chaves"); // Palavra extrema (ruído comum)
