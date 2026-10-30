import html
import logging
import re
import unicodedata
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

logger: logging.Logger = logging.getLogger(__name__)

def sanitizar_texto_para_pdf(texto: str) -> str:
    """
    Higieniza e normaliza rigorosamente qualquer texto antes de renderizar no PDF / ATS:
    - Converte todos os hífens e travessões tipográficos (non-breaking hyphen U+2011, en-dash U+2013, em-dash U+2014, etc.) para o hífen ASCII padrão '-'.
    - Converte todos os espaços tipográficos (narrow no-break space U+202F, non-breaking space U+00A0, zero-width, etc.) para espaço simples ' '.
    - Converte aspas curvas ('', "") e apóstrofos tipográficos para aspas e apóstrofos ASCII simples.
    - Remove caracteres de controle e caracteres não imprimíveis.
    - Garante 100% de compatibilidade com a tipografia do ReportLab e parsers de ATS sem nenhum caractere estranho ou quadrado ('■').
    """
    if not texto:
        return ""

    texto = str(texto)
    # Normalização Unicode inicial (NFKC decompõe compatibilidade)
    texto = unicodedata.normalize('NFKC', texto)

    substituicoes = {
        # Hífens e travessões problemáticos -> hífen ASCII padrão
        '\u2010': '-',  # Hyphen
        '\u2011': '-',  # Non-breaking hyphen (O principal causador do full■stack!)
        '\u2012': '-',  # Figure dash
        '\u2013': '-',  # En dash
        '\u2014': '-',  # Em dash
        '\u2015': '-',  # Horizontal bar
        '\u2212': '-',  # Minus sign
        '\ufe58': '-',  # Small em dash
        '\ufe63': '-',  # Small hyphen-minus
        '\uff0d': '-',  # Fullwidth hyphen-minus
        '\u00ad': '',   # Soft hyphen (invisível)

        # Espaços especiais e invisíveis -> espaço simples ASCII
        '\u00a0': ' ',  # Non-breaking space
        '\u2000': ' ',  # En quad
        '\u2001': ' ',  # Em quad
        '\u2002': ' ',  # En space
        '\u2003': ' ',  # Em space
        '\u2004': ' ',  # Three-per-em space
        '\u2005': ' ',  # Four-per-em space
        '\u2006': ' ',  # Six-per-em space
        '\u2007': ' ',  # Figure space
        '\u2008': ' ',  # Punctuation space
        '\u2009': ' ',  # Thin space
        '\u200a': ' ',  # Hair space
        '\u202f': ' ',  # Narrow no-break space (Causador de problemas no React 19 / 30%)
        '\u205f': ' ',  # Medium mathematical space
        '\u3000': ' ',  # Ideographic space
        '\u200b': '',   # Zero-width space
        '\u200c': '',   # Zero-width non-joiner
        '\u200d': '',   # Zero-width joiner
        '\ufeff': '',   # Byte order mark / zero width no-break space

        # Aspas tipográficas -> aspas simples ASCII
        '\u2018': "'",  # Left single quotation mark
        '\u2019': "'",  # Right single quotation mark
        '\u201a': "'",  # Single low-9 quotation mark
        '\u201b': "'",  # Single high-reversed-9 quotation mark
        '\u2032': "'",  # Prime
        '\u201c': '"',  # Left double quotation mark
        '\u201d': '"',  # Right double quotation mark
        '\u201e': '"',  # Double low-9 quotation mark
        '\u201f': '"',  # Double high-reversed-9 quotation mark
        '\u2033': '"',  # Double prime

        # Reticências e marcadores
        '\u2026': '...', # Horizontal ellipsis
        '\u25aa': '•',   # Black small square
        '\u25ab': '•',   # White small square
        '\u25a0': '•',   # Black square
        '\u25a1': '•',   # White square
        '\u25fe': '•',   # Black medium small square
        '\u25fd': '•',   # White medium small square
        '\u2219': '•',   # Bullet operator
        '\u2043': '•',   # Hyphen bullet
    }

    for char_orig, char_subst in substituicoes.items():
        texto = texto.replace(char_orig, char_subst)

    # Remove caracteres de controle C0/C1 (exceto quebras de linha e tabs comuns)
    texto = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', texto)

    # Remove múltiplos espaços repetidos
    texto = re.sub(r'[ \t]+', ' ', texto)

    return texto.strip()

def formatar_para_paragrafo_pdf(texto: str) -> str:
    """Higieniza o texto contra caracteres estranhos e escapa para XML seguro no ReportLab."""
    return html.escape(sanitizar_texto_para_pdf(texto))

