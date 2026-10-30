import base64
import ctypes
import html
import logging
import os
import re
import socket
import sys
import threading
import time
from typing import Any

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

logger: logging.Logger = logging.getLogger(__name__)

# Configura encoding de saída para evitar crash com emojis no console do Windows (cp1252)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def prevenir_sono_sistema():
    """Informa ao Windows que este processo exige o sistema ativo (impede suspensão por inatividade)."""
    if sys.platform == "win32":
        try:
            ES_CONTINUOUS = 0x80000000
            ES_SYSTEM_REQUIRED = 0x00000001
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
            logger.info("[POWER MANAGEMENT] Trava de inatividade ativada: Windows impedido de suspender o bot.")
        except Exception as e:
            logger.warning("[POWER MANAGEMENT] Aviso ao configurar trava de inatividade: %s", e)

ULTIMO_PING_ONLINE = time.time()

def iniciar_heartbeat_monitor():
    """Thread de Heartbeat que roda a cada 60s mantendo o socket e a conexão 24/7 sem dormir."""
    def heartbeat_worker():
        global ULTIMO_PING_ONLINE
        while True:
            time.sleep(60)
            agora = time.time()
            # Se passaram mais de 2 minutos sem resposta de update, força ping getMe para manter TCP vivo
            if agora - ULTIMO_PING_ONLINE > 120:
                try:
                    res = requests.get(f"{API_URL}/getMe", timeout=10)
                    if res.status_code == 200:
                        ULTIMO_PING_ONLINE = agora
                except Exception:
                    pass
    t = threading.Thread(target=heartbeat_worker, daemon=True)
    t.start()

