#!/usr/bin/env python3
"""
Agromercantil Analytics
Flask Full Stack Application
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

# Configuração do Banco de Dados PostgreSQL
DATABASE_URL = os.environ.get(
    'DATABASE_URL', 
    'postgresql://agro_user:agro123456@localhost:5432/agromercantil'
)
engine = create_engine(DATABASE_URL)

# ============================================
# AUTENTICAÇÃO
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
# ROTAS DE AUTENTICAÇÃO
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
            error = "Usuário não encontrado!"
    
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ============================================
# DASHBOARD
# ============================================
@app.route('/dashboard')
@login_required
def dashboard():
    # Métricas principais
    metrics = get_metrics()
    
    # Gráficos
    charts = {
        'tendencias': get_tendencias_chart(),
        'rfv_segmentos': get_rfv_segmentos_chart(),
        'produtos': get_produtos_chart()
    }
    
    return render_template('dashboard.html', 
                         username=session.get('username'),
                         metrics=metrics,
                         charts=charts)

# ============================================
# CHATBOT
# ============================================
@app.route('/chat')
@login_required
def chat_page():
    return render_template('chat.html', username=session.get('username'))

@app.route('/api/chat', methods=['POST'])
@login_required
def chat_api():
    data = request.json
    message = data.get('message', '').lower()
    
    # Respostas simples baseadas em palavras-chave
    responses = {
        'faturamento': 'O faturamento total da Agromercantil é de R$ 5.2M no último ano.',
        'cliente': 'Temos 847 clientes ativos, sendo 234 classificados como "Campeões".',
        'produto': 'Soja é o produto mais vendido, representando 45% da receita.',
        'commodity': 'As principais commodities são: Soja, Milho, Café, Algodão e Trigo.',
        'ajuda': 'Posso responder sobre: faturamento, clientes, produtos, commodities e anomalias.',
    }
    
    response = "Desculpe, não entendi. Tente perguntar sobre: faturamento, clientes, produtos ou commodities."
    
    for key, value in responses.items():
        if key in message:
            response = value
            break
    
    return jsonify({'response': response})

# ============================================
# API - DADOS
# ============================================
@app.route('/api/rfv')
@login_required
def api_rfv():
    df = calcular_rfv()
    return jsonify(df.to_dict('records'))

@app.route('/api/tendencias')
@login_required
def api_tendencias():
    df = tendencias_mensais()
    return jsonify(df.to_dict('records'))

@app.route('/api/anomalias')
@login_required
def api_anomalias():
    df = detectar_anomalias()
    return jsonify(df.to_dict('records'))

@app.route('/api/inativos')
@login_required
def api_inativos():
    df = clientes_inativos()
    return jsonify(df.to_dict('records'))

# ============================================
# FUNÇÕES DE DADOS
# ============================================
def run_query(query, params=None):
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            return pd.DataFrame(result.fetchall(), columns=result.keys())
    except Exception as e:
        print(f"Erro na query: {e}")
        return pd.DataFrame()

def get_metrics():
    """Retorna métricas principais do dashboard"""
    try:
        df_pedidos = run_query("""
            SELECT COUNT(*) as total, SUM(valor_total) as valor 
            FROM pedidos WHERE status != 'Cancelado'
        """)
        df_clientes = run_query("SELECT COUNT(*) as total FROM clientes")
        
        return {
            'faturamento': f"R$ {df_pedidos['valor'].iloc[0]/1e6:.1f}M" if not df_pedidos.empty else "R$ 0M",
            'contratos': int(df_pedidos['total'].iloc[0]) if not df_pedidos.empty else 0,
            'clientes': int(df_clientes['total'].iloc[0]) if not df_clientes.empty else 0
        }
    except:
        return {'faturamento': 'R$ 0M', 'contratos': 0, 'clientes': 0}

def calcular_rfv():
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
               WHEN uc.dias_desde_ultimo <= 30 AND m.total_pedidos >= 5 THEN 'Campeão'
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

def top_produtos():
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
    FROM receita_produtos ORDER BY total_receita DESC LIMIT 5;
    """)

# ============================================
# GRÁFICOS PLOTLY
# ============================================
def get_tendencias_chart():
    df = tendencias_mensais()
    if df.empty:
        return None
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df['mes_ano'], 
        y=df['vendas'], 
        name='Vendas',
        marker_color='#112800'
    ))
    fig.add_trace(go.Scatter(
        x=df['mes_ano'], 
        y=df['crescimento'], 
        name='% Crescimento',
        yaxis='y2',
        line=dict(color='#F58220', width=3)
    ))
    
    fig.update_layout(
        yaxis2=dict(overlaying='y', side='right', title='%'),
        template='plotly_white',
        height=400,
        margin=dict(l=40, r=40, t=40, b=40),
        legend=dict(orientation='h', yanchor='bottom', y=1.02)
    )
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def get_rfv_segmentos_chart():
    df = calcular_rfv()
    if df.empty:
        return None
    
    dist = df['segmento'].value_counts()
    colors = {'Campeão': '#112800', 'Fiel': '#436900', 'Ativo': '#4A5568', 'Em Risco': '#E53E3E'}
    
    fig = px.pie(
        values=dist.values, 
        names=dist.index,
        color=dist.index,
        color_discrete_map=colors,
        hole=0.4
    )
    
    fig.update_layout(
        template='plotly_white',
        height=350,
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=-0.1)
    )
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def get_produtos_chart():
    df = top_produtos()
    if df.empty:
        return None
    
    fig = px.bar(
        df, 
        x='total_vendas', 
        y='nome',
        orientation='h',
        color_discrete_sequence=['#112800']
    )
    
    fig.update_layout(
        template='plotly_white',
        height=300,
        margin=dict(l=40, r=40, t=20, b=40),
        showlegend=False,
        xaxis_title='Total Vendas (R$)',
        yaxis_title=''
    )
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

# ============================================
# MAIN
# ============================================
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
