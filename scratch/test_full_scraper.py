import os
import sys
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv()

from modules.scraper import coletar_vagas_todas_fontes

vagas = coletar_vagas_todas_fontes([])
print(f"\n==========================================")
print(f"TOTAL DE VAGAS FILTRADAS E QUALIFICADAS DE TODAS AS FONTES: {len(vagas)}")
print(f"==========================================")

by_source = {}
for v in vagas:
    f = v.get("fonte", "Outros")
    by_source[f] = by_source.get(f, 0) + 1
    print(f" - [{f}] {v.get('titulo')} | Empresa: {v.get('empresa')}")

print(f"\nResumo de Vagas Aprovadas por Fonte: {by_source}")
