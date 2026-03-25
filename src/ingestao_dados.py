#!/usr/bin/env python3
"""
Script de Ingestão de Dados - Agromercantil
Lê o Excel e popula o banco PostgreSQL com dados reais.

Correções aplicadas:
  1. Remove colunas GENERATED (subtotal) e auto-geradas (created_at) antes do INSERT
  2. Reseta sequences após ingestão com IDs explícitos
  3. Gera dados de pedido_clientes (compras compartilhadas)
"""

import pandas as pd
from sqlalchemy import create_engine, text
from tqdm import tqdm
import os
import random
from datetime import date

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    "postgresql://agro_user:agro123456@localhost:5432/agromercantil"
)
engine = create_engine(DATABASE_URL)

EXCEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'dados_agromercantil_commodities.xlsx')


# ─── LEITURA DO EXCEL ────────────────────────────────────────────────────────

def ler_excel():
    caminho = os.path.abspath(EXCEL_PATH)
    if not os.path.exists(caminho):
        print(f"[ERRO] Arquivo nao encontrado: {caminho}")
        return None, None, None, None

    print(f"[INFO] Lendo {caminho}...")
    df_clientes  = pd.read_excel(caminho, sheet_name='clientes')
    df_produtos  = pd.read_excel(caminho, sheet_name='produtos')
    df_pedidos   = pd.read_excel(caminho, sheet_name='pedidos')
    df_itens     = pd.read_excel(caminho, sheet_name='itens_pedido')

    print(f"[INFO] Clientes: {len(df_clientes)}, Produtos: {len(df_produtos)}, "
          f"Pedidos: {len(df_pedidos)}, Itens: {len(df_itens)}")
    return df_clientes, df_produtos, df_pedidos, df_itens


# ─── PREPARAÇÃO DOS DataFrames ────────────────────────────────────────────────

def preparar_dataframes(df_clientes, df_produtos, df_pedidos, df_itens):
    """
    Remove colunas que o PostgreSQL gerencia automaticamente:
      - 'subtotal' em itens_pedido -> coluna GENERATED ALWAYS (calculada pelo banco)
      - 'created_at' em todas -> DEFAULT CURRENT_TIMESTAMP (não precisa ser enviada)
    Também garante tipos corretos.
    """
    colunas_auto = ['created_at']

    # Colunas a remover por tabela
    df_clientes = df_clientes.drop(columns=[c for c in colunas_auto if c in df_clientes.columns])
    df_produtos = df_produtos.drop(columns=[c for c in colunas_auto if c in df_produtos.columns])
    df_pedidos  = df_pedidos.drop(columns=[c for c in colunas_auto  if c in df_pedidos.columns])

    # itens_pedido: remover subtotal (GENERATED ALWAYS) + created_at
    itens_remover = colunas_auto + ['subtotal']
    df_itens = df_itens.drop(columns=[c for c in itens_remover if c in df_itens.columns])

    # Converter datas para string ISO (evitar conflitos de timezone no pandas)
    for col in ['data_cadastro']:
        if col in df_clientes.columns:
            df_clientes[col] = pd.to_datetime(df_clientes[col]).dt.date

    for col in ['data_pedido', 'data_entrega']:
        if col in df_pedidos.columns:
            df_pedidos[col] = pd.to_datetime(df_pedidos[col]).dt.date

    return df_clientes, df_produtos, df_pedidos, df_itens


# ─── LIMPEZA ─────────────────────────────────────────────────────────────────

def limpar_tabelas():
    """Trunca todas as tabelas preservando a estrutura."""
    with engine.connect() as conn:
        conn.execute(text(
            "TRUNCATE TABLE pedido_clientes, itens_pedido, pedidos, produtos, clientes "
            "RESTART IDENTITY CASCADE;"
        ))
        conn.commit()
    print("[INFO] Tabelas limpas (TRUNCATE + RESTART IDENTITY)")


# ─── INSERÇÃO ────────────────────────────────────────────────────────────────

def inserir_batch(tabela, df, batch_size=500):
    """Insere DataFrame em lotes usando to_sql (append)."""
    total = len(df)
    print(f"[INFO] Inserindo {tabela} ({total} registros)...")
    for i in tqdm(range(0, total, batch_size), desc=tabela):
        batch = df.iloc[i:i+batch_size]
        batch.to_sql(tabela, engine, if_exists='append', index=False, method='multi')
    print(f"[OK] {tabela}: {total} registros inseridos")


# ─── RESET DE SEQUENCES ───────────────────────────────────────────────────────

