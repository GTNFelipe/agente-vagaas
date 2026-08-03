import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

def realizar_candidatura_auto_email(vaga_info: dict, analise_ia: dict, caminho_pdf: str) -> bool:
    """
    Envia o e-mail de candidatura DIRETO para o recrutador e envia uma CÓPIA para o candidato.
    """
    remetente = os.getenv("GMAIL_USER") or "felipestartt@gmail.com"
    senha_app = os.getenv("GMAIL_APP_PASSWORD")
    email_recrutador = vaga_info.get("email_candidatura")

    if not senha_app or not email_recrutador:
        return False

    assunto = f"Candidatura: {vaga_info.get('titulo')} - Felipe Santana da Silva"
    
    cover_text = analise_ia.get('cover_letter', '').replace('\n', '<br>')
    
    corpo_html_recrutador = f"""
    <div style="font-family: Arial, sans-serif; color: #2D3748; line-height: 1.6;">
        <p>Prezado(a) Recrutador(a) / Equipe de Seleção da <b>{vaga_info.get('empresa')}</b>,</p>
        
        {cover_text}
        
        <br>
        <hr style="border: 0; border-top: 1px solid #E2E8F0;">
        <p><b>Felipe Santana da Silva</b><br>
        Trainee TI / Desenvolvedor Backend<br>
        Rio de Janeiro, RJ | (21) 96961-3192<br>
        Email: felipestartt@gmail.com | LinkedIn: https://linkedin.com/in/gtnfelipe | GitHub: https://github.com/gtnfelipe</p>
        <p><i>📎 O currículo completo em formato PDF encontra-se em anexo nesta mensagem.</i></p>
    </div>
    """

    msg = MIMEMultipart()
    msg['From'] = remetente
    msg['To'] = email_recrutador
    msg['Cc'] = remetente
    msg['Subject'] = assunto
    msg.attach(MIMEText(corpo_html_recrutador, 'html'))

    if caminho_pdf and os.path.exists(caminho_pdf):
        with open(caminho_pdf, "rb") as f:
            pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
            clean_title = str(vaga_info.get('titulo', 'Vaga')).replace(' ', '_').replace('/', '_')
            filename = f"CV_Felipe_Santana_{clean_title}.pdf"
            pdf_attachment.add_header('Content-Disposition', 'attachment', filename=filename)
            msg.attach(pdf_attachment)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(remetente, senha_app)
            destinatarios = [email_recrutador, remetente]
            server.send_message(msg, to_addrs=destinatarios)
        print(f"[SUCESSO] CANDIDATURA AUTOMATICA ENVIADA para {email_recrutador} com sucesso!")
        return True
    except Exception as e:
        print(f"[ERRO] Erro ao enviar candidatura por e-mail: {e}")
        return False

def enviar_notificacao_vaga(vaga_info: dict, analise_ia: dict, caminho_pdf: str = None, modo_candidatura: str = "manual"):
    """
    Envia alerta ao candidato sobre uma nova vaga encontrada.
    """
    remetente = os.getenv("GMAIL_USER") or "felipestartt@gmail.com"
    senha_app = os.getenv("GMAIL_APP_PASSWORD")
    if not senha_app:
        print("[AVISO] GMAIL_APP_PASSWORD nao configurada. Alerta nao enviado.")
        return

    destinatario = os.getenv("NOTIFY_EMAIL") or remetente
    
    if modo_candidatura == "auto":
        assunto = f"[CANDIDATADO AUTO] Vaga: {vaga_info.get('titulo')} - {vaga_info.get('empresa')}"
        status_banner = "<div style='background: #C6F6D5; color: #22543D; padding: 10px; border-radius: 5px; font-weight: bold;'>✅ Candidatura enviada automaticamente por e-mail para o recrutador! (Cópia no seu e-mail)</div>"
    else:
        assunto = f"[ALERTA VAGA] {vaga_info.get('titulo')} - Match: {analise_ia.get('match_score')}%"
        status_banner = "<div style='background: #EBF8FF; color: #2B6CB0; padding: 10px; border-radius: 5px; font-weight: bold;'>🔗 Candidatura Externa: Clique no link abaixo para anexar o PDF gerado.</div>"

    corpo_html = f"""
    <h2>🎯 Oportunidade Qualificada pelo Agente</h2>
    {status_banner}
    <br>
    <p><b>Empresa:</b> {vaga_info.get('empresa')}</p>
    <p><b>Cargo:</b> {vaga_info.get('titulo')}</p>
    <p><b>Score de Match:</b> <span style="color: green; font-weight: bold;">{analise_ia.get('match_score')}%</span></p>
    <p><b>Justificativa:</b> {analise_ia.get('justificativa_match')}</p>
    <p><b>Link da Vaga:</b> <a href="{vaga_info.get('link')}">Ver Anúncio</a></p>
    <hr>
    <h3>📝 Resumo Otimizado para esta Vaga:</h3>
    <p><i>{analise_ia.get('resumo_adaptado')}</i></p>
    <hr>
    <p>📎 <i>O currículo completo otimizado em PDF está anexado a esta mensagem.</i></p>
    """

    msg = MIMEMultipart()
    msg['From'] = remetente
    msg['To'] = destinatario
    msg['Subject'] = assunto
    msg.attach(MIMEText(corpo_html, 'html'))

    if caminho_pdf and os.path.exists(caminho_pdf):
        with open(caminho_pdf, "rb") as f:
            pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
            pdf_attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(caminho_pdf))
            msg.attach(pdf_attachment)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(remetente, senha_app)
            server.send_message(msg)
        print(f"[SUCESSO] Alerta enviado para {destinatario}!")
    except Exception as e:
        print(f"[ERRO] Erro ao enviar e-mail de alerta: {e}")

# Alias para compatibilidade
send_job_notification = enviar_notificacao_vaga
