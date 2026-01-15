// Teste de Exclusão Mútua de Hardware (AudioMutex)

let hardwareMicActive = false;
let isSpeaking = false;

// Mock do objeto Recognition do Browser
const recognition = {
    start: () => { 
        if (hardwareMicActive) throw new Error("CONFLITO: Hardware de mic já está sendo usado!");
        hardwareMicActive = true; 
        console.log("[HARDWARE]: Microfone LIGADO 🟢"); 
    },
    stop: () => { 
        hardwareMicActive = false; 
        console.log("[HARDWARE]: Microfone DESLIGADO 🔴"); 
    }
};

// --- MOCK DA LOGICA APP.JS ---
const AudioMutex = {
    locked: false,
    lock: function() {
        if (this.locked) return;
        this.locked = true;
        console.log("[MUTEX]: 🔒 BLOQUEANDO...");
        recognition.stop();
    },
    unlock: function() {
        if (!this.locked) return;
        this.locked = false;
        console.log("[MUTEX]: 🔓 LIBERANDO...");
        recognition.start();
    }
};

function simular_ciclo_fala() {
    console.log("=== INICIANDO TESTE DE EXCLUSÃO MÚTUA ===");
    
    // Estado inicial: Usuário falando
    recognition.start();
    console.log("Status: Usuário falando... (Mic Ativo)");

    // Bot começa a responder
    console.log("\n[EVENTO]: Resposta da IA chegou. Iniciando TTS...");
    AudioMutex.lock();
    
    // Tentativa de entrada de áudio durante a fala (Eco ou Ruído)
    console.log("\n[TESTE CONCORRÊNCIA]: Simulando eco captado pelo mic...");
    if (hardwareMicActive) {
        console.log("FALHA: Microfone ainda está ativo durante a fala! ❌");
    } else {
        console.log("SUCESSO: Microfone está fisicamente desligado. Eco impossível. ✅");
    }

    // Fim da fala
    console.log("\n[EVENTO]: TTS Finalizado.");
    AudioMutex.unlock();
    
    if (hardwareMicActive) {
        console.log("SUCESSO: Microfone reativado para o próximo comando. ✅");
    }
}

simular_ciclo_fala();
