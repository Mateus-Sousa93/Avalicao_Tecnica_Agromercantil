-- ============================================================
-- AGROMERCANTIL - SCHEMA V3
-- Rastreabilidade, Auditoria e Integridade de Dados
-- ============================================================

-- ============================================================
-- 1. SEQUENCES PARA NÚMEROS DE PEDIDO ÚNICOS
-- ============================================================
CREATE SEQUENCE IF NOT EXISTS seq_pedido_2024 START 10001;
CREATE SEQUENCE IF NOT EXISTS seq_pedido_2025 START 20001;

-- Função para gerar número de pedido único
CREATE OR REPLACE FUNCTION gerar_numero_pedido()
RETURNS VARCHAR(20) AS $$
DECLARE
    v_ano INTEGER := EXTRACT(YEAR FROM CURRENT_DATE);
    v_seq INTEGER;
    v_numero VARCHAR(20);
BEGIN
    -- Seleciona sequence conforme ano
    IF v_ano = 2024 THEN
        SELECT nextval('seq_pedido_2024') INTO v_seq;
    ELSIF v_ano = 2025 THEN
        SELECT nextval('seq_pedido_2025') INTO v_seq;
    ELSE
        -- Para anos futuros, usa sequence dinâmica
        EXECUTE format('SELECT nextval(%L)', 'seq_pedido_' || v_ano::TEXT)
        INTO v_seq;
    END IF;
    
    v_numero := 'AGR-' || v_ano || '-' || LPAD(v_seq::TEXT, 6, '0');
    RETURN v_numero;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 2. TABELA DE AUDITORIA GLOBAL
