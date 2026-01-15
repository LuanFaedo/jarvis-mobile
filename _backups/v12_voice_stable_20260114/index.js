import pkg from 'whatsapp-web.js';
const { Client, LocalAuth, MessageMedia } = pkg;
import qrcode from 'qrcode-terminal';
import dotenv from 'dotenv';
import chalk from 'chalk';

dotenv.config();

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
        headless: true
    }
});

client.on('qr', (qr) => qrcode.generate(qr, { small: true }));

client.on('ready', () => {
    console.log(chalk.green('✅ JARVIS WHATSAPP CONECTADO E PRONTO.'));
});

const START_TIMESTAMP = Math.floor(Date.now() / 1000);

client.on('message', async msg => {
    try {
        // 1. Ignora status e mensagens do próprio bot
        if (msg.from === 'status@broadcast' || msg.fromMe) return;

        // 2. Ignora mensagens antigas (antes do bot ligar) para evitar spam
        if (msg.timestamp < START_TIMESTAMP) {
            console.log(chalk.gray(`[Ignorado] Mensagem antiga de ${msg.timestamp}`));
            return;
        }

        const userText = msg.body;
        const senderId = msg.from;

        console.log(chalk.blue(`[📩]: ${userText}`));

        let mediaData = null;
        if (msg.hasMedia) {
            const media = await msg.downloadMedia();
            // Aceita Áudio ou Imagem
            if (media && (media.mimetype.startsWith('audio/') || media.mimetype.startsWith('image/') || msg.type === 'ptt')) {
                mediaData = {
                    data: media.data,
                    mimetype: media.mimetype
                };
                const tipo = media.mimetype.startsWith('image/') ? 'Imagem' : 'Áudio';
                console.log(chalk.yellow(`[📎] ${tipo} recebido.`));
            }
        }

        // Chama o cérebro com identificação do chat
        const brainData = await generateJarvisResponse(userText, senderId, mediaData, msg.from);

        // 1. Envia Texto
        if (brainData.response) {
            await client.sendMessage(senderId, brainData.response);
            console.log(chalk.gray(`[🤖]: Texto enviado.`));
        }

        // 2. Envia Áudio(s) - Suporte a múltiplos áudios para respostas longas
        if (brainData.audio_parts && brainData.audio_parts.length > 0) {
            const totalParts = brainData.audio_parts.length;
            console.log(chalk.yellow(`[🔊] Enviando ${totalParts} parte(s) de áudio...`));

            for (const audioPart of brainData.audio_parts) {
                try {
                    const audioMedia = new MessageMedia('audio/mp3', audioPart.audio);
                    await client.sendMessage(senderId, audioMedia, { sendAudioAsVoice: true });
                    console.log(chalk.gray(`[🔊]: Áudio ${audioPart.parte}/${audioPart.total} enviado.`));

                    // Pequena pausa entre áudios para evitar flood
                    if (totalParts > 1 && audioPart.parte < totalParts) {
                        await new Promise(resolve => setTimeout(resolve, 500));
                    }
                } catch (audioError) {
                    console.error(chalk.red(`[❌] Erro ao enviar áudio ${audioPart.parte}: ${audioError.message}`));
                }
            }
        } else if (brainData.audio_response) {
            // Fallback para compatibilidade com resposta única
            console.log(chalk.yellow(`[🔊] Enviando resposta em áudio...`));
            const audioMedia = new MessageMedia('audio/mp3', brainData.audio_response);
            await client.sendMessage(senderId, audioMedia, { sendAudioAsVoice: true });
            console.log(chalk.gray(`[🔊]: Áudio enviado.`));
        }

    } catch (error) {
        console.error(chalk.red('Erro:'), error.message);
    }
});

async function generateJarvisResponse(input, senderId, media = null, chatId = null) {
    try {
        console.log(chalk.yellow(`[⏳] Enviando para Cérebro Python... (Txt: ${input.length} chars | Media: ${media ? 'Sim' : 'Não'} | Chat: ${chatId || senderId})`));

        const payload = {
            text: input,
            sender: senderId,
            chat_id: chatId || senderId  // Identifica o chat para processamento simultâneo
        };

        if (media) {
            payload.mimetype = media.mimetype;
            if (media.mimetype.startsWith('image/')) {
                payload.image_data = media.data;
            } else {
                payload.audio_data = media.data;
            }
        }

        const response = await fetch("http://localhost:5000/api/whatsapp", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
            signal: AbortSignal.timeout(300000) // 5 Minutos de espera
        });

        if (!response.ok) {
            throw new Error(`HTTP Error: ${response.status}`);
        }

        const data = await response.json();

        // Log de múltiplos áudios
        if (data.total_parts && data.total_parts > 1) {
            console.log(chalk.cyan(`[📦] Resposta dividida em ${data.total_parts} partes de áudio`));
        }

        // Retorna o objeto completo { response, audio_response, audio_parts, total_parts, chat_id }
        return data;

    } catch (e) {
        console.error(chalk.red(`[❌] Erro de Conexão com Python: ${e.message}`));
        return { response: "⚠️ Erro de conexão com o cérebro (Python). Verifique se o app.py está rodando." };
    }
}

client.initialize();
