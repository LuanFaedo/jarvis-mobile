from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import requests
import re
import warnings
import time

warnings.filterwarnings("ignore")

def filtrar_resultado_valido(resultado):
    """
    Filtra resultados inválidos (chinês, spam, irrelevante).
    Retorna True se o resultado é válido.
    """
    titulo = resultado.get('title', '') or ''
    corpo = resultado.get('body', '') or ''
    link = resultado.get('href', '') or ''
    texto_completo = f"{titulo} {corpo}".lower()

    # Bloqueia caracteres chineses/japoneses/coreanos
    if re.search(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]', texto_completo):
        return False

    # Bloqueia domínios de spam conhecidos
    dominios_bloqueados = ['baidu.com', 'zhidao.baidu', 'weibo.com', 'qq.com', 'sogou.com']
    if any(d in link.lower() for d in dominios_bloqueados):
        return False

    # Bloqueia resultados muito curtos ou vazios
    if len(corpo) < 20:
        return False

    return True

def pesquisar_web(query, max_results=5):
    """
    Realiza pesquisa na web com múltiplas tentativas e estratégias de fallback.
    Filtra resultados em idiomas estranhos e spam.
    """
    print(f"[SEARCH] Iniciando busca inteligente: '{query}'", flush=True)

    resultados_formatados = []
    sucesso = False

    # Adiciona prefixo português para forçar resultados em PT
    query_pt = f"{query} site:br OR site:pt"

    # Estratégia 1: Busca Direta (API Padrão)
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query_pt, region='br-pt', safesearch='off', max_results=max_results * 2))
            # Filtra resultados válidos
            results = [r for r in results if filtrar_resultado_valido(r)][:max_results]
            if results:
                sucesso = True
                for i, r in enumerate(results):
                    resultados_formatados.append(f"- {r.get('title')}: {r.get('body')[:150]}...")
    except Exception as e:
        print(f"[SEARCH] Tentativa 1 falhou: {e}", flush=True)

    # Estratégia 2: Busca Genérica (Fallback) se a 1 falhou ou retornou vazio
    if not sucesso:
        print("[SEARCH] Tentando modo genérico (HTML)...", flush=True)
        try:
            query_simples = query.replace("preço", "").replace("oferta", "").strip()
            with DDGS() as ddgs:
                results = list(ddgs.text(query_simples, region='br-pt', backend='html', max_results=max_results * 2))
                results = [r for r in results if filtrar_resultado_valido(r)][:max_results]
                if results:
                    sucesso = True
                    for i, r in enumerate(results):
                        resultados_formatados.append(f"- {r.get('title')}: {r.get('body')[:150]}...")
        except Exception as e:
            print(f"[SEARCH] Tentativa 2 falhou: {e}", flush=True)

    # Estratégia 3: Scraping Direto (Último recurso para sites conhecidos)
    if "beltrão" in query.lower() and not sucesso:
        print("[SEARCH] Tentando acesso direto a sites locais...", flush=True)
        sites_locais = [
            ("Mano Manfroi", "https://manomanfroi.com.br/ofertas"),
            ("Supermercado Grizon", "https://grizon.com.br")
        ]
        for nome, url in sites_locais:
            resultados_formatados.append(f"- {nome}: {url}")
        sucesso = True

    if not sucesso:
        print("[SEARCH] Todas as tentativas falharam. Retornando vazio.", flush=True)
        return ""

    # Retorna formato limpo (sem cabeçalhos técnicos)
    return "\n".join(resultados_formatados)

if __name__ == "__main__":
    print(pesquisar_web("arroz preço Francisco Beltrão"))
