import os
import re
import html
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

def realizar_candidatura_auto_email(vaga_info: dict, analise_ia: dict, caminho_pdf: str, perfil_base: dict = None) -> bool:
    """
    Envia o e-mail de candidatura DIRETO para o recrutador e envia uma CÓPIA para o candidato.
    """
    remetente = os.getenv("GMAIL_USER")
    senha_app = os.getenv("GMAIL_APP_PASSWORD")
    email_recrutador = vaga_info.get("email_candidatura")

    if not remetente or not senha_app or not email_recrutador:
        return False

    contato = perfil_base.get("contato", {}) if perfil_base else {}
    nome_candidato = perfil_base.get("nome", "Candidato") if perfil_base else "Candidato"
    cargo_candidato = perfil_base.get("cargo_atual", "") if perfil_base else ""
    localizacao = perfil_base.get("localizacao", "") if perfil_base else ""
    phone = contato.get("phone", "")
    email_candidato = contato.get("email", remetente)
    linkedin = contato.get("linkedin", "")
    github = contato.get("github", "")

    assunto = f"Candidatura: {vaga_info.get('titulo')} - {nome_candidato}"
    
    cover_text = analise_ia.get('cover_letter', '').replace('\n', '<br>')
    
    info_rodape = []
    if cargo_candidato:
        info_rodape.append(html.escape(cargo_candidato))
    contatos_linha = []
    if localizacao:
        contatos_linha.append(html.escape(localizacao))
    if phone:
        contatos_linha.append(html.escape(phone))
    
    links_linha = []
    if email_candidato:
        links_linha.append(f"Email: {html.escape(email_candidato)}")
    if linkedin:
        links_linha.append(f"LinkedIn: {html.escape(linkedin)}")
    if github:
        links_linha.append(f"GitHub: {html.escape(github)}")

    rodape_html = f"<b>{html.escape(nome_candidato)}</b><br>"
    if info_rodape:
        rodape_html += f"{' | '.join(info_rodape)}<br>"
    if contatos_linha:
        rodape_html += f"{' | '.join(contatos_linha)}<br>"
    if links_linha:
        rodape_html += f"{' | '.join(links_linha)}"

    corpo_html_recrutador = f"""
    <div style="font-family: Arial, sans-serif; color: #2D3748; line-height: 1.6;">
        <p>Prezado(a) Recrutador(a) / Equipe de Seleção da <b>{html.escape(str(vaga_info.get('empresa', '')))}</b>,</p>
        
        {cover_text}
        
        <br>
        <hr style="border: 0; border-top: 1px solid #E2E8F0;">
        <p>{rodape_html}</p>
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
            filename = os.path.basename(caminho_pdf)
            pdf_attachment.add_header('Content-Disposition', 'attachment', filename=filename)
            msg.attach(pdf_attachment)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=15) as server:
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
    chat_id = os.getenv("TELEGRAM_CHAT_ID")


    if not token or not chat_id:
        print("⚠️ Credentials do Telegram não configuradas (TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID). Pulando notificação no Telegram.")
        return False

    match_score = analise_ia.get("match_score", 0)
    emoji_status = "🤖 [AUTO-APPLY]" if modo_candidatura == "auto" else "🎯 [NOVA VAGA QUALIFICADA]"
    
    dossie_info = analise_ia.get("dossie_entrevista", {})
    pitch = html.escape(str(dossie_info.get("pitch_elevador", "")))
    carta = html.escape(str(analise_ia.get("cover_letter", "")))
    link_vaga = vaga_info.get("link", "#")
    empresa = html.escape(str(vaga_info.get('empresa', '')))
    titulo = html.escape(str(vaga_info.get('titulo', '')))
    justificativa = html.escape(str(analise_ia.get('justificativa_match', '')))
    resumo_adaptado = html.escape(str(analise_ia.get('resumo_adaptado', '')))

    mensagem = f"""<b>{emoji_status} Match: {match_score}%</b>

🏢 <b>Empresa:</b> {empresa}
💼 <b>Cargo:</b> {titulo}

💡 <b>Justificativa:</b>
<i>{justificativa}</i>

📝 <b>Resumo Otimizado:</b>
<i>{resumo_adaptado}</i>