def resetar_sequences():
    """
    Após INSERT com IDs explícitos, as sequences ficam em 1.
    Reseta para max(id) + 1 para evitar conflitos em novos inserts.
    """
    sequences = [
        ("clientes_id_cliente_seq",    "clientes",    "id_cliente"),
        ("produtos_id_produto_seq",    "produtos",    "id_produto"),
        ("pedidos_id_pedido_seq",      "pedidos",     "id_pedido"),
        ("itens_pedido_id_item_seq",   "itens_pedido","id_item"),
    ]
    with engine.connect() as conn:
        for seq_name, tabela, col in sequences:
            result = conn.execute(text(f"SELECT MAX({col}) FROM {tabela}"))
            max_id = result.scalar() or 0
            conn.execute(text(f"SELECT setval('{seq_name}', {max_id}, true)"))
        conn.commit()
    print("[OK] Sequences resetadas")


# ─── COMPRAS COMPARTILHADAS ───────────────────────────────────────────────────

def gerar_pedido_clientes(df_pedidos, df_clientes):
    """
    Simula compras compartilhadas para ~15% dos pedidos de maior valor.
    Lógica:
      - Seleciona o top 15% por valor_total
      - Para cada pedido selecionado, adiciona um segundo cliente da MESMA região
        como co-participante com percentual de rateio aleatório (20–40%)
      - O cliente principal fica com (100 - percentual_co) %
      - valor_rateado = valor_total * percentual / 100
    Justificativa: Cooperativas e trading companies do agronegócio frequentemente
    compartilham contratos de compra de commodities para diluir riscos e otimizar
    volumes, especialmente em regiões com forte presença cooperativista.
    """
    random.seed(42)

    # Top 15% por valor_total
    n_compartilhados = max(1, int(len(df_pedidos) * 0.15))
    pedidos_grandes = df_pedidos.nlargest(n_compartilhados, 'valor_total').copy()

    # Índice de clientes por região para facilitar lookup
    clientes_por_regiao = (
        df_clientes.groupby('regiao')['id_cliente']
        .apply(list)
        .to_dict()
    )

    registros = []

    for _, pedido in pedidos_grandes.iterrows():
        id_pedido    = int(pedido['id_pedido'])
        id_cliente1  = int(pedido['id_cliente'])
        valor_total  = float(pedido['valor_total'])

        # Região do cliente principal
        cliente_row  = df_clientes[df_clientes['id_cliente'] == id_cliente1]
        if cliente_row.empty:
            continue
        regiao = cliente_row.iloc[0]['regiao']

        # Candidatos da mesma região (excluindo o próprio)
        candidatos = [c for c in clientes_por_regiao.get(regiao, []) if c != id_cliente1]
        if not candidatos:
            candidatos = df_clientes[df_clientes['id_cliente'] != id_cliente1]['id_cliente'].tolist()
        if not candidatos:
            continue

        id_cliente2 = random.choice(candidatos)

        # Percentual do co-participante
        pct_co = round(random.uniform(20.0, 40.0), 2)
        pct_principal = round(100.0 - pct_co, 2)

        registros.append({
            'id_pedido':         id_pedido,
            'id_cliente':        id_cliente1,
            'percentual_rateio': pct_principal,
            'valor_rateado':     round(valor_total * pct_principal / 100, 2)
        })
        registros.append({
            'id_pedido':         id_pedido,
            'id_cliente':        id_cliente2,
            'percentual_rateio': pct_co,
            'valor_rateado':     round(valor_total * pct_co / 100, 2)
        })

    df_pc = pd.DataFrame(registros)
    print(f"[INFO] pedido_clientes: {len(df_pc)} registros gerados ({n_compartilhados} pedidos compartilhados)")
    return df_pc


# ─── VALIDAÇÃO PÓS-INGESTÃO ──────────────────────────────────────────────────

def validar_ingestao():
    """Verifica contagens após a carga."""
    tabelas = ['clientes', 'produtos', 'pedidos', 'itens_pedido', 'pedido_clientes']
    print("\n[VALIDAÇÃO] Contagens pós-ingestão:")
    with engine.connect() as conn:
        for t in tabelas:
            n = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
            print(f"  {t:<20} {n:>6} registros")
    print()


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    df_clientes, df_produtos, df_pedidos, df_itens = ler_excel()
    if df_clientes is None:
        return

    # Preparar (remover colunas geradas pelo banco)
    df_clientes, df_produtos, df_pedidos, df_itens = preparar_dataframes(
        df_clientes, df_produtos, df_pedidos, df_itens
    )

    # Gerar dados de compras compartilhadas ANTES de limpar (usa df_pedidos original)
    df_pc = gerar_pedido_clientes(df_pedidos, df_clientes)

    # Limpar tabelas
    limpar_tabelas()

    # Inserir na ordem correta (respeitar FKs)
    inserir_batch('clientes',    df_clientes, 500)
    inserir_batch('produtos',    df_produtos, 500)
    inserir_batch('pedidos',     df_pedidos,  1000)
    inserir_batch('itens_pedido', df_itens,   1000)
    inserir_batch('pedido_clientes', df_pc,   500)

    # Resetar sequences
    resetar_sequences()

    # Validar
    validar_ingestao()

    print("[CONCLUÍDO] Ingestão finalizada com sucesso!")


if __name__ == "__main__":
    main()
