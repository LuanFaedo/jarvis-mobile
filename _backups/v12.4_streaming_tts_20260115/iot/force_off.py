from tv_controller import TVController
from samsungtvws import SamsungTVWS
import time

IP = "192.168.3.141"

def force_off():
    print(f"Tentando forçar desligamento em {IP}...")
    
    # Método 1: Key Power via Controller (Padrão)
    print("1. Tentando KEY_POWER padrão...")
    ctrl = TVController(IP)
    res = ctrl.desligar()
    print(f"Resultado: {res}")
    
    time.sleep(2)
    
    # Método 2: Power via Shortcuts (API Alternativa)
    print("2. Tentando Shortcuts Power...")
    try:
        token = ctrl.token
        tv = SamsungTVWS(host=IP, port=8002, token=token, timeout=5, name='Jarvis')
        tv.shortcuts().power()
        print("Comando enviado (Shortcuts).")
    except Exception as e:
        print(f"Erro shortcuts: {e}")

    time.sleep(2)

    # Método 3: Enviar tecla POWER via Raw Remote
    print("3. Tentando Raw Key KEY_POWER...")
    try:
        tv.send_key('KEY_POWER')
        print("Enviado KEY_POWER raw.")
    except Exception as e:
        print(f"Erro raw: {e}")

    # Método 4: Enviar tecla POWEROFF explicita
    print("4. Tentando Raw Key KEY_POWEROFF...")
    try:
        tv.send_key('KEY_POWEROFF')
        print("Enviado KEY_POWEROFF raw.")
    except Exception as e:
        print(f"Erro raw off: {e}")

if __name__ == "__main__":
    force_off()
