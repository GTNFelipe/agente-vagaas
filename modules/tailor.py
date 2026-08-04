import os
import json
import logging
import time
from typing import Dict, Any

try:
    from groq import Groq, RateLimitError
except ImportError:
    Groq = None
    RateLimitError = Exception

logger = logging.getLogger(__name__)

def adaptar_curriculo(descricao_vaga: str, perfil_json: dict) -> dict:
    """
    Usa a API da Groq para analisar a vaga e adequar o perfil profissional base, gerando também a cover letter.
    """
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        logger.warning("[AVISO] GROQ_API_KEY nao foi definida. Usando resposta fallback para execucao local de testes.")
        return _fallback_adaptacao(perfil_json, descricao_vaga)

    if Groq is None:
        raise ImportError("A biblioteca 'groq' nao esta instalada.")

    client = Groq(api_key=api_key)

    prompt = f"""
    Você é um especialista em Recrutamento, Seleção, Otimização de Currículos e Preparação para Entrevistas.

    PERFIL PROFISSIONAL BASE:
    {json.dumps(perfil_json, ensure_ascii=False, indent=2)}

    DESCRIÇÃO DA VAGA DE EMPREGO:
    {descricao_vaga}

    SUA TAREFA:
    1. Calcule uma pontuação de aderência (match_score de 0 a 100) entre o perfil base e a vaga.
    2. Escreva uma breve justificativa para a pontuação.
    3. Reescreva o resumo profissional (resumo_adaptado) de forma altamente personalizada para ESTA vaga específica. Destaque em 3 a 5 linhas as tecnologias, ferramentas, metodologias e experiências do perfil base que coincidem diretamente com os requisitos desta vaga, otimizando com as palavras-chave da vaga para passar em leitores ATS.
    4. Reordene e selecione as habilidades técnicas do perfil base mais relevantes para essa vaga.
    5. Escreva uma CARTA DE APRESENTAÇÃO profissional (cover_letter) curta, direta e convincente (máximo 3 parágrafos) em 1ª pessoa, pronta para ser enviada no corpo do e-mail ao recrutador.
    6. Crie um DOSSIÊ DE PREPARAÇÃO PARA ENTREVISTA (dossie_entrevista) contendo:
       - pontos_fortes: Principais trunfos factuais do candidato para destacar na entrevista.
       - perguntas_provaveis: 3 perguntas técnicas/comportamentais prováveis com respostas sugeridas baseadas na experiência real do perfil base.
       - perguntas_para_recrutador: 2 ou 3 perguntas estratégicas para o candidato fazer na entrevista.
       - pitch_elevador: Um resumo verbal convincente de 1 minuto para se apresentar no início da entrevista.
    7. REGRA RÍGIDA: NUNCA invente habilidades, empresas ou experiências que não estejam no perfil base.

    RETORNE ESTRITAMENTE UM JSON NO SEGUINTE FORMATO (Sem markdown em volta ou texto extra):
    {{
        "match_score": 85,
        "justificativa_match": "Explicação em uma frase",
        "resumo_adaptado": "Resumo profissional totalmente customizado e otimizado com palavras-chave desta vaga específica",
        "habilidades_destacadas": ["Skill 1", "Skill 2", "Skill 3"],
        "cover_letter": "Texto completo da carta de apresentação para o recrutador",
        "dossie_entrevista": {{
            "pontos_fortes": ["Ponto 1", "Ponto 2", "Ponto 3"],
            "perguntas_provaveis": [
                {{"pergunta": "Pergunta 1", "resposta_sugerida": "Resposta baseada na experiência real do perfil"}},
                {{"pergunta": "Pergunta 2", "resposta_sugerida": "Resposta baseada na experiência real do perfil"}},
                {{"pergunta": "Pergunta 3", "resposta_sugerida": "Resposta baseada na experiência real do perfil"}}
            ],
            "perguntas_para_recrutador": ["Pergunta 1", "Pergunta 2"],
            "pitch_elevador": "Apresentação pessoal de 1 minuto para o início da entrevista"
        }}
    }}
    """

    max_tentativas = 3
    tempo_espera = 15

    for tentativa in range(1, max_tentativas + 1):
        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except RateLimitError as e:
            if tentativa < max_tentativas:
                msg_aviso = f"⚠️ Limite de taxa da Groq atingido. Aguardando {tempo_espera}s para tentar novamente ({tentativa}/{max_tentativas})..."
                logger.warning(msg_aviso)
                print(msg_aviso)
                time.sleep(tempo_espera)
                tempo_espera += 10
            else:
                raise e

def _fallback_adaptacao(perfil_json: dict, descricao_vaga: str) -> dict:
    """Retorna uma estrutura fallback para execução de teste local sem a chave Groq."""
    return {
        "match_score": 85,
        "justificativa_match": "Forte correspondência técnica em Python, Docker, APIs REST, Postgres e automação com n8n.",
        "resumo_adaptado": perfil_json.get("resumo_profissional", ""),
        "habilidades_destacadas": [
            "Python / APIs REST",
            "Docker & Infraestrutura",
            "n8n & Automação de Processos",
            "PostgreSQL & Supabase",
            "Sistemas Backend & Mainframe (COBOL)"
        ],
        "cover_letter": "Prezado(a) Recrutador(a),\n\nTenho grande interesse na oportunidade. Possuo sólida experiência em desenvolvimento backend com Python, criação de APIs RESTful e automação de processos corporativos.\n\nFico à disposição para agendarmos uma conversa.\n\nAtenciosamente,\nFelipe Santana da Silva",
        "dossie_entrevista": {
            "pontos_fortes": [
                "Experiência prática na modernização de 62 programas COBOL/Mainframe no Bradesco.",
                "Criação de ecossistemas de automação com n8n e integração com APIs de IA.",
                "Domínio em infraestrutura Docker, Linux, Supabase e PostgreSQL."
            ],
            "perguntas_provaveis": [
                {
                    "pergunta": "Como você lida com sistemas legados e modernização de código?",
                    "resposta_sugerida": "Trabalhei refatorando rotinas COBOL e alterando layouts de dados sensíveis sob rigoroso controle ALM via Changeman no Bradesco."
                },
                {
                    "pergunta": "Qual sua experiência com automação de processos e IA?",
                    "resposta_sugerida": "Construí ecossistemas de consultoria automatizados integrando n8n, OpenAI API e bancos Postgres/Redis."
                }
            ],
            "perguntas_para_recrutador": [
                "Quais são os principais desafios técnicos da equipe nos próximos 6 meses?",
                "Qual é a stack de infraestrutura e esteira de CI/CD utilizada no dia a dia?"
            ],
            "pitch_elevador": "Sou desenvolvedor backend focado em arquitetura crítica e automação. Tenho vivência sólida em ambientes de alta disponibilidade como o Banco Bradesco e na criação de soluções inteligentes com Python, Java, COBOL e n8n."
        }
    }
