import os
import sys
import time
import requests
from dotenv import load_dotenv

# Configura encoding de saída para evitar crash com emojis no console do Windows (cp1252)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv()

# Adiciona o diretório raiz ao PYTHONPATH para permitir importações dos módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

def comando_buscar(chat_id: str):
    """Executa a busca de vagas em tempo real e notifica o Telegram."""
    enviar_mensagem_telegram(chat_id, "⚡ <b>[BUSCA INICIADA]</b> Varrendo a web por novas vagas agora... Aguarde alguns instantes!")
    try:
        main.main()
        enviar_mensagem_telegram(chat_id, "✅ <b>[BUSCA CONCLUÍDA]</b> Varredura finalizada com sucesso! Se houverem novas vagas qualificadas, elas já foram enviadas acima.")
    except Exception as e:
        enviar_mensagem_telegram(chat_id, f"❌ <b>[ERRO NA BUSCA]</b> Falha ao executar varredura: {e}")

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
📊 /status - Exibe estatísticas de vagas e candidaturas.
⚡ /buscar - Dispara uma busca de vagas imediatamente.
❓ /ajuda - Exibe este menu de ajuda."""
        enviar_mensagem_telegram(chat_id, ajuda_texto)

    elif text == "/status":
        status_msg = comando_status()
        enviar_mensagem_telegram(chat_id, status_msg)

    elif text == "/buscar":
        comando_buscar(chat_id)

def escutar_comandos():
    """Inicia o loop de escuta de comandos do Telegram via Long Polling."""
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
