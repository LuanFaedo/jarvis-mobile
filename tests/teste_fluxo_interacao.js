// Simulação do Fluxo de Interação V12 (Jarvis Awake Mode)

// --- MOCKS (Imitando o navegador) ---
let isAwake = false;
const WAKE_WORD = "jarvis";

function sendText(cmd) { 
    console.log(`[AÇÃO EXECUTADA]: Enviando para o servidor -> "${cmd}"`); 
    // Ao enviar, o Jarvis volta a dormir (standby)
    isAwake = false;
    console.log("[ESTADO]: Voltando para STANDBY (isAwake = false)");
}

function playSystemSound(type) { 
    if (type === "estou_aqui") console.log(`[FEEDBACK SONORO]: "Estou aqui"`); 
}

function logDebug(msg) { 
    console.log(`[DEBUG MIC - POPULANDO]: ${msg}`);
}

// --- LÓGICA CORE (Cópia fiel do app.js refatorado) ---
function processVoiceCommand(fullText) {
    if (!fullText) return;
    
    // Simula o debug visual solicitado
    logDebug(fullText);

    const lowerText = fullText.toLowerCase();

    // CASO 1: Jarvis já estava atento (respondeu "Estou aqui" antes)
    if (isAwake) {
        console.log(`[MODO ATENTO DETECTADO]: Processando comando direto...`);
        sendText(fullText); 
        return;
    }

    // CASO 2: Detectou "Jarvis" agora
    if (lowerText.includes(WAKE_WORD)) {
        console.log(`[WAKE WORD]: Detectada em "${fullText}"`);

        const parts = lowerText.split(WAKE_WORD);
        let command = parts[parts.length - 1].trim();

        if (command.length > 0) {
            // Sub-caso A: "Jarvis, abra o youtube"
            sendText(command);
        } else {
            // Sub-caso B: Apenas "Jarvis" -> Ativa modo atenção
            playSystemSound("estou_aqui");
            isAwake = true;
            console.log("[ESTADO]: MUDANÇA PARA MODO ATENTO (isAwake = true)");
            console.log("[UI]: Exibindo 'DIGA O COMANDO...' ");
        }
    } else {
        console.log(`[IGNORADO]: Ruído em standby -> "${fullText}"`);
    }
}

// --- CENÁRIO DE TESTE (Simulando uma conversa real) ---

console.log("--- TESTE 1: Ruído Inicial ---");
processVoiceCommand("hoje o dia está bonito"); // Deve ignorar

console.log("\n--- TESTE 2: Ativação Apenas pelo Nome ---");
processVoiceCommand("Jarvis"); 
// Esperado: "Estou aqui", isAwake = true

console.log("\n--- TESTE 3: Comando Sequencial (Sem dizer Jarvis) ---");
// Como isAwake está true, ele DEVE aceitar isso como comando
processVoiceCommand("Abra o navegador"); 
// Esperado: Enviar "Abra o navegador", isAwake = false

console.log("\n--- TESTE 4: Verificando Reset ---");
processVoiceCommand("Obrigado"); 
// Esperado: Ignorar, pois voltou para standby

console.log("\n--- TESTE 5: Comando Direto (One-Shot) ---");
processVoiceCommand("Jarvis qual a cotação do dólar");
// Esperado: Enviar "qual a cotação do dólar", manter standby
