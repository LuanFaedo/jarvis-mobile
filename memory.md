# JARVIZ - Memória do Projeto (V11 STABLE)
*Última Atualização: 10 de Janeiro de 2026*

## 👑 Identidade e Governança
- **Criador/Mestre:** Patrick.
- **Assistente:** Jarviz (IA local baseada em Ollama/Llama 3.2).
- **Supervisor:** Gemini (Arquiteto Sênior Cloud).

## 📡 Conectividade e IoT
- **TV Samsung (Tizen):** 
  - IP: `192.168.3.140`
  - MAC: `e0:9d:13:5d:9b:f4`
  - Status: Root Exploit mapeado via scripts em `iot/`.
- **WhatsApp:** Ativo via pasta `jarvis-mcp-whatsapp` (Node.js).
- **Mobile:** Controle via `tools/scrcpy`.

## 🧠 Estado da Memória (SQLite)
- **Banco Principal:** `memoria/jarvis_memoria.db` (SQLite) - Gerencia fatos, financeiro e histórico de chat.
- **Legado/Backup:** `memoria/memoria.json` ainda existe mas a prioridade é o banco SQL.
- **Fatos Salvos:** Comandos ADB, IPs de rede, preferências de modelo (gpt-oss:120b-cloud).
- **Financeiro:** Módulo de controle de saldo e transações ativo via SQLite.

---
## 🔄 Regra de Persistência (Ponto Único de Verdade)
- **Ação Obrigatória:** O Agente Gemini deve atualizar este arquivo (`memory.md`) ao final de cada tarefa.
- **Contexto Central:** Este é o único arquivo para rastreamento de progresso, decisões arquiteturais e histórico de conversas relevantes, substituindo qualquer outro log de histórico anterior.

## 📅 Histórico de Atividades Recentes
- **10/01/2026:** Escaneamento completo do diretório realizado. Identificada estrutura de IoT, WhatsApp e Memória SQLite. Criado o arquivo `memory.md` inicial e estabelecida a regra de auto-atualização.
- **10/01/2026:** Corrigido Erro 403 intermitente. O problema foi rastreado até o módulo de busca web (`sistema/web_search.py`). Implementado tratamento silencioso de exceções HTTP para evitar que erros técnicos apareçam para o usuário final no WhatsApp.
- **10/01/2026:** Gemini realizou leitura completa do contexto (app.py, core, db, whatsapp) e validou a estrutura do projeto V11. Sistema pronto para operações.
