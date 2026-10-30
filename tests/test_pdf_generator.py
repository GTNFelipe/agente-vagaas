import os
from modules.pdf_generator import gerar_pdf_curriculo, sanitizar_texto_para_pdf


def test_sanitizar_texto_para_pdf():
    # Testa o caractere \u2011 (non-breaking hyphen) que gerava o 'full■stack'
    texto_problematico = "Engenheiro de Software full\u2011stack usando React\u202f19 e 30\u202f% de efici\u00eancia."
    texto_limpo = sanitizar_texto_para_pdf(texto_problematico)
    
    assert "\u2011" not in texto_limpo
    assert "\u202f" not in texto_limpo
    assert "full-stack" in texto_limpo
    assert "React 19" in texto_limpo


def test_gerar_pdf_curriculo(tmp_path):
    perfil_base = {
        "nome": "João Silva",
        "cargo_atual": "Desenvolvedor Python",
        "localizacao": "São Paulo",
        "contato": {"email": "joao@example.com", "phone": "11999999999", "linkedin": "linkedin.com/in/joao"},
        "resumo_profissional": "Desenvolvedor experiente.",
        "habilidades_tecnicas": {"linguagens": ["Python", "JavaScript"]},
        "experiencias": [{"cargo": "Dev", "empresa": "Tech", "periodo": "2020-2022", "detalhes": ["Fez coisas full\u2011stack."]}],
        "formacao": [{"curso": "Ciência da Computação", "instituicao": "USP", "conclusao": "2019"}]
    }
    analise_ia = {
        "resumo_adaptado": "Desenvolvedor focado em Python e full\u2011stack com React\u202f19.",
        "habilidades_destacadas": ["Python", "full\u2011stack"]
    }
    
    output_file = tmp_path / "test_curriculo.pdf"
    result = gerar_pdf_curriculo(perfil_base, analise_ia, str(output_file))
    
    assert result == str(output_file)
    assert os.path.exists(result)
    assert os.path.getsize(result) > 500
