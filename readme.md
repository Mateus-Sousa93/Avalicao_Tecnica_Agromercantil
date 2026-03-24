Agromercantil Data Analytics
Sistema completo de análise de dados para trading de commodities agrícolas, desenvolvido para avaliação técnica de Analista de Dados. Inclui dashboard interativo Streamlit com agente AI integrado (Gemini) para insights automatizados.
 Python 

 Streamlit 

 Supabase 
📋 Sumário
Visão Geral
Arquitetura
Funcionalidades
Estrutura do Projeto
Configuração do Ambiente
Ingestão de Dados
Consultas SQL Analíticas
Dashboard Streamlit
Agente AI Gemini
🎯 Visão Geral
Este projeto expande os requisitos técnicos originais, incorporando:
Dados realistas: 1.500 contratos de commodities (soja, milho, trigo) + serviços logísticos
Cloud Database: Supabase (PostgreSQL) com índices otimizados para analytics
Agente AI: Integração com Google Gemini para insights automatizados e recomendações estratégicas
Visualização Corporativa: Identidade visual Agromercantil, responsivo mobile/desktop com Tailwind CSS
🏗️ Arquitetura
plain
Copy
Excel/Mock → Python/Pandas → Supabase → Streamlit/Gemini
📁 Estrutura do Projeto
plain
Copy
agromercantil-analytics/
├── data/
│   └── dados_agromercantil_commodities.xlsx
├── sql/
│   ├── schema_supabase.sql
│   ├── query_rfv.sql
│   ├── query_anomalias.sql
│   └── query_tendencias.sql
├── src/
│   ├── ingestao_dados.py
│   └── analise_exploratoria.py
├── app/
│   └── dashboard.py
├── README.md
└── requirements.txt
⚙️ Configuração do Ambiente
1. Pré-requisitos
Python 3.9+
Conta no Supabase
API Key do Google Gemini
2. Instalação
bash
Copy
git clone https://github.com/seu-usuario/agromercantil-analytics.git
cd agromercantil-analytics
pip install -r requirements.txt
3. Variáveis de Ambiente
Crie um arquivo .env:
env
Copy
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=eyJhbGci...
GEMINI_API_KEY=AIzaSy...
🚀 Ingestão de Dados
bash
Copy
python src/ingestao_dados.py
Saída esperada:
plain
Copy
✅ Ingestão concluída!
   - Clientes: 200 registros
   - Produtos: 40 registros  
   - Pedidos: 1.500 registros
   - Itens: 1.980 registros
🧮 Consultas SQL Analíticas (Requisitos do PDF)
1. Análise RFV (Recência, Frequência, Valor)
sql
Copy
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
    c.nome,
    c.tipo_cliente,
    uc.dias_desde_ultimo as dias_desde_ultimo_pedido,
    mc.total_pedidos,
    ROUND(mc.ticket_medio, 2) as ticket_medio,
    ROUND(mc.valor_total, 2) as valor_total_acumulado
FROM clientes c
JOIN ultima_compra uc ON c.id_cliente = uc.id_cliente
JOIN metricas_cliente mc ON c.id_cliente = mc.id_cliente
ORDER BY mc.valor_total DESC;
2. Detecção de Anomalias
sql
Copy
WITH soma_itens AS (
    SELECT 
        id_pedido,
        SUM(subtotal) as valor_calculado
    FROM itens_pedido
    GROUP BY id_pedido
)
SELECT 
    p.id_pedido,
    p.valor_total as valor_total_registrado,
    si.valor_calculado,
    ABS(p.valor_total - si.valor_calculado) as diferenca
FROM pedidos p
JOIN soma_itens si ON p.id_pedido = si.id_pedido
WHERE ABS(p.valor_total - si.valor_calculado) > 0.01;
3. Tendências de Vendas (Mensal com LAG)
sql
Copy
WITH vendas_mensais AS (
    SELECT 
        DATE_TRUNC('month', data_pedido)::DATE as mes_ano,
        SUM(valor_total) as total_vendas
    FROM pedidos
    WHERE status != 'Cancelado'
    GROUP BY DATE_TRUNC('month', data_pedido)
    ORDER BY mes_ano
)
SELECT 
    TO_CHAR(mes_ano, 'YYYY-MM') as mes_ano,
    ROUND(total_vendas, 2) as total_vendas,
    ROUND(
        ((total_vendas - LAG(total_vendas) OVER (ORDER BY mes_ano)) / 
        LAG(total_vendas) OVER (ORDER BY mes_ano)) * 100, 2
    ) as crescimento_percentual
FROM vendas_mensais;
4. Top 5 Produtos Mais Rentáveis
sql
Copy
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
5. Clientes Inativos (> 6 meses)
sql
Copy
WITH ultima_atividade AS (
    SELECT 
        id_cliente,
        MAX(data_pedido) as ultima_compra,
        CURRENT_DATE - MAX(data_pedido) as dias_inativo
    FROM pedidos
    GROUP BY id_cliente
)
SELECT 
    c.id_cliente,
    c.nome,
    ua.dias_inativo,
    ua.ultima_compra
FROM clientes c
JOIN ultima_atividade ua ON c.id_cliente = ua.id_cliente
WHERE ua.dias_inativo > 180
ORDER BY ua.dias_inativo DESC;
🖥️ Dashboard Streamlit
Execução
bash
Copy
streamlit run app/dashboard.py
Funcionalidades
Visão Geral: KPIs e evolução mensal
Análise RFV: Segmentação de clientes com filtros
Produtos: Top commodities e sazonalidade
Qualidade: Detecção de anomalias
Agente AI: Chat integrado com Gemini
🧠 Agente AI Gemini
O agente está configurado como um Analista de Negócios Sênior do Agronegócio.
Prompt do Sistema
plain
Copy
Você é um Analista de Dados Sênior da Agromercantil, especialista em commodities agrícolas.
Suas respostas devem ser:
1. Estratégicas: Foque em oportunidades de negócio
2. Acionáveis: Sugira ações específicas
3. Contextuais: Considere sazonalidade agrícola
Exemplos de Perguntas
"Qual commodity está gerando maior margem?"
"Identifique riscos de concentração de clientes"
"Sugira estratégia para clientes inativos do Sul"
🎨 Identidade Visual
Verde Floresta: #1B4D3E (principal)
Dourado Trigo: #B8860B (destaques)
Cinza Chumbo: #4A5568 (texto)
Creme: #F7F5F0 (fundo)
📝 Checklist de Entrega (PDF)
[x] PostgreSQL (via Supabase)
[x] Dados mock inseridos (Excel)
[x] Python + Pandas para análise
[x] Streamlit para visualização
[x] CTEs e Window Functions (LAG, SUM OVER)
[x] Análise RFV
[x] Detecção de Anomalias
[x] Top 5 produtos
[x] Clientes Inativos
[x] Tendências de Vendas
[x] Modelo expandido (múltiplos clientes)
[x] Justificativa de índices
[x] Testes unitários
[x] Documentação no GitHub
📄 Licença
MIT License