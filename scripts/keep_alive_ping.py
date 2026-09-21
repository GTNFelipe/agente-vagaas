import os
import sys
import time
import socket
import subprocess
import requests
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env_file = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_file):
    load_dotenv(dotenv_path=env_file)
else:
    load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}" if TELEGRAM_TOKEN else None
PORT_LOCK = 47891

def bot_esta_rodando(port: int = PORT_LOCK) -> bool:
    """Testa se a porta de trava do bot está ativa na máquina local."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", port))
        sock.close()
        return False  # Porta livre = bot NÃO está rodando
    except socket.error:
        return True   # Porta ocupada = bot ESTÁ rodando com sucesso

def disparar_ping_keepalive():
    """
    Monitora a cada 5 minutos (300 segundos).
    Testa a saúde da API do Telegram e se o bot caiu, relança-o automaticamente.
    """
    print(f"🔄 [PING KEEPALIVE 24/7] Monitorando o Agente de Vagas a cada 5 minutos (300s)...")
    
    while True:
        agora_str = time.strftime("%d/%m/%Y às %H:%M:%S")
        rodando = bot_esta_rodando()
        api_status = False

        if TELEGRAM_TOKEN:
            try:
                res = requests.get(f"{API_URL}/getMe", timeout=10)
                if res.status_code == 200:
                    api_status = True
            except Exception as e:
                print(f"⚠️ [{agora_str}] Falha de conexão na API do Telegram: {e}")

        if rodando and api_status:
            print(f"🟢 [{agora_str}] [PING 5M OK] Bot operante e conectado ao Telegram 24h!")
        else:
            print(f"⚠️ [{agora_str}] [PING 5M ALERTA] Bot offline ou sem resposta! Relançando processo...")
            
            # Localiza o executável do Python correto (.venv ou venv ou sistema)
            venv_python = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")
            if not os.path.exists(venv_python):
                venv_python = os.path.join(BASE_DIR, "venv", "Scripts", "python.exe")
            if not os.path.exists(venv_python):
                venv_python = "python"

            bot_script = os.path.join(BASE_DIR, "modules", "telegram_bot.py")
            try:
                subprocess.Popen([venv_python, "-u", bot_script], cwd=BASE_DIR)
                print(f"🚀 [{agora_str}] Processo do Bot relançado com sucesso!")
            except Exception as err:
                print(f"❌ [{agora_str}] Erro ao relançar Bot: {err}")

        time.sleep(300)  # Aguarda 5 minutos para a próxima checagem

if __name__ == "__main__":
    disparar_ping_keepalive()
