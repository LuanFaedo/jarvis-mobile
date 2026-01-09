# JARVIS - Módulo WhatsApp (MCP Integration)

Este módulo conecta a inteligência do JARVIS ao WhatsApp, utilizando a Hugging Face para raciocínio.

## Pré-requisitos
- Node.js v18+
- Conta na Hugging Face (para obter o Token)

## Instalação

1. Abra o terminal na pasta `jarvis-mcp-whatsapp`:
   ```bash
   cd jarvis-mcp-whatsapp
   npm install
   ```

2. Configure o Token:
   - Abra o arquivo `.env`
   - Substitua `seu_token_huggingface_aqui` pelo seu token de acesso da Hugging Face (Read Access).

## Execução

1. Inicie o JARVIS:
   ```bash
   npm start
   ```

2. **Pareamento:**
   - Um QR Code aparecerá no terminal.
   - Abra o WhatsApp no seu celular -> Aparelhos Conectados -> Conectar Aparelho.
   - Escaneie o QR Code.

3. **Interação:**
   - Envie mensagens para o número conectado (ou peça para outra pessoa enviar).
   - O JARVIS responderá automaticamente.
   - Use comandos como `/ajuda` ou `/status`.

## Arquitetura MCP

O arquivo `mcp-config.json` contém a especificação para conectar este bot a clientes MCP como o Claude Desktop, caso deseje integrar o controle do bot a uma IA superior no futuro.
