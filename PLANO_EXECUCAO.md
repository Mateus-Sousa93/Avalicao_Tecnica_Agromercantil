# 🌾 PLANO DE EXECUÇÃO - AVALIAÇÃO TÉCNICA AGROMERCANTIL

> **Objetivo:** Implementar projeto completo seguindo RIGOROSAMENTE as regras do PDF da avaliação técnica, rodando na VPS para economizar custos de Supabase.

---

## 📋 REGRAS DO PDF (NÃO NEGOCIÁVEIS)

### Requisitos Técnicos Obrigatórios:
1. ✅ **PostgreSQL** para SQL (PDF: "Utilize PostgreSQL para responder às questões de SQL")
2. ✅ **Python + Streamlit** para visualização (PDF: "Utilize Python com Streamlit para apresentar os resultados")
3. ✅ **Dados mock inseridos manualmente** (PDF: "Insira os dados manualmente, simulando cenário real")
4. ✅ **GitHub documentado** com prints (PDF: "A avaliação deve ser documentada no GitHub, incluindo prints")
5. ✅ **Justificar índices e otimizações** (PDF: "Justifique a criação de índices e outras otimizações")

### Questões SQL Obrigatórias (pontuação total: 175 pts):
| # | Questão | Pontos | Status |
|---|---------|--------|--------|
| 1 | Inserção e Mock de Dados + Justificativa | 20 | ⬜ |
| 2 | Análise RFV (CTE + Window Functions) | 30 | ⬜ |
| 3 | Alteração Modelo (múltiplos clientes/pedido) | 20 | ⬜ |
| 4 | Top 5 Produtos Mais Rentáveis (último ano) | 30 | ⬜ |
| 5 | Tendências de Vendas (CTE + LAG) | 30 | ⬜ |
| 6 | Clientes Inativos (> 6 meses) | 20 | ⬜ |
| 7 | Detecção de Anomalias | 25 | ⬜ |
| 8 | Otimização e Indexação | 20 | ⬜ |

### Questões Python/Streamlit (pontuação total: 80 pts):
| # | Questão | Pontos | Status |
|---|---------|--------|--------|
| 1 | Apresentação dos Dados (dashboards interativos, filtros) | 50 | ⬜ |
| 2 | Análise Exploratória (Pandas + Matplotlib/gráficos) | 30 | ⬜ |

---

## 🏗️ ARQUITETURA DO PROJETO

```
agromercantil-analytics/
├── 📁 data/                          # Dados mock/Excel
│   └── dados_agromercantil_commodities.xlsx
│
├── 📁 sql/                           # Queries SQL separadas por questão
│   ├── schema.sql                    # DDL completo (tabelas + índices)
│   ├── query_rfv.sql                 # Questão 2: RFV
│   ├── query_top5_produtos.sql       # Questão 4: Top 5 produtos
│   ├── query_tendencias.sql          # Questão 5: Tendências mensais
│   ├── query_clientes_inativos.sql   # Questão 6: Clientes inativos
│   ├── query_anomalias.sql           # Questão 7: Anomalias
│   └── query_modelo_expandido.sql    # Questão 3: Múltiplos clientes
│
├── 📁 src/                           # Scripts Python de análise
│   ├── ingestao_dados.py             # Carrega Excel → PostgreSQL
│   ├── analise_exploratoria.py       # EDA com Pandas/Matplotlib
│   └── testes_unitarios.py           # Testes automatizados
│
├── 📁 app/                           # Dashboard Streamlit
│   └── dashboard.py                  # Interface principal
│
├── 📁 docs/                          # Documentação + prints
│   ├── prints_consultas/
│   └── prints_dashboard/
│
├── .env                              # Variáveis de ambiente (NÃO COMMITAR)
├── .env.example                      # Template do .env
├── requirements.txt                  # Dependências Python
├── setup_vps.md                      # Guia de deploy na VPS
└── README.md                         # Documentação principal
```

---

## 🎯 FASES DE IMPLEMENTAÇÃO

### 🔧 FASE 1: Configurar Ambiente Local
**Objetivo:** Preparar o ambiente de desenvolvimento

**Tarefas:**
- [ ] Criar estrutura de pastas (data/, sql/, src/, docs/)
- [ ] Instalar PostgreSQL local (ou usar Docker)
- [ ] Criar banco `agromercantil` e usuário `agro_user`
- [ ] Configurar `.env` com DATABASE_URL local
- [ ] Instalar dependências: `pip install -r requirements.txt`

**Entregável:** Ambiente funcional rodando localmente

---

### 🗄️ FASE 2: Schema SQL e Dados Mock
**Objetivo:** Criar tabelas conforme PDF e popular com dados

**Tarefas:**
- [ ] Executar `schema.sql` (já temos) criando:
  - `clientes` (200 registros)
  - `produtos` (40 registros)
  - `pedidos` (1.500 registros)
  - `itens_pedido` (~1.980 registros)
  - `pedido_clientes` (modelo expandido)
- [ ] **JUSTIFICAR no código:** Cada índice criado (requisito PDF)
- [ ] Criar dados mock variados:
  - Diferentes categorias (Soja, Milho, Trigo, Serviços)
  - Variação de preços realistas
  - Datas distribuídas ao longo de 1+ ano
  - Clientes de diferentes regiões

**Justificativa dos Dados (PDF requer):**
- Commodities agrícolas refletem cenário real do agro brasileiro
- Variação de preços simula volatilidade do mercado
- Diferentes tipos de cliente (Produtor, Cooperativa, Trading)
- Período de 12+ meses permite análise de tendências

---

