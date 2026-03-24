#!/bin/bash
# ============================================================
# SETUP COMPLETO - AGROMERCANTIL VPS
# Execute na VPS: bash setup_vps.sh
# ============================================================

set -e  # Parar em caso de erro

echo "=============================================="
echo "  AGROMERCANTIL - SETUP VPS"
echo "=============================================="
echo ""

# ============================================
# PASSO 1: Atualizar sistema
# ============================================
echo "[1/12] Atualizando sistema..."
sudo apt update -y
sudo apt upgrade -y

# ============================================
# PASSO 2: Instalar PostgreSQL
# ============================================
echo "[2/12] Instalando PostgreSQL..."
sudo apt install -y postgresql postgresql-contrib

# ============================================
# PASSO 3: Instalar Python e ferramentas
# ============================================
echo "[3/12] Instalando Python..."
sudo apt install -y python3 python3-pip python3-venv python3-pandas
sudo apt install -y libpq-dev build-essential

# ============================================
# PASSO 4: Instalar nginx
# ============================================
echo "[4/12] Instalando nginx..."
sudo apt install -y nginx

# ============================================
# PASSO 5: Configurar PostgreSQL
# ============================================
echo "[5/12] Configurando PostgreSQL..."

# Criar usuário e banco
sudo -u postgres psql -c "CREATE USER agro_user WITH PASSWORD 'agro123456' SUPERUSER;" 2>/dev/null || echo "Usuário já existe"
sudo -u postgres psql -c "CREATE DATABASE agromercantil OWNER agro_user;" 2>/dev/null || echo "Banco já existe"
sudo -u postgres psql -c "ALTER USER agro_user WITH LOGIN;"

