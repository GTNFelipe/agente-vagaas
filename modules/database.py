import os
import json
import re
import logging
from datetime import datetime
from typing import Optional, Any
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

try:
    from supabase import create_client, Client
except ImportError:
    Client = None
    create_client = None

LOCAL_DB_FILE = "vagas_processadas.json"

_SUPABASE_INSTANCE: Optional[Client] = None

def inicializar_supabase() -> Optional[Client]:
    global _SUPABASE_INSTANCE
    if _SUPABASE_INSTANCE is not None:
        return _SUPABASE_INSTANCE

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_file = os.path.join(base_dir, ".env")
    if os.path.exists(env_file):
        load_dotenv(dotenv_path=env_file, override=True)
    else:
        load_dotenv(override=True)

    raw_url = os.getenv("SUPABASE_URL", "")
    raw_key = os.getenv("SUPABASE_KEY", "")

    # Higieniza espaços, aspas simples/duplas acidentais
    url = raw_url.strip().strip('"').strip("'")
    key = raw_key.strip().strip('"').strip("'")

    if url and not (url.startswith("http://") or url.startswith("https://")):
        url = f"https://{url}"

    if not url or not key or create_client is None:
        logger.warning("SUPABASE_URL ou SUPABASE_KEY nao encontradas nas variaveis de ambiente.")
        return None
    try:
        _SUPABASE_INSTANCE = create_client(url, key)
        return _SUPABASE_INSTANCE
    except Exception as e:
        logger.exception("Falha ao conectar no Supabase")
        return None

