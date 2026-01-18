from tv_controller import TVController
import time

# IP da sua TV
TV_IP = "192.168.3.140"

def testar_navegacao():
    print("--- TESTE DE NAVEGAÇÃO SMART HUB ---")
    ctrl = TVController(TV_IP)
    
    print("1. Apertando HOME (Abrir barra)...")
    ctrl.home()
    time.sleep(3) # Espera barra subir
    
    print("2. Indo para DIREITA (x3)...")
    ctrl.right(3)
    time.sleep(1)
    
    print("3. Apertando ENTER (Selecionar)...")
    ctrl.enter()

    print("--- FIM DO TESTE ---")

if __name__ == "__main__":
    testar_navegacao()
