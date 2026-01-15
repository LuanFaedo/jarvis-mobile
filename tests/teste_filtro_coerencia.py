# Teste de Filtro de Coerência
import sys
import os
sys.path.append(os.getcwd())

from sistema.auditoria import validar_coerencia, gravar_diario_voz
import memoria.db_memoria as db

def teste_filtro():
    print("--- TESTE DE FILTRO DE COERÊNCIA ---")
    
    amostras = [
        ("Olá tudo bem", True),           # Frase normal
        ("a", False),                     # Muito curto
        ("hum", False),                   # Curto/Ruído
        ("sim", False),                   # Palavra única curta
        ("Paralelepípedo", True),         # Palavra única longa (pode ser válida)
        ("aaaaaaaaaaaaa", False),         # Repetição
        ("k k k k k k", False),           # Repetição com espaço
        ("Jarvis qual a hora", True),     # Comando válido
        ("t t t t", False)                # Ruído de microfone
    ]
    
    acertos = 0
    for texto, esperado in amostras:
        resultado = validar_coerencia(texto)
        status = "✅" if resultado == esperado else "❌"
        if resultado == esperado: acertos += 1
        
        tipo = "COERENTE" if resultado else "RUÍDO   "
        print(f"[{status}] Texto: '{texto}' -> Classificado como: {tipo}")

    print(f"\nTaxa de Acerto: {acertos}/{len(amostras)}")
    
    # Teste de persistência real
    print("\nGravando frase teste no DB...")
    frase_real = "Isto é um teste de gravação coerente."
    gravar_diario_voz(frase_real)
    
    # Verifica DB
    conn = db.get_connection()
    row = conn.execute("SELECT texto FROM diario_voz ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    
    if row and row['texto'] == frase_real:
        print(f"DB OK: '{row['texto']}' gravado com sucesso. ✅")
    else:
        print(f"DB ERRO: Última gravação foi '{row['texto'] if row else 'Nada'}' ❌")

if __name__ == "__main__":
    teste_filtro()