def _carregar_vagas_locais() -> list:
    if os.path.exists(LOCAL_DB_FILE):
        try:
            with open(LOCAL_DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            logger.exception("Erro ao carregar cache local de vagas")
            return []
    return []

def _salvar_vagas_locais(vagas: list):
    try:
        with open(LOCAL_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(vagas, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.exception("Nao foi possivel salvar cache local de vagas")

def _normalizar_string(s: str) -> str:
    if not s:
        return ""
    s = s.lower().strip()
    return re.sub(r'\s+', ' ', s)

def _normalizar_url(url: str) -> str:
    if not url:
        return ""
    url = url.split("?")[0].rstrip("/")
    return url.lower().strip()

def vaga_ja_processada(supabase: Optional[Client], vaga_or_link: Any) -> bool:
    """
    Verifica se a vaga já foi registrada ou candidatada anteriormente.
    Consulta tanto o arquivo local (vagas_processadas.json) quanto o Supabase.
    """
    if isinstance(vaga_or_link, dict):
        link = vaga_or_link.get("link", "") or ""
        titulo = vaga_or_link.get("titulo", "") or ""
        empresa = vaga_or_link.get("empresa", "") or ""
    else:
        link = str(vaga_or_link) if vaga_or_link else ""
        titulo = ""
        empresa = ""

    norm_link = _normalizar_url(link)
    norm_titulo = _normalizar_string(titulo)
    norm_empresa = _normalizar_string(empresa)

    # 1. Checar no cache local (vagas_processadas.json)
    vagas_locais = _carregar_vagas_locais()
    for item in vagas_locais:
        item_link = _normalizar_url(item.get("link_vaga") or item.get("link", ""))
        item_titulo = _normalizar_string(item.get("titulo_vaga") or item.get("titulo", ""))
        item_empresa = _normalizar_string(item.get("empresa", ""))

        if norm_link and item_link and norm_link == item_link:
            return True
        if norm_titulo and norm_empresa and norm_titulo == item_titulo and norm_empresa == item_empresa:
            return True
        if norm_titulo and norm_titulo == item_titulo and (not norm_empresa or norm_empresa == "portal remotar / web"):
            return True

    # 2. Checar no Supabase (vagas_processadas e vagas)
    if supabase:
        try:
            if link:
                clean_link = link.split("?")[0].rstrip("/")
                res_link = supabase.table("vagas_processadas").select("id").ilike("link_vaga", f"%{clean_link}%").execute()
                if res_link.data and len(res_link.data) > 0:
                    return True

            if titulo:
                # Checa por título exato (insensível a maiúsculas/minúsculas) em vagas_processadas
                res_title = supabase.table("vagas_processadas").select("id").ilike("titulo_vaga", titulo.strip()).execute()
                if res_title.data and len(res_title.data) > 0:
                    return True

                # Checa por título na tabela vagas base
                res_vagas = supabase.table("vagas").select("id").ilike("titulo", titulo.strip()).execute()
                if res_vagas.data and len(res_vagas.data) > 0:
                    return True
        except Exception as e:
            logger.exception("Erro ao verificar duplicata no Supabase")

    return False

def salvar_vaga_base(supabase: Optional[Client], vaga_data: dict, match_score: int, status: str = "ENCONTRADA") -> Optional[str]:
    """
    Registra a vaga na tabela 'vagas' do Supabase e retorna o ID UUID gerado.
    """
    if not supabase:
        return None

    registro = {
        "titulo": vaga_data.get("titulo"),
        "empresa": vaga_data.get("empresa"),
        "link": vaga_data.get("link"),
        "descricao": vaga_data.get("descricao", ""),
        "match_score": match_score,
        "status": status
    }

    try:
        res = supabase.table("vagas").insert(registro).execute()
        if res.data and len(res.data) > 0:
            vaga_id = res.data[0].get("id")
            logger.info("Vaga salva na tabela 'vagas' Supabase (ID: %s)!", vaga_id)
            return vaga_id
    except Exception as e:
        logger.exception("Erro ao salvar na tabela 'vagas'")
        try:
            if vaga_data.get("link"):
                res_exist = supabase.table("vagas").select("id").eq("link", vaga_data.get("link")).execute()
                if res_exist.data and len(res_exist.data) > 0:
                    exist_id = res_exist.data[0].get("id")
                    logger.info("ID de vaga existente utilizado: %s", exist_id)
                    return exist_id
        except Exception:
            pass
    return None

def salvar_vaga_processada(supabase: Optional[Client], vaga_data: dict, analise_ia: dict, status_candidatura: str = "alerta_manual") -> Optional[str]:
    """
    Registra o histórico da análise na tabela 'vagas_processadas' do Supabase.
    """
    registro_supabase = {
        "titulo_vaga": vaga_data.get("titulo"),
        "empresa": vaga_data.get("empresa"),
        "link_vaga": vaga_data.get("link"),
        "match_score": analise_ia.get("match_score"),
        "justificativa": analise_ia.get("justificativa_match"),
        "resumo_adaptado": analise_ia.get("resumo_adaptado"),
        "status_candidatura": status_candidatura
    }

    registro_local = dict(registro_supabase)
    registro_local["criado_em"] = datetime.now().isoformat()

    # 1. Salvar no cache local
    vagas_locais = _carregar_vagas_locais()
    link_reg = _normalizar_url(registro_supabase.get("link_vaga", ""))
    tit_reg = _normalizar_string(registro_supabase.get("titulo_vaga", ""))
    emp_reg = _normalizar_string(registro_supabase.get("empresa", ""))

    ja_existe_local = False
    for v in vagas_locais:
        v_link = _normalizar_url(v.get("link_vaga", ""))
        v_tit = _normalizar_string(v.get("titulo_vaga", ""))
        v_emp = _normalizar_string(v.get("empresa", ""))
        if (link_reg and v_link == link_reg) or (tit_reg and emp_reg and v_tit == tit_reg and v_emp == emp_reg):
            ja_existe_local = True
            break

    if not ja_existe_local:
        vagas_locais.append(registro_local)
        _salvar_vagas_locais(vagas_locais)

    # 2. Salvar no Supabase
    if supabase:
        try:
            res = supabase.table("vagas_processadas").insert(registro_supabase).execute()
            logger.info("Vaga '%s' salva em 'vagas_processadas' Supabase!", vaga_data.get('titulo'))
            if res.data and len(res.data) > 0:
                return res.data[0].get("id")
        except Exception as e:
            logger.exception("Erro ao salvar em 'vagas_processadas'")
    else:
        logger.info("Supabase nao conectado. Vaga '%s' registrada localmente em 'vagas_processadas.json'.", vaga_data.get('titulo'))
    return None

def salvar_curriculo_gerado(supabase: Optional[Client], vaga_id: Optional[str], pdf_path: str, analise_ia: dict) -> Optional[str]:
    """
    Registra o currículo otimizado na tabela 'curriculos_gerados' do Supabase.
    """
    if not supabase or not vaga_id:
        return None

    registro = {
        "vaga_id": vaga_id,
        "pdf_url": pdf_path,
        "conteudo_json": analise_ia
    }

    try:
        res = supabase.table("curriculos_gerados").insert(registro).execute()
        if res.data and len(res.data) > 0:
            cg_id = res.data[0].get("id")
            logger.info("Currículo registrado na tabela 'curriculos_gerados' Supabase (ID: %s)!", cg_id)
            return cg_id
    except Exception as e:
        logger.exception("Erro ao salvar em 'curriculos_gerados'")
    return None

def salvar_dossie_entrevista(supabase: Optional[Client], vaga_id: Optional[str], analise_ia: dict) -> Optional[str]:
    """
    Registra o dossiê de entrevista na tabela 'prep_dossies' do Supabase.
    """
    if not supabase or not vaga_id:
        return None

    dossie_data = analise_ia.get("dossie_entrevista", {})
    resumo_empresa = analise_ia.get("justificativa_match") or analise_ia.get("resumo_adaptado") or ""

    registro = {
        "vaga_id": vaga_id,
        "resumo_empresa": resumo_empresa,
        "perguntas_sugeridas": dossie_data
    }

    try:
        res = supabase.table("prep_dossies").insert(registro).execute()
        if res.data and len(res.data) > 0:
            pd_id = res.data[0].get("id")
            logger.info("Dossiê registrado na tabela 'prep_dossies' Supabase (ID: %s)!", pd_id)
            return pd_id
    except Exception as e:
        logger.exception("Erro ao salvar em 'prep_dossies'")
    return None
