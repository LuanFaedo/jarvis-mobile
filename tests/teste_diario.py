# Teste de Gravação de Diário de Voz (Corrigido)
import sys
import os
sys.path.append(os.getcwd()) # Adiciona raiz ao path

import sistema.auditoria as aud
from datetime import datetime

def testar_diario():
    print("--- TESTE DE DIÁRIO DE VOZ ---")
    texto_teste = "Isso é apenas um ruído de fundo que deve ser gravado."
    
    # Executa gravação
    aud.gravar_diario_voz(texto_teste)
    
    # Verifica arquivo
    data_hoje = datetime.now().strftime("%Y-%m-%d")
    caminho = os.path.join("logs", "diario_voz", data_hoje, "log_integral.txt")
    
    if os.path.exists(caminho):
        print(f"SUCESSO: Arquivo criado em {caminho}")
        with open(caminho, 'r', encoding='utf-8') as f:
            conteudo = f.read()
            print(f"CONTEÚDO:\n{conteudo}")
            
        if texto_teste in conteudo:
            print("VALIDAÇÃO: O texto foi gravado corretamente. ✅")
        else:
            print("ERRO: Texto não encontrado no arquivo. ❌")
    else:
        print(f"ERRO: Arquivo não foi criado. ❌")

if __name__ == "__main__":
    testar_diario()