def garantir_instancia_unica(port: int = 47891):
    """
    Garante que apenas UMA única instância do bot do Telegram rode na máquina por vez.
    Se outra instância tentar iniciar, ela é encerrada imediatamente para evitar respostas duplicadas.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", port))
        return sock
    except OSError:
        logger.warning("[BOT LOCK] Outra instância do bot já está rodando (Porta %s). Encerrando duplicata.", port)
        sys.exit(0)

# Adiciona o diretório raiz ao PYTHONPATH para permitir importações dos módulos
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

ENV_FILE = os.path.join(BASE_DIR, ".env")
if os.path.exists(ENV_FILE):
    load_dotenv(dotenv_path=ENV_FILE)
else:
    load_dotenv()

try:
    from datetime import UTC
except ImportError:
    from datetime import timezone
    UTC = timezone.utc

import main
from modules.cover_letter import gerar_arquivo_carta_apresentacao
from modules.database import (
    inicializar_supabase,
    salvar_curriculo_gerado,
    salvar_dossie_entrevista,
    salvar_vaga_base,
    salvar_vaga_processada,
)
from modules.dossier import gerar_dossie_vaga
from modules.notifier import enviar_notificacao_vaga, realizar_candidatura_auto_email
from modules.pdf_generator import gerar_pdf_curriculo, sanitizar_texto_para_pdf
from modules.tailor import adaptar_curriculo, obter_cliente_e_modelos, obter_provedores_ia

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def enviar_mensagem_telegram(chat_id: str, texto: str) -> None:
    """Envia mensagem formatada em HTML para o chat do Telegram com fallback para texto puro."""
    if not isinstance(chat_id, str) or not isinstance(texto, str):
        logger.warning("[FAIL FAST] chat_id e texto devem ser strings válidas.")
        return
        
    if not TELEGRAM_TOKEN or not chat_id:
        return
        
    url: str = f"{API_URL}/sendMessage"
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": texto,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code != 200:
            resp_data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            desc = resp_data.get("description", resp.text)
            if "parse" in desc.lower() or "entity" in desc.lower() or "tag" in desc.lower():
                payload.pop("parse_mode", None)
                requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.warning("[ERRO TELEGRAM] Falha ao enviar mensagem: %s", e)

def consultar_uso_serpapi() -> dict[str, Any]:
    """Consulta os dados reais de uso da API SerpAPI diretamente na API oficial (consolida todas as chaves configuradas)."""
    raw_keys = os.getenv("SERPAPI_KEYS") or os.getenv("SERPAPI_KEY") or ""
    chaves = [k.strip() for k in re.split(r"[,;\s]+", raw_keys) if k.strip()]
    if not chaves:
        return {}

    total_usadas = 0
    total_restantes = 0
    total_limite = 0
    renovacao = "N/A"
    chaves_validas = 0

    for key in chaves:
        try:
            url = f"https://serpapi.com/account?api_key={key}"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                total_usadas += data.get("this_month_usage", 0)
                total_restantes += data.get("total_searches_left", 0)
                total_limite += data.get("searches_per_month", 100)
                if renovacao == "N/A":
                    renovacao = data.get("plan_renewal_date", "N/A")
                chaves_validas += 1
        except Exception as e:
            logger.error("[ERRO SERPAPI ACCOUNT] %s", e)

        if chaves_validas > 0:
            return {
                "usadas": total_usadas,
                "restantes": total_restantes,
                "limite": total_limite,
                "renovacao": renovacao,
                "chaves_ativas": chaves_validas
            }
        return {}

def extrair_texto_url(url: str) -> str:
    """
    Extrator inteligente e robusto de conteúdo de vagas via URL:
    - Suporta LinkedIn (incluindo links curtos lnkd.in, mobile e guest API oficial)
    - Suporta Gupy (decodificação de links base64 e extração de dados do __NEXT_DATA__)
    - Suporta Schema.org JSON-LD (JobPosting) presente em Indeed, Glassdoor, Catho, etc.
    - Suporta plataformas de ATS (Greenhouse, Lever, Workable, Programathor)
    - Fallback com limpeza de navegação, rodapé, banners de cookies e scripts.
    """
    if not url or not isinstance(url, str):
        return ""

    url_alvo = url.strip().rstrip(".,;)>]")
    if not url_alvo.startswith("http"):
        url_alvo = "https://" + url_alvo

    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Upgrade-Insecure-Requests": "1"
    }
    session.headers.update(headers)

    # 1. TRATAMENTO DEDICADO PARA LINKEDIN (INCLUINDO LNKD.IN)
    if "linkedin.com" in url_alvo.lower() or "lnkd.in" in url_alvo.lower():
        try:
            resp_init = session.get(url_alvo, allow_redirects=True, timeout=12)
            url_final = resp_init.url

            job_id_match = (
                re.search(r'/jobs/view/(?:[a-zA-Z0-9\-]+-)?(\d{8,12})', url_final)
                or re.search(r'currentJobId=(\d{8,12})', url_final)
                or re.search(r'(\d{8,12})', url_final)
                or re.search(r'(\d{8,12})', url_alvo)
            )

            if job_id_match:
                job_id = job_id_match.group(1)
                guest_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
                r_guest = session.get(guest_url, timeout=12)
                if r_guest.status_code == 200 and len(r_guest.text) > 300:
                    soup_li = BeautifulSoup(r_guest.text, 'html.parser')
                    title_elem = soup_li.find('h2', class_='top-card-layout__title') or soup_li.find('h1')
                    comp_elem = soup_li.find('a', class_='topcard__org-name-link') or soup_li.find('span', class_='topcard__flavor')
                    loc_elem = soup_li.find('span', class_='topcard__flavor--bullet')
                    desc_elem = soup_li.find('div', class_='show-more-less-html__markup') or soup_li.find('section', class_='show-more-less-html')

                    titulo = title_elem.get_text(strip=True) if title_elem else "Vaga no LinkedIn"
                    empresa = comp_elem.get_text(strip=True) if comp_elem else "Empresa no LinkedIn"
                    loc = loc_elem.get_text(strip=True) if loc_elem else ""
                    desc = desc_elem.get_text(separator="\n", strip=True) if desc_elem else ""

                    criterios = [crit.get_text(separator=" ", strip=True) for crit in soup_li.find_all('li', class_='description__job-criteria-item')]
                    crit_text = "\n".join(criterios)

                    blocos = [f"Vaga: {titulo}", f"Empresa: {empresa}"]
                    if loc:
                        blocos.append(f"Localização: {loc}")
                    if crit_text:
                        blocos.append(f"\nCritérios da Vaga:\n{crit_text}")
                    if desc:
                        blocos.append(f"\nDescrição da Vaga:\n{desc}")

                    texto_completo = "\n".join(blocos)
                    return sanitizar_texto_para_pdf(texto_completo)
        except Exception as e:
            logger.warning("[EXTRATOR LINKEDIN] Falha ao raspar API pública do LinkedIn: %s", e)

    # 2. TRATAMENTO DEDICADO PARA GUPY
    if "gupy.io" in url_alvo.lower():
        try:
            resp_gupy = session.get(url_alvo, allow_redirects=True, timeout=12)
            if resp_gupy.status_code == 200:
                soup_g = BeautifulSoup(resp_gupy.text, 'html.parser')
                next_data = soup_g.find('script', id='__NEXT_DATA__')
                if next_data and next_data.string:
                    import json as _json
                    data = _json.loads(next_data.string)
                    job = data.get('props', {}).get('pageProps', {}).get('job', {})
                    if job:
                        nome = job.get('name', '')
                        empresa = job.get('careerPageName', '')
                        if not empresa:
                            sub_match = re.search(r'https?://([^.]+)\.gupy\.io', url_alvo)
                            if sub_match:
                                empresa = sub_match.group(1).capitalize()

                        modalidade = job.get('workplaceType', '')
                        cidade = job.get('city', '')
                        estado = job.get('state', '')
                        loc = f"{cidade}/{estado}".strip('/') if cidade or estado else ""

                        def _limpar_html_bloco(html_content: str) -> str:
                            if not html_content:
                                return ""
                            s_bloco = BeautifulSoup(html_content, 'html.parser')
                            return s_bloco.get_text(separator="\n", strip=True)

                        desc = _limpar_html_bloco(job.get('description', ''))
                        resp_atrib = _limpar_html_bloco(job.get('responsibilities', ''))
                        requisitos = _limpar_html_bloco(job.get('prerequisites', ''))
                        adicionais = _limpar_html_bloco(job.get('additionalInformation', ''))

                        blocos = [f"Vaga: {nome}", f"Empresa: {empresa}"]
                        if modalidade or loc:
                            blocos.append(f"Modalidade/Local: {modalidade} {loc}".strip())
                        if desc:
                            blocos.append(f"\nDescrição da Vaga:\n{desc}")
                        if resp_atrib:
                            blocos.append(f"\nResponsabilidades e Atribuições:\n{resp_atrib}")
                        if requisitos:
                            blocos.append(f"\nRequisitos e Qualificações:\n{requisitos}")
                        if adicionais:
                            blocos.append(f"\nInformações Adicionais:\n{adicionais}")

                        return sanitizar_texto_para_pdf("\n".join(blocos))
        except Exception as e:
            logger.warning("[EXTRATOR GUPY] Falha ao extrair dados Next.js da Gupy: %s", e)

    # 3. TRATAMENTO GENÉRICO (JSON-LD SCHEMA.ORG JOBPOSTING E SELETORES ATS)
    try:
        resp = session.get(url_alvo, allow_redirects=True, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, "html.parser")

            # Tenta extrair Schema.org JobPosting em JSON-LD
            for script_ld in soup.find_all('script', type='application/ld+json'):
                try:
                    if not script_ld.string:
                        continue
                    import json as _json
                    ld_data = _json.loads(script_ld.string)
                    itens_ld = ld_data if isinstance(ld_data, list) else [ld_data]
                    for item in itens_ld:
                        if isinstance(item, dict) and item.get('@type') in ['JobPosting', 'jobPosting']:
                            t_vaga = item.get('title', '')
                            h_org = item.get('hiringOrganization', {})
                            e_vaga = h_org.get('name', '') if isinstance(h_org, dict) else str(h_org)
                            d_vaga_html = item.get('description', '')
                            d_clean = BeautifulSoup(d_vaga_html, 'html.parser').get_text(separator="\n", strip=True)

                            blocos = []
                            if t_vaga:
                                blocos.append(f"Vaga: {t_vaga}")
                            if e_vaga:
                                blocos.append(f"Empresa: {e_vaga}")
                            if d_clean:
                                blocos.append(f"\nDescrição da Vaga:\n{d_clean}")

                            res_ld = "\n".join(blocos)
                            if len(res_ld) > 120:
                                return sanitizar_texto_para_pdf(res_ld)
                except Exception:
                    pass

            # Remove tags irrelevantes de layout
            for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "iframe", "aside"]):
                tag.decompose()

            # Procura container principal da vaga
            seletor_principal = (
                soup.find('main')
                or soup.find('article')
                or soup.find(class_=re.compile(r'(job[-_]?description|vaga[-_]?detalhe|posting[-_]?content|job[-_]?detail)', re.I))
                or soup.find(id=re.compile(r'(job[-_]?description|vaga|content)', re.I))
                or soup.body
            )

            if seletor_principal:
                texto_extraido = seletor_principal.get_text(separator="\n", strip=True)
                if len(texto_extraido) > 80:
                    return sanitizar_texto_para_pdf(texto_extraido)
    except Exception as e:
        logger.warning("[EXTRATOR URL GENERICO] %s: %s", url_alvo, e)

    return ""

def extrair_texto_imagem_groq(image_path: str) -> str:
    """Usa a Groq (modelo vision) para extrair texto de uma imagem enviada pelo Telegram."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.warning("[GROQ] GROQ_API_KEY não definida. Impossível extrair texto da imagem.")
        return ""
    
    try:
        client, modelos_chat = obter_cliente_e_modelos()
        if not client or not modelos_chat:
            from groq import Groq
            client = Groq(api_key=api_key)
            modelos_chat = ["qwen/qwen3.8-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b"]
        
        import io
        from PIL import Image
        
        # Otimizar a imagem para evitar limites de resolução da API Groq
        with Image.open(image_path) as img:
            if img.mode == 'RGBA':
                img = img.convert('RGB')
                
            max_size = (1024, 1024)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            base64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
        prompt = "Transcreva todo o texto presente nesta imagem. Se for uma vaga de emprego, mantenha o foco nos requisitos, cargo e descrição. Retorne APENAS o texto extraído, sem comentários adicionais."
        
        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.1,
            max_tokens=600
        )
        return sanitizar_texto_para_pdf(response.choices[0].message.content.strip())
    except Exception as e:
        logger.error(f"[ERRO OCR GROQ] Falha ao processar imagem: {e}")
        try:
            with open("debug_groq_error.log", "a") as f:
                f.write(f"ERRO GROQ: {e}\n")
                if hasattr(e, 'response'):
                    f.write(f"API DETAILS: {e.response.json()}\n")
        except Exception: pass
        return ""

