import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

import pathlib
import tempfile
import main
from modules.pdf_generator import gerar_pdf_curriculo, sanitizar_texto_para_pdf
from modules.tailor import adaptar_curriculo
from modules.telegram_bot import extrair_texto_url

def test_sanitization_fullstack():
    # Testa o caso específico que o usuário relatou com o quadrado no fullstack
    texto_com_quadrado = "Engenheiro de Software com sólida experiência em desenvolvimento full\u2011stack usando React\u202f19, TypeScript e React Query."
    limpo = sanitizar_texto_para_pdf(texto_com_quadrado)
    assert "\u2011" not in limpo
    assert "\u202f" not in limpo
    assert "full-stack" in limpo
    assert "React 19" in limpo

def test_fullstack_pipeline_end_to_end():
    perfil = main.carregar_perfil_base()
    
    descricao_vaga = """
    Vaga: Desenvolvedor(a) Full Stack Junior
    Empresa: Startup Inovadora
    Modalidade: Remoto
    Requisitos:
    - Experiência com React e TypeScript
    - Conhecimento em bancos relacionais (PostgreSQL)
    - Testes unitários com Vitest
    - Boas práticas de versionamento (Git)
    """
    
    analise = adaptar_curriculo(descricao_vaga, perfil)
    assert isinstance(analise, dict)
    assert analise.get("match_score", 0) >= 70
    
    # Verifica assertividade na curadoria de experiências
    assert "experiencias_selecionadas" in analise
    exps = analise["experiencias_selecionadas"]
    assert 1 <= len(exps) <= 4, f"Esperado entre 1 e 4 experiências assertivas, obteve {len(exps)}"
    for exp in exps:
        detalhes = exp.get("detalhes", [])
        assert len(detalhes) <= 5, f"Esperado no máximo 5 detalhes assertivos por experiência, obteve {len(detalhes)}"
    
    resumo = analise.get("resumo_adaptado", "")
    assert "\u2011" not in resumo
    assert "\u202f" not in resumo
    
    with tempfile.TemporaryDirectory() as td:
        pdf_path = os.path.join(td, "test_cv.pdf")
        gerar_pdf_curriculo(perfil, analise, pdf_path)
        assert os.path.exists(pdf_path)
        assert os.path.getsize(pdf_path) > 1000

if __name__ == "__main__":
    test_sanitization_fullstack()
    print("test_sanitization_fullstack PASSED!")
    test_fullstack_pipeline_end_to_end()
    print("test_fullstack_pipeline_end_to_end PASSED!")
