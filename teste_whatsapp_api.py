"""
Teste de API WhatsApp - Verifica se a comunicação Python está funcionando
"""
import requests
import json

def testar_api_whatsapp():
    print("=" * 50)
    print("TESTE DE API WHATSAPP")
    print("=" * 50)

    url = "http://localhost:5000/api/whatsapp"

    payload = {
        "text": "Olá Jarvis, me responda com uma frase curta",
        "sender": "teste_local",
        "chat_id": "teste_local"
    }

    print(f"\n[1] Enviando requisição para: {url}")
    print(f"[2] Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(url, json=payload, timeout=60)

        print(f"\n[3] Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"\n[4] Resposta JSON recebida:")
            print(f"    - response: {data.get('response', 'NULL')[:100]}...")
            print(f"    - audio_response: {'SIM (' + str(len(data.get('audio_response', '') or '')) + ' chars)' if data.get('audio_response') else 'NULL'}")
            print(f"    - audio_parts: {len(data.get('audio_parts', [])) if data.get('audio_parts') else 0} partes")
            print(f"    - total_parts: {data.get('total_parts', 0)}")
            print(f"    - chat_id: {data.get('chat_id', 'NULL')}")

            # Verificar estrutura dos audio_parts
            if data.get('audio_parts'):
                print(f"\n[5] Detalhes dos audio_parts:")
                for i, part in enumerate(data['audio_parts']):
                    audio_data = part.get('audio', '')
                    print(f"    - Parte {i+1}: {len(audio_data)} chars base64")

            print("\n" + "=" * 50)
            print("RESULTADO: API FUNCIONANDO CORRETAMENTE")
            print("=" * 50)
            return True
        else:
            print(f"\n[ERRO] Resposta não-200: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print("\n[ERRO] Não foi possível conectar ao servidor Flask")
        print("       Verifique se app.py está rodando na porta 5000")
        return False
    except Exception as e:
        print(f"\n[ERRO] Exceção: {e}")
        return False

if __name__ == "__main__":
    testar_api_whatsapp()
