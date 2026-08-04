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
            default_link = job.get("share_link", "")
            link_vaga = escolher_melhor_link_gratuito(apply_options, default_link)

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

def escolher_melhor_link_gratuito(apply_options: list, default_link: str) -> str:
    """
    Dada a lista de opções de candidatura do Google Jobs, escolhe prioritariamente 
    links diretos e gratuitos (Gupy, LinkedIn, Glassdoor, site da empresa, etc.) 
    em vez de redirecionadores agregadores.
    """
    if not apply_options:
        return default_link

    preferenciais = ["gupy.io", "linkedin.com", "glassdoor", "smartrecruiters", "greenhouse.io", "lever.co", "workable", "solides.jobs", "programathor"]
    
    for opt in apply_options:
        link_opt = str(opt.get("link", "")).lower()
        title_opt = str(opt.get("title", "")).lower()
        for pref in preferenciais:
            if pref in link_opt or pref in title_opt:
                return opt.get("link")

    return apply_options[0].get("link", default_link)

def eh_candidatura_gratuita(vaga: dict) -> bool:
    """
    Verifica se a candidatura para esta vaga específica é 100% gratuita.
    Descarte anúncios específicos que exijam assinatura paga, plano VIP ou pagamento para enviar o currículo.
    Bloqueia 100% das vagas do portal Bebee conforme solicitação explícita do usuário.
    """
    link = str(vaga.get("link", "")).lower()
    descricao = str(vaga.get("descricao", "")).lower()
    titulo = str(vaga.get("titulo", "")).lower()
    empresa = str(vaga.get("empresa", "")).lower()
    texto_completo = f"{link} {titulo} {empresa} {descricao}"

    # Bloqueio explícito do Bebee
    if "bebee.com" in link:
        print(f"[FILTRO BEBEE] Vaga descartada por ser do portal Bebee: '{vaga.get('titulo')}'")
        return False

    padroes_paywall = [
        r'assine\b.*?\bpara\s+(se\s+)?candidatar\b',
        r'vaga\s+exclusiva\s+para\s+assinantes\b',
        r'membros?\s+premium\b',
        r'plano\s+vip\b',
        r'seja\s+vip\b',
        r'torne-se\s+vip\b',
        r'\bvaga\s+vip\b',
        r'\bárea\s+vip\b',
        r'assinatura\s+paga\b',
        r'fa[cç]a\s+um\s+plano\s+para\b',
        r'candidatura\s+paga\b',
        r'pague\s+para\s+candidatar\b',
        r'empresa\s+confidencial\b.*?\bvip\b',
        r'trabalhaes\.com\.br',
        r'bebee\.com'
    ]

    for padrao in padroes_paywall:
        if re.search(padrao, texto_completo, re.IGNORECASE):
            print(f"[FILTRO CANDIDATURA PAGA] Vaga descartada por requerer assinatura VIP/Pagamento: '{vaga.get('titulo')}'")
            return False

    return True

CARGOS_EXCLUIDOS_REGEX = [
    # Infra, Cloud, DevOps, SRE, Dados, Suporte, Redes, Segurança
    r'\bcloud\b', r'\bdevops\b', r'\bsre\b',
    r'\bdados\b', r'\bdata\b', r'\bbi\b', r'\bbusiness\s+intelligence\b',
    r'\bsuporte\b', r'\bhelpdesk\b', r'\bservice\s*desk\b', r'\bn1\b', r'\bn2\b', r'\bn3\b',
    r'\binfraestrutura\b', r'\binfra\b', r'\bredes\b', r'\bt[eé]cnico\b', r'\binfosec\b', r'\bsoc\b',

    # Ensino, Docência e Treinamento (Ex: Professor(a) de Automação)
    r'\bprofessor[a]?\b', r'\bdocente\b', r'\binstrutor[a]?\b', r'\btutor[a]?\b', r'\btreinador[a]?\b',

    # Vendas, Comercial, Gestão de Produtos/Projetos, Design
    r'\bcomercial\b', r'\bvendas\b', r'\bvendedor[a]?\b', r'\bsdr\b', r'\bbdr\b',
    r'\bscrum\s*master\b', r'\bagile\s*coach\b', r'\bproduct\s*owner\b', r'\bproduct\s*manager\b',
    r'\bdesigner\b', r'\bux\b', r'\bui\b'
]

SENIORIDADE_ALTA_REGEX = [
    r'\bs[eê]nior\b', r'\bsr\.?\b', r'\bsnr\b',
    r'\blead\b', r'\bl[ií]der\b', r'\bcoordenador\b', r'\bgerente\b', r'\bmanager\b',
    r'\bhead\b', r'\bdiretor\b', r'\barquitet[oa]\b', r'\barchitect\b', r'\bespecialista\b', r'\bspecialist\b'
]

