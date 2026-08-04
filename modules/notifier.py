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
    Dispara notificações ricas e exclusivas com botões inline diretamente para o Telegram do usuário.
    """
    import requests
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID") or "5610262269"

    if not token or not chat_id:
        print("⚠️ Credentials do Telegram não configuradas (TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID). Pulando notificação no Telegram.")
        return False

    match_score = analise_ia.get("match_score", 0)
    emoji_status = "🤖 [AUTO-APPLY]" if modo_candidatura == "auto" else "🎯 [NOVA VAGA QUALIFICADA]"
    
    dossie_info = analise_ia.get("dossie_entrevista", {})
    pitch = dossie_info.get("pitch_elevador", "")
    carta = analise_ia.get("cover_letter", "")
    link_vaga = vaga_info.get("link", "#")

    mensagem = f"""<b>{emoji_status} Match: {match_score}%</b>

🏢 <b>Empresa:</b> {vaga_info.get('empresa')}
💼 <b>Cargo:</b> {vaga_info.get('titulo')}

💡 <b>Justificativa:</b>
<i>{analise_ia.get('justificativa_match')}</i>

📝 <b>Resumo Otimizado:</b>
<i>{analise_ia.get('resumo_adaptado')}</i>

───────────────
🎙️ <b>Pitch de 1 Minuto:</b>
<i>"{pitch}"</i>

✉️ <b>Carta de Apresentação:</b>
<i>{carta}</i>
"""

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    doc_url = f"https://api.telegram.org/bot{token}/sendDocument"

    reply_markup = {
        "inline_keyboard": [
            [{"text": "🔗 Abrir Anúncio da Vaga", "url": link_vaga}]
        ]
    }

    payload = {
        "chat_id": chat_id,
        "text": mensagem,
        "parse_mode": "HTML",
        "reply_markup": reply_markup,
        "disable_web_page_preview": False
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("📱 Notificação enviada para o Telegram com sucesso!")
        else:
            print(f"❌ Erro ao enviar para o Telegram: {response.text}")
    except Exception as e:
        print(f"❌ Falha de conexão com a API do Telegram: {e}")

    # Envia os documentos (PDF, Dossiê MD, Carta TXT) para o Telegram
    for fpath in [caminho_pdf, caminho_dossie, caminho_carta]:
        if fpath and os.path.exists(fpath):
            try:
                with open(fpath, "rb") as doc_file:
                    files = {"document": (os.path.basename(fpath), doc_file)}
                    data = {"chat_id": chat_id}
                    requests.post(doc_url, data=data, files=files, timeout=15)
                print(f"📎 Anexo '{os.path.basename(fpath)}' enviado para o Telegram!")
            except Exception as e:
                print(f"❌ Erro ao enviar anexo '{fpath}' para o Telegram: {e}")

    return True

def enviar_notificacao_vaga(vaga_info: dict, analise_ia: dict, caminho_pdf: str = None, caminho_dossie: str = None, caminho_carta: str = None, modo_candidatura: str = "manual"):
    """
    Notifica o candidato EXCLUSIVAMENTE via Telegram (removendo envio de e-mails para o candidato).
    """
    enviar_notificacao_telegram(
        vaga_info=vaga_info,
        analise_ia=analise_ia,
        caminho_pdf=caminho_pdf,
        caminho_dossie=caminho_dossie,
        caminho_carta=caminho_carta,
        modo_candidatura=modo_candidatura
    )

# Alias para compatibilidade
send_job_notification = enviar_notificacao_vaga
