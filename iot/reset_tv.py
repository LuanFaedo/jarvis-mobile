import os
import time
from samsungtvws import SamsungTVWS

TOKEN_FILE = 'tv_token.json'
IP = '192.168.3.141'

def reset_and_connect():
    print(f"--- RESETANDO CONEXÃO COM TV {IP} ---")
    
    # 1. Apaga token antigo
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
        print("Token antigo removido.")
    
    # 2. Tenta conectar (Vai pedir permissão na TV)
    print("\n[ATENÇÃO] OLHE PARA A TV AGORA E ACEITE A CONEXÃO!")
    print("Tentando conectar...")
    
    try:
        # Timeout alto para dar tempo de você aceitar
        tv = SamsungTVWS(host=IP, port=8002, timeout=15, name='Jarvis')
        
        # Envia um comando inofensivo para testar
        tv.send_key('KEY_VOLDOWN')
        print("SUCESSO! Conexão estabelecida e comando enviado.")
        
        # Salva o novo token manualmente para garantir
        import json
        with open(TOKEN_FILE, 'w') as f:
            json.dump({IP: tv.token}, f)
        print("Novo token salvo com sucesso.")
        
    except Exception as e:
        err_str = str(e)
        if "ms.remote.touchEnable" in err_str or "ms.remote.touchDisable" in err_str:
            print("SUCESSO (Evento Touch recebido)!")
            # Tenta salvar o token se disponível no objeto tv, mesmo após exceção
            try:
                if tv.token:
                    import json
                    with open(TOKEN_FILE, 'w') as f:
                        json.dump({IP: tv.token}, f)
                    print(f"Novo token salvo: {tv.token}")
            except:
                print("Token não pôde ser recuperado do objeto TV.")
        else:
            print(f"FALHA REAL: {e}")

if __name__ == "__main__":
    # Garante que estamos na pasta certa para deletar o arquivo
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    reset_and_connect()
