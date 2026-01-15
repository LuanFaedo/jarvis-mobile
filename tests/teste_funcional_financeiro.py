# Teste Funcional de Integração Financeira (Simulação de Voz)
import sys
import os

# Configura o path externo (Simulando o app.py)
EXTERNAL_PATH = r"D:\compartilhado\Projetos\jarvis01\jarvizsql-FINANEIRO-ZAP"
if os.path.exists(EXTERNAL_PATH):
    sys.path.insert(0, EXTERNAL_PATH)

try:
    from memoria.db_memoria import get_saldo, get_fatos
    
    # ID da Pâmela descoberto na auditoria
    ID_PAMELA = "120363405780854837@g.us"
    
    print("--- TESTE DE CONSULTA FINANCEIRA VIA INTEGRAÇÃO ---")
    
    # 1. Consulta Saldo
    print(f"Consultando saldo para ID: {ID_PAMELA}...")
    saldo = get_saldo(ID_PAMELA)
    
    print(f"SALDO RETORNADO: R$ {saldo:.2f}")
    
    if saldo == -4219.00:
        print("SUCESSO: Valor exato confirmado com a auditoria. ✅")
    else:
        print(f"ALERTA: Valor divergente (Esperado -4219.00). O banco pode ter sido atualizado. ⚠️")

    # 2. Teste de Fatos (Memória)
    print("\nConsultando fatos da Pâmela...")
    fatos = get_fatos(ID_PAMELA)
    if fatos:
        print(f"Fatos encontrados: {len(fatos)}")
        for f in fatos[:3]: # Mostra os 3 primeiros
            print(f"- {f['chave']}: {f['valor']}")
        print("SUCESSO: Memória de fatos acessível. ✅")
    else:
        print("AVISO: Nenhum fato encontrado para este usuário.")

except ImportError:
    print("ERRO CRÍTICO: Falha ao importar módulo de memória externo. ❌")
except Exception as e:
    print(f"ERRO DE EXECUÇÃO: {e} ❌")
