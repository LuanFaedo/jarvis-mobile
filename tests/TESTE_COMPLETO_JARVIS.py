import os
import sys
import json
from datetime import datetime

# Simula o ambiente do app.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

try:
    from app import gerar_resposta_jarvis, gerar_audio_b64
    from sistema.web_search import pesquisar_web
    
    print("--- TESTE 1: BUSCA WEB ---")
    resultado_busca = pesquisar_web("Preço do Arroz em Francisco Beltrão")
    print(f"Busca retornou: {len(resultado_busca)} caracteres.")
    
    print("\n--- TESTE 2: INTELIGENCIA (GPT-OSS 120B) ---")
    # Patrick é o sender padrão
    resposta = gerar_resposta_jarvis("Patrick", "Jarvis, faça uma busca rápida sobre o preço do dólar hoje e me dê sua opinião.")
    print(f"Jarvis respondeu: {resposta[:200]}...")
    
    print("\n--- TESTE 3: GERAÇÃO DE ÁUDIO ---")
    audio_b64 = gerar_audio_b64("Teste de voz do sistema Jarvis concluído com sucesso.")
    if audio_b64 and len(audio_b64) > 100:
        print(f"Áudio gerado com sucesso! (Tamanho: {len(audio_b64)} bytes)")
    else:
        print("Falha na geração de áudio.")

except Exception as e:
    print(f"ERRO NO TESTE: {e}")