def responder_como_ia(chat_id: str, texto_usuario: str):
    """Chat inteligente usando a Groq com pool de modelos e fallback automático para responder o usuário no Telegram."""
    provedores = obter_provedores_ia()
    if not provedores:
        enviar_mensagem_telegram(chat_id, "⚠️ Nenhuma chave de IA (GEMINI_API_KEY ou GROQ_API_KEY) configurada para chat.")
        return

    enviar_mensagem_telegram(chat_id, "🤔 <i>Pensando...</i>")
    try:
        from datetime import datetime, timedelta, timezone
        from modules.database import inicializar_supabase
        supabase = inicializar_supabase()
        
        # 1. Puxa o status real do dia
        contexto_hoje = gerar_relatorio_diario_telegram(automatico=True)
        
        # 2. Puxa perfil do usuário para a IA saber as preferências
        perfil = "Desconhecido"
        try:
            import json
            with open("master_profile.json", "r", encoding="utf-8") as f:
                mp = json.load(f)
                niveis = mp.get("preferencias_vaga", {}).get("niveis_experiencia", ["Junior"])
                niveis_str = "/".join(niveis) if niveis else "Junior"
                perfil = f"Objetivo: {mp.get('objetivo_profissional', 'Desenvolvedor')}, Senioridade alvo: {niveis_str}, Local: {mp.get('preferencias_vaga', {}).get('modelo_trabalho', 'Remoto')}."
        except Exception:
            perfil = "Objetivo: Desenvolvedor, Senioridade alvo: Junior, Local: Remoto."

        # 3. Puxa o detalhamento ampliado do Supabase
        detalhes_vagas = ""
        if supabase:
            try:
                # Vagas de hoje
                fuso_brt = timezone(timedelta(hours=-3))
                inicio_dia = datetime.now(fuso_brt).replace(hour=0, minute=0, second=0, microsecond=0)
                inicio_str = inicio_dia.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                
                res_hoje = supabase.table("vagas_processadas").select("titulo_vaga, empresa, match_score, status_candidatura").gte("created_at", inicio_str).execute()
                vagas_hoje = res_hoje.data or []
                detalhes_vagas += "--- VAGAS ANALISADAS HOJE ---\n"
                if vagas_hoje:
                    for v in vagas_hoje:
                        detalhes_vagas += f"- {v.get('titulo_vaga')} | {v.get('empresa')} | Match: {v.get('match_score')}% | Status: {v.get('status_candidatura')}\n"
                else:
                    detalhes_vagas += "Nenhuma hoje.\n"

                # Últimas 5 vagas que deram MATCH / CANDIDATURA (All time)
                res_match = supabase.table("vagas_processadas").select("titulo_vaga, empresa, created_at").eq("status_candidatura", "qualificada").order("created_at", desc=True).limit(5).execute()
                vagas_match = res_match.data or []
                detalhes_vagas += "\n--- ÚLTIMAS 5 VAGAS APROVADAS (HISTÓRICO) ---\n"
                if vagas_match:
                    for v in vagas_match:
                        detalhes_vagas += f"- {v.get('titulo_vaga')} | {v.get('empresa')} ({v.get('created_at')[:10]})\n"
                else:
                    detalhes_vagas += "Nenhuma vaga aprovada no histórico.\n"

                # Estatísticas Gerais (All time)
                res_all = supabase.table("vagas_processadas").select("status_candidatura").execute()
                all_data = res_all.data or []
                tot = len(all_data)
                tot_aprov = len([x for x in all_data if x.get("status_candidatura") == "qualificada"])
                tot_reprov = tot - tot_aprov
                detalhes_vagas += f"\n--- ESTATÍSTICAS TOTAIS (TODOS OS TEMPOS) ---\nTotal analisadas: {tot}\nAprovadas (Qualificadas): {tot_aprov}\nReprovadas/Descartadas: {tot_reprov}\n"

            except Exception as e:
                detalhes_vagas += f"\n(Erro ao buscar histórico: {e})"
        else:
            detalhes_vagas += "\n(Supabase offline)"

        prompt_sistema = (
            "Você é o Agente de Vagas, o assistente pessoal super inteligente do Felipe. "
            "Você é especialista em engenharia de software, recrutamento e vagas de emprego. "
            "Sua missão é responder de forma direta, prestativa e amigável (como um chatbot no Telegram). "
            "Use emojis para deixar a conversa leve.\n\n"
            "⚠️ REGRA CRÍTICA DE FORMATAÇÃO: O Telegram usa HTML, não Markdown. NUNCA use asteriscos (**) ou underscores (_) para formatação. "
            "Para negrito, use <b>texto</b>. Para itálico, use <i>texto</i>. Para código, use <code>texto</code>.\n\n"
            f"**Perfil do Felipe**: {perfil}\n\n"
            "**Termos Reais de Busca do Robô (Scraper)**:\n"
            "Atualmente, o scraper roda todos os dias com queries fixas rotativas no Google Jobs e LinkedIn Público. "
            "As queries exatas são: 'Desenvolvedor Backend Junior', 'Desenvolvedor Fullstack Junior', "
            "'Desenvolvedor COBOL Mainframe Junior', 'Analista COBOL Mainframe Junior', 'Analista de Sistemas Junior', 'Analista de Automação n8n Junior' e 'Desenvolvedor Low code No code Junior'. "
            "(Ele não puxa palavras-chave soltas do master profile para buscar, mas usa o master profile na hora de dar o MATCH nas vagas encontradas).\n\n"
            f"**Resumo de Hoje**:\n{contexto_hoje}\n\n"
            f"**Contexto Completo do Banco de Dados**:\n{detalhes_vagas}\n\n"
            "Instruções: Se o usuário perguntar sobre vagas, use o contexto acima para responder. Se ele perguntar algo que não está aí, seja honesto. Se ele fizer perguntas técnicas, responda normalmente."
        )
        
        resposta = None
        ultimo_erro = None

        for client_atual, modelo_atual, nome_provedor in provedores:
            try:
                response = client_atual.chat.completions.create(
                    model=modelo_atual,
                    messages=[
                        {"role": "system", "content": prompt_sistema},
                        {"role": "user", "content": texto_usuario}
                    ],
                    temperature=0.7,
                    max_tokens=600
                )
                resposta = response.choices[0].message.content.strip()
                if resposta:
                    resposta = sanitizar_texto_para_pdf(resposta)
                    break
            except Exception as model_err:
                ultimo_erro = model_err
                logger.warning("[IA CHAT] Falha no modelo %s (%s): %s. Tentando fallback...", modelo_atual, nome_provedor, model_err)
                continue

        if resposta:
            enviar_mensagem_telegram(chat_id, resposta)
        else:
            raise ultimo_erro or Exception("Nenhum modelo de IA respondeu.")
    except Exception as e:
        logger.error(f"[ERRO IA CHAT] {e}")
        enviar_mensagem_telegram(chat_id, "❌ Ops! Minha IA falhou ao gerar a resposta. Tente novamente.")