def eh_cargo_e_nivel_permitido(vaga: dict) -> bool:
    """
    Filtra estritamente para garantir que a vaga seja de Desenvolvedor ou Analista de Sistemas/Automação:
    - COBOL, Mainframe, Analista de Sistemas e Java: APENAS nível JÚNIOR / TRAINEE.
    - Automação / n8n: Nível JÚNIOR, TRAINEE ou PLENO.
    Descarte para: Professor/Docente, Vendas/Comercial, Scrum Master/PO/PM, Design/UX, Cloud, DevOps, SRE, Dados, Suporte e nível Sênior/Lead.
    """
    titulo = str(vaga.get("titulo", "")).lower()
    descricao = str(vaga.get("descricao", "")).lower()
    texto_completo = f"{titulo} {descricao}"

    # 1. Descarte imediato de áreas/funções não desejadas no título (Ensino, Vendas, Cloud, DevOps, SRE, Dados, Suporte)
    for area in CARGOS_EXCLUIDOS_REGEX:
        if re.search(area, titulo, re.IGNORECASE):
            print(f"[FILTRO ÁREA EXCLUÍDA] Vaga descartada por ser de área/função não desejada ({area}): '{vaga.get('titulo')}'")
            return False

    # 2. Descarte imediato de senioridade alta (Sênior, Lead, Gerente, Especialista, Architect)
    for sen in SENIORIDADE_ALTA_REGEX:
        if re.search(sen, titulo, re.IGNORECASE):
            print(f"[FILTRO SENIORIDADE ALTA] Vaga descartada por ser de nível Sênior/Lead ({sen}): '{vaga.get('titulo')}'")
            return False

    # 3. Validação de Título: Deve se enquadrar como Desenvolvedor/Programador/Engenheiro de Software ou Analista de Sistemas/Automação
    padroes_titulo_dev_analista = [
        r'\bdesenvolvedor[a]?\b', r'\bdeveloper\b', r'\bprogramador[a]?\b', r'\bprogrammer\b',
        r'\bsoftware\s+engineer\b', r'\bengenheiro[a]?\s+de\s+software\b',
        r'\banalista\s+de\s+sistemas\b', r'\banalista\s+de\s+automa[cç][aã]o\b',
        r'\banalista\s+n8n\b', r'\banalista\s+de\s+desenvolvimento\b', r'\banalista\s+backend\b'
    ]

    tem_titulo_dev_analista = any(re.search(ptd, titulo, re.IGNORECASE) for ptd in padroes_titulo_dev_analista)
    if not tem_titulo_dev_analista:
        print(f"[FILTRO TITULO DEVIANTE] Vaga descartada por fugir do perfil de Desenvolvedor / Analista de Sistemas: '{vaga.get('titulo')}'")
        return False

    # 4. Identifica se a vaga é de Automação / n8n ou de outros cargos válidos (COBOL, Mainframe, Java, Analista de Sistemas)
    eh_automacao = bool(re.search(r'\b(n8n|automa[cç][aã]o)\b', texto_completo, re.IGNORECASE))
    eh_outros_cargos_validos = bool(re.search(r'\b(cobol|mainframe|analista\s+de\s+sistemas|java(?!\s*script))\b', texto_completo, re.IGNORECASE))

    if not eh_automacao and not eh_outros_cargos_validos:
        print(f"[FILTRO CARGO] Vaga descartada por não conter COBOL, Mainframe, Analista de Sistemas, Java ou Automação: '{vaga.get('titulo')}'")
        return False

    # 5. Checagem de Nível Pleno: Permitido APENAS se for vaga de Automação / n8n
    eh_pleno = bool(re.search(r'\b(pleno|pl\.?|mid\s*-?\s*level)\b', titulo, re.IGNORECASE))
    if eh_pleno and not eh_automacao:
        print(f"[FILTRO SENIORIDADE] Vaga de Pleno descartada (permitida apenas para Automação/n8n): '{vaga.get('titulo')}'")
        return False

    return True

PAISES_ESTRANGEIROS_BLOQUEADOS = [
    r'\bunited\s+states\b', r'\busa?\b(?!\s*a\b)', r'\bcanada\b', r'\bgermany\b', r'\balemanha\b',
    r'\bunited\s+kingdom\b', r'\buk\b', r'\bportugal\b', r'\blisboa\b', r'\bporto\b',
    r'\bspain\b', r'\bespanha\b', r'\bmadrid\b', r'\bnetherlands\b', r'\bamsterdam\b',
    r'\bpoland\b', r'\bpolonia\b', r'\bindia\b', r'\baustralia\b'
]

