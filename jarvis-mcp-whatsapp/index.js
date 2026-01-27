import pkg from 'whatsapp-web.js';
const { Client, LocalAuth, MessageMedia } = pkg;
import qrcode from 'qrcode-terminal';
import dotenv from 'dotenv';
import chalk from 'chalk';
import fs from 'fs';
import path from 'path';

dotenv.config();

// --- CONFIGURAÇÃO META AI ---
const META_AI_ID = '13135550002@c.us'; 
const imageRequests = new Map(); 

// Variável para controlar a "Cobrança" (Nudge)
let metaAiNudgeTimer = null;

const BRIDGE_FILE = path.resolve('../meta_ai_trigger.json');

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        args: [
            '--no-sandbox', 
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu'
        ],
        headless: true
    },
    webVersionCache: {
        type: 'remote',
        remotePath: 'https://raw.githubusercontent.com/wppconnect-team/wa-version/main/html/2.2412.54.html',
    }
});

client.on('qr', (qr) => qrcode.generate(qr, { small: true }));

client.on('ready', async () => {
    console.log(chalk.green('✅ JARVIS WHATSAPP ONLINE E PRONTO!'));
    
    // --- PATCH NUCLEAR PARA CORRIGIR "NO LID FOR USER" ---
    try {
        await client.pupPage.evaluate(() => {
            const META_ID_USER = '13135550002';
            const META_ID_SERIAL = '13135550002@c.us';

            // Função auxiliar de Bypass
            function shouldBypass(wid) {
                if (!wid) return false;
                if (typeof wid === 'string') return wid.includes(META_ID_USER);
                if (wid._serialized === META_ID_SERIAL || wid.user === META_ID_USER) return true;
                return false;
            }

            // 1. Patch WidFactory
            if (window.Store && window.Store.WidFactory && window.Store.WidFactory.toUserLid) {
                const originalToUserLid = window.Store.WidFactory.toUserLid;
                window.Store.WidFactory.toUserLid = function (wid) {
                    if (shouldBypass(wid)) return wid; // Retorna o próprio ID sem converter
                    return originalToUserLid.apply(this, arguments);
                };
            }

            // 2. Patch LidUtils (Versões novas do WA)
            if (window.Store && window.Store.LidUtils && window.Store.LidUtils.getCurrentLid) {
                const originalGetCurrentLid = window.Store.LidUtils.getCurrentLid;
                window.Store.LidUtils.getCurrentLid = function (wid) {
                    if (shouldBypass(wid)) return wid;
                    return originalGetCurrentLid.apply(this, arguments);
                };
            }
            
            console.log("[PATCH] Sistema LID blindado para Meta AI.");
        });
    } catch (e) {
        console.error(chalk.red(`[PATCH ERRO] Falha ao aplicar vacina LID: ${e.message}`));
    }

    // --- LOOP DA BRIDGE ---
    setInterval(() => {
        if (fs.existsSync(BRIDGE_FILE)) {
            try {
                const rawData = fs.readFileSync(BRIDGE_FILE, 'utf8');
                try { fs.unlinkSync(BRIDGE_FILE); } catch(e){} 
                
                if (!rawData.trim()) return;

                const trigger = JSON.parse(rawData);
                console.log(chalk.magenta(`[BRIDGE] Pedido Imagem: ${trigger.prompt}`));

                imageRequests.set('latest', { 
                    user: trigger.target, 
                    prompt: trigger.prompt,
                    original_user: trigger.original_user_id 
                });
                
                // HUMANIZAÇÃO: Delay antes de enviar
                const delay = Math.floor(Math.random() * 3000) + 2000;
                console.log(chalk.yellow(`[BRIDGE] Aguardando ${delay}ms para digitar...`));

                setTimeout(() => {
                    sendToMetaAiWithNudge(trigger.prompt);
                }, delay);

            } catch (e) { console.error(chalk.red(`[BRIDGE ERRO] Loop: ${e.message}`)); }
        }
    }, 1000);
});

// --- FUNÇÃO DE ENVIO COM COBRANÇA (NUDGE) ---
async function sendToMetaAiWithNudge(prompt) {
    try {
        // Limpa qualquer timer pendente anterior (Reset)
        if (metaAiNudgeTimer) {
            clearTimeout(metaAiNudgeTimer);
            metaAiNudgeTimer = null;
        }

        // Envia o prompt principal
        await client.sendMessage(META_AI_ID, prompt);
        console.log(chalk.green(`[META AI] Prompt enviado: "${prompt.slice(0,30)}..."`));
        console.log(chalk.yellow(`[NUDGE] Preparando 'Ataque Duplo' em 5 segundos...`));

        // ATAQUE DUPLO: Cobra RÁPIDO (5s) para forçar o processamento
        metaAiNudgeTimer = setTimeout(async () => {
            console.log(chalk.yellow(`[NUDGE] Enviando reforço de cobrança...`));
            
            const nudges = ["Gerou a imagem?", "E a foto?", "Conseguiu?", "Manda aí"];
            const chosenNudge = nudges[Math.floor(Math.random() * nudges.length)];
            
            try {
                await client.sendMessage(META_AI_ID, chosenNudge);
                console.log(chalk.green(`[NUDGE] Reforço enviado: "${chosenNudge}"`));
            } catch (err) {
                console.error(chalk.red(`[NUDGE FALHA] ${err.message}`));
            }
            
            metaAiNudgeTimer = null;
        }, 5000); // 5 segundos apenas! 

    } catch (e) {
        console.error(chalk.red(`[ENVIO ERRO] ${e.message}`));
    }
}

