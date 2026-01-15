# Teste de Autonomia Local (Corrigido)
import sys
import os

# Adiciona diretório atual ao path
sys.path.append(os.getcwd())

# Remove caminhos externos (Simulação de ambiente limpo)
clean_path = [p for p in sys.path if "D:" not in p and "compartilhado" not in p]
sys.path = clean_path

print("--- TESTE DE AUTONOMIA (ZERO DEPENDÊNCIA EXTERNA) ---")

try:
    import memoria.db_memoria as db
    print(f"Módulo de Memória: {db.__file__}")
    
    # Teste de Função
    db.salvar_diario_voz("Teste de autonomia local.")
    print("SUCESSO: Função salvar_diario_voz executada sem erros. ✅")

except ImportError as e:
    print(f"FALHA: Erro de importação: {e} ❌")
except Exception as e:
    print(f"FALHA: Erro de execução: {e} ❌")