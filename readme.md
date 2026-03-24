# Agromercantil Analytics

Sistema de análise de commodities agrícolas desenvolvido para avaliação técnica de Analista de Dados.

## Descrição do Projeto

Plataforma de business intelligence para análise de dados comerciais de commodities agrícolas. O sistema permite visualizar tendências de vendas, segmentação de clientes (RFV), detecção de anomalias em pedidos e identificação de clientes inativos.

## Arquitetura

A aplicação foi desenvolvida utilizando arquitetura MVC com separação clara entre camada de apresentação, lógica de negócio e acesso a dados.

## Tecnologias Utilizadas

### Backend
- **Python 3.13**: Linguagem principal pela robustez em manipulação de dados e ampla biblioteca de ciência de dados
- **Flask 3.1**: Framework web minimalista que permite controle total sobre o fluxo de requisições e respostas, sem abstrações desnecessárias
- **SQLAlchemy 2.0**: ORM para abstração de consultas SQL mantendo a flexibilidade de queries complexas quando necessário
- **PostgreSQL**: Banco de dados relacional escolhido pelo suporte nativo a CTEs (Common Table Expressions) e funções de janela, essenciais para as análises RFV e tendências
- **Pandas 3.0**: Manipulação e análise estatística dos dados

### Frontend
- **Tailwind CSS**: Framework CSS utilitário que permite customização visual precisa sem conflitos com classes pré-definidas
- **Plotly.js**: Biblioteca de gráficos interativos com suporte a eventos de usuário e exportação de imagens
- **Jinja2**: Templates HTML com herança e macros para reaproveitamento de componentes

### Infraestrutura
- **python-dotenv**: Gerenciamento de variáveis de ambiente para configurações de desenvolvimento/produção
- **Gunicorn**: Servidor WSGI para deploy em produção

## Justificativa das Escolhas

### Por que Flask ao invés de Streamlit?

Embora o requisito original mencionasse Streamlit, optamos por Flask pelos seguintes motivos técnicos:

1. **Controle de Layout**: Streamlit impõe uma estrutura de containers que dificulta layouts complexos como split-screen e dashboards personalizados. Flask com Jinja2 permite HTML/CSS puro.

2. **Performance**: Streamlit reexecuta o script Python a cada interação do usuário. Flask mantém estado de sessão e processa apenas requisições necessárias.

3. **Manutenção**: Código Streamlit mistura lógica de negócio com apresentação. A separação MVC do Flask facilita testes unitários e manutenção.

4. **Escalabilidade**: Flask permite adicionar API REST, autenticação customizada e caching de forma modular.

### Por que Tailwind ao invés de Bootstrap/Material UI?

Tailwind oferece granularidade de estilos sem sobrescrever classes globais. Isso permitiu implementar o design system Material 3 exatamente conforme especificações de cores, tipografia e espaçamento, sem conflitos com componentes pré-estilizados.

## Funcionalidades Implementadas

### Módulo de Autenticação
- Sistema de login com sessão server-side
- Hash SHA-256 para armazenamento seguro de credenciais
- Proteção CSRF em formulários

### Módulo de Analytics

**1. Análise RFV (Recência, Frequência, Valor)**
- Segmentação automática de clientes em categorias: Campeão, Fiel, Ativo, Em Risco
- Utilização de CTEs e window functions (SUM OVER, COUNT OVER, LAG)
- Visualização em gráfico de pizza interativo

**2. Tendências de Vendas**
- Evolução mensal de faturamento
- Cálculo de crescimento percentual mês a mês usando LAG
- Gráfico combinado de barras e linhas

**3. Detecção de Anomalias**
- Identificação de pedidos onde valor_total não corresponde à soma dos itens
- Alertas em tempo real para divergências contábeis

**4. Clientes Inativos**
- Listagem de clientes sem compras nos últimos 180 dias
- Indicadores para estratégias de retenção

**5. Top Produtos**
- Ranking dos 5 produtos mais rentáveis do último ano
- Gráfico de barras horizontal com valores monetários

### Módulo de Assistente Virtual
- Interface de chat para consultas em linguagem natural
- Sugestões de perguntas frequentes
- Respostas contextualizadas baseadas em dados reais do sistema

## Estrutura do Projeto

```
├── app.py                  # Aplicação Flask principal
├── requirements.txt        # Dependências Python
├── schema.sql             # DDL do banco de dados
├── templates/             # Templates Jinja2
│   ├── login.html        # Tela de autenticação
│   ├── dashboard.html    # Painel principal
│   └── chat.html         # Interface do assistente
├── static/               # Assets estáticos
│   ├── css/             # Estilos customizados
│   ├── js/              # Scripts JavaScript
│   └── images/          # Imagens e logos
├── old/                 # Arquivos de referência (streamlit legado)
└── venv/                # Ambiente virtual Python
```

## Configuração do Ambiente

### Requisitos
- Python 3.13 ou superior
- PostgreSQL 14 ou superior
- Acesso à internet (para CDN do Tailwind e Plotly)

### Instalação

1. Clone o repositório:
```bash
git clone <repository-url>
cd Avalicao_Tecnica_Agromercantil
```

2. Crie e ative o ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure as variáveis de ambiente:
```bash
cp .env.example .env
# Edite .env com suas configurações de banco de dados
```

5. Execute a aplicação:
```bash
python app.py
```

A aplicação estará disponível em `http://localhost:5000`

### Deploy em Produção

Para deploy em servidor de produção:

```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

## Otimizações Realizadas

### Banco de Dados
- Criação de índices em colunas frequentemente filtradas (data_pedido, id_cliente)
- Utilização de CTEs para legibilidade e reuso de subconsultas
- Funções de janela para evitar joins desnecessários

### Aplicação
- Caching de conexões SQLAlchemy
- Lazy loading de gráficos Plotly (carregamento sob demanda)
- Compressão de assets estáticos

## Consultas SQL Destaque

### RFV - Segmentação de Clientes
```sql
WITH ultima_compra AS (
    SELECT id_cliente, 
           MAX(data_pedido) as ultima_data,
           CURRENT_DATE - MAX(data_pedido) as dias_desde_ultimo
    FROM pedidos 
    WHERE status != 'Cancelado' 
    GROUP BY id_cliente
),
metricas AS (
    SELECT id_cliente, 
           COUNT(*) as total_pedidos,
           ROUND(AVG(valor_total), 2) as ticket_medio,
           ROUND(SUM(valor_total), 2) as valor_total
    FROM pedidos 
    WHERE status != 'Cancelado' 
    GROUP BY id_cliente
)
SELECT c.id_cliente, c.nome, 
       uc.dias_desde_ultimo, 
       m.total_pedidos,
       m.ticket_medio, 
       m.valor_total,
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
```

## Licença

Projeto desenvolvido para fins de avaliação técnica.

## Contato

Desenvolvedor: Mateus Sousa
Avaliação: Analista de Dados - Agromercantil
