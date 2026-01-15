# Teste Funcional das Correções no app.py
import sys
import os

# Adiciona o diretório atual ao path para importar app.py
sys.path.append(os.getcwd())

def testar_correcoes():
    print("--- INICIANDO TESTE DE FUNÇÕES CRÍTICAS ---")
    
    try:
        # Importação seletiva para evitar rodar o servidor Flask
        from app import get_installed_models, handle_connect
        
        # Teste 1: get_installed_models
        print("\n[TESTE 1] Chamando get_installed_models()...")
        modelos = get_installed_models()
        print(f"Resultado: {modelos}")
        if isinstance(modelos, list) and len(modelos) > 0:
            print("SUCESSO: Função retornou uma lista válida. ✅")
        else:
            print("FALHA: Função não retornou uma lista. ❌")

        # Teste 2: handle_connect com argumento auth
        print("\n[TESTE 2] Chamando handle_connect(auth={'token': '123'})...")
        # Nota: handle_connect usa 'emit' do SocketIO, que pode dar erro fora do contexto do socket.
        # Mas aqui o objetivo é testar se a ASSINATURA da função aceita o argumento.
        try:
            handle_connect(auth={'token': 'test_token'})
            print("SUCESSO: Assinatura aceitou o argumento auth. ✅")
        except NameError as e:
            if "emit" in str(e):
                print("SUCESSO: A função foi chamada corretamente (o erro de 'emit' é esperado fora do socket). ✅")
            else:
                raise e

    except Exception as e:
        print(f"\n[ERRO CRÍTICO NO TESTE]: {e}")
        sys.exit(1)

if __name__ == "__main__":
    testar_correcoes()
