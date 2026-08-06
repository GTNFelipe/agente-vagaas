import os
import re
from datetime import datetime

def gerar_arquivo_carta_apresentacao(vaga_info: dict, analise_ia: dict, perfil_base: dict, output_dir: str = "cartas_apresentacao") -> str:
    """
    Gera um arquivo formatado (.txt / .md) da Carta de Apresentação de Alto Impacto para a vaga.
    """
    os.makedirs(output_dir, exist_ok=True)

    titulo = vaga_info.get("titulo", "Vaga_Desconhecida")
    empresa = vaga_info.get("empresa", "Empresa_Desconhecida")
    clean_title = (re.sub(r'[^\w\-_]', '_', str(titulo)).strip("_")[:35]) or "Vaga"
    clean_empresa = (re.sub(r'[^\w\-_]', '_', str(empresa)).strip("_")[:30]) or "Empresa"
    nome_arquivo = f"Carta_Apresentacao_{clean_title}_{clean_empresa}.txt"
    caminho_arquivo = os.path.join(output_dir, nome_arquivo)

    contato = perfil_base.get("contato", {}) if perfil_base else {}
    nome = perfil_base.get("nome", "Candidato") if perfil_base else "Candidato"
    email = contato.get("email", "")
    phone = contato.get("phone", "")
    linkedin = contato.get("linkedin", "")
    github = contato.get("github", "")
    localizacao = perfil_base.get("localizacao", "") if perfil_base else ""

    carta_texto = analise_ia.get("cover_letter", "")

    conteudo_completo = f"""================================================================================
CARTA DE APRESENTAÇÃO PROFISSIONAL
Candidato: {nome}
Cargo Alvo: {vaga_info.get('titulo')}
Empresa: {vaga_info.get('empresa')}
Data: {datetime.now().strftime('%d/%m/%Y')}
Contatos: {email} | Tel: {phone} | {localizacao}
LinkedIn: {linkedin} | GitHub: {github}
================================================================================

Prezado(a) Recrutador(a) / Equipe de Seleção da {vaga_info.get('empresa')},

{carta_texto}

Atenciosamente,
{nome}
{perfil_base.get('cargo_atual', 'Trainee TI / Desenvolvedor Backend')}
{email} | {phone}
"""

    with open(caminho_arquivo, "w", encoding="utf-8") as f:
        f.write(conteudo_completo)

    print(f"[CARTA] Carta de Apresentação salva em: '{caminho_arquivo}'")
    return caminho_arquivo
