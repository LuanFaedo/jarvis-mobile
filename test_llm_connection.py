import os
import sys
from openai import OpenAI
import time

# Configurações extraídas do app.py
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:11434/v1")
API_KEY = "AAAAC3NzaC1lZDI1NTE5AAAAIJ9KfyhZeNo5E84kORaqKYu7gxopcvqT2hRabwJU/sXF"
MODELO_ATIVO = "gpt-oss:120b-cloud"

print(f"--- INICIANDO DIAGNÓSTICO DO CÉREBRO ---")
print(f"URL: {API_BASE_URL}")
print(f"Modelo Alvo: {MODELO_ATIVO}")
print(f"----------------------------------------")

client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

def testar_conexao():
    try:
        print("1. Tentando listar modelos disponíveis...")
        try:
            models = client.models.list()
            model_names = [m.id for m in models.data]
            print(f"   [OK] Modelos encontrados: {model_names}")
            
            if MODELO_ATIVO not in model_names:
                print(f"   [AVISO] O modelo '{MODELO_ATIVO}' NÃO aparece na lista. Isso pode causar erro 404.")
        except Exception as e:
            print(f"   [ALERTA] Não foi possível listar modelos (o proxy pode não suportar esse endpoint): {e}")

        print(f"\n2. Testando geração de texto com '{MODELO_ATIVO}'...")
        start = time.time()
        resp = client.chat.completions.create(
            model=MODELO_ATIVO,
            messages=[{"role": "user", "content": "Responda apenas: CONEXÃO ESTABELECIDA." }],
            max_tokens=20,
            timeout=60
        )
        duration = time.time() - start
        
        content = resp.choices[0].message.content
        print(f"   [SUCESSO] Resposta recebida em {duration:.2f}s")
        print(f"   [CÉREBRO DIZ]: {content}")
        return True

    except Exception as e:
        print(f"\n[FALHA CRÍTICA] Erro ao conectar com o cérebro:")
        print(f"{e}")
        return False

if __name__ == "__main__":
    success = testar_conexao()
    if not success:
        sys.exit(1)