def eh_vaga_no_brasil(vaga: dict) -> bool:
    """
    Garante que a vaga seja localizada no Brasil (mesmo que o título ou descrição estejam em inglês).
    Bloqueia vagas internacionais que exigem moradia/relocação fora do Brasil (EUA, Europa, Canadá, etc.).
    """
    link = str(vaga.get("link", "")).lower()
    titulo = str(vaga.get("titulo", "")).lower()
    empresa = str(vaga.get("empresa", "")).lower()
    descricao = str(vaga.get("descricao", "")).lower()
    texto_completo = f"{link} {titulo} {empresa} {descricao}"

    # 1. Se contiver indicação explícita de Brasil / RJ / LATAM Brazil / Remoto Brasil, aprova!
    marcas_brasil = [
        r'\bbrasil\b', r'\bbrazil\b', r'\brj\b', r'\brio\s*de\s*janeiro\b',
        r'\bremoto\s*brasil\b', r'\bremote\s*\(\s*brazil\s*\)\b', r'\blatam\s*\(\s*brazil\s*\)\b',
        r'\blatam\b', r'\bsouth\s*america\b', r'\bamérica\s*latina\b'
    ]
    for mb in marcas_brasil:
        if re.search(mb, texto_completo, re.IGNORECASE):
            return True

    # 2. Se exigir relocalização externa ou moradia/autorização em outro país, rejeita
    termos_exclusao_exterior = [
        r'relocat(e|ion)\s+to',
        r'must\s+be\s+located\s+in\s+the\s+u\.?s\.?',
        r'us\s+work\s+authorization',
        r'must\s+reside\s+in\s+europe',
        r'eu\s+work\s+permit',
        r'presencial\s+em\s+portugal',
        r'presencial\s+em\s+madrid'
    ]
    for te in termos_exclusao_exterior:
        if re.search(te, texto_completo, re.IGNORECASE):
            print(f"[FILTRO INTERNACIONAL] Vaga descartada por exigir relocalização no exterior: '{vaga.get('titulo')}'")
            return False

    # 3. Se mencionar país estrangeiro sem ter menção a Brasil / LATAM
    for pe in PAISES_ESTRANGEIROS_BLOQUEADOS:
        if re.search(pe, texto_completo, re.IGNORECASE):
            print(f"[FILTRO INTERNACIONAL] Vaga descartada por localização no exterior ({pe}): '{vaga.get('titulo')}'")
            return False

    return True

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

TERMOS_EXCLUSIVOS_GRUPO_REGEX = [
    # Exclusivas / Afirmativas para Mulheres e Programas Femininos
    r'\belas\s+in\s+tech\b',
    r'\belas\s+na\s+tech\b',
    r'\belas\s+em\s+tech\b',
    r'\bprograma\s+elas\b',
    r'\bwomen\s+in\s+tech\b',
    r'\bwomen\s+tech\b',
    r'\bexclusiva\b.*?\bmulheres\b',
    r'\bafirmativa\b.*?\bmulheres\b',
    r'\bexclusivo\b.*?\bmulheres\b',
    r'\bsomente\b.*?\bmulheres\b',
    r'\bapenas\b.*?\bmulheres\b',
    r'\bvaga\s+para\s+mulheres\b',
    r'\bmulheres\s+na\s+tech\b',
    r'\bmulheres\s+in\s+tech\b',
    r'\bvaga\s+feminina\b',
    r'\bpara\s+elas\b',

    # Exclusivas / Afirmativas para PCD
    r'\bpcd\b',
    r'\bexclusiva\b.*?\bpcd\b',
    r'\bafirmativa\b.*?\bpcd\b',
    r'\bexclusivo\b.*?\bpcd\b',
    r'\bsomente\b.*?\bpcd\b',
    r'\bapenas\b.*?\bpcd\b',
    r'\bvaga\s+pcd\b',
    r'\bvagas?\s+pcd\b',
    r'\bvagas?\s+exclusivas?\s+para\s+pcd\b',
    r'\bvagas?\s+afirmativas?\s+para\s+pcd\b',
    r'\bexclusiva\s+para\s+pesso[as]\s+com\s+defici[êe]ncia\b',
    r'\bpesso[as]\s+com\s+defici[êe]ncia\b'
]

def eh_vaga_publico_geral(vaga: dict) -> bool:
    """
    Descarte anúncios de vagas afirmativas ou exclusivas para públicos específicos (ex: exclusivas para mulheres ou exclusivas para PCD).
    """
    titulo = str(vaga.get("titulo", "")).lower()
    descricao = str(vaga.get("descricao", "")).lower()
    texto_completo = f"{titulo} {descricao}"

    # Bloqueio imediato se a marcação PCD ou Mulheres estiver presente no título da vaga
    if re.search(r'\bpcd\b', titulo, re.IGNORECASE):
        print(f"[FILTRO PCD] Vaga descartada por ser direcionada a PCD (marcação no título): '{vaga.get('titulo')}'")
        return False

    for p_excl in TERMOS_EXCLUSIVOS_GRUPO_REGEX:
        if re.search(p_excl, texto_completo, re.IGNORECASE):
            print(f"[FILTRO AFIRMATIVO EXCLUSIVO] Vaga descartada por ser exclusiva/afirmativa para público específico: '{vaga.get('titulo')}'")
            return False

    return True

