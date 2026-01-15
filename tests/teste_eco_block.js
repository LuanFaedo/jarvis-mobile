// Teste de Bloqueio de Eco (Simulação de Estado)

let isSpeaking = false;
let audioQueue = [];

function log(msg) { console.log(`[LOG]: ${msg}`); }

function onMicInput(text) {
    if (isSpeaking) {
        log(`BLOQUEADO: Entrada '${text}' ignorada pois o bot está falando.`);
        return;
    }
    log(`ACEITO: Entrada '${text}' processada.`);
}

function startAudioPlayback() {
    log("Iniciando playback de áudio...");
    isSpeaking = true;
    log("STATUS: isSpeaking = true");
}

function finishAudioPlayback() {
    log("Playback finalizado.");
    isSpeaking = false;
    log("STATUS: isSpeaking = false");
}

// --- CENÁRIO ---
log("--- CENÁRIO 1: Usuário fala (Silêncio) ---");
onMicInput("Jarvis");

log("\n--- CENÁRIO 2: Bot começa a responder ---");
startAudioPlayback();

log("\n--- CENÁRIO 3: Microfone capta a própria voz do bot (Eco) ---");
onMicInput("Estou aqui para ajudar"); // Deve bloquear

log("\n--- CENÁRIO 4: Microfone capta usuário interrompendo ---");
onMicInput("Pare!"); // Deve bloquear (Infeliizmente, mas evita eco)

log("\n--- CENÁRIO 5: Bot termina de falar ---");
finishAudioPlayback();

log("\n--- CENÁRIO 6: Usuário fala novo comando ---");
onMicInput("Obrigado"); // Deve aceitar
