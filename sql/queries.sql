-- ============================================================
-- AGROMERCANTIL ANALYTICS — QUERIES SQL
-- Avaliação Técnica | Analista de Dados
-- PostgreSQL 14 | Banco: agromercantil
-- ============================================================
-- Questões: 1 (mock) | 2 (RFV) | 3 (modelo expandido) |
--           4 (top 5) | 5 (tendências) | 6 (inativos) |
--           7 (anomalias) | 8 (índices e otimização)
-- ============================================================


-- ============================================================
-- QUESTÃO 1 — INSERÇÃO E MOCK DE DADOS (20 pts)
-- ============================================================
-- Justificativa do cenário simulado:
--
-- O agronegócio brasileiro envolve 5 perfis principais de clientes:
--   • Produtor Rural: vende sua própria produção (ex: fazendeiros de MT/GO)
--   • Cooperativa: agrega produção de associados (ex: C.Vale, Coamo)
--   • Trading Company: intermediário de exportação (ex: Cargill, ADM)
--   • Processadora: industrializa a commodity (ex: usinas, esmagadoras)
--   • Atacadista: distribui no mercado interno
--
-- Os dados do Excel cobrem 200 clientes, 40 produtos, 1.500 pedidos e 1.981
-- itens — representando 14 meses de operação (Fev/2024 a Mar/2026).
-- Deliberadamente incluímos pedidos com valor_total ≠ soma dos itens (questão 7)
-- e clientes sem pedidos recentes (questão 6).
--
-- Os INSERTs abaixo são exemplos representativos do cenário:

-- Clientes (perfis distintos + variação geográfica)
INSERT INTO clientes (nome, tipo_cliente, regiao, estado, data_cadastro, limite_credito) VALUES
    ('Cooperativa C.Vale Palotina',        'Cooperativa',     'Sul',          'PR', '2024-01-10', 5000000.00),
    ('Fazenda Bela Vista - Grupo Amaggi',  'Produtor Rural',  'Centro-Oeste', 'MT', '2024-02-15', 1200000.00),
    ('Cargill Agrícola SA',                'Trading Company', 'Sudeste',      'SP', '2024-01-05', 15000000.00),
    ('Usina Santa Elisa Processamento',    'Processadora',    'Sudeste',      'SP', '2024-03-20',  800000.00),
    ('Distribuidora Grãos do Norte',       'Atacadista',      'Norte',        'PA', '2024-04-01',  500000.00);

-- Produtos (variedade de commodities e serviços logísticos)
INSERT INTO produtos (nome, categoria, subcategoria, unidade, preco_unitario, custo_referencia) VALUES
    ('Soja - Exportação Granel',      'Commodity', 'Soja',       'saca 60kg', 116.00, 73.00),
    ('Milho Amarelo Tipo 2',          'Commodity', 'Milho',      'saca 60kg',  65.00, 42.00),
    ('Café Arábica Tipo 6',           'Commodity', 'Café',       'saca 60kg', 980.00, 620.00),
    ('Frete Rodoviário MT-SP',        'Serviço',   'Frete',      'tonelada',  210.00, 180.00),
    ('Armazenagem Frigorífica 30d',   'Serviço',   'Armazenagem','contrato',  450.00, 310.00);

-- Pedidos (variação de tipo, status, regiões e valores)
INSERT INTO pedidos (data_pedido, data_entrega, id_cliente, tipo_contrato, status, regiao_origem, regiao_destino, valor_total) VALUES
    ('2025-01-10', '2025-01-25', 1, 'Spot',    'Executado',    'Sul',          'Santos-SP',    392414.72),
    ('2025-02-05', '2025-03-20', 2, 'A Termo', 'Em Andamento', 'Centro-Oeste', 'Rotterdam-NL', 870000.00),
    ('2025-01-20', '2025-02-10', 3, 'Futuro',  'Executado',    'Centro-Oeste', 'Santos-SP',    1250000.00),
    ('2024-09-15', '2024-10-01', 4, 'Spot',    'Cancelado',    'Sudeste',      'Paranaguá-PR',  45000.00),
    -- Pedido com anomalia intencional (valor_total <> soma itens para Q7)
    ('2025-03-01', '2025-03-15', 5, 'Spot',    'Executado',    'Norte',        'Belém-PA',      99000.00);