def eh_conteudo_vaga(texto: str, url: str = "") -> bool:
    """Verifica se um texto ou URL corresponde a uma vaga de emprego."""
    if url:
        dominios_vagas = [
            "linkedin.com", "lnkd.in", "gupy.io", "greenhouse.io", "lever.co",
            "vagas.com", "indeed.com", "catho.com", "infojobs.com", "glassdoor.com",
            "trampos.co", "programathor.com", "workana.com", "remotar.com",
            "remotamente.com.br", "kenoby.com"
        ]
        if any(dom in url.lower() for dom in dominios_vagas):
            return True

    keywords_vaga = [
        "vaga", "requisitos", "experiência", "experiencia", "habilidades", "salário",
        "salario", "benefícios", "beneficios", "contratação", "contratacao",
        "requirements", "experience", "sênior", "senior", "pleno", "junior", "júnior",
        "clt", "pj", "responsabilidades", "qualificações", "qualificacoes", "atividades",
        "candidatar", "job", "developer", "desenvolvedor", "desenvolvedora", "engenheiro",
        "engenheira", "analista", "full stack", "fullstack", "backend", "frontend",
        "estamos buscando", "oportunidade"
    ]
    texto_lower = texto.lower()
    matches = sum(1 for kw in keywords_vaga if kw in texto_lower)
    return matches >= 2

def tratar_entrada_usuario(chat_id: str, texto: str, forcar_vaga: bool = False):
    """
    Roteador inteligente:
    - Se encontrar URL (especialmente de LinkedIn/recrutamento), acessa a página e extrai a vaga.
    - Se for detectada uma vaga (por URL ou texto com termos de emprego), processa a vaga (CV, Dossiê, Carta, Auto-Apply).
    - Caso contrário, atua como IA conversacional prestativa.
    """
    urls = re.findall(r'(https?://[^\s]+)', texto)
    if urls:
        url_alvo = urls[0].rstrip(".,;)>]")
        enviar_mensagem_telegram(chat_id, "🔗 <b>[LINK DETECTADO]</b> Acessando o link para ler o conteúdo...")
        conteudo_raspado = extrair_texto_url(url_alvo)

        if not conteudo_raspado:
            enviar_mensagem_telegram(
                chat_id,
                "⚠️ Não foi possível extrair o texto diretamente deste link (alguns sites exigem login ou bloqueiam bots).\n\n"
                "💡 <b>Como resolver:</b>\n"
                "1. Copie e cole o texto da vaga diretamente aqui na conversa; OU\n"
                "2. Envie um print (screenshot) da vaga que minha IA lê o texto e gera seu currículo na hora!"
            )
            if forcar_vaga:
                return
            responder_como_ia(chat_id, texto)
            return

        # Verifica se o link/conteúdo raspado é uma vaga
        if forcar_vaga or eh_conteudo_vaga(conteudo_raspado, url=url_alvo):
            texto_extra = texto.replace(url_alvo, "").strip()
            texto_final = f"{texto_extra}\n\n[CONTEÚDO DO LINK]:\n{conteudo_raspado}".strip() if texto_extra else conteudo_raspado
            processar_vaga_direta(chat_id, texto_final, url_origem=url_alvo)
        else:
            # Não é vaga: responde usando o conteúdo da página como contexto
            responder_como_ia(chat_id, f"{texto}\n\n[CONTEÚDO DA PÁGINA]:\n{conteudo_raspado[:2500]}")
        return

    # Mensagem de texto sem link
    if forcar_vaga or (len(texto) >= 80 and eh_conteudo_vaga(texto)):
        processar_vaga_direta(chat_id, texto, url_origem="")
    else:
        responder_como_ia(chat_id, texto)

