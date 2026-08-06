import os
import sys
import time
import socket
import requests
from dotenv import load_dotenv

# Configura encoding de saída para evitar crash com emojis no console do Windows (cp1252)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

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
        print(f"[BOT LOCK] Outra instância do bot já está rodando (Porta {port}). Encerrando duplicata.")
        sys.exit(0)

# Adiciona o diretório raiz ao PYTHONPATH para permitir importações dos módulos
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

ENV_FILE = os.path.join(BASE_DIR, ".env")
if os.path.exists(ENV_FILE):
    load_dotenv(dotenv_path=ENV_FILE)
else:
    load_dotenv()

from modules.database import inicializar_supabase
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
        print(f"[ERRO TELEGRAM] Falha ao enviar mensagem: {e}")

def consultar_uso_serpapi() -> dict:
    """Consulta os dados reais de uso da API SerpAPI diretamente na API oficial."""
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        return {}
    try:
        url = f"https://serpapi.com/account?api_key={api_key}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "usadas": data.get("this_month_usage", 0),
                "restantes": data.get("total_searches_left", 0),
                "limite": data.get("searches_per_month", 250),
                "renovacao": data.get("plan_renewal_date", "N/A")
            }
    except Exception as e:
        print(f"[ERRO SERPAPI ACCOUNT] {e}")
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
    """Executa a busca de vagas em tempo real e notifica o Telegram."""
    global BUSCA_EM_ANDAMENTO

    if BUSCA_EM_ANDAMENTO:
        enviar_mensagem_telegram(chat_id, "⏳ <b>[BUSCA EM ANDAMENTO]</b> O robô já está varrendo a web neste momento. Aguarde a conclusão da rodada atual para disparar uma nova!")
        return

    BUSCA_EM_ANDAMENTO = True
    enviar_mensagem_telegram(chat_id, "⚡ <b>[BUSCA INICIADA]</b> Varrendo a web por novas vagas agora... Aguarde alguns instantes!")
    try:
        main.main()
        enviar_mensagem_telegram(chat_id, "✅ <b>[BUSCA CONCLUÍDA]</b> Varredura finalizada com sucesso! Se houverem novas vagas qualificadas, elas já foram enviadas acima.")
    except Exception as e:
        enviar_mensagem_telegram(chat_id, f"❌ <b>[ERRO NA BUSCA]</b> Falha ao executar varredura: {e}")
    finally:
        BUSCA_EM_ANDAMENTO = False

def gerar_relatorio_diario_telegram() -> str:
    """Gera o resumo diário de desempenho (Daily Digest) consultando o Supabase e com fallback local."""
    from datetime import datetime, timezone, timedelta
    
    # Define Horário de Brasília (UTC-3)
    fuso_brt = timezone(timedelta(hours=-3))
    agora_brt = datetime.now(fuso_brt)
    data_brt_str = agora_brt.strftime("%d/%m/%Y")

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
            print(f"[AVISO RELATORIO] Erro ao consultar Supabase, usando fallback local: {e}")
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

    mensagem = f"""📊 <b>[RESUMO DIÁRIO DO AGENTE DE VAGAS]</b>
📅 <b>Data:</b> {data_brt_str} (<i>{fonte_dados}</i>)

🔍 <b>Vagas Analisadas Hoje:</b> {total_proc_hoje}
🎯 <b>Vagas Qualificadas Hoje (Match >= 80%):</b> {qualificadas_hoje}
🤖 <b>Candidaturas Automáticas (Auto-Applies):</b> {auto_applies_hoje}

💳 <b>[COTA SERPAPI AO VIVO]</b>
• <b>Pesquisas Usadas Este Mês:</b> {usadas} / {limite}
• <b>Pesquisas Restantes:</b> {restantes}

🟢 <i>O robô continuará as varreduras diárias normalmente!</i>"""
    return mensagem

def processar_mensagem(update: dict):
    """Processa mensagens e comandos recebidos do Telegram."""
    message = update.get("message", {})
    text = message.get("text", "").strip()
    chat_id = str(message.get("chat", {}).get("id", ""))

    # Valida se a mensagem veio do seu chat autorizado
    if chat_id != str(TELEGRAM_CHAT_ID):
        print(f"[BOT SECURITY] Mensagem ignorada de chat não autorizado: {chat_id}")
        return

    if text in ["/start", "/ajuda", "/help"]:
        ajuda_texto = """🤖 <b>[MENU DO AGENTE DE VAGAS]</b>

Comandos disponíveis:
📊 /status - Exibe estatísticas de vagas e cota ao vivo.
📅 /relatorio - Exibe o resumo de desempenho do dia de hoje (Daily Digest).
⚡ /buscar - Dispara uma busca de vagas imediatamente.
❓ /ajuda - Exibe este menu de ajuda."""
        enviar_mensagem_telegram(chat_id, ajuda_texto)

    elif text == "/status":
        status_msg = comando_status()
        enviar_mensagem_telegram(chat_id, status_msg)

    elif text == "/relatorio":
        rel_msg = gerar_relatorio_diario_telegram()
        enviar_mensagem_telegram(chat_id, rel_msg)

    elif text == "/buscar":
        comando_buscar(chat_id)

def escutar_comandos():
    """Inicia o loop de escuta de comandos do Telegram via Long Polling."""
    # Ativa trava de instância única para o bot interativo
    garantir_instancia_unica()

    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[BOT TELEGRAM] TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID não definidos.")
        return

    print("🤖 [BOT TELEGRAM INTERATIVO] Escutando comandos... (Pressione Ctrl+C para parar)")
    offset = 0

    while True:
        try:
            url = f"{API_URL}/getUpdates?offset={offset}&timeout=20"
            resp = requests.get(url, timeout=25)
            if resp.status_code == 200:
                data = resp.json()
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    processar_mensagem(update)
            time.sleep(1)
        except Exception as e:
            print(f"[ERRO BOT TELEGRAM] {e}")
            time.sleep(5)

if __name__ == "__main__":
    escutar_comandos()
