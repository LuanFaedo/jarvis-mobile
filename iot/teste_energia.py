from tv_controller import TVController
import time

TV_IP = "192.168.3.141"
# MAC pego do banco de dados na sessão anterior
TV_MAC = "e0:9d:13:5d:9b:f4"

def teste_ciclo_energia():
    print("=== TESTE DE CICLO DE ENERGIA (Desligar -> Ligar) ===")
    ctrl = TVController(TV_IP, TV_MAC)
    
    # 1. Desligar
    print("\n[PASSO 1] Enviando comando DESLIGAR...")
    res = ctrl.desligar()
    print(f"Resultado: {res}")
    
    print(">> Aguardando 15 segundos para a TV desligar completamente...")
    time.sleep(15)
    
    # 2. Ligar
    print("\n[PASSO 2] Enviando comando LIGAR (WoL)...")
    res = ctrl.ligar()
    print(f"Resultado: {res}")
    
    print("\n--- FIM DO TESTE ---")

if __name__ == "__main__":
    teste_ciclo_energia()