def resolver_texto_com_url(chat_id: str, texto: str) -> str:
    """Verifica se há um URL no texto e tenta raspar (mantido para compatibilidade)."""
    urls = re.findall(r'(https?://\S+)', texto)
    if urls:
        url = urls[0].rstrip(".,;)>]")
        conteudo = extrair_texto_url(url)
        if conteudo:
            texto_sem_url = texto.replace(url, "").strip()
            return f"{texto_sem_url}\n\n[CONTEÚDO DO SITE]:\n{conteudo}".strip()
    return texto

def comando_status() -> str:
    """Gera o relatório de status consultando o Supabase e a API do SerpAPI ao vivo."""
    supabase = inicializar_supabase()
    if not supabase:
        return "⚠️ <b>Erro:</b> Supabase não configurado ou indisponível."

    try:
        # Busca total de vagas processadas
        res_proc = supabase.table("vagas_processadas").select("id, status_candidatura", count="exact").execute()
        total_proc = res_proc.count if res_proc.count is not None else len(res_proc.data or [])

        # Busca total de vagas qualificadas
        res_vagas = supabase.table("vagas").select("id", count="exact").execute()
        total_qual = res_vagas.count if res_vagas.count is not None else len(res_vagas.data or [])

        # Conta auto-applies efetuados
        auto_applies = sum(1 for item in (res_proc.data or []) if item.get("status_candidatura") == "candidatado_auto")

        # Consulta métricas da cota da SerpAPI em tempo real pela API oficial
        info_serp = consultar_uso_serpapi()
        usadas = info_serp.get("usadas", "N/A")
        restantes = info_serp.get("restantes", "N/A")
        limite = info_serp.get("limite", 250)
        renovacao = info_serp.get("renovacao", "N/A")

        mensagem = f"""📊 <b>[STATUS DO AGENTE DE VAGAS]</b>

🔍 <b>Vagas Analisadas:</b> {total_proc}
🎯 <b>Vagas Qualificadas (Match >= 80%):</b> {total_qual}
🤖 <b>Auto-Applies Efetuados:</b> {auto_applies}

💳 <b>[COTA SERPAPI AO VIVO]</b>
• <b>Pesquisas Usadas Este Mês:</b> {usadas} / {limite}
• <b>Pesquisas Restantes:</b> {restantes}
• <b>Data de Renovação:</b> {renovacao}

🟢 <i>O robô está rodando ativamente 8 vezes ao dia (08h às 22h).</i>"""
        return mensagem
    except Exception as e:
        return f"⚠️ <b>Erro ao obter status:</b> {e}"

BUSCA_EM_ANDAMENTO = False

def comando_buscar(chat_id: str):
    """Executa a busca de vagas em tempo real e notifica o Telegram em segundo plano."""
    global BUSCA_EM_ANDAMENTO

    if BUSCA_EM_ANDAMENTO:
        enviar_mensagem_telegram(chat_id, "⏳ <b>[BUSCA EM ANDAMENTO]</b> O robô já está varrendo a web neste momento. Aguarde a conclusão da rodada atual para disparar uma nova!")
        return

    BUSCA_EM_ANDAMENTO = True
    enviar_mensagem_telegram(chat_id, "⚡ <b>[BUSCA INICIADA]</b> Varrendo a web por novas vagas agora... Aguarde alguns instantes!")

    def worker_busca():
        global BUSCA_EM_ANDAMENTO
        try:
            main.main(manual=True, target_chat_id=chat_id)
        except Exception as e:
            import traceback
            traceback.print_exc()
            enviar_mensagem_telegram(chat_id, f"❌ <b>[ERRO NA BUSCA]</b> Falha ao executar varredura: {e}")
        finally:
            BUSCA_EM_ANDAMENTO = False

    threading.Thread(target=worker_busca, daemon=True).start()

def gerar_relatorio_diario_telegram(automatico: bool = False) -> str:
    """Gera o resumo diário de desempenho (Daily Digest) consultando o Supabase e com fallback local."""
    from datetime import datetime, timedelta, timezone
    
    # Define Horário de Brasília (UTC-3)
    fuso_brt = timezone(timedelta(hours=-3))
    agora_brt = datetime.now(fuso_brt)
    data_brt_str = agora_brt.strftime("%d/%m/%Y às %H:%M")

    # Calcula o início do dia no Horário de Brasília convertido para UTC (para consulta no Supabase)
    inicio_dia_brt = agora_brt.replace(hour=0, minute=0, second=0, microsecond=0)
    inicio_utc_str = inicio_dia_brt.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")

    total_proc_hoje = 0
    qualificadas_hoje = 0
    auto_applies_hoje = 0
    fonte_dados = "Supabase 🟢"

    supabase = inicializar_supabase()
    if supabase:
        try:
            res_proc = supabase.table("vagas_processadas").select("id, status_candidatura, created_at").gte("created_at", inicio_utc_str).execute()
            proc_hoje = res_proc.data or []
            total_proc_hoje = len(proc_hoje)
            auto_applies_hoje = sum(1 for item in proc_hoje if item.get("status_candidatura") == "candidatado_auto")

            res_vagas = supabase.table("vagas").select("id, created_at").gte("created_at", inicio_utc_str).execute()
            qualificadas_hoje = len(res_vagas.data or [])
        except Exception as e:
            logger.warning("[AVISO RELATORIO] Erro ao consultar Supabase, usando fallback local: %s", e)
            supabase = None

    if not supabase:
        fonte_dados = "Base Local 🟠"
        local_file = "vagas_processadas.json"
        if os.path.exists(local_file):
            try:
                import json
                with open(local_file, "r", encoding="utf-8") as f:
                    local_data = json.load(f)
                    total_proc_hoje = len(local_data)
                    qualificadas_hoje = sum(1 for item in local_data if item.get("match_score", 0) >= 80)
            except Exception:
                pass

    # Consulta SerpAPI
    info_serp = consultar_uso_serpapi()
    usadas = info_serp.get("usadas", "N/A")
    restantes = info_serp.get("restantes", "N/A")
    limite = info_serp.get("limite", 250)

    if automatico:
        cabecalho = "🤖 <b>[RELATÓRIO DIÁRIO AUTOMÁTICO - DIGEST DIÁRIO]</b>"
        rodape = "⏰ <i>Relatório automático disparado pela rotina das 20:00.</i>"
    else:
        cabecalho = "⚡ <b>[RELATÓRIO SOB DEMANDA - /relatorio]</b>"
        rodape = "💡 <i>Relatório gerado instantaneamente a seu pedido via Telegram.</i>"

    mensagem = f"""{cabecalho}
📅 <b>Emitido em:</b> {data_brt_str} (<i>{fonte_dados}</i>)

🔍 <b>Vagas Analisadas Hoje:</b> {total_proc_hoje}
🎯 <b>Vagas Qualificadas Hoje (Match >= 80%):</b> {qualificadas_hoje}
🤖 <b>Candidaturas Automáticas (Auto-Applies):</b> {auto_applies_hoje}

💳 <b>[COTA SERPAPI AO VIVO]</b>
• <b>Pesquisas Usadas Este Mês:</b> {usadas} / {limite}
• <b>Pesquisas Restantes:</b> {restantes}

{rodape}"""
    return mensagem