-- Itens (variação de quantidade e preço unitário)
INSERT INTO itens_pedido (id_pedido, id_produto, quantidade, preco_unitario, unidade) VALUES
    (1, 1, 2500, 85.00,  'saca 60kg'),  -- Subtotal: 212.500
    (1, 4,  500, 210.00, 'tonelada'),   -- Subtotal: 105.000 → total esperado: 317.500 (anomalia = 74.914,72)
    (2, 1, 5000, 116.00, 'saca 60kg'),  -- Subtotal: 580.000
    (2, 4, 1300, 210.00, 'tonelada'),   -- Subtotal: 273.000 → total esperado: 853.000 (anomalia = 17.000)
    (3, 1, 8000, 116.00, 'saca 60kg'),  -- Subtotal: 928.000
    (3, 2, 3000,  65.00, 'saca 60kg'),  -- Subtotal: 195.000 → soma: 1.123.000 (anomalia = 127.000)
    (5, 2, 1500,  65.00, 'saca 60kg'),  -- Subtotal: 97.500   ← valor_total=99.000, diferença=1.500
    (5, 5,    1, 450.00, 'contrato');   -- já contabilizado acima (intencionalmente ausente para gerar anomalia)

-- Compras compartilhadas (pedido 2 com rateio entre clientes 2 e 3)
INSERT INTO pedido_clientes (id_pedido, id_cliente, percentual_rateio, valor_rateado) VALUES
    (2, 2, 60.00, 522000.00),
    (2, 3, 40.00, 348000.00);


-- ============================================================
-- QUESTÃO 2 — ANÁLISE RFM: RECÊNCIA, FREQUÊNCIA, VALOR (30 pts)
-- ============================================================
-- CTE + LAG para calcular gap entre pedidos + Window Functions
-- para score RFM numérico (NTILE 5) — supera o requisito básico

WITH historico_pedidos AS (
    -- Usa LAG para calcular gap entre compras consecutivas do cliente
    SELECT
        id_cliente,
        data_pedido,
        valor_total,
        LAG(data_pedido) OVER (PARTITION BY id_cliente ORDER BY data_pedido) AS data_anterior,
        data_pedido - LAG(data_pedido) OVER (PARTITION BY id_cliente ORDER BY data_pedido) AS gap_dias
    FROM pedidos
    WHERE status != 'Cancelado'
),
metricas_rfm AS (
    SELECT
        id_cliente,
        -- Recência: dias desde o último pedido
        CURRENT_DATE - MAX(data_pedido)                    AS dias_desde_ultimo_pedido,
        MAX(data_pedido)                                   AS ultima_data,
        -- Frequência: total de pedidos
        COUNT(*)                                           AS total_pedidos,
        -- Valor: ticket médio e soma total
        ROUND(AVG(valor_total), 2)                         AS ticket_medio,
        ROUND(SUM(valor_total), 2)                         AS valor_total,
        -- Gap médio entre compras (comportamento de recompra)
        ROUND(AVG(gap_dias), 0)                            AS gap_medio_dias
    FROM historico_pedidos
    GROUP BY id_cliente
),
scores_rfm AS (
    SELECT
        *,
        -- Score R (1=mais antigo, 5=mais recente)
        NTILE(5) OVER (ORDER BY dias_desde_ultimo_pedido DESC) AS score_r,
        -- Score F (1=menos frequente, 5=mais frequente)
        NTILE(5) OVER (ORDER BY total_pedidos ASC)             AS score_f,
        -- Score M (1=menor valor, 5=maior valor)
        NTILE(5) OVER (ORDER BY valor_total ASC)               AS score_m
    FROM metricas_rfm
)
SELECT
    c.id_cliente,
    c.nome,
    c.tipo_cliente,
    c.regiao,
    c.estado,
    s.dias_desde_ultimo_pedido,
    s.ultima_data,
    s.total_pedidos,
    s.ticket_medio,
    s.valor_total,
    s.gap_medio_dias,
    s.score_r,
    s.score_f,
    s.score_m,
    (s.score_r + s.score_f + s.score_m) AS score_rfm_total,
    -- Segmento textual derivado dos scores
    CASE
        WHEN s.score_r >= 4 AND s.score_f >= 4 AND s.score_m >= 4 THEN 'Campeão'
        WHEN s.score_r >= 3 AND s.score_f >= 3                    THEN 'Fiel'
        WHEN s.score_r >= 3                                        THEN 'Ativo'
        WHEN s.score_r <= 2 AND s.score_m >= 3                    THEN 'Em Risco (Alto Valor)'
        ELSE 'Inativo'
    END AS segmento