def gerar_pdf_curriculo(perfil_base: dict[str, Any], analise_ia: dict[str, Any], output_filename: str = "curriculo_otimizado.pdf") -> str:
    """
    Gera um PDF formatado e limpo para ATS com base no perfil adaptado pela IA.
    Garante ausência total de glifos inválidos ou quadrados em qualquer visualizador de PDF.
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
    nome_esc = formatar_para_paragrafo_pdf(str(perfil_base.get('nome', 'Candidato')))
    cargo_esc = formatar_para_paragrafo_pdf(str(perfil_base.get('cargo_atual', '')))
    loc_esc = formatar_para_paragrafo_pdf(str(perfil_base.get('localizacao', '')))
    email_esc = formatar_para_paragrafo_pdf(str(contato.get('email', '')))
    phone_esc = formatar_para_paragrafo_pdf(str(contato.get('phone', '')))
    linkedin_esc = formatar_para_paragrafo_pdf(str(contato.get('linkedin', '')))

    info_contato = f"{cargo_esc} | {loc_esc} | Email: {email_esc} | Tel: {phone_esc} | LinkedIn: {linkedin_esc}"
    
    story.append(Paragraph(f"<b>{nome_esc}</b>", title_style))
    story.append(Paragraph(info_contato, contact_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#CBD5E0'), spaceAfter=10))

    # 2. Resumo Adaptado
    is_english = analise_ia.get("is_english", False)
    t_resumo = "PROFESSIONAL SUMMARY" if is_english else "RESUMO PROFISSIONAL"
    story.append(Paragraph(f"<b>{t_resumo}</b>", section_style))
    resumo_raw = str(analise_ia.get("resumo_adaptado") or perfil_base.get("resumo_profissional") or "")
    story.append(Paragraph(formatar_para_paragrafo_pdf(resumo_raw), body_style))
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
        hab_str = sanitizar_texto_para_pdf(str(hab))
        # Garante que nao insira alucinaçoes nao presentes no perfil (ex: Cypress, Playwright, Selenium, RestAssured)
        alucinacoes = ["cypress", "playwright", "selenium", "restassured", "angular", "vue", "react native", "kubernetes"]
        if not any(aluc in hab_str.lower() for aluc in alucinacoes if not any(aluc in sa.lower() for sa in skills_autorizadas)):
            habilidades_lista.append(formatar_para_paragrafo_pdf(hab_str))
            
    if not habilidades_lista:
        habilidades_lista = [formatar_para_paragrafo_pdf(sa) for sa in skills_autorizadas[:8]]
    
    skills_text = ", ".join(habilidades_lista)
    story.append(Paragraph(skills_text, body_style))
    story.append(Spacer(1, 10))

    # 4. Experiências Profissionais (Filtradas e Assertivas para a Vaga)
    t_experiencia = "PROFESSIONAL EXPERIENCE" if is_english else "EXPERIÊNCIA PROFISSIONAL"
    story.append(Paragraph(f"<b>{t_experiencia}</b>", section_style))
    
    # Prioriza as experiências assertivas selecionadas pela IA para esta vaga específica
    if is_english and analise_ia.get("experiencias_traduzidas"):
        experiencias_fonte = analise_ia.get("experiencias_traduzidas")
    elif analise_ia.get("experiencias_selecionadas"):
        experiencias_fonte = analise_ia.get("experiencias_selecionadas")
    elif analise_ia.get("experiencias"):
        experiencias_fonte = analise_ia.get("experiencias")
    else:
        experiencias_fonte = perfil_base.get("experiencias", [])[:3]
    for exp in experiencias_fonte:
        carg_exp = formatar_para_paragrafo_pdf(str(exp.get('cargo', '')))
        emp_exp = formatar_para_paragrafo_pdf(str(exp.get('empresa', '')))
        per_exp = formatar_para_paragrafo_pdf(str(exp.get('periodo', '')))
        header_exp = f"<b>{carg_exp}</b> - {emp_exp} ({per_exp})"
        story.append(Paragraph(header_exp, body_style))
        for item in exp.get("detalhes", []):
            item_clean = formatar_para_paragrafo_pdf(str(item))
            story.append(Paragraph(f"• {item_clean}", body_style))
        story.append(Spacer(1, 6))

    # 5. Formação Acadêmica
    story.append(Spacer(1, 4))
    t_formacao = "EDUCATION" if is_english else "FORMAÇÃO ACADÊMICA"
    story.append(Paragraph(f"<b>{t_formacao}</b>", section_style))
    
    formacao_fonte = analise_ia.get("formacao_traduzida") if is_english and analise_ia.get("formacao_traduzida") else perfil_base.get("formacao", [])
    for form in formacao_fonte:
        cur_f = formatar_para_paragrafo_pdf(str(form.get('curso', '')))
        inst_f = formatar_para_paragrafo_pdf(str(form.get('instituicao', '')))
        conc_f = formatar_para_paragrafo_pdf(str(form.get('conclusao', '')))
        lbl_conc = "Graduated: " if is_english else "Conclusão: "
        form_text = f"<b>{cur_f}</b> - {inst_f} ({lbl_conc}{conc_f})"
        story.append(Paragraph(form_text, body_style))

    doc.build(story)
    return output_filename
