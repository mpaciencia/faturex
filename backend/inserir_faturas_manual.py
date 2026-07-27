"""
Script para inserir manualmente faturas com QR danificado no Supabase.

Pede os dados essenciais de cada fatura e insere diretamente na BD.
Usa a service role key, portanto ignora RLS.

Utilização:
    venv\Scripts\python inserir_faturas_manual.py
"""

import sys
import time
from decimal import Decimal, InvalidOperation

from services.supabase_client import _client, insert_fatura
from services.nif_service import get_nome_emissor
from models.schemas import CATEGORIAS_VALIDAS

USER_ID = "7dbf3a36-d767-4164-816a-89e5000b0a66"

CATEGORIAS_LISTA = sorted(CATEGORIAS_VALIDAS)


def pedir_dados_fatura(n: int) -> dict | None:
    """Pede os dados de uma fatura ao utilizador via input interativo."""
    print(f"\n{'='*60}")
    print(f"  FATURA {n}")
    print(f"{'='*60}")
    print("(Escreve 'sair' em qualquer campo para terminar)\n")

    # ATCUD
    atcud = input("ATCUD (ex: ABCD1234-123): ").strip()
    if atcud.lower() == "sair":
        return None

    # NIF emissor
    nif_emissor = input("NIF do emissor (9 dígitos): ").strip()
    if nif_emissor.lower() == "sair":
        return None
    if not nif_emissor.isdigit() or len(nif_emissor) != 9:
        print(f"⚠ NIF inválido: '{nif_emissor}'. Deve ter 9 dígitos.")
        continuar = input("Continuar mesmo assim? (s/n): ").strip().lower()
        if continuar != "s":
            return None

    # Data da fatura
    data_fatura = input("Data da fatura (YYYY-MM-DD, ex: 2026-07-15): ").strip()
    if data_fatura.lower() == "sair":
        return None

    # Valor total
    valor_total_str = input("Valor total (com IVA, ex: 45.90): ").strip()
    if valor_total_str.lower() == "sair":
        return None
    try:
        valor_total = Decimal(valor_total_str)
    except InvalidOperation:
        print(f"⚠ Valor inválido: '{valor_total_str}'")
        return None

    # IVA total
    imposto_str = input("IVA total (ex: 8.63): ").strip()
    if imposto_str.lower() == "sair":
        return None
    try:
        imposto_total = Decimal(imposto_str)
    except InvalidOperation:
        print(f"⚠ Valor de IVA inválido: '{imposto_str}'")
        return None

    # Tipo
    tipo = input("Tipo (Despesa/Receita) [Despesa]: ").strip() or "Despesa"

    # Categoria
    print("\nCategorias disponíveis:")
    for i, cat in enumerate(CATEGORIAS_LISTA, 1):
        print(f"  {i}. {cat}")
    cat_input = input("Número da categoria (ou texto livre): ").strip()
    try:
        cat_idx = int(cat_input)
        if 1 <= cat_idx <= len(CATEGORIAS_LISTA):
            categoria = CATEGORIAS_LISTA[cat_idx - 1]
        else:
            categoria = "Outros"
    except ValueError:
        categoria = cat_input if cat_input else "Outros"

    # Observações
    observacoes = input("Observações (Enter para vazio): ").strip() or None

    # Nome emissor (tentar via API)
    print(f"\n🔍 A procurar nome do emissor para NIF {nif_emissor}...")
    try:
        nome_emissor = get_nome_emissor(nif_emissor)
        if nome_emissor:
            print(f"✅ Nome encontrado: {nome_emissor}")
        else:
            print("⚠ Nome não encontrado via API.")
            nome_emissor = input("Nome do emissor (manual, Enter para vazio): ").strip() or None
    except Exception as e:
        print(f"⚠ Erro ao consultar API NIF: {e}")
        nome_emissor = input("Nome do emissor (manual, Enter para vazio): ").strip() or None

    return {
        "atcud": atcud,
        "nif_emissor": nif_emissor,
        "data_fatura": data_fatura,
        "valor_total": str(valor_total),
        "imposto_total": str(imposto_total),
        "tipo": tipo,
        "categoria": categoria,
        "nome_emissor": nome_emissor,
        "observacoes": observacoes,
        "raw_qr_string": f"QR_DANIFICADO_{atcud}",
        "url_documento": "manual://sem-documento",
        "origem": "Mobile",
    }


def main():
    print("\n" + "=" * 60)
    print("  INSERÇÃO MANUAL DE FATURAS — FatureX")
    print("  (Para faturas com QR Code danificado)")
    print("=" * 60)
    print(f"\nUser ID: {USER_ID}")
    print(f"Serão inseridas na tabela 'faturas' do Supabase.\n")

    num_faturas = input("Quantas faturas queres inserir? [5]: ").strip()
    num_faturas = int(num_faturas) if num_faturas.isdigit() else 5

    inseridas = 0

    for i in range(1, num_faturas + 1):
        dados = pedir_dados_fatura(i)

        if dados is None:
            print("\n⏹ Inserção cancelada pelo utilizador.")
            break

        # Confirmar antes de inserir
        print(f"\n📋 Resumo da fatura {i}:")
        print(f"   ATCUD:      {dados['atcud']}")
        print(f"   NIF:        {dados['nif_emissor']}")
        print(f"   Emissor:    {dados['nome_emissor'] or '(não definido)'}")
        print(f"   Data:       {dados['data_fatura']}")
        print(f"   Total:      €{dados['valor_total']}")
        print(f"   IVA:        €{dados['imposto_total']}")
        print(f"   Tipo:       {dados['tipo']}")
        print(f"   Categoria:  {dados['categoria']}")
        print(f"   Observações: {dados['observacoes'] or '(vazio)'}")

        confirmar = input("\n✅ Inserir esta fatura? (s/n): ").strip().lower()
        if confirmar != "s":
            print("⏭ Fatura ignorada.")
            continue

        try:
            registo = insert_fatura(dados, USER_ID)
            print(f"🎉 Fatura inserida com sucesso! ID: {registo['id']}")
            inseridas += 1
        except Exception as e:
            print(f"❌ Erro ao inserir fatura: {e}")

        # Pausa entre faturas para evitar rate limits do NIF.pt
        if i < num_faturas:
            time.sleep(1.5)

    print(f"\n{'='*60}")
    print(f"  CONCLUÍDO: {inseridas} fatura(s) inserida(s) com sucesso.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
