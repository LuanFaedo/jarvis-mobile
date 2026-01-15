// Simulação da Lógica do Frontend (app.js)
const WAKE_WORD = "jarvis";
let logs = [];

function addLog(msg) { console.log("[LOG]:", msg); }
function sendText(cmd) { console.log("[AÇÃO]: Enviando comando para o servidor ->", cmd); }
function playSystemSound(type) { console.log("[FEEDBACK]: Tocando som ->", type); }

function processVoiceCommand(fullText) {
    console.log(`\n--- Testando entrada: "${fullText}" ---`);
    if (!fullText) return;

    const lowerText = fullText.toLowerCase();
    
    // Verifica se "Jarvis" foi dito
    if (lowerText.includes(WAKE_WORD)) {
        // Separa o comando real
        const parts = lowerText.split(WAKE_WORD);
        let command = parts[parts.length - 1].trim();

        if (command.length > 0) {
            // Caso 1: Comando completo
            sendText(command);
        } else {
            // Caso 2: Só o nome
            playSystemSound("estou_aqui");
        }
    } else {
        console.log("[IGNORADO]: Sem a palavra-chave.");
    }
}

// --- CENÁRIOS DE TESTE ---
processVoiceCommand("Olá tudo bem com você");       // Deve ignorar
processVoiceCommand("Jarvis");                      // Deve responder "Estou aqui"
processVoiceCommand("Oi Jarvis");                   // Deve responder "Estou aqui" (pois não tem comando depois)
processVoiceCommand("Jarvis qual a hora atual");    // Deve enviar "qual a hora atual"
processVoiceCommand("Por favor Jarvis abra o bloco de notas"); // Deve enviar "abra o bloco de notas"

