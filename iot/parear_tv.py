from samsungtvws import SamsungTVWS
import logging
import json
import os

# Configuração
TV_IP = "192.168.3.141"
TOKEN_FILE = 'tv_token.json'

logging.basicConfig(level=logging.INFO)

def parear():
    print(f"Tentando conectar na TV em {TV_IP}...")
    print(">>> OLHE PARA A TV AGORA E PREPARE O CONTROLE REMOTO <<<")
    
    token_path = os.path.join(os.path.dirname(__file__), TOKEN_FILE)

    # Tenta conectar SEM token para forçar o pedido
    try:
        print("Iniciando conexão WebSocket segura (Porta 8002)...")
        # Adiciona parametro 'name' para a TV saber quem está chamando
        tv = SamsungTVWS(host=TV_IP, port=8002, timeout=30, name='Jarvis')
        
        # Abre conexão WebSocket (aqui deve aparecer o popup)
        # O parametro initial_timeout dá tempo para você aceitar na TV
        tv.open()
        
        token = tv.token
        
        if token:
            print("\n>>> SUCESSO! TOKEN RECEBIDO! <<<")
            print(f"Token: {token}")
            
            # Salva o token
            data = {TV_IP: token}
            with open(token_path, 'w') as f:
                json.dump(data, f)
                
            print(f"Token salvo em {token_path}. Agora o Jarvis pode controlar a TV.")
        else:
            print("Conectou, mas não retornou token. Verifique se a TV já estava pareada antes.")
            
    except Exception as e:
        print(f"\n[ERRO] Falha no pareamento: {e}")
        print("Dica: Se a TV perguntar 'Permitir dispositivo?', selecione SIM rapidamente.")

if __name__ == "__main__":
    parear()
