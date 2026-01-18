# Script de reparo seguro
try:
    with open('../app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    with open('middle_part.py', 'r', encoding='utf-8') as f:
        middle = f.read()

    # Marcadores
    # O arquivo atual tem um buraco onde as funções sumiram.
    # Vamos achar o ponto antes e depois desse buraco.
    
    # Marcador 1: Onde termina a função carregar_base_conhecimento (que está incompleta no arquivo atual)
    start_marker = 'return "Base de conhecimento local não encontrada."'
    
    # Marcador 2: Onde começam as ferramentas auxiliares (que estão lá no final)
    end_marker = '# --- Utilitários de Modelo ---'
    
    idx_start = content.find(start_marker)
    idx_end = content.find(end_marker)

    if idx_start == -1 or idx_end == -1:
        print("ERRO: Marcadores não encontrados. Verifique o arquivo manualmente.")
        # Se não achou o start_marker, talvez a função inteira tenha sumido.
        # Vamos tentar achar o 'except: pass' anterior
        alt_start = 'except: pass'
        idx_alt = content.find(alt_start)
        if idx_alt != -1 and idx_end != -1:
             # Repara usando o marcador alternativo
             print("Usando marcador alternativo...")
             final_content = content[:idx_alt + len(alt_start)] + '\n' + middle + '\n' + content[idx_end:]
             with open('../app.py', 'w', encoding='utf-8') as f:
                 f.write(final_content)
             print("Reparo ALTERNATIVO concluído.")
        else:
             print(f"Start: {idx_start}, End: {idx_end}")
    else:
        # Substitui tudo entre o marcador de início e fim pelo conteúdo correto
        # Nota: middle_part.py já começa completando o 'return "Base..."' então pegamos ANTES dele
        # Mas espere, middle_part.py tem o return. O arquivo original tem?
        # O arquivo original tem APENAS '        except: pass' antes do buraco, segundo minha leitura anterior.
        
        # Vamos ser agressivos: Inserir DEPOIS de 'KNOWLEDGE_FILE)' e ANTES de 'Utilitários'
        
        final_content = content[:idx_start] + middle + '\n' + content[idx_end:]
        
        with open('../app.py', 'w', encoding='utf-8') as f:
            f.write(final_content)
        print("Reparo concluído com sucesso.")

except Exception as e:
    print(f"Erro no script de reparo: {e}")
