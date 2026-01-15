// Teste de Robustez Fonética e Fluxo de Atenção (Alexa Style)

let isAwake = false;
const WAKE_WORDS = [
    "jarvis", "jarviz", "javis", "jarves", "javes", 
    "jarbas", "gervis", "yaris", "travis", "djarvis"
];

function sendText(cmd) { 
    console.log(`[AÇÃO]: Enviando comando -> "${cmd}"`); 
    isAwake = false; 
}

function playSystemSound(type) { 
    if (type === "estou_aqui") console.log(`[FEEDBACK]: "Estou aqui" (Modo Atento Ativado)`); 
}

function processVoiceCommand(fullText) {
    console.log(`
Entrada: "${fullText}"`);
    const lowerText = fullText.toLowerCase();
    
    // Se já estiver acordado, processa direto
    if (isAwake) {
        console.log("[MODO ATENTO]: Capturando comando sequencial...");
        sendText(fullText);
        return;
    }

    // Busca por variações fonéticas
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
console.log("=== INICIANDO TESTES DE ROBUSTEZ ===");

processVoiceCommand("Ei Jarviz"); // Teste variação fonética 1
processVoiceCommand("Abrir o youtube"); // Teste fluxo sequencial (Alexa style)

processVoiceCommand("Javis"); // Teste variação fonética 2
processVoiceCommand("Que horas são"); // Teste fluxo sequencial

processVoiceCommand("Jarbas limpe o sistema"); // Teste comando direto (One-shot) com variação

processVoiceCommand("Ei Jarvis"); // Teste wake word padrão
processVoiceCommand("Gervis"); // Teste variação fonética 3
