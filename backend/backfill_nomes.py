"""
Script único de backfill: preenche nome_emissor em faturas onde ficou NULL
devido a falhas/rate-limit da API NIF.pt.
"""

import time
from services.supabase_client import _client
from services.nif_service import get_nome_emissor

# 1. Buscar todas as faturas sem nome_emissor
response = (
    _client.table("faturas")
    .select("id, nif_emissor")
    .is_("nome_emissor", "null")
    .execute()
)
faturas_pendentes = response.data
print(f"Faturas a corrigir: {len(faturas_pendentes)}")

# 2. Agrupar por NIF único para poupar pedidos à API
nifs_unicos = {f["nif_emissor"] for f in faturas_pendentes}
cache_nomes: dict[str, str | None] = {}

for nif in nifs_unicos:
    nome = get_nome_emissor(nif)
    cache_nomes[nif] = nome
    print(f"NIF {nif} -> {nome}")
    time.sleep(65)  # respeita o rate limit do NIF.pt — ajusta se ainda vires 429/erros

# 3. Atualizar cada fatura com o nome correspondente
atualizadas = 0
for fatura in faturas_pendentes:
    nome = cache_nomes.get(fatura["nif_emissor"])
    if nome:
        _client.table("faturas").update({"nome_emissor": nome}).eq("id", fatura["id"]).execute()
        atualizadas += 1

print(f"Faturas atualizadas: {atualizadas} de {len(faturas_pendentes)}")