const START_TIMESTAMP = Math.floor(Date.now() / 1000);

// --- ESCUTA RESPOSTAS DA META AI ---
client.on('message_create', async msg => {
    try {
        if (msg.timestamp < START_TIMESTAMP) return;

        // Se a Meta AI respondeu (Texto ou Imagem), cancela a cobrança!
        if (msg.from === META_AI_ID) {
            if (metaAiNudgeTimer) {
                clearTimeout(metaAiNudgeTimer);
                metaAiNudgeTimer = null;
                // console.log(chalk.gray(`[NUDGE] Timer cancelado (resposta recebida).`));
            }
        }

        // Se for a Imagem esperada
        if (msg.from === META_AI_ID && msg.hasMedia) {
            console.log(chalk.magenta(`[META AI] Imagem recebida!`));
            
            const requestInfo = imageRequests.get('latest');
            
            if (requestInfo) {
                const media = await msg.downloadMedia();
                await client.sendMessage(requestInfo.user, media, { caption: `🎨 ${requestInfo.prompt}` });
                console.log(chalk.green(`[ZAP] Entregue.`));

                if (requestInfo.original_user) {
                    try {
                        await fetch("http://localhost:5000/api/receive_image", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({
                                user_id: requestInfo.original_user,
                                image: media.data, 
                                caption: requestInfo.prompt
                            })
                        });
                        console.log(chalk.green(`[APP] Sincronizado.`));
                    } catch (errApi) {}
                }
            }
            return; 
        }
    } catch (e) { console.error(chalk.red(`[META AI] Erro: ${e.message}`)); }
});

// --- INTERAÇÃO NORMAL ---
client.on('message', async msg => {
    try {
        if (!msg || !msg.id || !msg.from) return;
        if (msg.from === 'status@broadcast' || msg.fromMe) return;
        if (msg.from === META_AI_ID) return; 
        if (msg.timestamp < START_TIMESTAMP) return;

        const senderId = msg.from;
        const userText = msg.body;

        let mediaData = null;
        if (msg.hasMedia) {
            try {
                const media = await msg.downloadMedia();
                if (media && (media.mimetype.startsWith('audio/') || msg.type === 'ptt' || media.mimetype.startsWith('image/'))) {
                    mediaData = { data: media.data, mimetype: media.mimetype };
                }
            } catch (e) {}
        }

        // Comando Direto /img
        if (userText.toLowerCase().startsWith('/img ') || userText.toLowerCase().startsWith('/gerar ')) {
            const prompt = userText.replace(/^\/img\s*/i, '').replace(/^\/gerar\s*/i, '').trim();
            imageRequests.set('latest', { user: senderId, prompt: prompt, original_user: senderId });
            
            // HUMANIZAÇÃO + NUDGE
            const delay = Math.floor(Math.random() * 3000) + 2000;
            setTimeout(() => {
                sendToMetaAiWithNudge(prompt);
            }, delay);
            
            await client.sendMessage(senderId, "🎨 Solicitando...");
            return;
        }

        // Cérebro Python
        const brainData = await generateJarvisResponse(userText, senderId, mediaData, senderId);

        if (brainData && brainData.response) {
            let finalText = brainData.response;
            
            // REMOVIDO TRIGGER DUPLICADO - A responsabilidade é da Bridge (JSON)
            finalText = finalText.replace(/\[\[GEN_IMG:.*?\]\]/g, '').trim();

            if (finalText) await client.sendMessage(senderId, finalText);

            if (brainData.audio_parts) {
                for (const part of brainData.audio_parts) {
                    if (part.audio) {
                        const audioMedia = new MessageMedia('audio/mp3', part.audio);
                        await client.sendMessage(senderId, audioMedia, { sendAudioAsVoice: true });
                        await new Promise(r => setTimeout(r, 300));
                    }
                }
            }
        }
    } catch (error) { console.error(chalk.red(`[ERRO] ${error.message}`)); }
});

async function generateJarvisResponse(input, senderId, media = null, chatId = null) {
    try {
        const payload = { text: input, sender: senderId, chat_id: chatId };
        if (media) {
            payload.mimetype = media.mimetype;
            if (media.mimetype.startsWith('image/')) payload.image_data = media.data;
            else payload.audio_data = media.data;
        }

        const response = await fetch("http://localhost:5000/api/whatsapp", {
            method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
        });
        return await response.json();
    } catch (e) { return { response: "Erro de conexão com o cérebro." }; }
}

client.initialize();
