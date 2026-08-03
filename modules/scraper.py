import os
import requests
from bs4 import BeautifulSoup

try:
    from serpapi import GoogleSearch
except ImportError:
    GoogleSearch = None

def buscar_vagas_google_jobs(query: str, localizacao: str = "Brazil") -> list:
    """
    Busca vagas no Google Jobs via SerpAPI (100 buscas grátis por mês).
    """
    api_key = os.getenv("SERPAPI_KEY")
    vagas_encontradas = []

    if not api_key:
        print("[AVISO] SERPAPI_KEY nao definida. Pulando busca no Google Jobs.")
        return vagas_encontradas

    if GoogleSearch is None:
        print("[AVISO] Biblioteca 'google-search-results' nao instalada. Pulando busca no Google Jobs.")
        return vagas_encontradas

    params = {
        "engine": "google_jobs",
        "q": query,
        "location": localizacao,
        "hl": "pt",
        "gl": "br",
        "api_key": api_key
    }

    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        jobs_results = results.get("jobs_results", [])

        for job in jobs_results:
            apply_options = job.get("apply_options", [])
            link_vaga = apply_options[0].get("link") if apply_options else job.get("share_link", "")

            vagas_encontradas.append({
                "titulo": job.get("title"),
                "empresa": job.get("company_name"),
                "link": link_vaga,
                "descricao": job.get("description", ""),
                "fonte": "Google Jobs"
            })
    except Exception as e:
        print(f"[ERRO] Erro ao buscar vagas no Google Jobs: {e}")

    return vagas_encontradas

def buscar_vagas_rss_feed() -> list:
    """
    Busca vagas em feeds RSS abertos de tecnologia.
    """
    vagas = []
    rss_urls = [
        "https://remotar.com.br/feed/"
    ]

    for url in rss_urls:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, features="xml")
                items = soup.find_all("item")
                for item in items[:5]: # Pega as 5 mais recentes
                    vagas.append({
                        "titulo": item.title.text if item.title else "Vaga Tech",
                        "empresa": "Portal Remotar / Web",
                        "link": item.link.text if item.link else "",
                        "descricao": item.description.text if item.description else "",
                        "fonte": "RSS Feed"
                    })
        except Exception as e:
            print(f"[AVISO] Erro ao ler RSS Feed {url}: {e}")

    return vagas

def coletar_vagas_todas_fontes(cargos_alvo: list) -> list:
    """
    Executa a varredura em todas as fontes configuradas.
    """
    todas_vagas = []
    
    for cargo in cargos_alvo[:2]:
        print(f"[BUSCA] Varrendo a web por: '{cargo}'...")
        vagas_google = buscar_vagas_google_jobs(query=cargo)
        todas_vagas.extend(vagas_google)

    print("[BUSCA] Varrendo feeds RSS de vagas...")
    vagas_rss = buscar_vagas_rss_feed()
    todas_vagas.extend(vagas_rss)

    print(f"[SUCESSO] Total de vagas coletadas na varredura: {len(todas_vagas)}")
    return todas_vagas
