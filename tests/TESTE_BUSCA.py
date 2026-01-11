from sistema.web_search import pesquisar_web

print("--- TESTE DE DIAGNÓSTICO DE REDE E BUSCA ---")
print("Tentando buscar: 'Ofertas supermercado Ítalo Francisco Beltrão PR'...")

resultado = pesquisar_web("Ofertas supermercado Ítalo Francisco Beltrão PR")

print("\n--- RESULTADO OBTIDO ---")
print(resultado)
print("\n------------------------")
if "Erro" in resultado or "não retornou" in resultado:
    print("DIAGNÓSTICO: A busca falhou. Pode ser bloqueio temporário do DuckDuckGo.")
else:
    print("DIAGNÓSTICO: A busca funcionou! Se o Jarvis não responder, reinicie o sistema.")

input("\nPressione ENTER para sair.")
