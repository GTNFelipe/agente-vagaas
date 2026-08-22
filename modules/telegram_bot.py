import os
import sys
import time
import socket
import threading
import re
import ctypes
import html
import requests
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

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
    except socket.error:
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

from modules.database import (
    inicializar_supabase,
    salvar_vaga_base,
    salvar_curriculo_gerado,
    salvar_dossie_entrevista,
    salvar_vaga_processada
)
from modules.tailor import adaptar_curriculo
from modules.pdf_generator import gerar_pdf_curriculo
from modules.dossier import gerar_dossie_vaga
from modules.cover_letter import gerar_arquivo_carta_apresentacao
from modules.notifier import enviar_notificacao_vaga, realizar_candidatura_auto_email
import main

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def enviar_mensagem_telegram(chat_id: str, texto: str):
    """Envia mensagem formatada em HTML para o chat do Telegram."""
    if not TELEGRAM_TOKEN or not chat_id:
        return
    url = f"{API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": texto,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error("[ERRO TELEGRAM] Falha ao enviar mensagem: %s", e)

def consultar_uso_serpapi() -> dict:
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
    from datetime import datetime, timezone, timedelta
    
    # Define Horário de Brasília (UTC-3)
    fuso_brt = timezone(timedelta(hours=-3))
    agora_brt = datetime.now(fuso_brt)
    data_brt_str = agora_brt.strftime("%d/%m/%Y às %H:%M")

    # Calcula o início do dia no Horário de Brasília convertido para UTC (para consulta no Supabase)
    inicio_dia_brt = agora_brt.replace(hour=0, minute=0, second=0, microsecond=0)
    inicio_utc_str = inicio_dia_brt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

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

def processar_vaga_direta(chat_id: str, texto_vaga: str):
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
        for line in lines[:5]:
            l_lower = line.lower()
            if l_lower.startswith("vaga:") or l_lower.startswith("cargo:") or l_lower.startswith("título:") or l_lower.startswith("titulo:"):
                titulo = line.split(":", 1)[1].strip()
            elif l_lower.startswith("empresa:"):
                empresa = line.split(":", 1)[1].strip()

        if titulo == "Vaga Solicitada via Telegram" and lines:
            primeira_linha = lines[0]
            if len(primeira_linha) <= 60 and not primeira_linha.lower().startswith("descriç"):
                titulo = primeira_linha

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
            "link": "",
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
    text = message.get("text", "").strip()
    chat_id = str(message.get("chat", {}).get("id", ""))

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
💼 /vaga &lt;descrição&gt; - Analisa uma vaga enviada via texto e gera CV, Dossiê e Carta.
❓ /ajuda - Exibe este menu de ajuda.

💡 <b>Dica:</b> Você também pode colar a descrição completa de uma vaga diretamente nesta conversa para receber o Currículo, Dossiê e Carta instantaneamente!"""
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
                texto_vaga = partes[1].strip()
                threading.Thread(target=processar_vaga_direta, args=(chat_id, texto_vaga), daemon=True).start()
            else:
                enviar_mensagem_telegram(chat_id, "⚠️ Por favor, envie a descrição da vaga após o comando.\nExemplo:\n<code>/vaga Desenvolvedor Python...</code>")
        else:
            enviar_mensagem_telegram(chat_id, "⚠️ Comando não reconhecido. Use /ajuda para ver os comandos ou envie a descrição da vaga diretamente.")
    else:
        if len(text) >= 15:
            threading.Thread(target=processar_vaga_direta, args=(chat_id, text), daemon=True).start()
        else:
            enviar_mensagem_telegram(chat_id, "ℹ️ Para analisar uma vaga, envie a descrição completa da vaga nesta conversa ou use o comando <code>/vaga &lt;descrição&gt;</code>.")

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
