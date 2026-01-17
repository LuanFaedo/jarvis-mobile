from tv_controller import TVController
import time

# IP da sua TV
TV_IP = "192.168.3.140"
# MAC da sua TV (pegando do que eu salvei no banco antes, mas vou forçar aqui pro teste)
# Se não tiver o MAC, o Ligar não funciona. Vou tentar pegar do controller se ele tiver salvo.

def auditoria():
    print("=== AUDITORIA DE COMANDOS TV SAMSUNG ===")
    
    # Instancia Controller
    # Tenta carregar token salvo
    ctrl = TVController(TV_IP)
    
    if not ctrl.token:
        print("[FALHA CRÍTICA] Token não encontrado! Rode o parear_tv.py primeiro.")
        return

    print(f"[OK] Token carregado: {ctrl.token[:5]}...")

    # 1. Teste de Volume (Mais seguro para ver se responde)
    print("\n[TESTE 1] Volume UP x3...")
    res = ctrl.volume_up(3)
    print(f"Resultado: {res}")
    if "sucesso" in res:
        print(">>> PASSOU")
    else:
        print(">>> FALHOU")

    # 2. Teste de Digitação
    print("\n[TESTE 2] Digitação 'TESTE'...")
    res = ctrl.type_text("TESTE")
    print(f"Resultado: {res}")
    if "Digitado" in res:
        print(">>> PASSOU")
    else:
        print(">>> FALHOU")

    # 3. Teste de Desligar (Cuidado, vai desligar a TV mesmo)
    print("\n[TESTE 3] Desligar TV...")
    res = ctrl.desligar()
    print(f"Resultado: {res}")
    
    # 4. Teste de Ligar (WoL) - Só funciona se tiver MAC
    # Vou injetar o MAC que você me passou antes no banco ou tentar deduzir
    # Se não tiver MAC, vou pular
    if ctrl.mac:
        print("\n[TESTE 4] Ligar TV (Aguardando 5s antes de ligar)...")
        time.sleep(5)
        res = ctrl.ligar()
        print(f"Resultado: {res}")
    else:
        print("\n[SKIP] Teste de Ligar pulado (MAC não configurado no controller deste script)")

if __name__ == "__main__":
    auditoria()
