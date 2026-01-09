from tv_controller import TVController
import time

# IP da sua TV
TV_IP = "192.168.3.140"

def testar_apps():
    print("--- INICIANDO TESTE DE ABERTURA DE APPS ---")
    ctrl = TVController(TV_IP)
    
    # Teste 1: Abrir YouTube
    print("\n[TESTE 1] Tentando abrir YouTube...")
    res = ctrl.open_app("youtube")
    print(f"Resultado: {res}")
    
    time.sleep(5) # Aguarda 5 segundos para você observar a TV
    
    # Teste 2: Abrir Navegador (Browser)
    print("\n[TESTE 2] Tentando abrir Navegador de Internet...")
    res = ctrl.open_app("browser")
    print(f"Resultado: {res}")

    print("\n--- FIM DO TESTE ---")

if __name__ == "__main__":
    testar_apps()