def coletar_vagas_todas_fontes(cargos_alvo: list) -> list:
    """
    Executa a varredura em 1 ÚNICA pesquisa unificada na SerpAPI por execução do bot,
    garantindo que 1 execução do bot consuma exatamente 1 pesquisa da sua cota.
    Isso permite rodar o bot até 8 vezes ao dia (240 pesquisas/mês) sem estourar o limite de 250!
    """
    todas_vagas = []
    
    # 1 Única requisição otimizada contendo todos os termos alvo
    query_unificada = "(COBOL OR Mainframe OR Java OR n8n OR 'Analista de Sistemas' OR 'Desenvolvedor') Brasil (remoto OR 'rio de janeiro')"
    print(f"[BUSCA UNIFICADA] Disparando 1 pesquisa na SerpAPI: '{query_unificada}'...")
    vagas_google = buscar_vagas_google_jobs(query=query_unificada)
    todas_vagas.extend(vagas_google)

    print("[BUSCA FEEDS] Varrendo RSS Feeds de vagas (Gratuito / Sem consumo de cota)...")
    vagas_rss = buscar_vagas_rss_feed()
    todas_coletadas = todas_vagas + vagas_rss

    vagas_filtradas = []
    
    for vaga in todas_coletadas:
        if eh_cargo_e_nivel_permitido(vaga):
            if eh_vaga_publico_geral(vaga):
                if eh_candidatura_gratuita(vaga):
                    if eh_vaga_no_brasil(vaga):
                        if eh_vaga_remota_ou_rj(vaga):
                            vagas_filtradas.append(vaga)
                        else:
                            print(f"[FILTRO LOCALIDADE] Vaga descartada (Presencial/Híbrida fora do RJ): '{vaga.get('titulo')}'")
                    else:
                        print(f"[FILTRO PAÍS] Vaga descartada por ser localizada fora do Brasil: '{vaga.get('titulo')}'")

    print(f"[SUCESSO] Total de vagas filtradas (Brasil, Gratuitas, Remoto/RJ): {len(vagas_filtradas)}")
    return vagas_filtradas

def vaga_ainda_ativa(url: str, timeout: int = 8) -> bool:
    """
    Verifica em tempo real se a vaga no link informado continua ativa e aceitando candidaturas gratuitas.
    Retorna False se o link retornar HTTP >= 400, redirecionar para página inicial genérica,
    contiver palavras-chave de encerramento ('vaga encerrada') ou exigir plano VIP/pago.
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

        # 1. Validação de encerramento
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

        # 2. Validação de Paywall / VIP na página ao vivo
        expressoes_paywall = [
            "seja vip",
            "torne-se vip",
            "empresa confidencial (torne-se vip",
            "assine para se candidatar",
            "exclusivo para assinantes",
            "membro premium",
            "plano vip",
            "candidatura paga"
        ]

        for pw in expressoes_paywall:
            if pw in texto_pagina:
                print(f"[VALIDAÇÃO PAYWALL] Vaga descartada por exigir plano VIP/Pagamento ('{pw}'): {url}")
                return False

        return True

    except Exception as e:
        print(f"[AVISO] Nao foi possivel checar status HTTP do link ({url}): {e}")
        return True

EMAILS_IGNORADOS = [
    "noreply", "no-reply", "donotreply", "do-not-reply",
    "support@", "suporte@", "privacy@", "privacidade@", "info@google",
    "example", "glassdoor", "gupy.io", "linkedin", "sentry.io", "github.com",
    "w3.org", "schema.org", "domain.com", "email.com"
]

def extrair_email_profundo(url: str, timeout: int = 8) -> str:
    """
    Realiza o Scraping Profundo acessando a página web do anúncio em tempo real
    para localizar e-mails diretos de recrutadores, RH e seleção.
    """
    if not url or not str(url).startswith("http"):
        return None

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    try:
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        if response.status_code >= 400:
            return None

        soup = BeautifulSoup(response.content, "html.parser")
        texto_pagina = soup.get_text()

        # Regex para capturar e-mails no HTML completo da página
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', texto_pagina)

        for email in emails:
            email_lower = email.lower()
            # Ignora e-mails genéricos de sistema/suporte/plataforma
            if not any(ign in email_lower for ign in EMAILS_IGNORADOS):
                print(f"[DEEP SCRAPING] E-mail de recrutador/RH encontrado na página original: {email} (Link: {url})")
                return email

    except Exception as e:
        print(f"[AVISO DEEP SCRAPING] Erro ao buscar e-mail em {url}: {e}")

    return None
