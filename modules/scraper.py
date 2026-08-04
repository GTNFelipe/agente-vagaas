import os
import re
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

def eh_vaga_remota_ou_rj(vaga: dict) -> bool:
    """
    Verifica se a vaga possui modalidade Remota ou é Híbrida/Presencial localizada no Rio de Janeiro (RJ).
    Descarta vagas presenciais ou híbridas em outros estados/cidades (SP, MG, PR, etc.).
    """
    texto = f"{vaga.get('titulo', '')} {vaga.get('empresa', '')} {vaga.get('descricao', '')}".lower()

    # 1. Modalidade Remota / Home Office / Remote
    if re.search(r'\b(remoto|remota|remote|home\s*office|teletrabalho|100%\s*remoto|work\s*from\s*home|anywhere)\b', texto):
        return True

    # 2. Localização no Rio de Janeiro (RJ)
    if re.search(r'\b(rio\s*de\s*janeiro|rj|barra\s*da\s*tijuca|centro\s*-\s*rj|botafogo|niter[oó]i|tijuca)\b', texto):
        return True

    # 3. Se mencionar explicitamente presencial/híbrido em outras regiões e NÃO tiver marcação de Remoto/RJ
    outras_regioes = r'\b(s[aã]o\s*paulo|sp|belo\s*horizonte|mg|curitiba|pr|porto\s*alegre|rs|florian[oó]polis|sc|bras[íi]lia|df|campinas)\b'
    if re.search(outras_regioes, texto):
        return False

    # Por padrão, permite vagas que não sejam presenciais em outros estados
    return True

def coletar_vagas_todas_fontes(cargos_alvo: list) -> list:
    """
    Executa a varredura em todas as fontes configuradas para os cargos alvo definidos,
    filtrando EXCLUSIVAMENTE por vagas Remotas ou Híbridas no Rio de Janeiro.
    """
    todas_vagas = []
    
    for cargo in cargos_alvo:
        query_busca = f"{cargo} (remoto OR 'rio de janeiro')"
        print(f"[BUSCA] Varrendo a web por: '{query_busca}'...")
        vagas_google = buscar_vagas_google_jobs(query=query_busca)
        todas_vagas.extend(vagas_google)

    print("[BUSCA] Varrendo feeds RSS de vagas...")
    vagas_rss = buscar_vagas_rss_feed()
    todas_coletadas = todas_vagas + vagas_rss

    vagas_filtradas = []
    padrao_relevancia = r'\bcobol\b|\bmainframe\b|\bjava\b(?!\s*script)|\bn8n\b|\bautoma[cç][aã]o\b|\banalista\b'
    
    for vaga in todas_coletadas:
        texto = f"{vaga.get('titulo', '')} {vaga.get('descricao', '')}".lower()
        if re.search(padrao_relevancia, texto, re.IGNORECASE):
            if eh_vaga_remota_ou_rj(vaga):
                vagas_filtradas.append(vaga)
            else:
                print(f"[FILTRO LOCALIDADE] Vaga descartada (Presencial/Híbrida fora do RJ): '{vaga.get('titulo')}'")

    print(f"[SUCESSO] Total de vagas filtradas (Remoto ou RJ): {len(vagas_filtradas)}")
    return vagas_filtradas

def vaga_ainda_ativa(url: str, timeout: int = 8) -> bool:
    """
    Verifica em tempo real se a vaga no link informado continua ativa e aceitando candidaturas.
    Retorna False se o link retornar HTTP >= 400, redirecionar para página inicial genérica,
    ou contiver palavras-chave de encerramento ('vaga encerrada', 'job closed', etc.).
    """
    if not url or not str(url).startswith("http"):
        return False

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    try:
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)

        if response.status_code >= 400:
            print(f"[VALIDAÇÃO] Link inativo ou indisponível (HTTP {response.status_code}): {url}")
            return False

        final_url = response.url.lower().rstrip("/")
        path_parts = [p for p in final_url.replace("https://", "").replace("http://", "").split("/") if p]
        if len(path_parts) <= 1:
            print(f"[VALIDAÇÃO] Link redirecionou para a página inicial (vaga removida): {url} -> {response.url}")
            return False

        soup = BeautifulSoup(response.content, "html.parser")
        texto_pagina = soup.get_text().lower()

        expressoes_encerramento = [
            "vaga encerrada",
            "vaga finalizada",
            "vaga inativa",
            "vaga expirada",
            "vaga preenchida",
            "vaga desativada",
            "vaga suspensa",
            "não aceita mais candidaturas",
            "nao aceita mais candidaturas",
            "não está mais aceitando",
            "nao esta mais aceitando",
            "esta vaga expirou",
            "vaga não disponível",
            "vaga nao disponivel",
            "job closed",
            "no longer accepting applications",
            "job is no longer available",
            "página não encontrada",
            "pagina nao encontrada",
            "404 not found"
        ]

        for expr in expressoes_encerramento:
            if expr in texto_pagina:
                print(f"[VALIDAÇÃO] Vaga encerrada detectada ('{expr}'): {url}")
                return False

        return True

    except Exception as e:
        print(f"[AVISO] Nao foi possivel checar status HTTP do link ({url}): {e}")
        return True
