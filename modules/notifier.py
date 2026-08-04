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

def enviar_notificacao_telegram(vaga_info: dict, analise_ia: dict, caminho_pdf: str = None, caminho_dossie: str = None, caminho_carta: str = None, modo_candidatura: str = "manual") -> bool:
    """
    Envia notificação rica via Bot do Telegram para o candidato com anexos (CV PDF, Dossiê MD, Carta TXT).
    """
    import requests
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        return False

    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    doc_url = f"https://api.telegram.org/bot{bot_token}/sendDocument"

    dossie_info = analise_ia.get("dossie_entrevista", {})
    pitch = dossie_info.get("pitch_elevador", "")
    pontos_fortes = "\n".join([f"• {pf}" for pf in dossie_info.get("pontos_fortes", [])])
    carta = analise_ia.get("cover_letter", "")

    if modo_candidatura == "auto":
        banner = "✅ <b>CANDIDATURA AUTOMÁTICA ENVIADA POR E-MAIL!</b>"
    else:
        banner = "🎯 <b>NOVA OPORTUNIDADE QUALIFICADA!</b>"

    mensagem = f"""{banner}

<b>Empresa:</b> {vaga_info.get('empresa')}
<b>Cargo:</b> {vaga_info.get('titulo')}
<b>Match Score:</b> 🟢 <b>{analise_ia.get('match_score')}%</b>
<b>Justificativa:</b> {analise_ia.get('justificativa_match')}

🔗 <a href="{vaga_info.get('link')}">Ver Anúncio da Vaga</a>

────────────────────────
🎙️ <b>Pitch de 1 Minuto para Entrevista:</b>
<i>"{pitch}"</i>

💪 <b>Pontos Fortes:</b>
{pontos_fortes}

────────────────────────
✉️ <b>Carta de Apresentação:</b>
<i>{carta}</i>
"""

    payload = {
        "chat_id": chat_id,
        "text": mensagem,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }

    try:
        resp = requests.post(api_url, data=payload, timeout=10)
        if resp.status_code == 200:
            print(f"[TELEGRAM] Notificação enviada com sucesso para o Telegram (Chat ID: {chat_id})!")
        else:
            print(f"[AVISO TELEGRAM] Falha ao enviar mensagem Telegram: {resp.text}")
    except Exception as e:
        print(f"[ERRO TELEGRAM] Erro ao enviar notificação Telegram: {e}")

    # Envia os anexos (PDF, Dossiê, Carta) se existirem
    for fpath in [caminho_pdf, caminho_dossie, caminho_carta]:
        if fpath and os.path.exists(fpath):
            try:
                with open(fpath, "rb") as doc_file:
                    files = {"document": (os.path.basename(fpath), doc_file)}
                    data = {"chat_id": chat_id}
                    requests.post(doc_url, data=data, files=files, timeout=15)
                print(f"[TELEGRAM] Anexo '{os.path.basename(fpath)}' enviado com sucesso para o Telegram!")
            except Exception as e:
                print(f"[ERRO TELEGRAM] Erro ao enviar anexo '{fpath}': {e}")

    return True

