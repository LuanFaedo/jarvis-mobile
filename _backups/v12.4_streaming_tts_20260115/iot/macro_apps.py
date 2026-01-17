from tv_controller import TVController
import time

TV_IP = "192.168.3.140"

def abrir_app_por_posicao(posicao):
    """
    Abre app baseado na posição na barra Home.
    Posição 1 = Primeiro app útil após o menu de sistema.
    """
    print(f"--- EXECUTANDO MACRO: Abrir App na Posição {posicao} ---")
    ctrl = TVController(TV_IP)
    
    # 1. Abrir Home
    print("1. HOME")
    ctrl.home()
    time.sleep(4) # Espera a barra carregar bem
    
    # 2. Resetar para a esquerda (garantir inicio)
    # Geralmente 10 esquerda é suficiente para bater no canto
    print("2. Resetando posição (<<<<<)")
    ctrl.left(10)
    time.sleep(1)
    
    # 3. Navegar para a direita até o app
    # Nota: As primeiras posições costumam ser [Config] [Source] [Search].
    # Vamos assumir que 'posicao' conta a partir do primeiro APP real.
    # Pode precisar ajustar o offset inicial.
    
    print(f"3. Navegando para o alvo (>> {posicao}x)")
    if posicao > 0:
        ctrl.right(posicao)
        time.sleep(1)
    
    # 4. Selecionar
    print("4. ENTER")
    ctrl.enter()
    
    print("--- MACRO FINALIZADA ---")

if __name__ == "__main__":
    # Exemplo: Tenta abrir o app na posição 3 (chute inicial)
    # Ajuste este numero no teste
    abrir_app_por_posicao(3)