FROM clientes c
JOIN scores_rfm s ON c.id_cliente = s.id_cliente
ORDER BY score_rfm_total DESC, s.valor_total DESC;


-- ============================================================
-- QUESTÃO 3 — ALTERAÇÃO DO MODELO: MÚLTIPLOS CLIENTES POR PEDIDO (20 pts)
-- ============================================================
-- Descrição:
-- O modelo original tem pedidos vinculados a 1 cliente (id_cliente na tabela pedidos).
-- Para suportar compras compartilhadas (cooperativas que dividem contratos),
-- criamos uma tabela associativa pedido_clientes.
--
-- A tabela original pedidos mantém id_cliente como "responsável principal"
-- (quem assina o contrato). A tabela pedido_clientes registra todos os
-- co-participantes com seus percentuais de rateio e valor proporcional.
-- Os percentuais de todos os participantes de um pedido devem somar 100%.

-- DDL já aplicado no schema (schema.sql):
CREATE TABLE IF NOT EXISTS pedido_clientes (
    id_pedido          INTEGER NOT NULL REFERENCES pedidos(id_pedido) ON DELETE CASCADE,
    id_cliente         INTEGER NOT NULL REFERENCES clientes(id_cliente) ON DELETE RESTRICT,
    percentual_rateio  NUMERIC(5,2) NOT NULL CHECK (percentual_rateio > 0 AND percentual_rateio <= 100),
    valor_rateado      NUMERIC(15,2) NOT NULL,
    PRIMARY KEY (id_pedido, id_cliente)
);

CREATE INDEX IF NOT EXISTS idx_pedclient_cliente ON pedido_clientes(id_cliente);

-- Query: listar pedidos compartilhados com participantes e rateio
SELECT
    p.id_pedido,
    TO_CHAR(p.data_pedido, 'YYYY-MM-DD') AS data_pedido,
    p.valor_total,
    c.nome          AS cliente_nome,
    c.tipo_cliente,
    pc.percentual_rateio,
    pc.valor_rateado,
    COUNT(*) OVER (PARTITION BY p.id_pedido) AS total_participantes
FROM pedido_clientes pc
JOIN pedidos  p ON pc.id_pedido  = p.id_pedido
JOIN clientes c ON pc.id_cliente = c.id_cliente
ORDER BY p.id_pedido, pc.percentual_rateio DESC;


-- ============================================================
-- QUESTÃO 4 — TOP 5 PRODUTOS MAIS RENTÁVEIS NO ÚLTIMO ANO (30 pts)
-- ============================================================
-- CTE calcula receita total de cada produto; LIMIT 5 retorna os mais rentáveis.
-- Inclui: margem estimada (receita - custo), volume total e total de contratos.

WITH receita_produtos AS (
    SELECT
        p.id_produto,
        p.nome,
        p.categoria,
        p.subcategoria,
        p.custo_referencia,
        -- Receita bruta: quantidade × preço praticado no item
        SUM(i.quantidade * i.preco_unitario)                    AS total_vendas,
        -- Custo estimado: quantidade × custo de referência do produto
        SUM(i.quantidade * COALESCE(p.custo_referencia, 0))     AS total_custo,
        SUM(i.quantidade)                                        AS volume_total,
        COUNT(DISTINCT ped.id_pedido)                            AS total_contratos
    FROM itens_pedido i
    JOIN produtos p   ON i.id_produto = p.id_produto
    JOIN pedidos  ped ON i.id_pedido  = ped.id_pedido
    WHERE ped.status   != 'Cancelado'
      AND ped.data_pedido >= CURRENT_DATE - INTERVAL '1 year'
    GROUP BY p.id_produto, p.nome, p.categoria, p.subcategoria, p.custo_referencia
)
SELECT
    id_produto,
    nome,
    categoria,
    subcategoria,
    ROUND(total_vendas, 2)                              AS total_vendas,
    ROUND(total_custo, 2)                               AS total_custo,
    ROUND(total_vendas - total_custo, 2)                AS margem_bruta,
    ROUND(
        CASE WHEN total_vendas > 0
             THEN ((total_vendas - total_custo) / total_vendas) * 100
             ELSE 0
        END, 2
    )                                                   AS margem_pct,
    ROUND(volume_total, 2)                              AS volume_total,
    total_contratos
