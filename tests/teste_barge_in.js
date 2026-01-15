// Teste de Barge-In (Interrupção)

let isSpeaking = false;
let audioQueue = ["Audio 1", "Audio 2", "Audio 3"];

// Mock do WAKE_WORDS
const WAKE_WORDS = ["jarvis", "jarviz"];

function handleInterruption() {
    console.log("🛑 BARGE-IN: Parando áudio e limpando fila.");
    isSpeaking = false;
    audioQueue = [];
}

function onMicInput(text) {
    console.log(`
Entrada Mic: "${text}"`);
    const lower = text.toLowerCase();
    
    if (isSpeaking) {
        const detected = WAKE_WORDS.find(w => lower.includes(w));
        if (detected) {
            console.log(`[GATILHO]: '${detected}' detectado.`);
            handleInterruption();
        } else {
            console.log("[ECO]: Ignorado.");
        }
    } else {
        console.log("[PROCESSAR]: Comando normal.");
    }
}

//CENÁRIO
console.log("--- INÍCIO: Bot Falando ---");
isSpeaking = true;

// 1. Eco da própria voz (Não contém wake word isolada ou usuário fala outra coisa)
// Nota: Se o bot disser "Eu sou o Jarvis", o barge-in VAI disparar. É uma limitação aceita.
onMicInput("Texto aleatório do bot"); 

// 2. Interrupção Real
onMicInput("Jarvis pare agora");

// 3. Pós-Interrupção
onMicInput("Novo comando");