───────────────
🎙️ <b>Pitch de 1 Minuto:</b>
<i>"{pitch}"</i>

✉️ <b>Carta de Apresentação:</b>
<i>{carta}</i>
"""

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    doc_url = f"https://api.telegram.org/bot{token}/sendDocument"

    payload = {
        "chat_id": chat_id,
        "text": mensagem,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }

    if link_vaga and (link_vaga.startswith("http://") or link_vaga.startswith("https://")):
        payload["reply_markup"] = {
            "inline_keyboard": [
                [{"text": "🔗 Abrir Anúncio da Vaga", "url": link_vaga}]
            ]
        }

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("[TELEGRAM] Notificacao enviada para o Telegram com sucesso!")
        else:
            resp_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            desc = resp_data.get("description", response.text)
            if "chat not found" in desc.lower():
                print(f"[ERRO TELEGRAM] Chat nao encontrado para o ID '{chat_id}'. ATENCAO: Voce precisa abrir a conversa com o seu Bot no Telegram e clicar em 'COMEÇAR' (/start) para autorizar o bot a enviar mensagens!")
            else:
                print(f"[ERRO TELEGRAM] Falha ao enviar mensagem: {desc}")
    except Exception as e:
        print(f"[ERRO TELEGRAM] Falha de conexao com a API do Telegram: {e}")

    # Envia os documentos (PDF, Dossiê MD, Carta TXT) para o Telegram
    for fpath in [caminho_pdf, caminho_dossie, caminho_carta]:
        if fpath and os.path.exists(fpath):
            try:
                with open(fpath, "rb") as doc_file:
                    files = {"document": (os.path.basename(fpath), doc_file)}
                    data = {"chat_id": chat_id}
                    requests.post(doc_url, data=data, files=files, timeout=15)
                print(f"[TELEGRAM] Anexo '{os.path.basename(fpath)}' enviado para o Telegram!")
            except Exception as e:
                print(f"[ERRO TELEGRAM] Erro ao enviar anexo '{fpath}' para o Telegram: {e}")

    return True

def notificar_resumo_varredura(vagas_coletadas: int, vagas_novas_processadas: int, manual: bool = False):
    """
    Envia uma mensagem de feedback no Telegram após a conclusão de qualquer varredura (automática 8x/dia ou manual).
    Informa claramente o status, a quantidade de vagas e se nenhuma vaga nova foi encontrada.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        return False

    from datetime import datetime, timezone, timedelta
    fuso_brt = timezone(timedelta(hours=-3))
    hora_atual = datetime.now(fuso_brt).strftime("%H:%M")

    origem = "Manual (/buscar)" if manual else "Automática (Cron 8x/dia)"

    if vagas_novas_processadas > 0:
        texto = f"""🔍 <b>[VARREDURA CONCLUÍDA - {origem}]</b>
⏰ <b>Horário:</b> {hora_atual} (BRT)

✅ <b>Resultado:</b> {vagas_novas_processadas} nova(s) vaga(s) qualificada(s) e processada(s) nesta rodada!
<i>(Todas as notificações com CV, Dossiê e Carta foram enviadas acima).</i>"""
    else:
        texto = f"""🔍 <b>[VARREDURA CONCLUÍDA - {origem}]</b>
⏰ <b>Horário:</b> {hora_atual} (BRT)

ℹ️ <b>Resultado:</b> Nenhuma vaga nova qualificada encontrada nesta rodada.
(Vagas raspadas: {vagas_coletadas} | Todas já cadastradas anteriormente ou fora do perfil).

🤖 <i>O agente continuará monitorando automaticamente na próxima execução agendada!</i>"""

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": texto,
        "parse_mode": "HTML"
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            print(f"[TELEGRAM] Resumo da varredura enviado com sucesso! ({vagas_novas_processadas} novas / {vagas_coletadas} coletadas)")
    except Exception as e:
        print(f"[ERRO TELEGRAM] Falha ao enviar resumo da varredura: {e}")

    return True


# Aliases para compatibilidade
enviar_notificacao_vaga = enviar_notificacao_telegram
send_job_notification = enviar_notificacao_telegram