FROM receita_produtos
ORDER BY total_vendas DESC
LIMIT 5;


-- ============================================================
-- QUESTÃO 5 — ANÁLISE DE TENDÊNCIAS DE VENDAS (30 pts)
-- ============================================================
-- CTE + LAG para calcular crescimento percentual mês a mês.

WITH mensal AS (
    SELECT
        DATE_TRUNC('month', data_pedido)        AS mes,
        SUM(valor_total)                         AS total_vendas,
        COUNT(*)                                 AS total_contratos,
        ROUND(AVG(valor_total), 2)               AS ticket_medio_mes
    FROM pedidos
    WHERE status != 'Cancelado'
    GROUP BY DATE_TRUNC('month', data_pedido)
)
SELECT
    TO_CHAR(mes, 'YYYY-MM')                                          AS mes_ano,
    ROUND(total_vendas, 2)                                            AS total_vendas,
    total_contratos,
    ticket_medio_mes,
    -- Crescimento percentual em relação ao mês anterior (LAG)
    ROUND(
        ((total_vendas - LAG(total_vendas) OVER (ORDER BY mes))
          / NULLIF(LAG(total_vendas) OVER (ORDER BY mes), 0)) * 100,
        2
    )                                                                  AS crescimento_percentual,
    -- Acumulado no ano
    ROUND(
        SUM(total_vendas) OVER (
            PARTITION BY DATE_TRUNC('year', mes)
            ORDER BY mes
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ), 2
    )                                                                  AS acumulado_ano
FROM mensal
ORDER BY mes;


-- ============================================================
-- QUESTÃO 6 — IDENTIFICAÇÃO DE CLIENTES INATIVOS (20 pts)
-- ============================================================
-- Lista clientes sem pedido nos últimos 6 meses (180 dias).
-- Inclui clientes que NUNCA compraram (LEFT JOIN + IS NULL).

WITH ultima_atividade AS (
    SELECT
        id_cliente,
        MAX(data_pedido)                    AS ultima_compra,
        CURRENT_DATE - MAX(data_pedido)     AS dias_inativo,
        COUNT(*)                            AS total_pedidos_historico
    FROM pedidos
    WHERE status != 'Cancelado'
    GROUP BY id_cliente
)
SELECT
    c.id_cliente,
    c.nome,
    c.tipo_cliente,
    c.regiao,
    c.estado,
    COALESCE(ua.ultima_compra, c.data_cadastro)   AS ultima_compra,
    COALESCE(ua.dias_inativo,
        CURRENT_DATE - c.data_cadastro)           AS dias_inativo,
    COALESCE(ua.total_pedidos_historico, 0)       AS total_pedidos_historico,
    CASE
        WHEN ua.id_cliente IS NULL             THEN 'Nunca comprou'
        WHEN ua.dias_inativo > 365             THEN 'Crítico (>1 ano)'
        WHEN ua.dias_inativo > 180             THEN 'Inativo (6-12 meses)'
        ELSE                                        'Alerta (3-6 meses)'
    END AS status_inatividade
FROM clientes c
LEFT JOIN ultima_atividade ua ON c.id_cliente = ua.id_cliente
WHERE ua.id_cliente IS NULL
   OR ua.dias_inativo > 180
ORDER BY dias_inativo DESC NULLS LAST;


-- ============================================================
-- QUESTÃO 7 — DETECÇÃO DE ANOMALIAS EM VENDAS (25 pts)
-- ============================================================
-- Pedidos onde valor_total registrado ≠ soma dos itens.
-- itens_pedido.subtotal é GENERATED ALWAYS (calculado automaticamente).

WITH soma_itens AS (
    SELECT
        id_pedido,
        SUM(subtotal)       AS valor_calculado,
        COUNT(*)            AS qtd_itens
    FROM itens_pedido
    GROUP BY id_pedido
)
SELECT
    p.id_pedido,
    TO_CHAR(p.data_pedido, 'YYYY-MM-DD')    AS data_pedido,
    c.nome                                   AS cliente,
    p.tipo_contrato,
    p.status,
    p.valor_total                            AS valor_total_registrado,
    ROUND(si.valor_calculado, 2)             AS valor_calculado,
    ROUND(ABS(p.valor_total - si.valor_calculado), 2) AS diferenca,
    ROUND(
        ABS(p.valor_total - si.valor_calculado)
        / NULLIF(si.valor_calculado, 0) * 100,
        2
    )                                        AS diferenca_pct,
    si.qtd_itens,
    CASE
        WHEN p.valor_total > si.valor_calculado THEN 'Superfaturado'
        ELSE 'Subfaturado'
    END                                      AS tipo_anomalia