def processar_vaga_direta(chat_id: str, texto_vaga: str, url_origem: str = ""):
    """
    Processa a descrição de uma vaga enviada diretamente pelo usuário no Telegram.
    Gera e envia o Currículo Otimizado (PDF), Dossiê de Entrevista (MD) e Carta de Apresentação (TXT).
    Se houver e-mail de recrutador no texto, executa candidatura automática por e-mail.
    """
    enviar_mensagem_telegram(
        chat_id,
        "⏳ <b>[PROCESSANDO VAGA]</b> Recebi a descrição da vaga!\n"
        "Analisando perfil, calculando match e gerando Currículo, Dossiê e Carta de Apresentação... Aguarde alguns instantes!"
    )
    try:
        perfil_base = main.carregar_perfil_base()

        # Tenta extrair título e empresa do texto se houver padrões comuns
        titulo = "Vaga Solicitada via Telegram"
        empresa = "Empresa via Telegram"

        lines = [l.strip() for l in texto_vaga.split("\n") if l.strip()]
        for line in lines[:15]:
            l_lower = line.lower()
            if l_lower.startswith(("vaga:", "cargo:", "título:", "titulo:")):
                titulo = line.split(":", 1)[1].strip()
            elif l_lower.startswith("empresa:"):
                empresa = line.split(":", 1)[1].strip()

        if titulo == "Vaga Solicitada via Telegram" and lines:
            for line in lines[:8]:
                clean_line = line.strip()
                if (clean_line.startswith("[") and clean_line.endswith("]:")) or clean_line.startswith("🔗"):
                    continue
                if 5 <= len(clean_line) <= 75 and not clean_line.lower().startswith(("descriç", "agree", "sign in", "skip to", "como se candid")):
                    titulo = clean_line
                    break

        analise = adaptar_curriculo(texto_vaga, perfil_base)
        match_score = analise.get("match_score", 0)

        empresa_identificada = analise.get("empresa_identificada", "").strip()
        if empresa == "Empresa via Telegram" and empresa_identificada and empresa_identificada.lower() not in ["", "vazia", "não informada", "nao informada"]:
            empresa = empresa_identificada

        tecnologia_principal = analise.get("tecnologia_principal", "").strip()
        if not tecnologia_principal or tecnologia_principal.lower() in ["", "vazia", "não informada", "nao informada"]:
            tecnologia_principal = "Tech"

        vaga_info = {
            "titulo": titulo,
            "empresa": empresa,
            "link": url_origem or "",
            "descricao": texto_vaga
        }

        nome_candidato_clean = (re.sub(r'[^\w\-_]', '_', str(perfil_base.get("nome", "Candidato"))).strip("_")[:30]).upper() or "CANDIDATO"

        if empresa == "Empresa via Telegram":
            sufixo_arquivo = (re.sub(r'[^\w\-_]', '_', str(tecnologia_principal)).strip("_")[:30]).upper()
        else:
            sufixo_arquivo = (re.sub(r'[^\w\-_]', '_', str(empresa)).strip("_")[:30]).upper()

        nome_arquivo_pdf = f"CV_{nome_candidato_clean}_{sufixo_arquivo}.pdf"

        # 1. Gerar PDF do Currículo Otimizado
        pasta_cvs = "curriculos_gerados"
        os.makedirs(pasta_cvs, exist_ok=True)
        caminho_pdf = os.path.join(pasta_cvs, nome_arquivo_pdf)
        gerar_pdf_curriculo(perfil_base, analise, output_filename=caminho_pdf)

        # 2. Gerar Dossiê de Entrevista
        caminho_dossie = gerar_dossie_vaga(vaga_info, analise)

        # 3. Gerar Carta de Apresentação
        caminho_carta = gerar_arquivo_carta_apresentacao(vaga_info, analise, perfil_base)

        # Extrai e-mail de candidatura da descrição da vaga para Auto-Apply
        email_recrutador = main.extrair_email_texto(texto_vaga)
        status_envio = "solicitado_telegram"
        modo_candidatura = "manual"

        if email_recrutador:
            vaga_info["email_candidatura"] = email_recrutador
            enviar_mensagem_telegram(chat_id, f"📧 <b>[AUTO-APPLY ENCONTRADO]</b> E-mail de recrutador identificado: <code>{email_recrutador}</code>.\nEnviando candidatura automática por e-mail com seu Currículo PDF anexo...")
            sucesso_apply = realizar_candidatura_auto_email(vaga_info, analise, caminho_pdf, perfil_base)
            if sucesso_apply:
                status_envio = "candidatado_auto"
                modo_candidatura = "auto"
                enviar_mensagem_telegram(chat_id, f"✅ <b>[AUTO-APPLY CONCLUÍDO]</b> Candidatura e currículo PDF enviados com sucesso para <code>{email_recrutador}</code>!")
            else:
                enviar_mensagem_telegram(chat_id, f"⚠️ <b>[AUTO-APPLY FALHOU]</b> Não foi possível enviar e-mail automático para <code>{email_recrutador}</code>. Verifique as credenciais do Gmail no .env.")

        # 4. Registrar no Supabase se disponível
        supabase_client = inicializar_supabase()
        vaga_id = salvar_vaga_base(supabase_client, vaga_info, match_score, status="SOLICITADA_TELEGRAM")
        if vaga_id:
            salvar_curriculo_gerado(supabase_client, vaga_id, caminho_pdf, analise)
            salvar_dossie_entrevista(supabase_client, vaga_id, analise)
        salvar_vaga_processada(supabase_client, vaga_info, analise, status_candidatura=status_envio)

        # 5. Enviar notificação com texto rico + anexos (PDF, Dossiê, Carta) no Telegram
        enviar_notificacao_vaga(
            vaga_info=vaga_info,
            analise_ia=analise,
            caminho_pdf=caminho_pdf,
            caminho_dossie=caminho_dossie,
            caminho_carta=caminho_carta,
            modo_candidatura=modo_candidatura
        )

        # 6. Limpeza dos arquivos temporários locais
        for temp_file in [caminho_pdf, caminho_dossie, caminho_carta]:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass

    except Exception as e:
        import traceback
        traceback.print_exc()
        enviar_mensagem_telegram(chat_id, f"❌ <b>[ERRO AO PROCESSAR VAGA]</b> Falha ao analisar vaga: {e}")

