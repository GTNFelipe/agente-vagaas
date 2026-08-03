import json
import os
import re
from dotenv import load_dotenv

from modules.scraper import coletar_vagas_todas_fontes
from modules.tailor import adaptar_curriculo
from modules.pdf_generator import gerar_pdf_curriculo
from modules.database import inicializar_supabase, vaga_ja_processada, salvar_vaga_processada
from modules.notifier import realizar_candidatura_auto_email, enviar_notificacao_vaga

load_dotenv()

def carregar_perfil_base() -> dict:
    with open("master_profile.json", "r", encoding="utf-8") as f:
        return json.load(f)

def extrair_email_texto(texto: str) -> str:
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', texto)
    return emails[0] if emails else None

def main():
    print("[INICIO] Executando Agente de Vagas & Candidatura Autonoma (Fase 3)...")
    
    perfil_base = carregar_perfil_base()
    cargos_alvo = perfil_base.get("cargos_alvo", ["Desenvolvedor Backend Python Junior"])
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

        if supabase_client and vaga_ja_processada(supabase_client, link):
            print(f"[SKIP] Vaga ja registrada: '{titulo}'. Pulando...")
            continue

        print(f"\n[VAGA] Analisando: {titulo} - {vaga.get('empresa')}")
        analise = adaptar_curriculo(vaga.get("descricao", titulo), perfil_base)
        match_score = analise.get("match_score", 0)
        print(f"[SCORE] Score de Match: {match_score}%")

        if match_score >= 80:
            clean_title = str(titulo).replace(' ', '_').replace('/', '_')
            nome_arquivo_pdf = f"CV_Felipe_Santana_{clean_title}_{match_score}.pdf"
            caminho_pdf = gerar_pdf_curriculo(perfil_base, analise, output_filename=nome_arquivo_pdf)

            email_recrutador = extrair_email_texto(vaga.get("descricao", ""))
            status_envio = "alerta_manual"

            # Se encontrou e-mail de recrutador -> APLICA AUTOMÁTICO!
            if email_recrutador:
                vaga["email_candidatura"] = email_recrutador
                print(f"[AUTO-APPLY] E-mail de recrutador identificado: {email_recrutador}. Executando Auto-Apply...")
                sucesso_apply = realizar_candidatura_auto_email(vaga, analise, caminho_pdf)
                if sucesso_apply:
                    status_envio = "candidatado_auto"

            # Envia cópia / alerta para o desenvolvedor
            enviar_notificacao_vaga(vaga, analise, caminho_pdf, modo_candidatura=("auto" if status_envio == "candidatado_auto" else "manual"))

            # Registra no Supabase com o status da candidatura
            salvar_vaga_processada(supabase_client, vaga, analise, status_candidatura=status_envio)

            if os.path.exists(caminho_pdf):
                os.remove(caminho_pdf)
        else:
            print(f"[INFO] Vaga descartada (Score {match_score}% < 80%).")
            salvar_vaga_processada(supabase_client, vaga, analise, status_candidatura="descartado")

    print("\n[SUCESSO] Execucao completa finalizada com sucesso!")

if __name__ == "__main__":
    main()
