from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import requests
import re
import warnings
import time

warnings.filterwarnings("ignore")

def pesquisar_web(query, max_results=5):
    """
    Realiza pesquisa na web com múltiplas tentativas e estratégias de fallback.
    """
    print(f"[SEARCH] Iniciando busca inteligente: '{query}'", flush=True)
    
    resultados_formatados = []
    sucesso = False
    
    # Estratégia 1: Busca Direta (API Padrão)
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, region='br-pt', safesearch='off', max_results=max_results))
            if results:
                sucesso = True
                resultados_formatados.append(f"=== RESULTADOS (Modo Preciso): '{query}' ===\n")
                for i, r in enumerate(results):
                    resultados_formatados.append(f"{i+1}. {r.get('title')}\n   {r.get('body')}\n   Link: {r.get('href')}\n")
    except Exception as e:
        print(f"[SEARCH] Tentativa 1 falhou: {e}", flush=True)

    # Estratégia 2: Busca Genérica (Fallback) se a 1 falhou ou retornou vazio
    if not sucesso:
        print("[SEARCH] Tentando modo genérico (HTML)...", flush=True)
        try:
            # Simplifica a query para aumentar chance de retorno
            query_simples = query.replace("preço", "").replace("oferta", "").strip()
            with DDGS() as ddgs:
                results = list(ddgs.text(query_simples, region='br-pt', backend='html', max_results=max_results))
                if results:
                    sucesso = True
                    resultados_formatados.append(f"=== RESULTADOS (Modo Genérico): '{query_simples}' ===\n")
                    for i, r in enumerate(results):
                        resultados_formatados.append(f"{i+1}. {r.get('title')}\n   {r.get('body')}\n   Link: {r.get('href')}\n")
        except Exception as e:
            print(f"[SEARCH] Tentativa 2 falhou: {e}", flush=True)

    # Estratégia 3: Scraping Direto (Último recurso para sites conhecidos)
    if "beltrão" in query.lower() and not sucesso:
        print("[SEARCH] Tentando acesso direto a sites locais...", flush=True)
        sites_locais = [
            ("Mano Manfroi", "https://manomanfroi.com.br/ofertas"),
            ("Supermercado Grizon", "https://grizon.com.br")
        ]
        resultados_formatados.append("=== LINKS DIRETOS LOCAIS (Busca falhou) ===\n")
        for nome, url in sites_locais:
            resultados_formatados.append(f"- {nome}: {url}\n")
        sucesso = True

    if not sucesso:
        # SILENCIO O ERRO 403 PARA O USUÁRIO
        print("[SEARCH] Todas as tentativas falharam. Retornando vazio para não travar o fluxo.", flush=True)
        return "" 

    return "\n".join(resultados_formatados)

if __name__ == "__main__":
    print(pesquisar_web("arroz preço Francisco Beltrão"))
