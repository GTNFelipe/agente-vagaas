import os
import pytest
from modules.pdf_generator import gerar_pdf_curriculo

def test_gerar_pdf_curriculo(tmp_path):
    perfil_base = {
        "nome": "João Silva",
        "cargo_atual": "Desenvolvedor Python",
        "localizacao": "São Paulo",
        "contato": {"email": "joao@example.com", "phone": "11999999999", "linkedin": "linkedin.com/in/joao"},
        "resumo_profissional": "Desenvolvedor experiente.",
        "habilidades_tecnicas": {"linguagens": ["Python", "JavaScript"]},
        "experiencias": [{"cargo": "Dev", "empresa": "Tech", "periodo": "2020-2022", "detalhes": ["Fez coisas."]}],
        "formacao": [{"curso": "Ciência da Computação", "instituicao": "USP", "conclusao": "2019"}]
    }
    analise_ia = {
        "resumo_adaptado": "Desenvolvedor focado em Python.",
        "habilidades_destacadas": ["Python"]
    }
    
    output_file = tmp_path / "test_curriculo.pdf"
    result = gerar_pdf_curriculo(perfil_base, analise_ia, str(output_file))
    
    assert result == str(output_file)
    assert os.path.exists(result)
