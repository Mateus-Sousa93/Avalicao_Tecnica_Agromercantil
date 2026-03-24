-- ============================================================
-- AGROMERCANTIL - SCHEMA V2
-- Inclui: Correção de Anomalias + Compra Compartilhada
-- ============================================================

-- ============================================================
-- 1. TABELA DE LOG DE CORREÇÕES (AUDITORIA)
-- ============================================================
CREATE TABLE IF NOT EXISTS log_correcoes (
    id_correcao SERIAL PRIMARY KEY,
    id_pedido INTEGER NOT NULL REFERENCES pedidos(id_pedido),
    campo_corrigido VARCHAR(50) NOT NULL,
    valor_anterior NUMERIC(15,2) NOT NULL,
    valor_novo NUMERIC(15,2) NOT NULL,
    tipo_correcao VARCHAR(20) NOT NULL CHECK (tipo_correcao IN ('AUTOMATICA', 'MANUAL')),
    usuario_correcao VARCHAR(100),
    motivo_correcao TEXT,
    data_correcao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_log_correcoes_pedido ON log_correcoes(id_pedido);
CREATE INDEX idx_log_correcoes_data ON log_correcoes(data_correcao);

COMMENT ON TABLE log_correcoes IS 'Registro de todas as correções feitas em pedidos para auditoria';

-- ============================================================
-- 2. ESTRUTURA PARA COMPRA COMPARTILHADA
-- ============================================================

-- Tabela de grupos de compra (cooperativas informais, grupos de produtores)
CREATE TABLE IF NOT EXISTS grupos_compra (
    id_grupo SERIAL PRIMARY KEY,
    nome_grupo VARCHAR(200) NOT NULL,
    tipo_grupo VARCHAR(50) NOT NULL CHECK (tipo_grupo IN ('COOPERATIVA', 'ASSOCIACAO', 'CONSORCIO', 'GRUPO_INFORMAL')),
    representante_id INTEGER REFERENCES clientes(id_cliente),
    data_criacao DATE DEFAULT CURRENT_DATE,
    ativo BOOLEAN DEFAULT TRUE,
    observacoes TEXT
);

-- Tabela de vínculo cliente-grupo
CREATE TABLE IF NOT EXISTS cliente_grupo (
    id_cliente INTEGER REFERENCES clientes(id_cliente),
    id_grupo INTEGER REFERENCES grupos_compra(id_grupo),
    percentual_participacao NUMERIC(5,2) NOT NULL CHECK (percentual_participacao > 0 AND percentual_participacao <= 100),
    data_entrada DATE DEFAULT CURRENT_DATE,
    ativo BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (id_cliente, id_grupo)
);

-- Tabela de pedidos compartilhados (co-proprietários)
CREATE TABLE IF NOT EXISTS pedido_coproprietario (
    id_pedido INTEGER REFERENCES pedidos(id_pedido),
    id_cliente INTEGER REFERENCES clientes(id_cliente),
    percentual_propriedade NUMERIC(5,2) NOT NULL CHECK (percentual_propriedade > 0 AND percentual_propriedade <= 100),
    valor_proporcional NUMERIC(15,2) NOT NULL,
    tipo_participacao VARCHAR(50) NOT NULL CHECK (tipo_participacao IN ('COMPRADOR', 'FINANCIADOR', 'REPRESENTANTE')),
    PRIMARY KEY (id_pedido, id_cliente)
);

CREATE INDEX idx_pedido_coproprietario_pedido ON pedido_coproprietario(id_pedido);
CREATE INDEX idx_pedido_coproprietario_cliente ON pedido_coproprietario(id_cliente);

COMMENT ON TABLE pedido_coproprietario IS 'Permite que um pedido seja compartilhado entre múltiplos clientes';

-- ============================================================
-- 3. VIEW PARA PEDIDOS COM PROPRIETÁRIOS
-- ============================================================
CREATE OR REPLACE VIEW vw_pedidos_completo AS
SELECT 
    p.id_pedido,
    p.data_pedido,
    p.data_entrega,
    p.valor_total,
    p.status,
    p.tipo_contrato,
    p.regiao_origem,
    p.regiao_destino,
    c.id_cliente,
    c.nome as cliente_principal,
    c.tipo_cliente,
    CASE 
        WHEN EXISTS (SELECT 1 FROM pedido_coproprietario pc WHERE pc.id_pedido = p.id_pedido) 
        THEN 'COMPARTILHADO' 
        ELSE 'INDIVIDUAL' 
    END as tipo_ownership,
    COALESCE(
        (SELECT STRING_AGG(c2.nome || ' (' || pc.percentual_propriedade || '%)', ', ')
         FROM pedido_coproprietario pc 
         JOIN clientes c2 ON pc.id_cliente = c2.id_cliente
         WHERE pc.id_pedido = p.id_pedido),
        c.nome
    ) as todos_proprietarios
FROM pedidos p
JOIN clientes c ON p.id_cliente = c.id_cliente;

-- ============================================================
-- 4. FUNÇÃO PARA CORRIGIR ANOMALIA AUTOMATICAMENTE
-- ============================================================
CREATE OR REPLACE FUNCTION corrigir_anomalia(
    p_id_pedido INTEGER,
    p_usuario VARCHAR(100) DEFAULT 'SISTEMA',
    p_motivo TEXT DEFAULT 'Correção automática de divergência'
)
RETURNS TABLE(
    status TEXT,
    valor_anterior NUMERIC,
    valor_novo NUMERIC
) AS $$
DECLARE
    v_valor_registrado NUMERIC(15,2);
    v_valor_calculado NUMERIC(15,2);
    v_diferenca NUMERIC(15,2);
BEGIN
    -- Buscar valores atuais
    SELECT p.valor_total, COALESCE(SUM(i.subtotal), 0)
    INTO v_valor_registrado, v_valor_calculado
    FROM pedidos p
    LEFT JOIN itens_pedido i ON p.id_pedido = i.id_pedido
    WHERE p.id_pedido = p_id_pedido
    GROUP BY p.id_pedido, p.valor_total;
    
    -- Calcular diferença
    v_diferenca := ABS(v_valor_registrado - v_valor_calculado);
    
    -- Se não há divergência, retornar
    IF v_diferenca <= 0.01 THEN
        RETURN QUERY SELECT 'SEM_DIVERGENCIA'::TEXT, v_valor_registrado, v_valor_calculado;
        RETURN;
    END IF;
    
    -- Registrar log antes da correção
    INSERT INTO log_correcoes (id_pedido, campo_corrigido, valor_anterior, valor_novo, 
                                tipo_correcao, usuario_correcao, motivo_correcao)
    VALUES (p_id_pedido, 'valor_total', v_valor_registrado, v_valor_calculado, 
            'AUTOMATICA', p_usuario, p_motivo);
    
    -- Aplicar correção
    UPDATE pedidos 
    SET valor_total = v_valor_calculado
    WHERE id_pedido = p_id_pedido;
    
    RETURN QUERY SELECT 'CORRIGIDO'::TEXT, v_valor_registrado, v_valor_calculado;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION corrigir_anomalia IS 'Corrige automaticamente divergências entre valor registrado e calculado dos itens';

-- ============================================================
-- 5. FUNÇÃO PARA CRIAR PEDIDO COMPARTILHADO
-- ============================================================
CREATE OR REPLACE FUNCTION criar_pedido_compartilhado(
    p_data_pedido DATE,
    p_data_entrega DATE,
    p_tipo_contrato VARCHAR(50),
    p_regiao_origem VARCHAR(100),
    p_regiao_destino VARCHAR(100),
    p_proprietarios JSONB  -- [{"cliente_id": 1, "percentual": 60, "tipo": "COMPRADOR"}, ...]
)
RETURNS INTEGER AS $$
DECLARE
    v_id_pedido INTEGER;
    v_valor_total NUMERIC(15,2) := 0;
    v_proprietario RECORD;
    v_percentual_total NUMERIC(5,2) := 0;
BEGIN
    -- Validar que percentuais somam 100
    SELECT COALESCE(SUM((value->>'percentual')::NUMERIC), 0)
    INTO v_percentual_total
    FROM jsonb_array_elements(p_proprietarios);
    
    IF v_percentual_total != 100 THEN
        RAISE EXCEPTION 'Percentuais devem somar 100%%. Total: %', v_percentual_total;
    END IF;
    
    -- Criar pedido com primeiro cliente como titular
    INSERT INTO pedidos (data_pedido, data_entrega, id_cliente, tipo_contrato, 
                         status, valor_total, regiao_origem, regiao_destino)
    SELECT p_data_pedido, p_data_entrega, 
           (p_proprietarios->0->>'cliente_id')::INTEGER,
           p_tipo_contrato, 'Pendente', 0, p_regiao_origem, p_regiao_destino
    RETURNING id_pedido INTO v_id_pedido;
    
    -- Inserir co-proprietários
    FOR v_proprietario IN 
        SELECT 
            (value->>'cliente_id')::INTEGER as cliente_id,
            (value->>'percentual')::NUMERIC as percentual,
            value->>'tipo' as tipo
        FROM jsonb_array_elements(p_proprietarios)
    LOOP
        -- Valor proporcional será atualizado após inserir itens
        INSERT INTO pedido_coproprietario (id_pedido, id_cliente, percentual_propriedade, 
                                           valor_proporcional, tipo_participacao)
        VALUES (v_id_pedido, v_proprietario.cliente_id, v_proprietario.percentual, 
                0, v_proprietario.tipo);
    END LOOP;
    
    RETURN v_id_pedido;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION criar_pedido_compartilhado IS 'Cria um pedido compartilhado entre múltiplos clientes';

-- ============================================================
-- 6. TRIGGER PARA ATUALIZAR VALORES PROPORCIONAIS
-- ============================================================
CREATE OR REPLACE FUNCTION atualizar_valores_proporcionais()
RETURNS TRIGGER AS $$
BEGIN
    -- Atualizar valores proporcionais dos co-proprietários
    UPDATE pedido_coproprietario
    SET valor_proporcional = NEW.valor_total * (percentual_propriedade / 100)
    WHERE id_pedido = NEW.id_pedido;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_atualizar_proporcoes ON pedidos;
CREATE TRIGGER trg_atualizar_proporcoes
    AFTER UPDATE OF valor_total ON pedidos
    FOR EACH ROW
    WHEN (NEW.valor_total IS DISTINCT FROM OLD.valor_total)
    EXECUTE FUNCTION atualizar_valores_proporcionais();

-- ============================================================
-- 7. VIEW PARA RELATÓRIO DE ANOMALIAS COM STATUS DE CORREÇÃO
-- ============================================================
CREATE OR REPLACE VIEW vw_anomalias_completas AS
WITH soma_itens AS (
    SELECT id_pedido, SUM(subtotal) as valor_calculado
    FROM itens_pedido 
    GROUP BY id_pedido
),
correcoes_recentes AS (
    SELECT DISTINCT ON (id_pedido) 
        id_pedido, 
        valor_novo,
        data_correcao,
        tipo_correcao
    FROM log_correcoes
    WHERE campo_corrigido = 'valor_total'
    ORDER BY id_pedido, data_correcao DESC
)
SELECT 
    p.id_pedido,
    p.data_pedido,
    c.id_cliente,
    c.nome as cliente,
    c.tipo_cliente,
    c.regiao,
    p.valor_total as valor_registrado,
    si.valor_calculado,
    ROUND(ABS(p.valor_total - si.valor_calculado), 2) as diferenca,
    CASE 
        WHEN cr.id_pedido IS NOT NULL THEN 'CORRIGIDO'
        ELSE 'PENDENTE'
    END as status_correcao,
    cr.data_correcao,
    cr.tipo_correcao,
    CASE 
        WHEN p.valor_total > si.valor_calculado THEN 'SOBREFATURAMENTO'
        WHEN p.valor_total < si.valor_calculado THEN 'SUBFATURAMENTO'
        ELSE 'OK'
    END as tipo_anomalia
FROM pedidos p
JOIN soma_itens si ON p.id_pedido = si.id_pedido
JOIN clientes c ON p.id_cliente = c.id_cliente
LEFT JOIN correcoes_recentes cr ON p.id_pedido = cr.id_pedido
WHERE ABS(p.valor_total - si.valor_calculado) > 0.01;

-- ============================================================
-- 8. DADOS DE EXEMPLO PARA COMPRA COMPARTILHADA
-- ============================================================

-- Inserir grupo de exemplo
INSERT INTO grupos_compra (nome_grupo, tipo_grupo, observacoes) VALUES
('Cooperativa Agrícola Vale do Rio', 'COOPERATIVA', 'Grupo de produtores do MT'),
('Associação de Produtores Sul', 'ASSOCIACAO', 'Produtores do RS e SC')
ON CONFLICT DO NOTHING;

-- Inserir clientes em grupos (assumindo IDs existentes)
-- Nota: Ajustar IDs conforme dados reais
INSERT INTO cliente_grupo (id_cliente, id_grupo, percentual_participacao) VALUES
(1, 1, 25.00),
(2, 1, 35.00),
(3, 1, 40.00)
ON CONFLICT DO NOTHING;

-- ============================================================
-- JUSTIFICATIVAS DOS ÍNDICES ADICIONAIS
-- ============================================================
/*
1. idx_log_correcoes_pedido: Permite buscar histórico de correções por pedido rapidamente
2. idx_log_correcoes_data: Facilita auditorias por período
3. idx_pedido_coproprietario_pedido: Otimiza joins na view vw_pedidos_completo
4. idx_pedido_coproprietario_cliente: Permite buscar todos os pedidos de um cliente co-proprietário

Os triggers garantem integridade referencial e auditoria automática.
As views facilitam consultas complexas sem duplicar lógica na aplicação.
*/
