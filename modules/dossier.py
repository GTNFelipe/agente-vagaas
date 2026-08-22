import os
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def gerar_dossie_vaga(vaga_info: dict, analise_ia: dict, output_dir: str = "dossies_vagas") -> str:
    """
    Gera um Dossiê completo de Preparação para Entrevista em formato Markdown (.md)
    com base nas análises e insights da IA sobre a vaga.
    """
    os.makedirs(output_dir, exist_ok=True)

    titulo = vaga_info.get("titulo", "Vaga_Desconhecida")
    empresa = vaga_info.get("empresa", "Empresa_Desconhecida")
    clean_title = (re.sub(r'[^\w\-_]', '_', str(titulo)).strip("_")[:35]) or "Vaga"
    clean_empresa = (re.sub(r'[^\w\-_]', '_', str(empresa)).strip("_")[:30]) or "Empresa"
    nome_arquivo = f"Dossie_{clean_title}_{clean_empresa}.md"
    caminho_arquivo = os.path.join(output_dir, nome_arquivo)

    dossie_data = analise_ia.get("dossie_entrevista", {})
    pontos_fortes = dossie_data.get("pontos_fortes", [])
    perguntas_provaveis = dossie_data.get("perguntas_provaveis", [])
    perguntas_recrutador = dossie_data.get("perguntas_para_recrutador", [])
    pitch = dossie_data.get("pitch_elevador", "")

    conteudo_md = f"""# 📋 Dossiê de Preparação para Entrevista

**Cargo:** {vaga_info.get('titulo')}
**Empresa:** {vaga_info.get('empresa')}
**Score de Aderência (Match):** {analise_ia.get('match_score')}%
**Link da Vaga:** {vaga_info.get('link')}
**Data da Análise:** {datetime.now().strftime('%d/%m/%Y %H:%M')}

---

## 🎯 Justificativa do Match
{analise_ia.get('justificativa_match', 'N/A')}

---

## 🎙️ Pitch de Apresentação (1 Minuto)
> "{pitch or 'Apresente sua trajetória destacando sua experiência prática em backend, COBOL/Mainframe, Java e automações n8n/IA Generativa.'}"

---

## 💪 Pontos Fortes a Destacar na Entrevista
"""
    for pf in pontos_fortes:
        conteudo_md += f"- {pf}\n"

    conteudo_md += "\n---\n\n## ❓ Perguntas Prováveis & Respostas Sugeridas\n\n"
    for i, item in enumerate(perguntas_provaveis, 1):
        if isinstance(item, dict):
            pergunta = item.get("pergunta", "")
            resposta = item.get("resposta_sugerida", "")
        else:
            pergunta = str(item)
            resposta = "Responda utilizando sua experiência prática factual registrada no perfil."
        conteudo_md += f"### {i}. {pergunta}\n**💡 Resposta Recomendada:** {resposta}\n\n"

    conteudo_md += "---\n\n## 💡 Perguntas Estratégicas para Fazer ao Recrutador\n\n"
    for pr in perguntas_recrutador:
        conteudo_md += f"- {pr}\n"

    conteudo_md += "\n---\n\n## 📝 Resumo Profissional Otimizado para ATS\n"
    conteudo_md += f"{analise_ia.get('resumo_adaptado', '')}\n"

    conteudo_md += "\n---\n\n## ✉️ Carta de Apresentação Gerada\n"
    conteudo_md += f"{analise_ia.get('cover_letter', '')}\n"

    with open(caminho_arquivo, "w", encoding="utf-8") as f:
        f.write(conteudo_md)

    logger.info("[DOSSIÊ] Dossiê de entrevista gerado com sucesso: '%s'", caminho_arquivo)
    return caminho_arquivo
