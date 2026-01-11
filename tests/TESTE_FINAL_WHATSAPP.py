import requests
import json

def testar_fluxo_completo():
    print("--- INICIANDO TESTE REAL (WHATSAPP -> PYTHON -> GPT-OSS) ---")
    
    # 1. Testa se o servidor Flask está respondendo (precisa estar rodando)
    try:
        url = "http://127.0.0.1:5000/api/whatsapp"
        payload = {
            "sender": "Patrick",
            "text": "Jarvis, teste de sistema. Verifique o preço do bitcoin e responda em áudio."
        }
        print(f"Enviando para Jarvis: {payload['text']}")
        
        # Timeout longo para o modelo de 120B processar
        response = requests.post(url, json=payload, timeout=120)
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ SUCESSO NO FLUXO!")
            print(f"RESPOSTA TEXTO: {data.get('response', '')[:150]}...")
            if data.get('audio_response'):
                print(f"RESPOSTA ÁUDIO: Gerada ({len(data['audio_response'])} bytes)")
            else:
                print("RESPOSTA ÁUDIO: Não gerada.")
        else:
            print(f"❌ ERRO NO SERVIDOR: Status {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ FALHA DE CONEXÃO: O app.py está rodando? Erro: {e}")

if __name__ == "__main__":
    testar_fluxo_completo()
