import html
import logging
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

logger: logging.Logger = logging.getLogger(__name__)

def gerar_pdf_curriculo(perfil_base: dict[str, Any], analise_ia: dict[str, Any], output_filename: str = "curriculo_otimizado.pdf") -> str:
    """
    Gera um PDF formatado e limpo para ATS com base no perfil adaptado pela IA.
    """
    if not perfil_base or not isinstance(perfil_base, dict):
        raise ValueError("[FAIL FAST] O dicionário perfil_base é inválido ou está vazio.")
    if not analise_ia or not isinstance(analise_ia, dict):
        raise ValueError("[FAIL FAST] O dicionário analise_ia é inválido ou está vazio.")

    doc = SimpleDocTemplate(
        output_filename,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1A202C'),
        spaceAfter=4
    )
    
    contact_style = ParagraphStyle(
        'ContactStyle',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#4A5568'),
        spaceAfter=10
    )
    
    section_style = ParagraphStyle(
        'SectionStyle',
        parent=styles['Heading2'],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#2B6CB0'),
        spaceBefore=10,
        spaceAfter=4
    )
    
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#2D3748')
    )

    # 1. Cabeçalho
    contato = perfil_base.get("contato", {})
    nome_esc = html.escape(str(perfil_base.get('nome', 'Candidato')))
    cargo_esc = html.escape(str(perfil_base.get('cargo_atual', '')))
    loc_esc = html.escape(str(perfil_base.get('localizacao', '')))
    email_esc = html.escape(str(contato.get('email', '')))
    phone_esc = html.escape(str(contato.get('phone', '')))
    linkedin_esc = html.escape(str(contato.get('linkedin', '')))

    info_contato = f"{cargo_esc} | {loc_esc} | Email: {email_esc} | Tel: {phone_esc} | LinkedIn: {linkedin_esc}"
    
    story.append(Paragraph(f"<b>{nome_esc}</b>", title_style))
    story.append(Paragraph(info_contato, contact_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#CBD5E0'), spaceAfter=10))

    # 2. Resumo Adaptado
    is_english = analise_ia.get("is_english", False)
    t_resumo = "PROFESSIONAL SUMMARY" if is_english else "RESUMO PROFISSIONAL"
    story.append(Paragraph(f"<b>{t_resumo}</b>", section_style))
    resumo_raw = str(analise_ia.get("resumo_adaptado") or perfil_base.get("resumo_profissional") or "")
    story.append(Paragraph(html.escape(resumo_raw), body_style))
    story.append(Spacer(1, 10))

    # 3. Habilidades Destacadas (100% Fatuais)
    t_habilidades = "TECHNICAL SKILLS" if is_english else "HABILIDADES TÉCNICAS"
    story.append(Paragraph(f"<b>{t_habilidades}</b>", section_style))
    
    # Monta conjunto factual autorizado
    skills_autorizadas = []
    hab_dict = perfil_base.get("habilidades_tecnicas", {})
    for cat_skills in hab_dict.values():
        if isinstance(cat_skills, list):
            skills_autorizadas.extend(cat_skills)

    habilidades_raw = analise_ia.get("habilidades_destacadas", [])
    habilidades_lista = []
    
    for hab in habilidades_raw:
        hab_str = str(hab).strip()
        # Garante que nao insira alucinaçoes nao presentes no perfil (ex: Cypress, Playwright, Selenium, RestAssured)
        alucinacoes = ["cypress", "playwright", "selenium", "restassured", "angular", "vue", "react native", "kubernetes"]
        if not any(aluc in hab_str.lower() for aluc in alucinacoes if not any(aluc in sa.lower() for sa in skills_autorizadas)):
            habilidades_lista.append(html.escape(hab_str))
            
    if not habilidades_lista:
        habilidades_lista = [html.escape(sa) for sa in skills_autorizadas[:8]]
    
    skills_text = ", ".join(habilidades_lista)
    story.append(Paragraph(skills_text, body_style))
    story.append(Spacer(1, 10))

    # 4. Experiências Profissionais
    t_experiencia = "PROFESSIONAL EXPERIENCE" if is_english else "EXPERIÊNCIA PROFISSIONAL"
    story.append(Paragraph(f"<b>{t_experiencia}</b>", section_style))
    
    experiencias_fonte = analise_ia.get("experiencias_traduzidas") if is_english and analise_ia.get("experiencias_traduzidas") else perfil_base.get("experiencias", [])
    for exp in experiencias_fonte:
        carg_exp = html.escape(str(exp.get('cargo', '')))
        emp_exp = html.escape(str(exp.get('empresa', '')))
        per_exp = html.escape(str(exp.get('periodo', '')))
        header_exp = f"<b>{carg_exp}</b> - {emp_exp} ({per_exp})"
        story.append(Paragraph(header_exp, body_style))
        for item in exp.get("detalhes", []):
            story.append(Paragraph(f"• {html.escape(str(item))}", body_style))
        story.append(Spacer(1, 6))

    # 5. Formação Acadêmica
    story.append(Spacer(1, 4))
    t_formacao = "EDUCATION" if is_english else "FORMAÇÃO ACADÊMICA"
    story.append(Paragraph(f"<b>{t_formacao}</b>", section_style))
    
    formacao_fonte = analise_ia.get("formacao_traduzida") if is_english and analise_ia.get("formacao_traduzida") else perfil_base.get("formacao", [])
    for form in formacao_fonte:
        cur_f = html.escape(str(form.get('curso', '')))
        inst_f = html.escape(str(form.get('instituicao', '')))
        conc_f = html.escape(str(form.get('conclusao', '')))
        lbl_conc = "Graduated: " if is_english else "Conclusão: "
        form_text = f"<b>{cur_f}</b> - {inst_f} ({lbl_conc}{conc_f})"
        story.append(Paragraph(form_text, body_style))

    doc.build(story)
    return output_filename
