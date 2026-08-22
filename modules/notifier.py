import os
import re
import html
import smtplib
import requests
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

logger = logging.getLogger(__name__)

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
            server.quit()
        logger.info("[SUCESSO] CANDIDATURA AUTOMATICA ENVIADA para %s com sucesso!", email_recrutador)
        return True
    except Exception as e:
        logger.error("Erro ao enviar candidatura por e-mail: %s", e)
        return False

def enviar_notificacao_telegram(vaga_info: dict, analise_ia: dict, caminho_pdf: str = None, caminho_dossie: str = None, caminho_carta: str = None, modo_candidatura: str = "manual") -> bool:
    """
    Dispara notificações ricas e exclusivas com botões inline diretamente para o Telegram do usuário.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        logger.warning("Credentials do Telegram não configuradas (TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID). Pulando notificação no Telegram.")
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
            logger.info("[TELEGRAM] Notificacao enviada para o Telegram com sucesso!")
        else:
            resp_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            desc = resp_data.get("description", response.text)
            if "chat not found" in desc.lower():
                logger.error("[ERRO TELEGRAM] Chat nao encontrado para o ID '%s'. ATENCAO: Voce precisa abrir a conversa com o seu Bot no Telegram e clicar em 'COMEÇAR' (/start) para autorizar o bot a enviar mensagens!", chat_id)
            else:
                logger.error("[ERRO TELEGRAM] Falha ao enviar mensagem: %s", desc)
            return False
    except Exception as e:
        logger.error("[ERRO TELEGRAM] Falha de conexao com a API do Telegram: %s", e)
        return False

    anexos = [f for f in [caminho_pdf, caminho_dossie, caminho_carta] if f and os.path.exists(f)]
    for fpath in anexos:
        try:
            with open(fpath, "rb") as doc_file:
                files = {"document": (os.path.basename(fpath), doc_file)}
                data = {"chat_id": chat_id}
                requests.post(doc_url, data=data, files=files, timeout=15)
            logger.info("[TELEGRAM] Anexo '%s' enviado para o Telegram!", os.path.basename(fpath))
        except Exception as e:
            logger.error("[ERRO TELEGRAM] Erro ao enviar anexo '%s' para o Telegram: %s", fpath, e)

    return True

def notificar_resumo_varredura(
    vagas_coletadas: int,
    vagas_novas_processadas: int,
    vagas_duplicadas: int = 0,
    vagas_encerradas: int = 0,
    vagas_descartadas_score: int = 0,
    vagas_auto_applied: int = 0,
    manual: bool = False,
    chat_id: str = None
):
    """
    Envia uma mensagem de feedback detalhada no Telegram após a conclusão de qualquer varredura (automática 8x/dia ou manual).
    Explica exatamente o resultado da execução, justificando o porquê de cada vaga ter sido aceita, descartada ou pulada.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    target_chat = chat_id or os.getenv("TELEGRAM_CHAT_ID")

    if not token or not target_chat:
        return False

    from datetime import datetime, timezone, timedelta
    fuso_brt = timezone(timedelta(hours=-3))
    hora_atual = datetime.now(fuso_brt).strftime("%H:%M")

    origem = "Manual (/buscar)" if manual else "Automática (Cron 8x/dia)"
    alertas_manuais = max(0, vagas_novas_processadas - vagas_auto_applied)

    if vagas_novas_processadas > 0:
        mensagem_motivo = f"✅ <b>Sucesso:</b> {vagas_novas_processadas} vaga(s) qualificada(s) com Match >= 80%!\n<i>(Currículo PDF, Dossiê e Carta de Apresentação gerados e anexados acima).</i>"
    elif vagas_coletadas == 0:
        mensagem_motivo = "ℹ️ <b>Motivo:</b> Nenhuma nova vaga foi retornada pelas fontes de busca nesta rodada. Isso pode ocorrer por ausência de novas publicações recentes nas plataformas monitoradas."
    else:
        mensagem_motivo = f"ℹ️ <b>Motivo:</b> Todas as {vagas_coletadas} vagas coletadas foram filtradas e nenhuma nova vaga atingiu a qualificação de 80%."

    texto = f"""🔍 <b>[RELATÓRIO DE VARREDURA - {origem}]</b>
⏰ <b>Horário:</b> {hora_atual} (BRT)

📊 <b>Resumo Detalhado da Execução:</b>
• 📥 <b>Vagas Coletadas na Web:</b> {vagas_coletadas}
• 🔄 <b>Já Processadas (Duplicatas):</b> {vagas_duplicadas}
• 🚫 <b>Inativas / Encerradas na Web:</b> {vagas_encerradas}
• 📉 <b>Descartadas (Match < 80%):</b> {vagas_descartadas_score}
• 🎯 <b>Vagas Qualificadas (Match >= 80%):</b> {vagas_novas_processadas}
  ├── 🤖 <i>Auto-Applies por E-mail:</i> {vagas_auto_applied}
  └── 📩 <i>Alertas para Candidatura Manual:</i> {alertas_manuais}

{mensagem_motivo}

🤖 <i>O robô continuará monitorando a web automaticamente na próxima execução!</i>"""

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": target_chat,
        "text": texto,
        "parse_mode": "HTML"
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info("[TELEGRAM] Resumo detalhado da varredura enviado para %s! (%s qualificadas / %s coletadas)", target_chat, vagas_novas_processadas, vagas_coletadas)
        else:
            logger.error("[ERRO TELEGRAM] Falha ao enviar resumo da varredura: %s", resp.text)
    except Exception as e:
        logger.error("[ERRO TELEGRAM] Exceção ao enviar resumo: %s", e)

    return True

# Aliases para compatibilidade
enviar_notificacao_vaga = enviar_notificacao_telegram