def enviar_notificacao_vaga(vaga_info: dict, analise_ia: dict, caminho_pdf: str = None, caminho_dossie: str = None, caminho_carta: str = None, modo_candidatura: str = "manual"):
    """
    Envia alerta ao candidato sobre uma nova vaga via Telegram (se configurado) e/ou E-mail.
    """
    # 1. Tenta enviar via Telegram
    enviado_telegram = enviar_notificacao_telegram(
        vaga_info=vaga_info,
        analise_ia=analise_ia,
        caminho_pdf=caminho_pdf,
        caminho_dossie=caminho_dossie,
        caminho_carta=caminho_carta,
        modo_candidatura=modo_candidatura
    )

    # 2. Envia via E-mail (Gmail SMTP) se configurado
    remetente = os.getenv("GMAIL_USER") or "felipestartt@gmail.com"
    senha_app = os.getenv("GMAIL_APP_PASSWORD")
    if not senha_app:
        if not enviado_telegram:
            print("[AVISO] Nem Telegram nem Gmail configurados. Notificação não enviada.")
        return

    destinatario = os.getenv("NOTIFY_EMAIL") or remetente
    
    if modo_candidatura == "auto":
        assunto = f"[CANDIDATADO AUTO] Vaga: {vaga_info.get('titulo')} - {vaga_info.get('empresa')}"
        status_banner = "<div style='background: #C6F6D5; color: #22543D; padding: 10px; border-radius: 5px; font-weight: bold;'>✅ Candidatura enviada automaticamente por e-mail para o recrutador! (Cópia no seu e-mail)</div>"
    else:
        assunto = f"[ALERTA VAGA] {vaga_info.get('titulo')} - Match: {analise_ia.get('match_score')}%"
        status_banner = "<div style='background: #EBF8FF; color: #2B6CB0; padding: 10px; border-radius: 5px; font-weight: bold;'>🔗 Candidatura Externa: Clique no link abaixo para anexar o PDF gerado.</div>"

    dossie_info = analise_ia.get("dossie_entrevista", {})
    pitch = dossie_info.get("pitch_elevador", "")
    pontos_fortes = "<br>".join([f"• {pf}" for pf in dossie_info.get("pontos_fortes", [])])
    carta_texto = analise_ia.get("cover_letter", "").replace("\n", "<br>")

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
    <h3>✉️ Carta de Apresentação Profissional (Pronta para Envio):</h3>
    <div style="background: #F7FAFC; padding: 15px; border-left: 4px solid #319795; font-family: Georgia, serif; line-height: 1.6; color: #2D3748;">
        {carta_texto}
    </div>
    <hr>
    <h3>🎙️ Pitch de 1 Minuto para a Entrevista:</h3>
    <p style="background: #FFF5F5; padding: 10px; border-left: 4px solid #E53E3E; font-style: italic;">"{pitch}"</p>
    {f"<h4>💪 Pontos Fortes a Destacar:</h4><p>{pontos_fortes}</p>" if pontos_fortes else ""}
    <hr>
    <h3>📝 Resumo Otimizado para esta Vaga:</h3>
    <p><i>{analise_ia.get('resumo_adaptado')}</i></p>
    <hr>
    <p>📎 <i>Os arquivos <b>Currículo PDF</b>, <b>Dossiê de Entrevista (.md)</b> e <b>Carta de Apresentação (.txt)</b> estão anexados a esta mensagem.</i></p>
    """

    msg = MIMEMultipart()
    msg['From'] = remetente
    msg['To'] = destinatario
    msg['Subject'] = assunto
    msg.attach(MIMEText(corpo_html, 'html'))

    # Anexo do Currículo PDF
    if caminho_pdf and os.path.exists(caminho_pdf):
        with open(caminho_pdf, "rb") as f:
            pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
            pdf_attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(caminho_pdf))
            msg.attach(pdf_attachment)

    # Anexo do Dossiê Markdown
    if caminho_dossie and os.path.exists(caminho_dossie):
        with open(caminho_dossie, "rb") as f:
            md_attachment = MIMEApplication(f.read(), _subtype="octet-stream")
            md_attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(caminho_dossie))
            msg.attach(md_attachment)

    # Anexo da Carta de Apresentação
    if caminho_carta and os.path.exists(caminho_carta):
        with open(caminho_carta, "rb") as f:
            txt_attachment = MIMEApplication(f.read(), _subtype="plain")
            txt_attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(caminho_carta))
            msg.attach(txt_attachment)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(remetente, senha_app)
            server.send_message(msg)
        print(f"[SUCESSO] Alerta enviado para {destinatario} via E-mail!")
    except Exception as e:
        print(f"[ERRO] Erro ao enviar e-mail de alerta: {e}")

# Alias para compatibilidade
send_job_notification = enviar_notificacao_vaga
