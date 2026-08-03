import os
from typing import Optional

try:
    from supabase import create_client, Client
except ImportError:
    Client = None
    create_client = None

def inicializar_supabase() -> Optional[Client]:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key or create_client is None:
        return None
    try:
        return create_client(url, key)
    except Exception:
        return None

def vaga_ja_processada(supabase: Optional[Client], link_vaga: str) -> bool:
    """
    Verifica no Supabase se o link da vaga já foi analisado anteriormente.
    """
    if not supabase or not link_vaga:
        return False

    try:
        res = supabase.table("vagas_processadas").select("id").eq("link_vaga", link_vaga).execute()
        return len(res.data) > 0
    except Exception as e:
        print(f"[AVISO] Erro ao verificar duplicata no Supabase: {e}")
        return False

def salvar_vaga_processada(supabase: Optional[Client], vaga_data: dict, analise_ia: dict, status_candidatura: str = "alerta_manual"):
    if not supabase:
        print("[AVISO] Supabase nao configurado. Ignorando persistencia em banco.")
        return

    registro = {
        "titulo_vaga": vaga_data.get("titulo"),
        "empresa": vaga_data.get("empresa"),
        "link_vaga": vaga_data.get("link"),
        "match_score": analise_ia.get("match_score"),
        "justificativa": analise_ia.get("justificativa_match"),
        "resumo_adaptado": analise_ia.get("resumo_adaptado"),
        "status_candidatura": status_candidatura
    }

    try:
        supabase.table("vagas_processadas").insert(registro).execute()
        print(f"[SUCESSO] Vaga '{vaga_data.get('titulo')}' salva no Supabase (Status: {status_candidatura})!")
    except Exception as e:
        print(f"[ERRO] Erro ao salvar no Supabase: {e}")

# Aliases para compatibilidade
get_supabase_client = inicializar_supabase
def save_job_record(job_title: str, company: str, job_description: str, tailored_data: dict) -> bool:
    client = inicializar_supabase()
    vaga_data = {"titulo": job_title, "empresa": company, "link": ""}
    salvar_vaga_processada(client, vaga_data, tailored_data)
    return client is not None
