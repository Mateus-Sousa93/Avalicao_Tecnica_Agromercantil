
-- ============================================================
-- SCHEMA AGROMERCANTIL - SUPABASE
-- Otimizado para análise de dados de commodities agrícolas
-- Requisitos: CTEs, Window Functions, Detecção de Anomalias, RFV
-- ============================================================

-- 1. TABELA CLIENTES
-- Justificativa: Base para análise RFV e segmentação geográfica
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

-- Índices CLIENTES:
-- idx_cliente_tipo: Otimiza GROUP BY e filtros por tipo (ex: análise de cooperativas vs produtores)
CREATE INDEX IF NOT EXISTS idx_cliente_tipo ON clientes(tipo_cliente);

-- idx_cliente_regiao: Otimiza análises geográficas e filtros por regional
CREATE INDEX IF NOT EXISTS idx_cliente_regiao ON clientes(regiao);

-- idx_cliente_cadastro: Otimiza análises de crescimento de base de clientes (window functions temporais)
CREATE INDEX IF NOT EXISTS idx_cliente_cadastro ON clientes(data_cadastro);


-- 2. TABELA PRODUTOS
-- Justificativa: Catálogo de commodities e serviços logísticos
CREATE TABLE IF NOT EXISTS produtos (
    id_produto SERIAL PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    categoria VARCHAR(50) NOT NULL CHECK (categoria IN ('Commodity', 'Serviço')),
    subcategoria VARCHAR(50) NOT NULL, -- Soja, Milho, Armazenagem, Frete...
    unidade VARCHAR(20) NOT NULL, -- saca 60kg, tonelada, contrato
    preco_unitario NUMERIC(12,2) NOT NULL CHECK (preco_unitario > 0),
    custo_referencia NUMERIC(12,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índices PRODUTOS:
-- idx_produto_categoria: Otimiza análises separando commodities físicas de serviços logísticos
CREATE INDEX IF NOT EXISTS idx_produto_categoria ON produtos(categoria);

-- idx_produto_subcategoria: Otimiza filtros por tipo específico de grão ou serviço
CREATE INDEX IF NOT EXISTS idx_produto_subcategoria ON produtos(subcategoria);


-- 3. TABELA PEDIDOS (Contratos)
-- Justificativa: Centro das análises temporais e financeiras
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

-- Índices PEDIDOS (Críticos para performance das consultas do PDF):

-- idx_pedido_data: ESSENCIAL para análise de tendências mensais e cálculo de recência (RFV)
-- Suporta DATE_TRUNC('month', data_pedido) e filtros temporais eficientes
CREATE INDEX IF NOT EXISTS idx_pedido_data ON pedidos(data_pedido);

-- idx_pedido_cliente_data: ESSENCIAL para Window Functions RFV (LAG, MAX OVER PARTITION)
-- Permite cálculos rápidos de dias desde último pedido e médias por cliente
CREATE INDEX IF NOT EXISTS idx_pedido_cliente_data ON pedidos(id_cliente, data_pedido DESC);

-- idx_pedido_status: Otimiza exclusão de cancelados nas análises de faturamento
CREATE INDEX IF NOT EXISTS idx_pedido_status ON pedidos(status) WHERE status != 'Cancelado';

-- idx_pedido_tipo: Otimiza análises comparativas Spot vs Futuro
CREATE INDEX IF NOT EXISTS idx_pedido_tipo ON pedidos(tipo_contrato);

-- idx_pedido_valor: Suporta análises de outlier e range de tickets
CREATE INDEX IF NOT EXISTS idx_pedido_valor ON pedidos(valor_total DESC);


-- 4. TABELA ITENS_PEDIDO
-- Justificativa: Detalhamento para análise de mix de produtos e detecção de anomalias
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

-- Índices ITENS_PEDIDO:

-- idx_item_pedido: ESSENCIAL para JOINs na detecção de anomalias (comparar valor_total vs soma itens)
CREATE INDEX IF NOT EXISTS idx_item_pedido ON itens_pedido(id_pedido);

-- idx_item_produto: Otimiza análises de top produtos e rentabilidade por commodity
CREATE INDEX IF NOT EXISTS idx_item_produto ON itens_pedido(id_produto);

-- idx_item_pedido_produto: Composite index para queries analíticas complexas (agregações por pedido+produto)
CREATE INDEX IF NOT EXISTS idx_item_pedido_produto ON itens_pedido(id_pedido, id_produto);


-- ============================================================
-- MODELO EXPANDIDO: MÚLTIPLOS CLIENTES POR PEDIDO (Compras Compartilhadas)
-- Justificativa: Permite cooperativas ou grupos de produtores
-- comprarem conjuntamente com rateio de custos
-- ============================================================

CREATE TABLE IF NOT EXISTS pedido_clientes (
    id_pedido INTEGER NOT NULL REFERENCES pedidos(id_pedido) ON DELETE CASCADE,
    id_cliente INTEGER NOT NULL REFERENCES clientes(id_cliente) ON DELETE RESTRICT,
    percentual_rateio NUMERIC(5,2) NOT NULL CHECK (percentual_rateio > 0 AND percentual_rateio <= 100),
    valor_rateado NUMERIC(15,2) NOT NULL,
    PRIMARY KEY (id_pedido, id_cliente)
);

-- Índice para consultas: "Quais pedidos o cliente X participou?"
CREATE INDEX IF NOT EXISTS idx_pedclient_cliente ON pedido_clientes(id_cliente);

COMMENT ON TABLE pedido_clientes IS 'Modelo de dados expandido permitindo múltiplos clientes por pedido (cooperativas/compras compartilhadas)';


-- ============================================================
-- COMENTÁRIOS DOCUMENTANDO JUSTIFICATIVAS (Requisito PDF)
-- ============================================================

COMMENT ON TABLE clientes IS 'Base de clientes: produtores, cooperativas e tradings. Índices otimizados para segmentação RFV';
COMMENT ON TABLE pedidos IS 'Contratos de compra/venda. Índice composto (id_cliente, data_pedido) crítico para Window Functions de recência';
COMMENT ON TABLE itens_pedido IS 'Itens dos contratos. Coluna subtotal GENERATED garante integridade para detecção de anomalias';
COMMENT ON COLUMN pedidos.valor_total IS 'Deve corresponder à soma dos subtotais dos itens (validado via query de anomalia)';