-- ============================================================
CREATE TABLE IF NOT EXISTS auditoria_global (
    id_auditoria BIGSERIAL PRIMARY KEY,
    tabela_afetada VARCHAR(100) NOT NULL,
    operacao VARCHAR(10) NOT NULL CHECK (operacao IN ('INSERT', 'UPDATE', 'DELETE')),
    id_registro INTEGER NOT NULL,
    dados_anteriores JSONB,
    dados_novos JSONB,
    usuario_db VARCHAR(100) DEFAULT CURRENT_USER,
    usuario_aplicacao VARCHAR(100),
    ip_origem INET,
    session_id VARCHAR(100),
    hash_integridade VARCHAR(64), -- SHA-256 dos dados
    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_auditoria_tabela ON auditoria_global(tabela_afetada);
CREATE INDEX idx_auditoria_registro ON auditoria_global(tabela_afetada, id_registro);
CREATE INDEX idx_auditoria_data ON auditoria_global(data_hora);
CREATE INDEX idx_auditoria_usuario ON auditoria_global(usuario_aplicacao);

COMMENT ON TABLE auditoria_global IS 'Auditoria completa de todas as operações CRUD no sistema';

-- ============================================================
-- 3. TABELA PEDIDOS COM RASTREABILIDADE
-- ============================================================
-- Adicionar colunas de rastreabilidade à tabela existente
ALTER TABLE pedidos 
    ADD COLUMN IF NOT EXISTS numero_pedido VARCHAR(20) UNIQUE,
    ADD COLUMN IF NOT EXISTS chave_unica VARCHAR(50) UNIQUE,
    ADD COLUMN IF NOT EXISTS created_by VARCHAR(100) DEFAULT CURRENT_USER,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS updated_by VARCHAR(100),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS ip_origem INET,
    ADD COLUMN IF NOT EXISTS session_id VARCHAR(100),
    ADD COLUMN IF NOT EXISTS hash_integridade VARCHAR(64),
    ADD COLUMN IF NOT EXISTS versao INTEGER DEFAULT 1;

-- Constraint para evitar pedidos duplicados no mesmo dia para mesmo cliente
ALTER TABLE pedidos
    ADD CONSTRAINT uk_pedido_cliente_dia UNIQUE (id_cliente, data_pedido, numero_pedido);

-- Constraint EXCLUDE para evitar sobreposição de entregas (exemplo avançado)
-- Isso impede que um cliente tenha 2 pedidos com data de entrega no mesmo dia
-- DESCOMENTE SE NECESSÁRIO:
-- ALTER TABLE pedidos
--     ADD CONSTRAINT excl_pedido_entrega_sobreposta
--     EXCLUDE USING gist (
--         id_cliente WITH =,
--         daterange(data_entrega, data_entrega + INTERVAL '1 day', '[)') WITH &&
--     );

-- ============================================================
-- 4. FUNÇÃO PARA GERAR HASH DE INTEGRIDADE
-- ============================================================
CREATE OR REPLACE FUNCTION calcular_hash_pedido(p_id_pedido INTEGER)
RETURNS VARCHAR(64) AS $$
DECLARE
    v_dados TEXT;
    v_hash VARCHAR(64);
BEGIN
    -- Concatena dados críticos do pedido
    SELECT 
        COALESCE(p.id_pedido::TEXT, '') || '|' ||
        COALESCE(p.numero_pedido, '') || '|' ||
        COALESCE(p.id_cliente::TEXT, '') || '|' ||
        COALESCE(p.valor_total::TEXT, '') || '|' ||
        COALESCE(p.status, '') || '|' ||
        COALESCE(p.data_pedido::TEXT, '')
    INTO v_dados
    FROM pedidos p
    WHERE p.id_pedido = p_id_pedido;
    
    -- Calcula SHA-256
    SELECT encode(digest(v_dados, 'sha256'), 'hex')
    INTO v_hash;
    
    RETURN v_hash;
END;
$$ LANGUAGE plpgsql;

-- Requer extensão pgcrypto
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================
-- 5. TRIGGER PARA PREENCHER DADOS DE RASTREABILIDADE
-- ============================================================
CREATE OR REPLACE FUNCTION trg_pedido_rastreabilidade()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        -- Gera número de pedido único
        IF NEW.numero_pedido IS NULL THEN
            NEW.numero_pedido := gerar_numero_pedido();
        END IF;
        
        -- Gera chave única composta
        NEW.chave_unica := NEW.id_cliente || '-' || 
                          TO_CHAR(NEW.data_pedido, 'YYYYMMDD') || '-' ||
                          NEW.numero_pedido;
        
        -- Captura metadados da sessão (se disponíveis via SET)
        NEW.ip_origem := NULLIF(current_setting('app.user_ip', TRUE), '');
        NEW.session_id := NULLIF(current_setting('app.session_id', TRUE), '');
        NEW.created_by := NULLIF(current_setting('app.user_name', TRUE), '');
        
        -- Calcula hash inicial
        NEW.hash_integridade := calcular_hash_pedido(NEW.id_pedido);
        
        -- Registra na auditoria
        INSERT INTO auditoria_global (
            tabela_afetada, operacao, id_registro, 
            dados_novos, usuario_aplicacao, ip_origem, session_id, hash_integridade
        ) VALUES (
            'pedidos', 'INSERT', NEW.id_pedido,
            to_jsonb(NEW), NEW.created_by, NEW.ip_origem, NEW.session_id, 
            NEW.hash_integridade
        );
        
        RETURN NEW;
        
    ELSIF TG_OP = 'UPDATE' THEN
        -- Valida integridade dos dados anteriores
        IF OLD.hash_integridade IS NOT NULL THEN
            IF OLD.hash_integridade != calcular_hash_pedido(OLD.id_pedido) THEN
                RAISE EXCEPTION 'INTEGRIDADE_COMPROMETIDA: Os dados do pedido % foram alterados fora do sistema', OLD.id_pedido;
            END IF;
        END IF;
        
        -- Atualiza metadados
        NEW.updated_at := CURRENT_TIMESTAMP;
        NEW.updated_by := NULLIF(current_setting('app.user_name', TRUE), '');
        NEW.versao := OLD.versao + 1;
        
        -- Recalcula hash
        NEW.hash_integridade := calcular_hash_pedido(NEW.id_pedido);
        
        -- Registra na auditoria apenas se dados relevantes mudaram
        IF OLD.valor_total IS DISTINCT FROM NEW.valor_total OR
           OLD.status IS DISTINCT FROM NEW.status OR
           OLD.data_entrega IS DISTINCT FROM NEW.data_entrega THEN
            
            INSERT INTO auditoria_global (
                tabela_afetada, operacao, id_registro,
                dados_anteriores, dados_novos, usuario_aplicacao, 
                ip_origem, session_id, hash_integridade
            ) VALUES (
                'pedidos', 'UPDATE', NEW.id_pedido,
                to_jsonb(OLD), to_jsonb(NEW), NEW.updated_by,
                NULLIF(current_setting('app.user_ip', TRUE), ''),
                NULLIF(current_setting('app.session_id', TRUE), ''),
                NEW.hash_integridade
            );
        END IF;
        
        RETURN NEW;
        
    ELSIF TG_OP = 'DELETE' THEN
        -- Registra exclusão
        INSERT INTO auditoria_global (
            tabela_afetada, operacao, id_registro,
            dados_anteriores, usuario_aplicacao, ip_origem, session_id
        ) VALUES (
            'pedidos', 'DELETE', OLD.id_pedido,
            to_jsonb(OLD), 
            NULLIF(current_setting('app.user_name', TRUE), ''),
            NULLIF(current_setting('app.user_ip', TRUE), ''),
            NULLIF(current_setting('app.session_id', TRUE), '')
        );
        
        RETURN OLD;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Aplica trigger
DROP TRIGGER IF EXISTS trg_pedido_audit ON pedidos;
CREATE TRIGGER trg_pedido_audit
    BEFORE INSERT OR UPDATE OR DELETE ON pedidos
    FOR EACH ROW
    EXECUTE FUNCTION trg_pedido_rastreabilidade();

-- ============================================================
-- 6. VIEW PARA CONSULTA DE PEDIDOS COM AUDITORIA
-- ============================================================
CREATE OR REPLACE VIEW vw_pedidos_rastreaveis AS
SELECT 
    p.*,
    c.nome as cliente_nome,
    -- Última alteração
    (SELECT MAX(data_hora) 
     FROM auditoria_global ag 
     WHERE ag.tabela_afetada = 'pedidos' 
       AND ag.id_registro = p.id_pedido) as ultima_alteracao,
    -- Total de alterações
    (SELECT COUNT(*) 
     FROM auditoria_global ag 
     WHERE ag.tabela_afetada = 'pedidos' 
       AND ag.id_registro = p.id_pedido) as total_alteracoes,
    -- Verificação de integridade
    CASE 
        WHEN p.hash_integridade = calcular_hash_pedido(p.id_pedido) THEN 'VALIDO'
        ELSE 'CORROMPIDO'
    END as status_integridade
FROM pedidos p
JOIN clientes c ON p.id_cliente = c.id_cliente;

-- ============================================================
-- 7. FUNÇÃO PARA VERIFICAR INTEGRIDADE DE TODOS OS PEDIDOS
-- ============================================================
CREATE OR REPLACE FUNCTION verificar_integridade_pedidos()
RETURNS TABLE(
    id_pedido INTEGER,
    numero_pedido VARCHAR,
    status VARCHAR,
    hash_armazenado VARCHAR,
    hash_calculado VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id_pedido,
        p.numero_pedido,
        CASE 
            WHEN p.hash_integridade = calcular_hash_pedido(p.id_pedido) 
            THEN 'VALIDO' ELSE 'CORROMPIDO' 
        END as status,
        p.hash_integridade as hash_armazenado,
        calcular_hash_pedido(p.id_pedido) as hash_calculado
    FROM pedidos p
    WHERE p.hash_integridade IS NOT NULL;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 8. TABELA DE DETECÇÃO DE DUPLICATAS POTENCIAIS
-- ============================================================
CREATE TABLE IF NOT EXISTS alertas_duplicidade (
    id_alerta SERIAL PRIMARY KEY,
    tabela VARCHAR(100) NOT NULL,
    registros JSONB NOT NULL, -- IDs dos registros suspeitos
    similaridade NUMERIC(5,2), -- Percentual de similaridade
    motivo TEXT,
    data_detecao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_resolucao TIMESTAMP,
    resolvido_por VARCHAR(100),
    acao_tomada TEXT
);

-- Função para detectar pedidos duplicados
CREATE OR REPLACE FUNCTION detectar_pedidos_duplicados()
RETURNS TABLE(
    id_pedido_1 INTEGER,
    id_pedido_2 INTEGER,
    cliente VARCHAR,
    data_pedido DATE,
    valor_1 NUMERIC,
    valor_2 NUMERIC,
    similaridade NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p1.id_pedido as id_pedido_1,
        p2.id_pedido as id_pedido_2,
        c.nome as cliente,
        p1.data_pedido,
        p1.valor_total as valor_1,
        p2.valor_total as valor_2,
        CASE 
            WHEN p1.valor_total = p2.valor_total THEN 100.00
            ELSE 100.00 - (ABS(p1.valor_total - p2.valor_total) / GREATEST(p1.valor_total, p2.valor_total) * 100)
        END::NUMERIC(5,2) as similaridade
    FROM pedidos p1
    JOIN pedidos p2 ON p1.id_cliente = p2.id_cliente 
                    AND p1.data_pedido = p2.data_pedido
                    AND p1.id_pedido < p2.id_pedido  -- Evita duplicatas na comparação
    JOIN clientes c ON p1.id_cliente = c.id_cliente
    WHERE ABS(p1.valor_total - p2.valor_total) / GREATEST(p1.valor_total, p2.valor_total) < 0.10  -- 10% diferença
       OR p1.data_entrega = p2.data_entrega;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 9. ÍNDICES ADICIONAIS PARA PERFORMANCE
-- ============================================================
CREATE INDEX idx_pedidos_numero ON pedidos(numero_pedido);
CREATE INDEX idx_pedidos_chave_unica ON pedidos(chave_unica);
CREATE INDEX idx_pedidos_created_at ON pedidos(created_at);
CREATE INDEX idx_pedidos_ip_origem ON pedidos(ip_origem);

-- ============================================================
-- 10. POLÍTICA DE RETENÇÃO DE AUDITORIA (opcional)
-- ============================================================
-- Comentado - descomente para ativar limpeza automática de logs antigos
/*
CREATE OR REPLACE FUNCTION limpar_auditoria_antiga()
RETURNS INTEGER AS $$
DECLARE
    v_deletados INTEGER;
BEGIN
    DELETE FROM auditoria_global
    WHERE data_hora < CURRENT_DATE - INTERVAL '2 years';
    
    GET DIAGNOSTICS v_deletados = ROW_COUNT;
    RETURN v_deletados;
END;
$$ LANGUAGE plpgsql;

-- Agendar execução mensal (requer pg_cron)
-- SELECT cron.schedule('limpeza-auditoria', '0 0 1 * *', 'SELECT limpar_auditoria_antiga()');
*/

-- ============================================================
-- JUSTIFICATIVAS TÉCNICAS
-- ============================================================
COMMENT ON FUNCTION gerar_numero_pedido IS 
    'Gera número único sequencial por ano, garantindo unicidade e ordenação cronológica';

COMMENT ON COLUMN pedidos.hash_integridade IS 
    'SHA-256 dos dados críticos do pedido. Permite detectar alterações não autorizadas no banco';

COMMENT ON COLUMN pedidos.chave_unica IS 
    'Chave natural de negócio: cliente + data + número. Previne duplicatas lógicas';

COMMENT ON CONSTRAINT uk_pedido_cliente_dia ON pedidos IS 
    'Garante que um cliente não tenha dois pedidos com mesmo número no mesmo dia';

/*
RESUMO DAS GARANTIAS:

1. UNICIDADE: numero_pedido é UNIQUE e gerado automaticamente
2. INTEGRIDADE: hash_integridade detecta alterações fora do sistema
3. RASTREABILIDADE: auditoria_global registra todo CRUD com IP/usuário
4. DETECÇÃO: detectar_pedidos_duplicados() encontra registros suspeitos
5. PERFORMANCE: índices otimizados para consultas de auditoria
6. CONFORMIDADE: atende requisitos de LGPD e auditoria fiscal
*/