def comando_historico_vagas(chat_id: str):
    """Envia o histórico de todas as vagas qualificadas armazenadas no banco de dados Supabase com o Currículo PDF anexo."""
    supabase = inicializar_supabase()
    if not supabase:
        enviar_mensagem_telegram(chat_id, "⚠️ Supabase indisponível no momento.")
        return

    def worker_historico():
        try:
            res_vagas = supabase.table("vagas").select("*").order("created_at", desc=True).execute()
            vagas = res_vagas.data or []

            if not vagas:
                enviar_mensagem_telegram(chat_id, "ℹ️ <b>Nenhuma vaga qualificada registrada no histórico ainda.</b>")
                return

            enviar_mensagem_telegram(chat_id, f"📋 <b>[HISTÓRICO DE VAGAS COM CURRÍCULOS PDF]</b>\nTotal de vagas qualificadas (Match >= 80%): <b>{len(vagas)}</b>\n\nGerando e enviando os currículos em PDF em anexo abaixo...")

            perfil_base = main.carregar_perfil_base()
            doc_url = f"{API_URL}/sendDocument"

            for idx, v in enumerate(vagas, start=1):
                vaga_id = v.get("id")
                titulo = v.get("titulo", "Sem título")
                empresa = v.get("empresa", "Empresa não informada")
                score = v.get("match_score", 80)
                link = v.get("link", "")
                data_criacao = str(v.get("created_at", ""))[:10]
                descricao = v.get("descricao") or titulo

                analise_ia = None
                if vaga_id:
                    try:
                        res_cg = supabase.table("curriculos_gerados").select("conteudo_json").eq("vaga_id", vaga_id).execute()
                        if res_cg.data and len(res_cg.data) > 0:
                            analise_ia = res_cg.data[0].get("conteudo_json")
                    except Exception:
                        pass

                if not analise_ia:
                    analise_ia = adaptar_curriculo(descricao, perfil_base)

                clean_empresa = (re.sub(r'[^\w\-_]', '_', str(empresa)).strip("_")[:30]) or "Empresa"
                nome_candidato_clean = (re.sub(r'[^\w\-_]', '_', str(perfil_base.get("nome", "Candidato"))).strip("_")[:30]) or "Candidato"
                
                pasta_cvs = "curriculos_gerados"
                os.makedirs(pasta_cvs, exist_ok=True)
                nome_pdf = f"CV_{nome_candidato_clean}_{clean_empresa}.pdf"
                caminho_pdf = os.path.join(pasta_cvs, nome_pdf)

                gerar_pdf_curriculo(perfil_base, analise_ia, output_filename=caminho_pdf)

                link_html = f'<a href="{link}">🔗 Abrir Anúncio da Vaga</a>' if link and link.startswith("http") else "<i>Link indisponível</i>"
                legenda_html = (
                    f"<b>{idx}. {html.escape(titulo)}</b>\n"
                    f"🏢 <b>Empresa:</b> {html.escape(empresa)}\n"
                    f"🎯 <b>Match:</b> {score}%\n"
                    f"📅 <b>Data:</b> {data_criacao}\n"
                    f"{link_html}"
                )

                if os.path.exists(caminho_pdf):
                    try:
                        with open(caminho_pdf, "rb") as doc_file:
                            files = {"document": (os.path.basename(caminho_pdf), doc_file)}
                            data_form = {"chat_id": chat_id, "caption": legenda_html, "parse_mode": "HTML"}
                            requests.post(doc_url, data=data_form, files=files, timeout=15)
                    except Exception as e:
                        logger.error("[ERRO TELEGRAM HISTORICO] Falha ao enviar PDF: %s", e)
                    
                    try:
                        os.remove(caminho_pdf)
                    except Exception:
                        pass

                time.sleep(1.2)
        except Exception as e:
            enviar_mensagem_telegram(chat_id, f"❌ <b>Erro ao carregar histórico com PDFs:</b> {e}")

    threading.Thread(target=worker_historico, daemon=True).start()

