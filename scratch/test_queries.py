import os
import sys
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv()

from modules.scraper import (
    buscar_vagas_google_jobs,
    eh_cargo_e_nivel_permitido,
    eh_vaga_publico_geral,
    eh_candidatura_gratuita,
    eh_vaga_no_brasil,
    eh_vaga_remota_ou_rj
)

queries = [
    'Desenvolvedor Java Junior Brasil',
    'Analista de Sistemas Junior Brasil',
    'Desenvolvedor COBOL Junior Brasil',
    'n8n automacao Brasil'
]

for q in queries:
    res = buscar_vagas_google_jobs(query=q)
    print(f"\nQuery '{q}' -> Retornou {len(res)} vagas no Google Jobs:")
    for v in res[:4]:
        ok = (eh_cargo_e_nivel_permitido(v) and 
              eh_vaga_publico_geral(v) and 
              eh_candidatura_gratuita(v) and 
              eh_vaga_no_brasil(v) and 
              eh_vaga_remota_ou_rj(v))
        print(f"   - [{v.get('empresa')}] {v.get('titulo')} | Passa Filtros: {ok}")
