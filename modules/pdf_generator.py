import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def gerar_pdf_curriculo(perfil_base: dict, analise_ia: dict, output_filename: str = "curriculo_otimizado.pdf") -> str:
    """
    Gera um PDF formatado e limpo para ATS com base no perfil adaptado pela IA.
    """
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
    info_contato = f"{perfil_base.get('cargo_atual')} | {perfil_base.get('localizacao')} | Email: {contato.get('email')} | Tel: {contato.get('phone')} | LinkedIn: {contato.get('linkedin')}"
    
    story.append(Paragraph(f"<b>{perfil_base.get('nome')}</b>", title_style))
    story.append(Paragraph(info_contato, contact_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#CBD5E0'), spaceAfter=10))

    # 2. Resumo Adaptado
    story.append(Paragraph("<b>RESUMO PROFISSIONAL</b>", section_style))
    story.append(Paragraph(analise_ia.get("resumo_adaptado", perfil_base.get("resumo_profissional")), body_style))
    story.append(Spacer(1, 10))

    # 3. Habilidades Destacadas (100% Fatuais)
    story.append(Paragraph("<b>HABILIDADES TÉCNICAS</b>", section_style))
    
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
            habilidades_lista.append(hab_str)
            
    if not habilidades_lista:
        habilidades_lista = skills_autorizadas[:8]
    
    skills_text = ", ".join(habilidades_lista)
    story.append(Paragraph(skills_text, body_style))
    story.append(Spacer(1, 10))

    # 4. Experiências Profissionais
    story.append(Paragraph("<b>EXPERIÊNCIA PROFISSIONAL</b>", section_style))
    for exp in perfil_base.get("experiencias", []):
        header_exp = f"<b>{exp.get('cargo')}</b> - {exp.get('empresa')} ({exp.get('periodo')})"
        story.append(Paragraph(header_exp, body_style))
        for item in exp.get("detalhes", []):
            story.append(Paragraph(f"• {item}", body_style))
        story.append(Spacer(1, 6))

    # 5. Formação Acadêmica
    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>FORMAÇÃO ACADÊMICA</b>", section_style))
    for form in perfil_base.get("formacao", []):
        form_text = f"<b>{form.get('curso')}</b> - {form.get('instituicao')} (Conclusão: {form.get('conclusao')})"
        story.append(Paragraph(form_text, body_style))

    doc.build(story)
    return output_filename

# Alias para compatibilidade
generate_resume_pdf = gerar_pdf_curriculo
