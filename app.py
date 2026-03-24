#!/usr/bin/env python3
"""
Agromercantil Analytics
Flask Full Stack Application
Design System: Material 3 - Precision Harvest
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from functools import wraps
import hashlib
import os
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.utils
import json

# Database
from sqlalchemy import create_engine, text

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'agromercantil-secret-key-2025')

# Configuracao do Banco de Dados PostgreSQL
# Local desenvolvimento
LOCAL_DB = "postgresql://agro_user:agro123456@localhost:5432/agromercantil"
# VPS - usar quando deployado na VPS
VPS_DB = "postgresql://agro_user:agro123456@localhost:5432/agromercantil"

DATABASE_URL = os.environ.get('DATABASE_URL', LOCAL_DB)

# Flag para verificar se banco esta disponivel
DB_AVAILABLE = False
engine = None

def check_db_connection():
    """Verifica se consegue conectar no banco"""
    global DB_AVAILABLE, engine
    try:
        if engine is None:
            engine = create_engine(DATABASE_URL, connect_args={'connect_timeout': 3})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        DB_AVAILABLE = True
        return True
    except Exception as e:
        DB_AVAILABLE = False
        return False

# Tentar conectar na inicializacao (nao falha se nao conseguir)
check_db_connection()

# ============================================
# DADOS MOCK (para visualizacao sem banco)
# ============================================
MOCK_METRICS = {
    'faturamento': 'R$ 5.2M',
    'ticket_medio': 'R$ 18.450',
    'contratos': 1248,
    'clientes': 847,
    'variacao_contratos': 'Estavel',
    'last_update': datetime.now().strftime('%H:%M')
}

MOCK_TOP_CLIENTES = [
    {'nome': 'Cooperativa Agricola Mato Grosso', 'valor_total': 2450000, 'segmento': 'Campeao'},
    {'nome': 'Agropecuaria Sul LTDA', 'valor_total': 1890000, 'segmento': 'Campeao'},
    {'nome': 'Fazenda Boa Vista', 'valor_total': 1240000, 'segmento': 'Fiel'},
    {'nome': 'Cerealista Brasil SA', 'valor_total': 980000, 'segmento': 'Fiel'},
    {'nome': 'Produtores Associados GO', 'valor_total': 765000, 'segmento': 'Ativo'},
]

MOCK_TOP_PRODUTOS = [
    {'nome': 'Soja Premium (GMO)', 'total_vendas': 4250000, 'percentual': 100},
    {'nome': 'Milho Amarelo Tipo 2', 'total_vendas': 3180000, 'percentual': 75},
    {'nome': 'Cafe Arabica SC-17', 'total_vendas': 2150000, 'percentual': 51},
    {'nome': 'Trigo Soft Red', 'total_vendas': 1680000, 'percentual': 40},
]

# ============================================
# AUTENTICACAO
# ============================================
USERS = {
    "admin": hashlib.sha256("admin123".encode()).hexdigest(),
    "avaliador": hashlib.sha256("agro2024".encode()).hexdigest(),
    "mateus": hashlib.sha256("231181mateu$".encode()).hexdigest()
}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'authenticated' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ============================================
# ROTAS DE AUTENTICACAO
# ============================================
@app.route('/')
def index():
    if 'authenticated' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if username in USERS:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            if password_hash == USERS[username]:
                session['authenticated'] = True
                session['username'] = username
                return redirect(url_for('dashboard'))
            else:
                error = "Senha incorreta!"
        else:
            error = "Usuario nao encontrado!"
    
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ============================================
# DASHBOARD PRINCIPAL
# ============================================
@app.route('/dashboard')
@login_required
def dashboard():
    global DB_AVAILABLE
    
    # Verificar se banco voltou (em desenvolvimento)
    if not DB_AVAILABLE:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            DB_AVAILABLE = True
            print("✅ Banco de dados reconectado")
        except:
            pass
    
    if DB_AVAILABLE:
        # Buscar metricas em tempo real
        metrics = get_metrics()
        top_clientes = get_top_clientes(5)
        top_produtos = get_top_produtos(4)
    else:
        # Usar dados mock
        metrics = MOCK_METRICS
        top_clientes = MOCK_TOP_CLIENTES
        top_produtos = MOCK_TOP_PRODUTOS
    
    # Gerar grafico de tendencias
    chart_tendencias = get_tendencias_chart()
    
    return render_template('dashboard.html', 
                         username=session.get('username'),
                         metrics=metrics,
                         top_clientes=top_clientes,
                         top_produtos=top_produtos,
                         chart_tendencias=chart_tendencias,
                         db_available=DB_AVAILABLE)

# ============================================
# PAGINAS ADICIONAIS (placeholders)
# ============================================
@app.route('/rfv')
@login_required
def rfv_page():
    """Pagina completa de analise RFV"""
    if DB_AVAILABLE:
        rfv_data = calcular_rfv()
        data = rfv_data.to_dict('records') if not rfv_data.empty else []
    else:
        data = MOCK_TOP_CLIENTES
    
    return render_template('rfv.html',
                         username=session.get('username'),
                         rfv_data=data,
                         db_available=DB_AVAILABLE)

@app.route('/produtos')
@login_required
def produtos_page():
    """Pagina de analise de produtos"""
    produtos = MOCK_TOP_PRODUTOS if not DB_AVAILABLE else get_top_produtos(10)
    return render_template('produtos.html',
                         username=session.get('username'),
                         produtos=produtos,
                         db_available=DB_AVAILABLE)

@app.route('/tendencias')
@login_required
def tendencias_page():
    """Pagina de tendencias detalhada"""
    chart_data = get_tendencias_chart()
    tend_data = tendencias_mensais().to_dict('records') if DB_AVAILABLE else []
    return render_template('tendencias.html',
                         username=session.get('username'),
                         tendencias=tend_data,
                         chart=chart_data,
                         db_available=DB_AVAILABLE)

@app.route('/inativos')
@login_required
def inativos_page():
    """Pagina de clientes inativos - Questao 6"""
    if DB_AVAILABLE:
        inativos = clientes_inativos().to_dict('records')
    else:
        inativos = [
            {'nome': 'Fazenda Sao Joao', 'tipo_cliente': 'Produtor', 'regiao': 'Mato Grosso', 'dias_inativo': 245, 'ultima_compra': '2024-07-15'},
            {'nome': 'Cooperativa Oeste', 'tipo_cliente': 'Cooperativa', 'regiao': 'Goias', 'dias_inativo': 198, 'ultima_compra': '2024-09-02'},
            {'nome': 'Agropecuaria Norte', 'tipo_cliente': 'Empresa', 'regiao': 'Parana', 'dias_inativo': 312, 'ultima_compra': '2024-05-20'},
            {'nome': 'Fazenda Primavera', 'tipo_cliente': 'Produtor', 'regiao': 'Bahia', 'dias_inativo': 189, 'ultima_compra': '2024-09-18'},
        ]
    
    return render_template('inativos.html',
                         username=session.get('username'),
                         inativos=inativos,
                         db_available=DB_AVAILABLE)

@app.route('/anomalias')
@login_required
def anomalias_page():
    """Pagina de anomalias - Questao 7"""
    if DB_AVAILABLE:
        anomalias = detectar_anomalias().to_dict('records')
    else:
        anomalias = [
            {'id_pedido': 1542, 'data_pedido': '2024-03-15', 'cliente': 'Cooperativa MT', 'registrado': 45000.00, 'valor_calculado': 42500.00, 'diferenca': 2500.00},
            {'id_pedido': 1621, 'data_pedido': '2024-03-18', 'cliente': 'Fazenda Sul', 'registrado': 12800.00, 'valor_calculado': 15600.00, 'diferenca': 2800.00},
            {'id_pedido': 1893, 'data_pedido': '2024-04-02', 'cliente': 'Cerealista BR', 'registrado': 89000.00, 'valor_calculado': 87500.00, 'diferenca': 1500.00},
        ]
    
    return render_template('anomalias.html',
                         username=session.get('username'),
                         anomalias=anomalias,
                         db_available=DB_AVAILABLE)

@app.route('/analise')
@login_required
def analise_page():
    """Pagina de analise exploratoria - Questao Python"""
    # Dados para os graficos
    charts = {
        'histogram': get_histogram_data(),
        'boxplot': get_boxplot_data(),
        'scatter': get_scatter_data(),
        'correlation': get_correlation_data()
    }
    
    return render_template('analise.html',
                         username=session.get('username'),
                         charts=charts,
                         db_available=DB_AVAILABLE)

# ============================================
# CHATBOT API
# ============================================
@app.route('/api/chat', methods=['POST'])
@login_required
def chat_api():
    data = request.json
    message = data.get('message', '').lower()
    
    # Respostas baseadas em dados mock ou reais
    if DB_AVAILABLE:
        metrics = get_metrics()
        top_prod = get_top_produtos(1)
        produto = top_prod[0]['nome'] if top_prod else 'N/A'
    else:
        metrics = MOCK_METRICS
        produto = MOCK_TOP_PRODUTOS[0]['nome']
    
    responses = {
        'faturamento': f"O faturamento total e de {metrics['faturamento']}.",
        'cliente': f"Temos {metrics['clientes']} clientes ativos no sistema.",
        'produto': f"O produto mais vendido e {produto}.",
        'ticket': f"O ticket medio e de {metrics['ticket_medio']}.",
        'contrato': f"Temos {metrics['contratos']} contratos ativos.",
        'ajuda': 'Posso responder sobre: faturamento, clientes, produtos, ticket medio e contratos.',
    }
    
    response = "Desculpe, nao entendi. Tente perguntar sobre faturamento, clientes ou produtos."
    
    for key, value in responses.items():
        if key in message:
            response = value
            break
    
    return jsonify({'response': response})

# ============================================
# APIs - DADOS
# ============================================
@app.route('/api/rfv')
@login_required
def api_rfv():
    if not DB_AVAILABLE:
        return jsonify(MOCK_TOP_CLIENTES)
    df = calcular_rfv()
    return jsonify(df.to_dict('records'))

@app.route('/api/tendencias')
@login_required
def api_tendencias():
    if not DB_AVAILABLE:
        return jsonify([])
    df = tendencias_mensais()
    return jsonify(df.to_dict('records'))

@app.route('/api/anomalias')
@login_required
def api_anomalias():
    if not DB_AVAILABLE:
        return jsonify([])
    df = detectar_anomalias()
    return jsonify(df.to_dict('records'))

@app.route('/api/inativos')
@login_required
def api_inativos():
    if not DB_AVAILABLE:
        return jsonify([])
    df = clientes_inativos()
    return jsonify(df.to_dict('records'))

# ============================================
# FUNCOES DE DADOS
# ============================================
def run_query(query, params=None):
    """Executa query SQL e retorna DataFrame"""
    global DB_AVAILABLE
    if not DB_AVAILABLE and not check_db_connection():
        return pd.DataFrame()
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            return pd.DataFrame(result.fetchall(), columns=result.keys())
    except Exception as e:
        print(f"Erro na query: {e}")
        DB_AVAILABLE = False
        return pd.DataFrame()

def get_metrics():
    """Retorna metricas principais do dashboard"""
    if not DB_AVAILABLE:
        return MOCK_METRICS
    
    try:
        df_pedidos = run_query("""
            SELECT 
                COUNT(*) as total, 
                SUM(valor_total) as valor,
                AVG(valor_total) as ticket_medio
            FROM pedidos 
            WHERE status != 'Cancelado'
        """)
        df_clientes = run_query("SELECT COUNT(*) as total FROM clientes")
        
        last_update = datetime.now().strftime('%H:%M')
        faturamento = df_pedidos['valor'].iloc[0] if not df_pedidos.empty else 0
        ticket_medio = df_pedidos['ticket_medio'].iloc[0] if not df_pedidos.empty else 0
        
        return {
            'faturamento': f"R$ {faturamento/1e6:.1f}M" if faturamento else "R$ 0M",
            'ticket_medio': f"R$ {ticket_medio:,.0f}".replace(',', '.') if ticket_medio else "R$ 0",
            'contratos': int(df_pedidos['total'].iloc[0]) if not df_pedidos.empty else 0,
            'clientes': int(df_clientes['total'].iloc[0]) if not df_clientes.empty else 0,
            'variacao_contratos': 'Estavel',
            'last_update': last_update
        }
    except Exception as e:
        print(f"Erro em get_metrics: {e}")
        return MOCK_METRICS

def get_top_clientes(limit=5):
    """Retorna top clientes por valor total"""
    if not DB_AVAILABLE:
        return MOCK_TOP_CLIENTES[:limit]
    
    df = calcular_rfv()
    if df.empty:
        return MOCK_TOP_CLIENTES[:limit]
    
    top = df.nlargest(limit, 'valor_total')
    return top.to_dict('records')

def get_top_produtos(limit=5):
    """Retorna top produtos mais vendidos"""
    if not DB_AVAILABLE:
        return MOCK_TOP_PRODUTOS[:limit]
    
    df = top_produtos_db()
    if df.empty:
        return MOCK_TOP_PRODUTOS[:limit]
    
    max_valor = df['total_vendas'].max()
    df['percentual'] = (df['total_vendas'] / max_valor * 100).round(0)
    return df.head(limit).to_dict('records')

def calcular_rfv():
    """Questao 2: RFV - Usa CTE + Window Functions"""
    return run_query("""
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
               WHEN uc.dias_desde_ultimo <= 30 AND m.total_pedidos >= 5 THEN 'Campeao'
               WHEN uc.dias_desde_ultimo <= 60 AND m.total_pedidos >= 3 THEN 'Fiel'
               WHEN uc.dias_desde_ultimo <= 90 THEN 'Ativo'
               ELSE 'Em Risco'
           END as segmento
    FROM clientes c
    JOIN ultima_compra uc ON c.id_cliente = uc.id_cliente
    JOIN metricas m ON c.id_cliente = m.id_cliente
    ORDER BY m.valor_total DESC;
    """)

def tendencias_mensais():
    """Questao 5: Tendencias - Usa CTE + LAG"""
    return run_query("""
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
    """)

def detectar_anomalias():
    """Questao 7: Anomalias - Usa CTE"""
    return run_query("""
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
    ORDER BY diferenca DESC;
    """)

def clientes_inativos():
    """Questao 6: Clientes Inativos - Usa CTE"""
    return run_query("""
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
    """)

def top_produtos_db():
    """Questao 4: Top 5 Produtos - Usa CTE"""
    return run_query("""
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
    FROM receita_produtos ORDER BY total_receita DESC;
    """)

# ============================================
# DADOS PARA ANALISE EXPLORATORIA
# ============================================
def get_histogram_data():
    """Dados para histograma de distribuicao de valores"""
    # Mock data - em producao viria do banco
    return {
        'bins': ['0-10k', '10-50k', '50-100k', '100-500k', '500k+'],
        'counts': [45, 128, 89, 34, 12]
    }

def get_boxplot_data():
    """Dados para box plot por segmento"""
    return {
        'segmentos': ['Campeao', 'Fiel', 'Ativo', 'Em Risco'],
        'data': [
            [45000, 52000, 48000, 61000, 55000, 58000, 49000],  # Campeao
            [35000, 28000, 42000, 38000, 31000, 36000, 39000],  # Fiel
            [25000, 18000, 22000, 28000, 15000, 19000, 21000],  # Ativo
            [12000, 8000, 15000, 11000, 9000, 5000, 7000],      # Em Risco
        ]
    }

def get_scatter_data():
    """Dados para scatter plot valor vs quantidade"""
    import random
    random.seed(42)
    pontos = []
    for i in range(50):
        qtd = random.randint(1, 20)
        valor = qtd * random.uniform(2000, 5000) + random.uniform(-5000, 5000)
        pontos.append({'x': qtd, 'y': round(valor, 2)})
    return pontos

def get_correlation_data():
    """Dados para heatmap de correlacao"""
    return {
        'variables': ['Valor', 'Quantidade', 'Ticket', 'Frequencia'],
        'matrix': [
            [1.0, 0.85, 0.92, 0.45],
            [0.85, 1.0, 0.65, 0.38],
            [0.92, 0.65, 1.0, 0.52],
            [0.45, 0.38, 0.52, 1.0]
        ]
    }

# ============================================
# GRAFICOS PLOTLY
# ============================================
def get_tendencias_chart():
    """Gera grafico de tendencias em formato Plotly"""
    
    # Dados mock para o grafico (quando nao tem banco)
    mock_data = {
        'mes_ano': ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'],
        'vendas': [2.1, 2.3, 2.8, 3.2, 3.5, 3.8, 4.1, 4.5, 4.8, 5.1, 5.3, 5.2],
        'crescimento': [0, 9.5, 21.7, 14.3, 9.4, 8.6, 7.9, 9.8, 6.7, 6.3, 3.9, -1.9]
    }
    
    if DB_AVAILABLE:
        df = tendencias_mensais()
        if not df.empty:
            df = df.iloc[::-1]  # Ordem cronologica
            mock_data = {
                'mes_ano': df['mes_ano'].tolist(),
                'vendas': [v/1e6 for v in df['vendas'].tolist()],
                'crescimento': df['crescimento'].fillna(0).tolist()
            }
    
    fig = go.Figure()
    
    # Barra de vendas
    fig.add_trace(go.Bar(
        x=mock_data['mes_ano'], 
        y=mock_data['vendas'], 
        name='Vendas (R$ M)',
        marker_color='#112800'
    ))
    
    # Linha de crescimento
    fig.add_trace(go.Scatter(
        x=mock_data['mes_ano'], 
        y=mock_data['crescimento'], 
        name='Crescimento %',
        yaxis='y2',
        line=dict(color='#F58220', width=3),
        mode='lines+markers'
    ))
    
    fig.update_layout(
        yaxis=dict(
            title='Vendas (R$ M)',
            tickprefix='R$ ',
            gridcolor='rgba(116, 121, 108, 0.1)'
        ),
        yaxis2=dict(
            overlaying='y',
            side='right',
            title='Crescimento %',
            tickformat='.1f',
            ticksuffix='%',
            gridcolor='rgba(116, 121, 108, 0.05)'
        ),
        xaxis=dict(
            gridcolor='rgba(116, 121, 108, 0.1)'
        ),
        template='plotly_white',
        margin=dict(l=50, r=50, t=40, b=40),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1,
            font=dict(size=10)
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        hovermode='x unified'
    )
    
    return json.loads(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))

# ============================================
# MAIN
# ============================================
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
