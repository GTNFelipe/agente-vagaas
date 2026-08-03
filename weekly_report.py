import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from modules.database import inicializar_supabase

load_dotenv()

def gerar_relatorio_semanal():
    supabase = inicializar_supabase()
    if not supabase:
        print("[AVISO] Supabase nao disponivel para o relatorio.")
        return

    try:
        res = supabase.table("vagas_processadas").select("*").execute()
        dados = res.data

        total_vagas = len(dados)
        candidatadas_auto = len([v for v in dados if v.get("status_candidatura") == "candidatado_auto"])
        alertas_manuais = len([v for v in dados if v.get("status_candidatura") == "alerta_manual"])
        descartadas = len([v for v in dados if v.get("status_candidatura") == "descartado"])
        
        scores = [v.get("match_score", 0) for v in dados if v.get("match_score")]
        media_score = round(sum(scores) / len(scores), 1) if scores else 0

        remetente = os.getenv("GMAIL_USER") or "felipestartt@gmail.com"
        senha_app = os.getenv("GMAIL_APP_PASSWORD")
        if not senha_app:
            print("[AVISO] GMAIL_APP_PASSWORD nao configurada. Relatorio nao enviado.")
            return

        destinatario = os.getenv("NOTIFY_EMAIL") or remetente
        assunto = "[Relatorio Semanal] Performance do Agente de Vagas"
        corpo = f"""
        <h2>📊 Relatório Semanal de Candidaturas e Analytics</h2>
        <p>Aqui está o resumo do desempenho do seu agente de IA nos últimos dias:</p>
        <ul>
            <li><b>Total de vagas analisadas:</b> {total_vagas}</li>
            <li><b>Candidaturas 100% Automáticas enviadas:</b> <span style="color: green; font-weight: bold;">{candidatadas_auto}</span></li>
            <li><b>Vagas qualificadas para candidatura manual:</b> {alertas_manuais}</li>
            <li><b>Vagas descartadas (Match < 70%):</b> {descartadas}</li>
            <li><b>Média de Match Score das Vagas:</b> {media_score}%</li>
        </ul>
        <hr>
        <p><i>O agente continua rodando a cada 6 horas no GitHub Actions!</i></p>
        """

        msg = MIMEMultipart()
        msg['From'] = remetente
        msg['To'] = destinatario
        msg['Subject'] = assunto
        msg.attach(MIMEText(corpo, 'html'))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(remetente, senha_app)
            server.send_message(msg)
        print("[SUCESSO] Relatorio semanal enviado com sucesso!")
    except Exception as e:
        print(f"[ERRO] Erro ao gerar relatorio: {e}")

if __name__ == "__main__":
    gerar_relatorio_semanal()
