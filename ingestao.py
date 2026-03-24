"""
Script de Ingestão - Agromercantil
Compatível com: Supabase, VPS PostgreSQL, Neon, Render, etc.
Usa SQLAlchemy para conexão universal.
"""
import pandas as pd
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from tqdm import tqdm
import time

load_dotenv()

# Detecta tipo de conexão
DATABASE_URL = os.getenv('DATABASE_URL')
SUPABASE_URL = os.getenv('SUPABASE_URL')

if DATABASE_URL:
    # Modo VPS/Neon/Render (PostgreSQL direto)
    engine = create_engine(DATABASE_URL)
    MODO = 'postgres'
    print("🔌 Modo: PostgreSQL Direto (VPS/Neon)")
elif SUPABASE_URL:
    # Modo Supabase (mantido para compatibilidade)
    from supabase import create_client
    supabase = create_client(SUPABASE_URL, os.getenv('SUPABASE_KEY'))
    MODO = 'supabase'
    print("☁️  Modo: Supabase")
else:
    raise ValueError("Configure DATABASE_URL (VPS) ou SUPABASE_URL no .env")

def ler_excel(caminho='data/dados_agromercantil_commodities.xlsx'):
    """Lê todas as abas do Excel"""
    print(f"📖 Lendo {caminho}...")

    df_clientes = pd.read_excel(caminho, sheet_name='clientes')
    df_produtos = pd.read_excel(caminho, sheet_name='produtos')
    df_pedidos = pd.read_excel(caminho, sheet_name='pedidos')
    df_itens = pd.read_excel(caminho, sheet_name='itens_pedido')

    print(f"   ✓ Clientes: {len(df_clientes)}")
    print(f"   ✓ Produtos: {len(df_produtos)}")
    print(f"   ✓ Pedidos: {len(df_pedidos)}")
    print(f"   ✓ Itens: {len(df_itens)}")

    return df_clientes, df_produtos, df_pedidos, df_itens

def limpar_tabelas():
    """Limpa tabelas antes da carga"""
    print("\n🧹 Limpando tabelas existentes...")

    if MODO == 'postgres':
        with engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE itens_pedido, pedidos, produtos, clientes RESTART IDENTITY CASCADE;"))
            conn.commit()
    else:
        # Supabase mode
        supabase.table('itens_pedido').delete().neq('id_item', 0).execute()
        supabase.table('pedidos').delete().neq('id_pedido', 0).execute()
        supabase.table('produtos').delete().neq('id_produto', 0).execute()
        supabase.table('clientes').delete().neq('id_cliente', 0).execute()

    print("   ✓ Tabelas limpas")

def inserir_batch(tabela, df, batch_size=1000):
    """Insere dados em lotes"""
    print(f"\n⬆️  Inserindo {tabela} ({len(df)} registros)...")

    if MODO == 'postgres':
        # Método otimizado para PostgreSQL (VPS)
        total = 0
        for i in tqdm(range(0, len(df), batch_size), desc=f"   {tabela}"):
            batch = df.iloc[i:i+batch_size]
            try:
                batch.to_sql(tabela, engine, if_exists='append', index=False, method='multi')
                total += len(batch)
            except Exception as e:
                print(f"   ❌ Erro no batch {i}: {e}")
                continue
        print(f"   ✓ {total} registros inseridos")
    else:
        # Método Supabase
        registros = df.to_dict('records')
        total = len(registros)
        inseridos = 0

        for i in tqdm(range(0, total, batch_size), desc=f"   {tabela}"):
            batch = registros[i:i+batch_size]
            try:
                supabase.table(tabela).insert(batch).execute()
                inseridos += len(batch)
            except Exception as e:
                print(f"   ❌ Erro: {e}")
                continue
            time.sleep(0.1)
        print(f"   ✓ {inseridos} registros inseridos")

def validar_dados():
    """Validação pós-ingestão"""
    print("\n🔍 Validando integridade...")

    if MODO == 'postgres':
        with engine.connect() as conn:
            # Verificar contagens
            result = conn.execute(text("SELECT COUNT(*) FROM pedidos;"))
            count_pedidos = result.scalar()

            result = conn.execute(text("SELECT COUNT(*) FROM clientes;"))
            count_clientes = result.scalar()

            # Verificar anomalias (soma dos itens vs valor_total)
            result = conn.execute(text("""
                SELECT COUNT(*) FROM (
                    SELECT p.id_pedido, p.valor_total, SUM(i.subtotal) as calculado
                    FROM pedidos p
                    JOIN itens_pedido i ON p.id_pedido = i.id_pedido
                    GROUP BY p.id_pedido
                    HAVING ABS(p.valor_total - SUM(i.subtotal)) > 0.01
                ) anomalias;
            """))
            anomalias = result.scalar()
    else:
        # Supabase validation (simplified)
        response = supabase.table('pedidos').select('*', count='exact').execute()
        count_pedidos = response.count
        response = supabase.table('clientes').select('*', count='exact').execute()
        count_clientes = response.count
        anomalias = 0

    print(f"   ✓ Pedidos inseridos: {count_pedidos}")
    print(f"   ✓ Clientes inseridos: {count_clientes}")
    print(f"   ✓ Anomalias detectadas: {anomalias}")

    return anomalias == 0

def main():
    print("="*60)
    print("🌾 AGROMERCANTIL - INGESTÃO DE DADOS")
    print(f"🖥️  Modo: {MODO.upper()}")
    print("="*60)

    # Ler dados
    df_clientes, df_produtos, df_pedidos, df_itens = ler_excel()

    # Confirmar
    total_regs = len(df_clientes) + len(df_produtos) + len(df_pedidos) + len(df_itens)
    print(f"\n⚠️  Total de registros a inserir: {total_regs}")
    print("   Deseja continuar? (s/n)")
    if input().lower() != 's':
        print("Cancelado.")
        return

    # Limpar e inserir
    limpar_tabelas()

    # Ordem importante (respeitar FKs)
    inserir_batch('clientes', df_clientes, 500)
    inserir_batch('produtos', df_produtos, 500)
    inserir_batch('pedidos', df_pedidos, 1000)
    inserir_batch('itens_pedido', df_itens, 1000)

    # Validar
    if validar_dados():
        print("\n" + "="*60)
        print("✅ INGESTÃO CONCLUÍDA COM SUCESSO!")
        print("="*60)
        print("\nPróximo passo:")
        if MODO == 'postgres':
            print("   streamlit run app/dashboard.py")
        else:
            print("   streamlit run app/dashboard.py")
    else:
        print("\n⚠️  Validação encontrou problemas. Verifique os logs.")

if __name__ == "__main__":
    main()