def processar_mensagem(update: dict):
    """Processa mensagens e comandos recebidos do Telegram."""
    message = update.get("message", {})
    chat_id = str(message.get("chat", {}).get("id", ""))
    
    photo_array = message.get("photo")
    caption = message.get("caption", "").strip()
    text = message.get("text", "").strip()
    
    if photo_array:
        enviar_mensagem_telegram(chat_id, "📸 <b>[IMAGEM RECEBIDA]</b> Baixando e extraindo texto via IA (OCR)...")
        file_id = photo_array[-1].get("file_id")
        file_url = f"{API_URL}/getFile?file_id={file_id}"
        try:
            resp_file = requests.get(file_url, timeout=10)
            if resp_file.status_code == 200:
                file_path = resp_file.json().get("result", {}).get("file_path")
                download_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
                img_resp = requests.get(download_url, timeout=15)
                if img_resp.status_code == 200:
                    tmp_img = f"tmp_img_{chat_id}.jpg"
                    with open(tmp_img, "wb") as f:
                        f.write(img_resp.content)
                    
                    texto_extraido = extrair_texto_imagem_groq(tmp_img)
                    
                    if os.path.exists(tmp_img):
                        try:
                            os.remove(tmp_img)
                        except Exception: pass
                        
                    if texto_extraido:
                        enviar_mensagem_telegram(chat_id, "✅ <b>[LEITURA CONCLUÍDA]</b> Texto extraído com sucesso! Processando a vaga...")
                        texto_final = f"{caption}\n\n[TEXTO DA IMAGEM]:\n{texto_extraido}".strip()
                        threading.Thread(target=tratar_entrada_usuario, args=(chat_id, texto_final, True), daemon=True).start()
                        return
                    else:
                        enviar_mensagem_telegram(chat_id, "⚠️ Não consegui extrair texto claro dessa imagem.")
                        return
        except Exception as e:
            logger.error("Erro ao baixar/processar foto: %s", e)
            enviar_mensagem_telegram(chat_id, "⚠️ Erro ao processar imagem.")
            return

    if not text:
        return

    logger.info("[BOT TELEGRAM] Mensagem recebida de %s: '%s...'", chat_id, text[:30])

    # Valida se a mensagem veio do seu chat autorizado (se TELEGRAM_CHAT_ID estiver configurado)
    authorized_chat_id = str(os.getenv("TELEGRAM_CHAT_ID") or TELEGRAM_CHAT_ID or "").strip()
    if authorized_chat_id and chat_id != authorized_chat_id:
        logger.warning("[BOT SECURITY] Mensagem ignorada de chat não autorizado: %s (esperado: %s)", chat_id, authorized_chat_id)
        return

    if text.startswith("/"):
        partes = text.split(maxsplit=1)
        # Extrai a primeira palavra do comando e remove o sufixo @nome_do_bot (ex: /start@vaga_felipebot -> /start)
        cmd = partes[0].lower().split("@")[0]

        if cmd in ["/start", "/ajuda", "/help"]:
            ajuda_texto = """🤖 <b>[MENU DO AGENTE DE VAGAS]</b>

Comandos disponíveis:
📊 /status - Exibe estatísticas de vagas e cota ao vivo.
📅 /relatorio - Exibe o resumo de desempenho do dia de hoje (Daily Digest).
📋 /historico ou /vagas - Lista todas as vagas qualificadas já encontradas.
⚡ /buscar - Dispara uma busca de vagas na web imediatamente.
💼 /vaga &lt;link ou texto&gt; - Analisa uma vaga e gera CV, Dossiê e Carta.
❓ /ajuda - Exibe este menu de ajuda.

💡 <b>Dica:</b> Você pode enviar diretamente o link do LinkedIn (ou de qualquer outro site de vagas) ou colar a descrição completa da vaga nesta conversa para receber o Currículo, Dossiê e Carta instantaneamente!"""
            enviar_mensagem_telegram(chat_id, ajuda_texto)

        elif cmd == "/status":
            status_msg = comando_status()
            enviar_mensagem_telegram(chat_id, status_msg)

        elif cmd == "/relatorio":
            rel_msg = gerar_relatorio_diario_telegram()
            enviar_mensagem_telegram(chat_id, rel_msg)

        elif cmd in ["/historico", "/vagas"]:
            comando_historico_vagas(chat_id)

        elif cmd == "/buscar":
            comando_buscar(chat_id)

        elif cmd in ["/vaga", "/analisar"]:
            if len(partes) > 1 and partes[1].strip():
                conteudo_param = partes[1].strip()
                threading.Thread(target=tratar_entrada_usuario, args=(chat_id, conteudo_param, True), daemon=True).start()
            else:
                enviar_mensagem_telegram(chat_id, "⚠️ Por favor, envie o link ou a descrição da vaga após o comando.\nExemplo:\n<code>/vaga https://linkedin.com/...</code> ou <code>/vaga Desenvolvedor Python...</code>")
        else:
            enviar_mensagem_telegram(chat_id, "⚠️ Comando não reconhecido. Use /ajuda para ver os comandos ou envie a descrição ou link da vaga diretamente.")
    else:
        threading.Thread(target=tratar_entrada_usuario, args=(chat_id, text, False), daemon=True).start()

def escutar_comandos():
    """Inicia o loop de escuta de comandos do Telegram via Long Polling ininterrupto (Anti-Sleep)."""
    global ULTIMO_PING_ONLINE

    # Evita que o Windows coloque o sistema ou a placa de rede em suspensão/dormir
    prevenir_sono_sistema()

    # Ativa trava de instância única para o bot interativo
    _lock_socket = garantir_instancia_unica()

    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("[BOT TELEGRAM] TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID não definidos.")
        return

    iniciar_heartbeat_monitor()

    logger.info("🤖 [BOT TELEGRAM INTERATIVO 24/7] Escutando comandos continuamente... (Pressione Ctrl+C para parar)")
    offset = 0

    session = requests.Session()
    session.headers.update({"Connection": "keep-alive"})

    while True:
        try:
            url = f"{API_URL}/getUpdates?offset={offset}&timeout=15"
            resp = session.get(url, timeout=(10, 25))
            ULTIMO_PING_ONLINE = time.time()

            if resp.status_code == 200:
                data = resp.json()
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    processar_mensagem(update)
            elif resp.status_code == 409:
                logger.warning("[BOT TELEGRAM] Conflito (409) detectado. Reaguardando 5s...")
                time.sleep(5)
            else:
                logger.warning("[BOT TELEGRAM] Código HTTP %s. Aguardando 3s...", resp.status_code)
                time.sleep(3)
        except requests.exceptions.Timeout:
            # Timeout normal do long polling (15s sem mensagens). Continua o loop imediatamente mantendo a conexão aquecida!
            ULTIMO_PING_ONLINE = time.time()
            continue
        except requests.exceptions.RequestException as req_err:
            logger.warning("[ERRO REDE TELEGRAM] Oscilação de conexão: %s. Reconectando sessão HTTP em 3s...", req_err)
            session = requests.Session()
            session.headers.update({"Connection": "keep-alive"})
            time.sleep(3)
        except Exception as e:
            logger.error("[ERRO BOT TELEGRAM] %s", e)
            time.sleep(5)


if __name__ == "__main__":
    escutar_comandos()
