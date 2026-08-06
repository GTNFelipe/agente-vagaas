import sys
import os
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv()

from modules.scraper import (
    buscar_vagas_google_jobs,
    buscar_vagas_rss_feed,
    buscar_vagas_programathor,
    buscar_vagas_github_repos,
    eh_cargo_e_nivel_permitido,
    eh_vaga_publico_geral,
    eh_candidatura_gratuita,
    eh_vaga_no_brasil,
    eh_vaga_remota_ou_rj
)

query_unificada = "(COBOL OR Mainframe OR Java OR n8n OR 'Analista de Sistemas' OR 'Desenvolvedor') Brasil (remoto OR 'rio de janeiro')"

print("=== 1. TESTANDO GOOGLE JOBS (SerpAPI) ===")
v_google = buscar_vagas_google_jobs(query=query_unificada)
print(f"Retornadas Google Jobs: {len(v_google)}")
for v in v_google[:5]:
    ok = (eh_cargo_e_nivel_permitido(v) and 
          eh_vaga_publico_geral(v) and 
          eh_candidatura_gratuita(v) and 
          eh_vaga_no_brasil(v) and 
          eh_vaga_remota_ou_rj(v))
    print(f"  - [{v.get('empresa')}] {v.get('titulo')} | Passa: {ok}")

print("\n=== 2. TESTANDO PROGRAMATHOR ===")
v_prog = buscar_vagas_programathor()
print(f"Retornadas Programathor: {len(v_prog)}")
for v in v_prog[:5]:
    ok = (eh_cargo_e_nivel_permitido(v) and 
          eh_vaga_publico_geral(v) and 
          eh_candidatura_gratuita(v) and 
          eh_vaga_no_brasil(v) and 
          eh_vaga_remota_ou_rj(v))
    print(f"  - [{v.get('empresa')}] {v.get('titulo')} | Passa: {ok}")

print("\n=== 3. TESTANDO GITHUB REPOS ===")
v_gh = buscar_vagas_github_repos()
print(f"Retornadas GitHub Repos: {len(v_gh)}")
for v in v_gh[:5]:
    ok = (eh_cargo_e_nivel_permitido(v) and 
          eh_vaga_publico_geral(v) and 
          eh_candidatura_gratuita(v) and 
          eh_vaga_no_brasil(v) and 
          eh_vaga_remota_ou_rj(v))
    print(f"  - [{v.get('empresa')}] {v.get('titulo')} | Passa: {ok}")
