import json
import os
import sys
import re
import time
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from modules.scraper import coletar_vagas_todas_fontes, vaga_ainda_ativa, extrair_email_profundo
from modules.tailor import adaptar_curriculo
from modules.pdf_generator import gerar_pdf_curriculo
from modules.dossier import gerar_dossie_vaga
from modules.cover_letter import gerar_arquivo_carta_apresentacao
from modules.database import (
    inicializar_supabase,
    vaga_ja_processada,
    salvar_vaga_base,
    salvar_vaga_processada,
    salvar_curriculo_gerado,
    salvar_dossie_entrevista
)
from modules.notifier import realizar_candidatura_auto_email, enviar_notificacao_vaga

load_dotenv()

def carregar_perfil_base() -> dict:
    if os.environ.get("MASTER_PROFILE_JSON"):
        return json.loads(os.environ["MASTER_PROFILE_JSON"])
    if os.path.exists("master_profile.json"):
        with open("master_profile.json", "r", encoding="utf-8") as f:
            return json.load(f)
    raise FileNotFoundError("Perfil mestre não encontrado. Defina a variável MASTER_PROFILE_JSON ou crie o arquivo master_profile.json.")


def extrair_email_texto(texto: str) -> str:
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', texto)
    return emails[0] if emails else None

def main():
    print("[INICIO] Executando Agente de Vagas & Candidatura Autonoma (Fase 3)...")
    
    perfil_base = carregar_perfil_base()
    cargos_alvo = perfil_base.get("cargos_alvo", ["Desenvolvedor COBOL", "Desenvolvedor Java Junior"])
    supabase_client = inicializar_supabase()

    # 1. Coleta Vagas na Web
    vagas_encontradas = coletar_vagas_todas_fontes(cargos_alvo)

    if not vagas_encontradas:
        print("[INFO] Nenhuma vaga nova nesta rodada.")
        return

    # 2. Processamento
    for vaga in vagas_encontradas:
        link = vaga.get("link")
        titulo = vaga.get("titulo")

        if vaga_ja_processada(supabase_client, vaga):
            print(f"[SKIP] Vaga ja registrada/candidatada: '{titulo}' ({vaga.get('empresa')}). Pulando...")
            continue

        # Validação de status em tempo real na web
        if link and not vaga_ainda_ativa(link):
            print(f"[SKIP] Vaga ENCERRADA ou Inativa na web: '{titulo}' ({vaga.get('empresa')}). Pulando...")
            salvar_vaga_processada(supabase_client, vaga, {"match_score": 0, "justificativa_match": "Vaga encerrada ou inativa na web"}, status_candidatura="encerrada")
            continue

        print(f"\n[VAGA] Analisando: {titulo} - {vaga.get('empresa')}")
        analise = adaptar_curriculo(vaga.get("descricao", titulo), perfil_base)
        match_score = analise.get("match_score", 0)
        print(f"[SCORE] Score de Match: {match_score}%")

        if match_score >= 80:
            clean_empresa = (re.sub(r'[^\w\-_]', '_', str(vaga.get("empresa", "Empresa"))).strip("_")[:30]) or "Empresa"
            
            # 1. Gerar e SALVAR o PDF do Currículo Otimizado em pasta dedicada
            pasta_cvs = "curriculos_gerados"
            os.makedirs(pasta_cvs, exist_ok=True)
            nome_candidato_clean = (re.sub(r'[^\w\-_]', '_', str(perfil_base.get("nome", "Candidato"))).strip("_")[:30]) or "Candidato"
            nome_arquivo_pdf = f"CV_{nome_candidato_clean}_{clean_empresa}.pdf"
            caminho_pdf = os.path.join(pasta_cvs, nome_arquivo_pdf)
            gerar_pdf_curriculo(perfil_base, analise, output_filename=caminho_pdf)

            # 2. Gerar e SALVAR o Dossiê de Preparação para Entrevista
            caminho_dossie = gerar_dossie_vaga(vaga, analise)

            # 3. Gerar e SALVAR a Carta de Apresentação Profissional
            caminho_carta = gerar_arquivo_carta_apresentacao(vaga, analise, perfil_base)

            # 4. Registrar na tabela 'vagas' no Supabase para obter vaga_id (UUID)
            vaga_id = salvar_vaga_base(supabase_client, vaga, match_score, status="QUALIFICADA")

            # 5. Registrar na tabela 'curriculos_gerados' no Supabase
            salvar_curriculo_gerado(supabase_client, vaga_id, caminho_pdf, analise)

            # 6. Registrar na tabela 'prep_dossies' no Supabase
            salvar_dossie_entrevista(supabase_client, vaga_id, analise)

            email_recrutador = extrair_email_texto(vaga.get("descricao", ""))
            
            # Se não encontrou e-mail no resumo -> Executa o SCRAPING PROFUNDO na página web oficial da vaga!
            if not email_recrutador and vaga.get("link"):
                print(f"[DEEP SCRAPING] Investigando e-mail de RH na página original: {vaga.get('link')}...")
                email_recrutador = extrair_email_profundo(vaga.get("link"))

            status_envio = "alerta_manual"

            # Se encontrou e-mail de recrutador -> APLICA AUTOMÁTICO!
            if email_recrutador:
                vaga["email_candidatura"] = email_recrutador
                print(f"[AUTO-APPLY] E-mail de recrutador identificado ({email_recrutador}). Executando Auto-Apply...")
                sucesso_apply = realizar_candidatura_auto_email(vaga, analise, caminho_pdf)
                if sucesso_apply:
                    status_envio = "candidatado_auto"

            # Envia cópia / alerta para o desenvolvedor anexando o CV, Dossiê e Carta
            enviar_notificacao_vaga(
                vaga_info=vaga,
                analise_ia=analise,
                caminho_pdf=caminho_pdf,
                caminho_dossie=caminho_dossie,
                caminho_carta=caminho_carta,
                modo_candidatura=("auto" if status_envio == "candidatado_auto" else "manual")
            )

            # Registra na tabela 'vagas_processadas' do Supabase e cache local
            salvar_vaga_processada(supabase_client, vaga, analise, status_candidatura=status_envio)

            # Limpeza automática: Deleta os arquivos temporários após envio (mantendo salvos 100% no Supabase)
            for temp_file in [caminho_pdf, caminho_dossie, caminho_carta]:
                if temp_file and os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception as e:
                        print(f"[AVISO] Erro ao remover arquivo temporario ({temp_file}): {e}")
        else:
            print(f"[INFO] Vaga descartada (Score {match_score}% < 80%).")
            salvar_vaga_processada(supabase_client, vaga, analise, status_candidatura="descartado")

        time.sleep(20)

    print("\n[SUCESSO] Execucao completa finalizada com sucesso!")

if __name__ == "__main__":
    main()
