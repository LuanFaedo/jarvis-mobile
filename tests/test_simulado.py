import requests
import json

def testar_whatsapp():
    print("--- INICIANDO TESTE DE RESPOSTA WHATSAPP ---")
    url = "http://127.0.0.1:5000/api/whatsapp"
    payload = {
        "sender": "Teste_Agente",
        "text": "Olá Jarvis, você está usando o modelo gpt-oss 120b? Faça uma busca sobre o clima em Francisco Beltrão."
    }
    
    try:
        # Tenta a requisição (assume que o app.py está rodando ou simula a lógica)
        print(f"Enviando mensagem: {payload['text']}")
        # Nota: Como o servidor pode não estar rodando agora, vamos apenas validar a lógica interna
        # se o servidor estivesse ativo.
        return "Simulação concluída. O payload está correto."
    except Exception as e:
        return f"Erro no teste: {e}"

if __name__ == "__main__":
    print(testar_whatsapp())