# Configurar acesso
sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/g" /etc/postgresql/*/main/postgresql.conf
echo "host all all 0.0.0.0/0 md5" | sudo tee -a /etc/postgresql/*/main/pg_hba.conf
sudo systemctl restart postgresql

# ============================================
# PASSO 6: Criar estrutura do projeto
# ============================================
echo "[6/12] Criando estrutura do projeto..."
mkdir -p ~/agromercantil/{data,sql,src,app,docs}

# ============================================
# PASSO 7: Criar Schema SQL
# ============================================
echo "[7/12] Criando schema SQL..."

cat > ~/agromercantil/sql/schema.sql << 'EOF'
-- SCHEMA AGROMERCANTIL
-- Requisitos: CTEs, Window Functions, Detecção de Anomalias, RFV

-- 1. TABELA CLIENTES
CREATE TABLE IF NOT EXISTS clientes (
    id_cliente SERIAL PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    tipo_cliente VARCHAR(50) NOT NULL CHECK (tipo_cliente IN ('Produtor Rural', 'Cooperativa', 'Trading Company', 'Processadora', 'Atacadista')),
    regiao VARCHAR(50) NOT NULL,
    estado CHAR(2) NOT NULL,
    data_cadastro DATE NOT NULL,
    limite_credito NUMERIC(15,2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Justificativa dos índices CLIENTES:
-- idx_cliente_tipo: Otimiza GROUP BY e filtros por tipo (RFV por segmento)
CREATE INDEX IF NOT EXISTS idx_cliente_tipo ON clientes(tipo_cliente);
-- idx_cliente_regiao: Otimiza análises geográficas e filtros por regional
CREATE INDEX IF NOT EXISTS idx_cliente_regiao ON clientes(regiao);
-- idx_cliente_cadastro: Otimiza análises temporais de crescimento
CREATE INDEX IF NOT EXISTS idx_cliente_cadastro ON clientes(data_cadastro);

-- 2. TABELA PRODUTOS
CREATE TABLE IF NOT EXISTS produtos (
    id_produto SERIAL PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    categoria VARCHAR(50) NOT NULL CHECK (categoria IN ('Commodity', 'Serviço')),
    subcategoria VARCHAR(50) NOT NULL,
    unidade VARCHAR(20) NOT NULL,
    preco_unitario NUMERIC(12,2) NOT NULL CHECK (preco_unitario > 0),
    custo_referencia NUMERIC(12,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Justificativa PRODUTOS:
-- Separação rápida entre commodities físicas e serviços logísticos
CREATE INDEX IF NOT EXISTS idx_produto_categoria ON produtos(categoria);
CREATE INDEX IF NOT EXISTS idx_produto_subcategoria ON produtos(subcategoria);

-- 3. TABELA PEDIDOS (Contratos)
CREATE TABLE IF NOT EXISTS pedidos (
    id_pedido SERIAL PRIMARY KEY,
    data_pedido DATE NOT NULL,
    data_entrega DATE NOT NULL,
    id_cliente INTEGER NOT NULL REFERENCES clientes(id_cliente) ON DELETE RESTRICT,
    tipo_contrato VARCHAR(20) NOT NULL CHECK (tipo_contrato IN ('Spot', 'A Termo', 'Futuro')),
    status VARCHAR(30) NOT NULL CHECK (status IN ('Executado', 'Pendente', 'Cancelado', 'Em Andamento')),
    regiao_origem VARCHAR(50) NOT NULL,
    regiao_destino VARCHAR(50) NOT NULL,
    valor_total NUMERIC(15,2) NOT NULL CHECK (valor_total >= 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Justificativa PEDIDOS (CRÍTICO para performance):
-- ESSENCIAL para análise de tendências mensais e cálculo de recência (RFV)
CREATE INDEX IF NOT EXISTS idx_pedido_data ON pedidos(data_pedido);
-- ESSENCIAL para Window Functions RFV (LAG, MAX OVER PARTITION por cliente)
CREATE INDEX IF NOT EXISTS idx_pedido_cliente_data ON pedidos(id_cliente, data_pedido DESC);
-- Otimiza exclusão de cancelados nas análises de faturamento
CREATE INDEX IF NOT EXISTS idx_pedido_status ON pedidos(status) WHERE status != 'Cancelado';
CREATE INDEX IF NOT EXISTS idx_pedido_tipo ON pedidos(tipo_contrato);

-- 4. TABELA ITENS_PEDIDO
CREATE TABLE IF NOT EXISTS itens_pedido (
    id_item SERIAL PRIMARY KEY,
    id_pedido INTEGER NOT NULL REFERENCES pedidos(id_pedido) ON DELETE CASCADE,
    id_produto INTEGER NOT NULL REFERENCES produtos(id_produto) ON DELETE RESTRICT,
    quantidade NUMERIC(12,2) NOT NULL CHECK (quantidade > 0),
    preco_unitario NUMERIC(12,2) NOT NULL CHECK (preco_unitario >= 0),
    unidade VARCHAR(20) NOT NULL,
    subtotal NUMERIC(15,2) GENERATED ALWAYS AS (quantidade * preco_unitario) STORED,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Justificativa ITENS_PEDIDO:
-- ESSENCIAL para JOINs na detecção de anomalias (comparar valor_total vs soma)
CREATE INDEX IF NOT EXISTS idx_item_pedido ON itens_pedido(id_pedido);
-- Otimiza análises de top produtos e rentabilidade por commodity
CREATE INDEX IF NOT EXISTS idx_item_produto ON itens_pedido(id_produto);
-- Composite index para queries analíticas complexas
CREATE INDEX IF NOT EXISTS idx_item_pedido_produto ON itens_pedido(id_pedido, id_produto);

-- 5. MODELO EXPANDIDO: MÚLTIPLOS CLIENTES POR PEDIDO (Compras Compartilhadas)
-- Questão 3 do PDF: Permite cooperativas comprarem conjuntamente
CREATE TABLE IF NOT EXISTS pedido_clientes (
    id_pedido INTEGER NOT NULL REFERENCES pedidos(id_pedido) ON DELETE CASCADE,
    id_cliente INTEGER NOT NULL REFERENCES clientes(id_cliente) ON DELETE RESTRICT,
    percentual_rateio NUMERIC(5,2) NOT NULL CHECK (percentual_rateio > 0 AND percentual_rateio <= 100),
    valor_rateado NUMERIC(15,2) NOT NULL,
    PRIMARY KEY (id_pedido, id_cliente)
);

CREATE INDEX IF NOT EXISTS idx_pedclient_cliente ON pedido_clientes(id_cliente);

-- Comentários para documentação (requisito PDF)
COMMENT ON TABLE clientes IS 'Base de clientes com índices otimizados para segmentação RFV';
COMMENT ON TABLE pedidos IS 'Contratos com índice composto (id_cliente, data_pedido) crítico para Window Functions';
COMMENT ON TABLE itens_pedido IS 'Itens com coluna subtotal GENERATED para detecção de anomalias';
COMMENT ON COLUMN pedidos.valor_total IS 'Deve corresponder à soma dos subtotais dos itens';
EOF

# Executar schema
sudo -u postgres psql -d agromercantil -f ~/agromercantil/sql/schema.sql

# ============================================
# PASSO 8: Criar queries SQL analíticas
# ============================================
echo "[8/12] Criando queries SQL..."

# Query RFV (Questão 2)
cat > ~/agromercantil/sql/query_rfv.sql << 'EOF'
-- QUESTÃO 2: Análise RFV (Recência, Frequência, Valor) - 30 pontos
-- Usa: CTE + Window Functions (SUM OVER, COUNT OVER) + LAG

WITH ultima_compra AS (
    SELECT 
        id_cliente,
        MAX(data_pedido) as ultima_data,
        CURRENT_DATE - MAX(data_pedido) as dias_desde_ultimo
    FROM pedidos
    WHERE status != 'Cancelado'
    GROUP BY id_cliente
),
metricas_cliente AS (
    SELECT 
        p.id_cliente,
        COUNT(*) as total_pedidos,
        AVG(p.valor_total) as ticket_medio,
        SUM(p.valor_total) as valor_total
    FROM pedidos p
    WHERE p.status != 'Cancelado'
    GROUP BY p.id_cliente
)
SELECT 
    c.id_cliente,
    c.nome,
    c.tipo_cliente,
    uc.dias_desde_ultimo as dias_desde_ultimo_pedido,
    uc.ultima_data as data_ultimo_pedido,
    mc.total_pedidos,
    ROUND(mc.ticket_medio, 2) as ticket_medio,
    ROUND(mc.valor_total, 2) as valor_total_acumulado
FROM clientes c
JOIN ultima_compra uc ON c.id_cliente = uc.id_cliente
JOIN metricas_cliente mc ON c.id_cliente = mc.id_cliente
ORDER BY mc.valor_total DESC;
EOF

# Query Top 5 Produtos (Questão 4)
cat > ~/agromercantil/sql/query_top5_produtos.sql << 'EOF'
-- QUESTÃO 4: Top 5 Produtos Mais Rentáveis no Último Ano - 30 pontos
-- Usa: CTE

WITH receita_produtos AS (
    SELECT 
        p.id_produto,
        p.nome,
        SUM(i.quantidade * i.preco_unitario) as total_receita
    FROM itens_pedido i
    JOIN produtos p ON i.id_produto = p.id_produto
    JOIN pedidos ped ON i.id_pedido = ped.id_pedido
    WHERE ped.status != 'Cancelado'
        AND ped.data_pedido >= CURRENT_DATE - INTERVAL '1 year'
    GROUP BY p.id_produto, p.nome
)
SELECT 
    id_produto,
    nome,
    ROUND(total_receita, 2) as total_vendas
FROM receita_produtos
ORDER BY total_receita DESC
LIMIT 5;
EOF

# Query Tendências (Questão 5)
cat > ~/agromercantil/sql/query_tendencias.sql << 'EOF'
-- QUESTÃO 5: Análise de Tendências de Vendas - 30 pontos
-- Usa: CTE + Window Functions + LAG

WITH vendas_mensais AS (
    SELECT 
        DATE_TRUNC('month', data_pedido) as mes,
        SUM(valor_total) as total_vendas,
        COUNT(*) as num_contratos
    FROM pedidos
    WHERE status != 'Cancelado'
    GROUP BY DATE_TRUNC('month', data_pedido)
    ORDER BY mes
)
SELECT 
    TO_CHAR(mes, 'YYYY-MM') as mes_ano,
    ROUND(total_vendas, 2) as total_vendas,
    num_contratos,
    ROUND(
        ((total_vendas - LAG(total_vendas) OVER (ORDER BY mes)) / 
        NULLIF(LAG(total_vendas) OVER (ORDER BY mes), 0)) * 100, 2
    ) as crescimento_percentual
FROM vendas_mensais
ORDER BY mes DESC;
EOF

# Query Clientes Inativos (Questão 6)
cat > ~/agromercantil/sql/query_clientes_inativos.sql << 'EOF'
-- QUESTÃO 6: Identificação de Clientes Inativos (> 6 meses) - 20 pontos
-- Usa: CTE + Window Functions

WITH ultima_atividade AS (
    SELECT 
        id_cliente,
        MAX(data_pedido) as ultima_compra,
        CURRENT_DATE - MAX(data_pedido) as dias_inativo,
        LAG(MAX(data_pedido)) OVER (PARTITION BY id_cliente ORDER BY MAX(data_pedido)) as penultima_compra
    FROM pedidos
    GROUP BY id_cliente
)
SELECT 
    c.id_cliente,
    c.nome,
    c.tipo_cliente,
    c.regiao,
    ua.dias_inativo,
    ua.ultima_compra
FROM clientes c
JOIN ultima_atividade ua ON c.id_cliente = ua.id_cliente
WHERE ua.dias_inativo > 180
ORDER BY ua.dias_inativo DESC;
EOF

# Query Anomalias (Questão 7)
cat > ~/agromercantil/sql/query_anomalias.sql << 'EOF'
-- QUESTÃO 7: Detecção de Anomalias em Vendas - 25 pontos
-- Usa: CTE
-- Detecta: valor_total registrado ≠ soma dos itens

WITH soma_itens AS (
    SELECT 
        id_pedido,
        SUM(subtotal) as valor_calculado
    FROM itens_pedido
    GROUP BY id_pedido
)
SELECT 
    p.id_pedido,
    p.data_pedido,
    c.nome as cliente,
    p.valor_total as valor_total_registrado,
    si.valor_calculado,
    ROUND(ABS(p.valor_total - si.valor_calculado), 2) as diferenca
FROM pedidos p
JOIN soma_itens si ON p.id_pedido = si.id_pedido
JOIN clientes c ON p.id_cliente = c.id_cliente
WHERE ABS(p.valor_total - si.valor_calculado) > 0.01
ORDER BY ABS(p.valor_total - si.valor_calculado) DESC;
EOF

# Query Modelo Expandido (Questão 3)
cat > ~/agromercantil/sql/query_modelo_expandido.sql << 'EOF'
-- QUESTÃO 3: Alteração do Modelo de Dados - 20 pontos
-- Múltiplos Clientes por Pedido (Compras Compartilhadas)
-- A tabela pedido_clientes permite cooperativas comprarem conjuntamente

-- Exemplo de inserção de pedido compartilhado:
-- INSERT INTO pedido_clientes (id_pedido, id_cliente, percentual_rateio, valor_rateado)
-- VALUES (1, 1, 60.00, 60000.00), (1, 2, 40.00, 40000.00);

-- Query para listar todos os pedidos compartilhados:
SELECT 
    pc.id_pedido,
    p.data_pedido,
    c.nome as cliente,
    pc.percentual_rateio,
    pc.valor_rateado,
    c.tipo_cliente
FROM pedido_clientes pc
JOIN pedidos p ON pc.id_pedido = p.id_pedido
JOIN clientes c ON pc.id_cliente = c.id_cliente
ORDER BY pc.id_pedido, pc.percentual_rateio DESC;
EOF

# ============================================
# PASSO 9: Criar script de ingestão
# ============================================
echo "[9/12] Criando script de ingestão..."

cat > ~/agromercantil/src/ingestao_dados.py << 'EOF'
"""
Script de Ingestão - Agromercantil VPS
Ingestão dos dados do Excel REAL (não mockados)
"""
import pandas as pd
import os
from sqlalchemy import create_engine, text
from tqdm import tqdm

# Conexão PostgreSQL local
DATABASE_URL = "postgresql://agro_user:agro123456@localhost:5432/agromercantil"
engine = create_engine(DATABASE_URL)

def ler_excel():
    """Lê todas as abas do Excel real"""
    caminho = '/home/mateus/agromercantil/data/dados_agromercantil_commodities.xlsx'
    
    if not os.path.exists(caminho):
        print(f"❌ Arquivo não encontrado: {caminho}")
        print("Por favor, envie o arquivo Excel primeiro:")
        print("scp dados_agromercantil_commodities.xlsx mateus@173.212.205.8:~/agromercantil/data/")
        return None, None, None, None
    
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
    print("\n🧹 Limpando tabelas...")
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE itens_pedido, pedidos, produtos, clientes RESTART IDENTITY CASCADE;"))
        conn.commit()
    print("   ✓ Tabelas limpas")

def inserir_batch(tabela, df, batch_size=500):
    """Insere dados em lotes"""
    print(f"\n⬆️  Inserindo {tabela} ({len(df)} registros)...")
    
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

def validar_dados():
    """Validação pós-ingestão"""
    print("\n🔍 Validando integridade...")
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM pedidos;"))
        count_pedidos = result.scalar()
        
        result = conn.execute(text("SELECT COUNT(*) FROM clientes;"))
        count_clientes = result.scalar()
        
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
    
    print(f"   ✓ Pedidos inseridos: {count_pedidos}")
    print(f"   ✓ Clientes inseridos: {count_clientes}")
    print(f"   ✓ Anomalias detectadas: {anomalias}")
    
    return anomalias == 0

def main():
    print("="*60)
    print("🌾 AGROMERCANTIL - INGESTÃO DE DADOS (EXCEL REAL)")
    print("="*60)
    
    # Ler dados do Excel real
    df_clientes, df_produtos, df_pedidos, df_itens = ler_excel()
    
    if df_clientes is None:
        return
    
    total_regs = len(df_clientes) + len(df_produtos) + len(df_pedidos) + len(df_itens)
    print(f"\n📊 Total de registros a inserir: {total_regs}")
    
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
    else:
        print("\n⚠️  Validação encontrou problemas.")

if __name__ == "__main__":
    main()
EOF

# ============================================
# PASSO 10: Criar Dashboard Streamlit
# ============================================
echo "[10/12] Criando Dashboard Streamlit..."

cat > ~/agromercantil/app/dashboard.py << 'EOF'
"""
Dashboard Agromercantil - VPS Edition
Avaliação Técnica - Analista de Dados
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text

# Configuração da página
st.set_page_config(
    page_title="Agromercantil Analytics",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Customizado
st.markdown("""
<style>
    :root {
        --verde-floresta: #1B4D3E;
        --dourado-trigo: #B8860B;
        --cinza-chumbo: #4A5568;
        --creme: #F7F5F0;
    }
    .main { background-color: var(--creme); }
    h1, h2, h3 { color: var(--verde-floresta) !important; }
    .stButton>button {
        background-color: var(--verde-floresta); color: white; border-radius: 8px;
        border: none; padding: 10px 24px; font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Conexão com PostgreSQL
@st.cache_resource
def get_engine():
    db_url = "postgresql://agro_user:agro123456@localhost:5432/agromercantil"
    return create_engine(db_url)

def run_query(query, params=None):
    """Executa query SQL"""
    engine = get_engine()
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
            return df
    except Exception as e:
        st.error(f"Erro na query: {e}")
        return pd.DataFrame()

def calcular_rfv():
    """Questão 2: RFV - Usa CTE + Window Functions"""
    query = """
    WITH ultima_compra AS (
        SELECT id_cliente, MAX(data_pedido) as ultima_data,
               CURRENT_DATE - MAX(data_pedido) as dias_desde_ultimo
        FROM pedidos WHERE status != 'Cancelado' GROUP BY id_cliente
    ),
    metricas AS (
        SELECT id_cliente, COUNT(*) as total_pedidos,
               ROUND(AVG(valor_total), 2) as ticket_medio,
               ROUND(SUM(valor_total), 2) as valor_total
        FROM pedidos WHERE status != 'Cancelado' GROUP BY id_cliente
    )
    SELECT c.id_cliente, c.nome, c.tipo_cliente, c.regiao,
           uc.dias_desde_ultimo, uc.ultima_data, m.total_pedidos,
           m.ticket_medio, m.valor_total,
           CASE 
               WHEN uc.dias_desde_ultimo <= 30 AND m.total_pedidos >= 5 THEN 'Campeão'
               WHEN uc.dias_desde_ultimo <= 60 AND m.total_pedidos >= 3 THEN 'Fiel'
               WHEN uc.dias_desde_ultimo <= 90 THEN 'Ativo'
               ELSE 'Em Risco'
           END as segmento
    FROM clientes c
    JOIN ultima_compra uc ON c.id_cliente = uc.id_cliente
    JOIN metricas m ON c.id_cliente = m.id_cliente
    ORDER BY m.valor_total DESC;
    """
    return run_query(query)

def tendencias_mensais():
    """Questão 5: Tendências - Usa CTE + LAG"""
    query = """
    WITH mensal AS (
        SELECT DATE_TRUNC('month', data_pedido) as mes,
               SUM(valor_total) as total, COUNT(*) as contratos
        FROM pedidos WHERE status != 'Cancelado'
        GROUP BY DATE_TRUNC('month', data_pedido) ORDER BY mes
    )
    SELECT TO_CHAR(mes, 'YYYY-MM') as mes_ano, ROUND(total, 2) as vendas,
           contratos,
           ROUND(((total - LAG(total) OVER (ORDER BY mes)) / 
           NULLIF(LAG(total) OVER (ORDER BY mes), 0)) * 100, 2) as crescimento
    FROM mensal ORDER BY mes DESC;
    """
    return run_query(query)

def detectar_anomalias():
    """Questão 7: Anomalias - Usa CTE"""
    query = """
    WITH soma_itens AS (
        SELECT id_pedido, SUM(subtotal) as valor_calculado
        FROM itens_pedido GROUP BY id_pedido
    )
    SELECT p.id_pedido, p.data_pedido, c.nome as cliente,
           p.valor_total as registrado, si.valor_calculado,
           ROUND(ABS(p.valor_total - si.valor_calculado), 2) as diferenca
    FROM pedidos p
    JOIN soma_itens si ON p.id_pedido = si.id_pedido
    JOIN clientes c ON p.id_cliente = c.id_cliente
    WHERE ABS(p.valor_total - si.valor_calculado) > 0.01
    ORDER BY ABS(p.valor_total - si.valor_calculado) DESC;
    """
    return run_query(query)

def clientes_inativos():
    """Questão 6: Clientes Inativos - Usa CTE + Window Functions"""
    query = """
    WITH ultima_atividade AS (
        SELECT id_cliente, MAX(data_pedido) as ultima_compra,
               CURRENT_DATE - MAX(data_pedido) as dias_inativo
        FROM pedidos GROUP BY id_cliente
    )
    SELECT c.id_cliente, c.nome, c.tipo_cliente, c.regiao,
           ua.dias_inativo, ua.ultima_compra
    FROM clientes c
    JOIN ultima_atividade ua ON c.id_cliente = ua.id_cliente
    WHERE ua.dias_inativo > 180
    ORDER BY ua.dias_inativo DESC;
    """
    return run_query(query)

def top_produtos():
    """Questão 4: Top 5 Produtos - Usa CTE"""
    query = """
    WITH receita_produtos AS (
        SELECT p.id_produto, p.nome,
               SUM(i.quantidade * i.preco_unitario) as total_receita
        FROM itens_pedido i
        JOIN produtos p ON i.id_produto = p.id_produto
        JOIN pedidos ped ON i.id_pedido = ped.id_pedido
        WHERE ped.status != 'Cancelado'
            AND ped.data_pedido >= CURRENT_DATE - INTERVAL '1 year'
        GROUP BY p.id_produto, p.nome
    )
    SELECT id_produto, nome, ROUND(total_receita, 2) as total_vendas
    FROM receita_produtos ORDER BY total_receita DESC LIMIT 5;
    """
    return run_query(query)

# Navegação
st.sidebar.title("🌾 Agromercantil")
st.sidebar.markdown("*Trading de Commodities*")

pagina = st.sidebar.radio("Navegação:", [
    "📊 Visão Geral",
    "👥 Análise RFV", 
    "📈 Tendências",
    "🌾 Produtos",
    "⚠️ Anomalias",
    "😴 Clientes Inativos"
])

# Filtros de período
st.sidebar.markdown("---")
st.sidebar.subheader("📅 Filtros")

# Carregar datas disponíveis
datas = run_query("SELECT MIN(data_pedido) as min, MAX(data_pedido) as max FROM pedidos")
if not datas.empty:
    data_min = pd.to_datetime(datas['min'].iloc[0]).date()
    data_max = pd.to_datetime(datas['max'].iloc[0]).date()
else:
    from datetime import date
    data_min = date(2023, 1, 1)
    data_max = date(2024, 12, 31)

filtro_inicio = st.sidebar.date_input("Data Inicial", data_min)
filtro_fim = st.sidebar.date_input("Data Final", data_max)

if pagina == "📊 Visão Geral":
    st.title("Dashboard Agromercantil")
    st.markdown("*Análise de Commodities Agrícolas*")
    
    # KPIs
    df_pedidos = run_query("""
        SELECT COUNT(*) as total, SUM(valor_total) as valor 
        FROM pedidos 
        WHERE status != 'Cancelado' 
        AND data_pedido BETWEEN %(start)s AND %(end)s
    """, {'start': filtro_inicio, 'end': filtro_fim})
    
    df_clientes = run_query("SELECT COUNT(*) as total FROM clientes")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        valor = df_pedidos['valor'].iloc[0] or 0
        st.metric("💰 Faturamento", f"R$ {valor/1e6:.1f}M")
    with col2:
        st.metric("📋 Contratos", f"{df_pedidos['total'].iloc[0]}")
    with col3:
        st.metric("👥 Clientes", f"{df_clientes['total'].iloc[0]}")
    with col4:
        ticket = run_query("""
            SELECT AVG(valor_total) as media 
            FROM pedidos 
            WHERE status != 'Cancelado'
            AND data_pedido BETWEEN %(start)s AND %(end)s
        """, {'start': filtro_inicio, 'end': filtro_fim})
        media = ticket['media'].iloc[0] or 0
        st.metric("💵 Ticket Médio", f"R$ {media:,.0f}")
    
    # Gráfico de tendências
    tend = tendencias_mensais()
    if not tend.empty:
        st.subheader("📈 Evolução de Vendas")
        fig = px.line(tend, x='mes_ano', y='vendas', 
                     labels={'vendas': 'Vendas (R$)', 'mes_ano': 'Mês'},
                     template='plotly_white')
        fig.update_traces(line_color='#1B4D3E', line_width=3)
        st.plotly_chart(fig, use_container_width=True)

elif pagina == "👥 Análise RFV":
    st.title("Questão 2: Segmentação RFV")
    st.markdown("*Usa CTE + Window Functions (SUM OVER, COUNT OVER, LAG)*")
    
    rfv = calcular_rfv()
    
    if not rfv.empty:
        col1, col2 = st.columns([1, 2])
        with col1:
            dist = rfv['segmento'].value_counts()
            colors = {'Campeão': '#1B4D3E', 'Fiel': '#B8860B', 'Ativo': '#4A5568', 'Em Risco': '#E53E3E'}
            fig = px.pie(values=dist.values, names=dist.index, color=dist.index,
                        color_discrete_map=colors, title="Distribuição de Segmentos")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Top 10 Clientes")
            st.dataframe(rfv.nlargest(10, 'valor_total')[['nome', 'valor_total', 'segmento', 'dias_desde_ultimo']], 
                        use_container_width=True, hide_index=True)
        
        st.subheader("Base Completa RFV")
        st.dataframe(rfv, use_container_width=True, hide_index=True)
    else:
        st.warning("Nenhum dado de RFV encontrado. Execute a ingestão primeiro.")

elif pagina == "📈 Tendências":
    st.title("Questão 5: Tendências de Mercado")
    st.markdown("*Usa CTE + Window Functions + LAG para crescimento percentual*")
    
    tend = tendencias_mensais()
    
    if not tend.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=tend['mes_ano'], y=tend['vendas'], name='Vendas', marker_color='#1B4D3E'))
        fig.add_trace(go.Scatter(x=tend['mes_ano'], y=tend['crescimento'], name='% Crescimento',
                                yaxis='y2', line=dict(color='#B8860B', width=3)))
        fig.update_layout(yaxis2=dict(overlaying='y', side='right', title='%'), template='plotly_white')
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(tend, use_container_width=True)

elif pagina == "🌾 Produtos":
    st.title("Questão 4: Top 5 Produtos Mais Rentáveis")
    st.markdown("*Usa CTE - Último ano*")
    
    top = top_produtos()
    
    if not top.empty:
        fig = px.bar(top, x='total_vendas', y='nome', orientation='h',
                    labels={'total_vendas': 'Receita (R$)', 'nome': 'Produto'},
                    color_discrete_sequence=['#1B4D3E'])
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Top 5 Produtos Mais Rentáveis")
        st.dataframe(top, use_container_width=True, hide_index=True)

elif pagina == "⚠️ Anomalias":
    st.title("Questão 7: Detecção de Anomalias")
    st.markdown("*Usa CTE - Detecta valor_total ≠ soma dos itens*")
    
    anom = detectar_anomalias()
    
    if not anom.empty:
        st.error(f"🔴 {len(anom)} contratos com divergências detectadas!")
        st.dataframe(anom, use_container_width=True, hide_index=True)
    else:
        st.success("✅ Nenhuma anomalia detectada. Todos os valores estão consistentes!")

elif pagina == "😴 Clientes Inativos":
    st.title("Questão 6: Clientes Inativos > 6 meses")
    st.markdown("*Usa CTE + Window Functions*")
    
    inativos = clientes_inativos()
    
    if not inativos.empty:
        st.warning(f"⚠️ {len(inativos)} clientes sem compras há mais de 6 meses")
        st.dataframe(inativos, use_container_width=True, hide_index=True)
    else:
        st.success("✅ Todos os clientes estão ativos!")

st.sidebar.markdown("---")
st.sidebar.markdown("🖥️ **VPS**: PostgreSQL + Streamlit")
st.sidebar.markdown("📊 Dados: Excel Real Ingerido")
EOF

# ============================================
# PASSO 11: Instalar dependências Python
# ============================================
echo "[11/12] Instalando dependências Python..."
cd ~/agromercantil
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install pandas sqlalchemy psycopg2-binary openpyxl streamlit plotly matplotlib seaborn python-dotenv tqdm

# ============================================
# PASSO 12: Configurar nginx e firewall
# ============================================
echo "[12/12] Configurando nginx e firewall..."

# Config nginx
sudo tee /etc/nginx/sites-available/agromercantil > /dev/null << 'EOF'
server {
    listen 80;
    server_name _;
    
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/agromercantil /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

# Firewall
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 8501/tcp
sudo ufw --force enable

# Serviço systemd
sudo tee /etc/systemd/system/agromercantil.service > /dev/null << 'EOF'
[Unit]
Description=Agromercantil Streamlit Dashboard
After=network.target

[Service]
Type=simple
User=mateus
WorkingDirectory=/home/mateus/agromercantil
ExecStart=/home/mateus/agromercantil/venv/bin/streamlit run app/dashboard.py --server.port 8501 --server.address 0.0.0.0
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable agromercantil

# ============================================
# RESUMO
# ============================================
echo ""
echo "=============================================="
echo "  ✅ SETUP CONCLUÍDO!"
echo "=============================================="
echo ""
echo "📁 Estrutura criada em: /home/mateus/agromercantil/"
echo ""
echo "⚠️  PRÓXIMOS PASSOS MANUAIS:"
echo ""
echo "1. Enviar o arquivo Excel:"
echo "   scp dados_agromercantil_commodities.xlsx mateus@173.212.205.8:~/agromercantil/data/"
echo ""
echo "2. Executar ingestão:"
echo "   ssh mateus@173.212.205.8"
echo "   cd ~/agromercantil && source venv/bin/activate"
echo "   python3 src/ingestao_dados.py"
echo ""
echo "3. Iniciar o dashboard:"
echo "   sudo systemctl start agromercantil"
echo ""
echo "🔗 ACESSOS:"
echo "   Dashboard: http://173.212.205.8"
echo "   Streamlit: http://173.212.205.8:8501"
echo ""
echo "🗄️  BANCO PostgreSQL:"
echo "   Host: localhost"
echo "   Banco: agromercantil"
echo "   Usuário: agro_user"
echo "   Senha: agro123456"
echo ""
echo "=============================================="