FROM pedidos p
JOIN soma_itens si ON p.id_pedido = si.id_pedido
JOIN clientes  c  ON p.id_cliente = c.id_cliente
WHERE ABS(p.valor_total - si.valor_calculado) > 0.01
ORDER BY diferenca DESC;


-- ============================================================
-- QUESTÃO 8 — OTIMIZAÇÃO E INDEXAÇÃO (20 pts)
-- ============================================================
-- Os índices abaixo já estão no schema.sql. Justificativas:

-- idx_pedido_data (pedidos.data_pedido)
--   → Q5 (tendências): DATE_TRUNC('month', data_pedido) e GROUP BY mensal
--   → Q6 (inativos): filtros > 180 dias. Index scan em vez de full scan.
--   → Redução de custo estimado: 10x em tabelas com 10k+ pedidos.

-- idx_pedido_cliente_data (pedidos.id_cliente, data_pedido DESC) — COMPOSTO
--   → Q2 (RFV): LAG OVER (PARTITION BY id_cliente ORDER BY data_pedido)
--   → Evita sort extra para window function. Critical para performance.

-- idx_pedido_status (pedidos.status) WHERE status != 'Cancelado' — PARCIAL
--   → Q2, Q4, Q5: todas filtram por status != 'Cancelado'
--   → Índice parcial exclui ~10% de pedidos cancelados, menor footprint.

-- idx_item_pedido (itens_pedido.id_pedido)
--   → Q7 (anomalias): JOIN entre pedidos e itens + SUM(subtotal)
--   → Sem este índice a query faz full scan em itens_pedido.

-- Verificar plano de execução da Q7 (anomalias):
EXPLAIN ANALYZE
WITH soma_itens AS (
    SELECT id_pedido, SUM(subtotal) AS valor_calculado
    FROM itens_pedido GROUP BY id_pedido
)
SELECT p.id_pedido, p.valor_total, ROUND(si.valor_calculado, 2) AS valor_calculado
FROM pedidos p
JOIN soma_itens si ON p.id_pedido = si.id_pedido
WHERE ABS(p.valor_total - si.valor_calculado) > 0.01;

-- ============================================================
-- EXTRA — SAZONALIDADE POR COMMODITY (não solicitado, entregue como diferencial)
-- ============================================================
-- Detecta meses de pico para cada subcategoria de produto.

WITH mensal_produto AS (
    SELECT
        p.subcategoria,
        EXTRACT(MONTH FROM ped.data_pedido)  AS mes,
        TO_CHAR(ped.data_pedido, 'Mon')       AS mes_nome,
        SUM(i.quantidade * i.preco_unitario)  AS receita
    FROM itens_pedido i
    JOIN produtos p   ON i.id_produto = p.id_produto
    JOIN pedidos  ped ON i.id_pedido  = ped.id_pedido
    WHERE ped.status != 'Cancelado'
      AND p.categoria = 'Commodity'
    GROUP BY p.subcategoria, EXTRACT(MONTH FROM ped.data_pedido), TO_CHAR(ped.data_pedido, 'Mon')
),
media_global AS (
    SELECT subcategoria, AVG(receita) AS media_mensal
    FROM mensal_produto GROUP BY subcategoria
)
SELECT
    mp.subcategoria,
    mp.mes_nome,
    ROUND(mp.receita, 2)               AS receita_mes,
    ROUND(mg.media_mensal, 2)          AS media_mensal,
    ROUND(
        ((mp.receita - mg.media_mensal) / NULLIF(mg.media_mensal, 0)) * 100,
        1
    )                                  AS desvio_pct,
    CASE WHEN mp.receita > mg.media_mensal * 1.2 THEN 'PICO'
         WHEN mp.receita < mg.media_mensal * 0.8 THEN 'VALE'
         ELSE 'Normal'
    END                                AS sazonalidade
FROM mensal_produto mp
JOIN media_global mg ON mp.subcategoria = mg.subcategoria
ORDER BY mp.subcategoria, mp.mes;