### 🐍 FASE 3: Scripts Python (Ingestão + Análise)
**Objetivo:** Implementar ingestão e análise exploratória

**Tarefas:**
- [ ] Adaptar `ingestao.py` para ler Excel e inserir no PostgreSQL
- [ ] Criar `analise_exploratoria.py` com:
  - Estatísticas descritivas (Pandas)
  - Histogramas de preços/volumes
  - Scatter plots (correlações)
  - Box plots (distribuições)
- [ ] Salvar outputs em `docs/analise_exploratoria/`

**Entregável:** Scripts funcionando com saída visual

---

### 📊 FASE 4: Queries SQL Analíticas
**Objetivo:** Implementar TODAS as 8 questões SQL do PDF

#### Questão 2: RFV (Recência, Frequência, Valor)
```sql
-- Deve usar: CTE + Window Functions (SUM OVER, COUNT OVER) + LAG
-- Retornar: id_cliente, dias_desde_ultimo_pedido, total_pedidos, ticket_medio
```

#### Questão 3: Modelo Expandido
```sql
-- Deve permitir múltiplos clientes por pedido (compras compartilhadas)
-- Usar tabela pedido_clientes com percentual_rateio
```

#### Questão 4: Top 5 Produtos
```sql
-- Deve usar: CTE
-- Retornar: id_produto, nome, total_vendas (soma quantidade * preco_unitario)
-- Filtro: último ano
```

#### Questão 5: Tendências de Vendas
```sql
-- Deve usar: CTE + Window Functions + LAG
-- Retornar: mes_ano, total_vendas, crescimento_percentual
```

#### Questão 6: Clientes Inativos
```sql
-- Deve usar: CTE + Window Functions
-- Retornar: clientes sem pedidos nos últimos 6 meses
```

#### Questão 7: Detecção de Anomalias
```sql
-- Deve usar: CTE
-- Retornar: id_pedido, valor_total_registrado, valor_calculado
-- Onde: valor_total ≠ soma(itens)
```

#### Questão 8: Otimização
```sql
-- Documentar justificativa de cada índice nos comentários
-- Explicar estratégia de otimização
```

**Entregável:** Arquivos .sql separados, todos testados

---

### 🎨 FASE 5: Dashboard Streamlit
**Objetivo:** Criar interface visual completa

**Funcionalidades obrigatórias (PDF):**
- [ ] Exibir dados processados em dashboards interativos
- [ ] Gráficos e tabelas interativas
- [ ] Filtros: clientes por atividade, pedidos por data
- [ ] Seleção de períodos para análise

**Páginas do Dashboard:**
1. **Visão Geral:** KPIs, evolução mensal, alertas
2. **Análise RFV:** Segmentação de clientes, distribuição
3. **Produtos:** Top commodities, rentabilidade
4. **Tendências:** Gráfico mensal com crescimento percentual
5. **Anomalias:** Lista de pedidos com divergências
6. **Clientes Inativos:** Tabela de clientes sem compras 6m+

**Identidade Visual (já definida):**
- Verde Floresta: #1B4D3E
- Dourado Trigo: #B8860B
- Cinza Chumbo: #4A5568
- Creme: #F7F5F0

---

### 🧪 FASE 6: Testes Unitários
**Objetivo:** Garantir qualidade do código

**Testes obrigatórios:**
- [ ] Testar conexão com PostgreSQL
- [ ] Testar queries SQL (retornam dados)
- [ ] Testar cálculos do RFV
- [ ] Testar detecção de anomalias
- [ ] Testar filtros do dashboard

---

### 🚀 FASE 7: Deploy na VPS
**Objetivo:** Subir para VPS e documentar

**Tarefas:**
- [ ] Instalar PostgreSQL na VPS
- [ ] Criar banco e usuário
- [ ] Executar schema.sql
- [ ] Rodar ingestão de dados
- [ ] Configurar `.env` com dados da VPS
- [ ] Rodar Streamlit: `streamlit run app/dashboard.py --server.address 0.0.0.0`
- [ ] Configurar firewall (porta 8501, 5432)
- [ ] **Tirar prints das consultas SQL rodando**
- [ ] **Tirar prints do dashboard funcionando**

---

## 📊 CRITÉRIOS DE AVALIAÇÃO DO PDF (CHECKLIST)

| Critério | Peso | Como Atender |
|----------|------|--------------|
| Precisão (resultados corretos) | 20% | Todas queries retornando dados corretos |
| Complexidade e Eficiência | 20% | Uso de CTEs, Window Functions, JOINs otimizados |
| Clareza e Estruturação | 20% | Código comentado, pastas organizadas |
| Visualização e Interatividade | 20% | Dashboard Streamlit com filtros funcionando |
| Justificativa das Decisões | 20% | Documentar mock de dados e otimizações |

---

## 📝 ENTREGÁVEIS FINAIS (GitHub)

1. **Repositório Git** com:
   - Código completo organizado
   - README.md explicativo
   - Requirements.txt
   - Scripts SQL separados

2. **Documentação em `docs/`:**
   - Prints das consultas SQL executando
   - Prints do dashboard Streamlit
   - Justificativa dos dados mock
   - Justificativa dos índices

3. **VPS rodando:**
   - Dashboard acessível via IP:8501
   - PostgreSQL acessível (se necessário)

---

## ⚡ PRÓXIMOS PASSOS IMEDIATOS

1. **Aprovar este plano**
2. **Iniciar FASE 1:** Configurar ambiente local
3. **Me informar:** VPS já está pronta? Qual o IP? PostgreSQL já instalado?

---

**Status:** ⏳ Aguardando aprovação do plano para iniciar
