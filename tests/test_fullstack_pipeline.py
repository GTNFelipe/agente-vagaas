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
    try:
        perfil = main.carregar_perfil_base()
    except (FileNotFoundError, ValueError):
        perfil = {
            "nome": "Felipe Santana da Silva",
            "cargo_atual": "Software Engineer",
            "localizacao": "Rio de Janeiro, RJ",
            "contato": {"email": "test@example.com", "phone": "123456789", "linkedin": "https://linkedin.com/in/test"},
            "resumo_profissional": "Engenheiro de Software com experiência em full-stack e backend com React 19, TypeScript, Vitest e NestJS.",
            "habilidades_tecnicas": {
                "linguagens": ["TypeScript", "JavaScript", "Python"],
                "frameworks": ["React", "Node.js", "NestJS"],
                "bancos": ["PostgreSQL", "Supabase"]
            },
            "experiencias": [
                {
                    "empresa": "FIRJAN SENAI (Instituto SENAI de Inovação - ISISVP)",
                    "cargo": "Bolsista Desenvolvedor Backend (NestJS, TypeScript & Prisma)",
                    "periodo": "09/2026 - Atual",
                    "detalhes": [
                        "Desenvolvimento de APIs RESTful com NestJS, Prisma 7 e PostgreSQL.",
                        "Configuração de esteira Docker com Alpine e Docker Compose.",
                        "Implementação de testes automatizados com Vitest."
                    ],
                    "tecnologias": ["NestJS", "TypeScript", "PostgreSQL", "Docker", "Vitest"]
                },
                {
                    "empresa": "Go Tech",
                    "cargo": "Desenvolvedor Full Stack Junior (React, TypeScript & Supabase)",
                    "periodo": "10/2026 - Atual",
                    "detalhes": [
                        "Desenvolvimento da plataforma Vertice ERP com React 19, TypeScript e Supabase.",
                        "Criação de componentes e testes unitários com Vitest."
                    ],
                    "tecnologias": ["React", "TypeScript", "Supabase", "Vitest"]
                }
            ],
            "formacao": [{"curso": "Engenharia de Software", "instituicao": "Faculdade", "conclusao": "2026"}]
        }
    
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
