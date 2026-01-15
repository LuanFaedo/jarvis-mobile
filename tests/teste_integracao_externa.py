# Teste de Integração Externa (D:)
import sys
import os

EXTERNAL_PATH = r"D:\compartilhado\Projetos\jarvis01\jarvizsql-FINANEIRO-ZAP"
if os.path.exists(EXTERNAL_PATH):
    sys.path.insert(0, EXTERNAL_PATH)

try:
    import memoria.db_memoria as db
    print(f"Módulo carregado de: {db.__file__}")
    
    if "D:" in db.__file__ or "compartilhado" in db.__file__:
        print("SUCESSO: Usando banco de dados EXTERNO. ✅")
        
        # Teste de leitura de dados reais
        print("\nConsultando Saldo Real...")
        saldo = db.get_saldo("Patrick") # Ou o ID que for usado lá
        print(f"Saldo no Banco D: R$ {saldo:.2f}")
        
    else:
        print("FALHA: Ainda usando banco LOCAL. ❌")

except Exception as e:
    print(f"ERRO CRÍTICO: {e}")

