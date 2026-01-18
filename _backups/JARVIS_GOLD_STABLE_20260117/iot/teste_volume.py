from tv_controller import TVController
import time

# IP da sua TV (já sabemos qual é)
TV_IP = "192.168.3.140"

def testar_volume():
    print("--- INICIANDO TESTE DE VOLUME ---")
    ctrl = TVController(TV_IP)
    
    print("Tentando aumentar volume (3x)...")
    for i in range(3):
        res = ctrl.volume_up()
        print(f"Comando {i+1}: {res}")
        time.sleep(1) # Pausa pequena entre comandos

    print("--- FIM DO TESTE ---")

if __name__ == "__main__":
    testar_volume()
