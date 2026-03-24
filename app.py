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

# Google Gemini - usando nova biblioteca google-genai
from dotenv import load_dotenv
load_dotenv()

GEMINI_AVAILABLE = False
gemini_client = None

try:
    from google import genai
    from google.genai import types
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    if GEMINI_API_KEY:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        GEMINI_AVAILABLE = True
        print("OK: Gemini API configurada")
    else:
        print("AVISO: GEMINI_API_KEY nao encontrada no .env")
except ImportError:
    print("AVISO: Biblioteca google-genai nao instalada")

app = Flask(__name__, static_folder='static', static_url_path='/static')
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
    {'id_cliente': 1, 'nome': 'Cooperativa Agricola Mato Grosso', 'tipo_cliente': 'Cooperativa', 'regiao': 'Mato Grosso', 'dias_desde_ultimo': 15, 'ultima_data': '2025-03-10', 'total_pedidos': 12, 'ticket_medio': 204167, 'valor_total': 2450000, 'segmento': 'Campeao'},
    {'id_cliente': 2, 'nome': 'Agropecuaria Sul LTDA', 'tipo_cliente': 'Empresa', 'regiao': 'Rio Grande do Sul', 'dias_desde_ultimo': 22, 'ultima_data': '2025-03-05', 'total_pedidos': 8, 'ticket_medio': 236250, 'valor_total': 1890000, 'segmento': 'Campeao'},
    {'id_cliente': 3, 'nome': 'Fazenda Boa Vista', 'tipo_cliente': 'Produtor', 'regiao': 'Goias', 'dias_desde_ultimo': 45, 'ultima_data': '2025-02-10', 'total_pedidos': 6, 'ticket_medio': 206667, 'valor_total': 1240000, 'segmento': 'Fiel'},
    {'id_cliente': 4, 'nome': 'Cerealista Brasil SA', 'tipo_cliente': 'Empresa', 'regiao': 'Sao Paulo', 'dias_desde_ultimo': 30, 'ultima_data': '2025-02-25', 'total_pedidos': 5, 'ticket_medio': 196000, 'valor_total': 980000, 'segmento': 'Fiel'},
    {'id_cliente': 5, 'nome': 'Produtores Associados GO', 'tipo_cliente': 'Cooperativa', 'regiao': 'Goias', 'dias_desde_ultimo': 60, 'ultima_data': '2025-01-25', 'total_pedidos': 4, 'ticket_medio': 191250, 'valor_total': 765000, 'segmento': 'Ativo'},
]

MOCK_TOP_PRODUTOS = [
    {'nome': 'Soja Premium (GMO)', 'total_vendas': 4250000, 'percentual': 100},
    {'nome': 'Milho Amarelo Tipo 2', 'total_vendas': 3180000, 'percentual': 75},
    {'nome': 'Cafe Arabica SC-17', 'total_vendas': 2150000, 'percentual': 51},
    {'nome': 'Trigo Soft Red', 'total_vendas': 1680000, 'percentual': 40},
]

MOCK_CLIENTES = [
    {'id_cliente': 1, 'nome': 'Cooperativa Agricola MT', 'tipo_cliente': 'Cooperativa', 'regiao': 'Mato Grosso', 'estado': 'MT', 'data_cadastro': '15/01/2020', 'limite_credito': 5000000},
    {'id_cliente': 2, 'nome': 'Agropecuaria Sul LTDA', 'tipo_cliente': 'Empresa', 'regiao': 'Rio Grande do Sul', 'estado': 'RS', 'data_cadastro': '22/03/2021', 'limite_credito': 3500000},
    {'id_cliente': 3, 'nome': 'Fazenda Boa Vista', 'tipo_cliente': 'Produtor', 'regiao': 'Goias', 'estado': 'GO', 'data_cadastro': '10/06/2022', 'limite_credito': 800000},
    {'id_cliente': 4, 'nome': 'Cerealista Brasil SA', 'tipo_cliente': 'Empresa', 'regiao': 'Sao Paulo', 'estado': 'SP', 'data_cadastro': '05/02/2019', 'limite_credito': 8000000},
    {'id_cliente': 5, 'nome': 'Produtores Associados GO', 'tipo_cliente': 'Cooperativa', 'regiao': 'Goias', 'estado': 'GO', 'data_cadastro': '18/09/2023', 'limite_credito': 2500000},
]

MOCK_PRODUTOS = [
    {'id_produto': 1, 'nome': 'Soja Premium (GMO)', 'categoria': 'Grãos', 'subcategoria': 'Soja', 'unidade': 'kg', 'preco_unitario': 85.50},
    {'id_produto': 2, 'nome': 'Milho Amarelo Tipo 2', 'categoria': 'Grãos', 'subcategoria': 'Milho', 'unidade': 'kg', 'preco_unitario': 42.30},
    {'id_produto': 3, 'nome': 'Cafe Arabica SC-17', 'categoria': 'Café', 'subcategoria': 'Arábica', 'unidade': 'saca', 'preco_unitario': 1250.00},
    {'id_produto': 4, 'nome': 'Trigo Soft Red', 'categoria': 'Grãos', 'subcategoria': 'Trigo', 'unidade': 'kg', 'preco_unitario': 58.70},
    {'id_produto': 5, 'nome': 'Algodão em Caroço', 'categoria': 'Fibras', 'subcategoria': 'Algodão', 'unidade': 'kg', 'preco_unitario': 95.20},
]

MOCK_PEDIDOS = [
    {'id_pedido': 1001, 'data_pedido': '15/01/2024', 'data_entrega': '20/01/2024', 'cliente_nome': 'Cooperativa Agricola MT', 'tipo_contrato': 'Spot', 'status': 'Executado', 'valor_total': 125000.00, 'regiao_origem': 'Mato Grosso', 'regiao_destino': 'Santos'},
    {'id_pedido': 1002, 'data_pedido': '18/01/2024', 'data_entrega': '25/01/2024', 'cliente_nome': 'Agropecuaria Sul LTDA', 'tipo_contrato': 'Futuro', 'status': 'Executado', 'valor_total': 89000.00, 'regiao_origem': 'Rio Grande do Sul', 'regiao_destino': 'Paranagua'},
    {'id_pedido': 1003, 'data_pedido': '22/01/2024', 'data_entrega': '28/01/2024', 'cliente_nome': 'Fazenda Boa Vista', 'tipo_contrato': 'Spot', 'status': 'Pendente', 'valor_total': 45000.00, 'regiao_origem': 'Goias', 'regiao_destino': 'Santos'},
    {'id_pedido': 1004, 'data_pedido': '25/01/2024', 'data_entrega': '05/02/2024', 'cliente_nome': 'Cerealista Brasil SA', 'tipo_contrato': 'Exportação', 'status': 'Em Andamento', 'valor_total': 350000.00, 'regiao_origem': 'Mato Grosso', 'regiao_destino': 'China'},
    {'id_pedido': 1005, 'data_pedido': '01/02/2024', 'data_entrega': '10/02/2024', 'cliente_nome': 'Produtores Associados GO', 'tipo_contrato': 'Spot', 'status': 'Executado', 'valor_total': 67000.00, 'regiao_origem': 'Goias', 'regiao_destino': 'Santos'},
]

MOCK_ITENS = [
    {'id_item': 1, 'id_pedido': 1001, 'produto_nome': 'Soja Premium (GMO)', 'quantidade': 1000, 'preco_unitario': 85.50, 'subtotal': 85500.00},
    {'id_item': 2, 'id_pedido': 1001, 'produto_nome': 'Milho Amarelo Tipo 2', 'quantidade': 500, 'preco_unitario': 42.30, 'subtotal': 21150.00},
    {'id_item': 3, 'id_pedido': 1002, 'produto_nome': 'Cafe Arabica SC-17', 'quantidade': 50, 'preco_unitario': 1250.00, 'subtotal': 62500.00},
    {'id_item': 4, 'id_pedido': 1003, 'produto_nome': 'Trigo Soft Red', 'quantidade': 400, 'preco_unitario': 58.70, 'subtotal': 23480.00},
    {'id_item': 5, 'id_pedido': 1004, 'produto_nome': 'Soja Premium (GMO)', 'quantidade': 2500, 'preco_unitario': 85.50, 'subtotal': 213750.00},
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

@app.route('/explorer')
@login_required
def explorer_page():
    """Pagina de exploracao de dados - todas as tabelas"""
    return render_template('explorer.html',
                         username=session.get('username'),
                         db_available=DB_AVAILABLE)

@app.route('/compra-compartilhada')
@login_required
def compra_compartilhada_page():
    """Pagina de compra compartilhada entre múltiplos clientes"""
    if DB_AVAILABLE:
        clientes = run_query("SELECT id_cliente, nome, tipo_cliente FROM clientes WHERE ativo = TRUE ORDER BY nome")
        grupos = run_query("SELECT id_grupo, nome_grupo, tipo_grupo FROM grupos_compra WHERE ativo = TRUE")
    else:
        clientes = pd.DataFrame(MOCK_CLIENTES)
        grupos = pd.DataFrame([
            {'id_grupo': 1, 'nome_grupo': 'Cooperativa Vale do Rio', 'tipo_grupo': 'COOPERATIVA'},
            {'id_grupo': 2, 'nome_grupo': 'Associação Sul', 'tipo_grupo': 'ASSOCIACAO'}
        ])
    
    return render_template('compra_compartilhada.html',
                         username=session.get('username'),
                         clientes=clientes.to_dict('records') if not clientes.empty else MOCK_CLIENTES,
                         grupos=grupos.to_dict('records') if not grupos.empty else [],
                         db_available=DB_AVAILABLE)

# ============================================
# CHATBOT API COM GEMINI
# ============================================

# Prompt de sistema para o AgroBot
AGROBOT_SYSTEM_PROMPT = """Você é o AgroBot, assistente virtual inteligente da Agromercantil.

IDENTIDADE E FUNÇÃO:
- Você é um assistente de análise de dados e BI (Business Intelligence)
- Sua função é ajudar usuários a consultar e interpretar dados do sistema Agromercantil
- Você acessa informações sobre: vendas, clientes (RFV), produtos, tendências, anomalias e pedidos
- Você NÃO é um trader de commodities - você é um analista de dados da plataforma

SOBRE A AGROMERCANTIL:
- Plataforma de gestão comercial para trading de commodities agrícolas
- Monitora pedidos, clientes, anomalias e tendências de vendas
- Dados disponíveis: faturamento, ticket médio, segmentação de clientes, produtos mais vendidos

COMO SE APRESENTAR:
- SAUDAÇÃO INICIAL OBRIGATÓRIA quando for a primeira mensagem: 
  "Olá! Sou o AgroBot, seu assistente de análise de dados da Agromercantil. Posso ajudá-lo a consultar informações sobre vendas, clientes, produtos e tendências do seu negócio. O que gostaria de saber?"
- Nas respostas seguintes: vá direto ao ponto, sem repetir a apresentação

ESTILO DE COMUNICAÇÃO:
- Profissional, direto e técnico - NUNCA use: "E aí", "Beleza", "Show", "Massa"
- Tom consultivo de analista de dados
- Linguagem corporativa, sem gírias

REGRAS:
1. PRIMEIRA INTERAÇÃO: Use a saudação de apresentação completa acima
2. NUNCA use expressões informais
3. NUNCA comece com "Como analista..." ou "De acordo com minha experiência..."
4. Dê a resposta direta primeiro
5. Se não souber algo, sugira verificar no dashboard
6. Mantenha respostas curtas (máximo 2-3 parágrafos)
7. Termine com convite para continuar

DADOS DO SISTEMA (use quando perguntarem):
- Faturamento: R$ 5.2M no último ano
- 847 clientes ativos
- Ticket médio: R$ 18.450
- 1.248 contratos
"""

@app.route('/api/chat', methods=['POST'])
@login_required
def chat_api():
    data = request.json
    user_message = data.get('message', '').strip()
    
    if not user_message:
        return jsonify({'response': 'Olá! Como posso ajudar você hoje?'})
    
    # Se Gemini não estiver disponível, usar respostas locais
    if not GEMINI_AVAILABLE or not gemini_client:
        return jsonify({'response': get_local_response(user_message)})
    
    try:
        # Preparar contexto com dados atuais
        context = get_context_data()
        
        # Criar prompt do usuário (apenas a pergunta)
        user_prompt = f"""Dados atuais do sistema:
{context}

Pergunta do usuário: {user_message}"""

        # Gerar resposta com Gemini 2.5 Flash usando system instruction
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=AGROBOT_SYSTEM_PROMPT,
                temperature=0.3,
                max_output_tokens=400,
                top_p=0.8
            )
        )
        
        bot_response = response.text.strip()
        
        # Se a resposta for muito curta ou vazia, usar fallback
        if not bot_response or len(bot_response) < 10:
            bot_response = get_local_response(user_message)
        
        return jsonify({'response': bot_response})
        
    except Exception as e:
        print(f"Erro Gemini: {e}")
        return jsonify({'response': get_local_response(user_message)})

def get_context_data():
    """Retorna dados atuais do sistema para contexto do bot"""
    if DB_AVAILABLE:
        metrics = get_metrics()
    else:
        metrics = MOCK_METRICS
    
    return f"""- Faturamento total: {metrics['faturamento']}
- Clientes ativos: {metrics['clientes']}
- Ticket médio: {metrics['ticket_medio']}
- Contratos: {metrics['contratos']}
- Última atualização: {metrics['last_update']}"""

def get_local_response(message):
    """Fallback simples quando Gemini nao disponivel"""
    return "Ops! Meu sistema de IA esta temporariamente indisponivel. Por favor, tente novamente em alguns segundos, ou verifique os dados diretamente no dashboard."

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
# APIs - CORREÇÃO DE ANOMALIAS
# ============================================
@app.route('/api/anomalias/corrigir/<int:pedido_id>', methods=['POST'])
@login_required
def api_corrigir_anomalia(pedido_id):
    """Corrige uma anomalia específica automaticamente"""
    if not DB_AVAILABLE:
        return jsonify({'success': False, 'error': 'Banco não disponível'})
    
    try:
        data = request.json or {}
        usuario = session.get('username', 'SISTEMA')
        motivo = data.get('motivo', 'Correção manual via interface')
        
        # Executar função de correção no banco
        result = run_query("""
            SELECT * FROM corrigir_anomalia(:pedido_id, :usuario, :motivo)
        """, {'pedido_id': pedido_id, 'usuario': usuario, 'motivo': motivo})
        
        if not result.empty:
            return jsonify({
                'success': True,
                'status': result.iloc[0]['status'],
                'valor_anterior': float(result.iloc[0]['valor_anterior']),
                'valor_novo': float(result.iloc[0]['valor_novo'])
            })
        else:
            return jsonify({'success': False, 'error': 'Pedido não encontrado'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/anomalias/corrigir-todas', methods=['POST'])
@login_required
def api_corrigir_todas():
    """Corrige todas as anomalias pendentes"""
    if not DB_AVAILABLE:
        return jsonify({'success': False, 'error': 'Banco não disponível'})
    
    try:
        # Buscar todas as anomalias pendentes
        anomalias = run_query("""
            SELECT id_pedido FROM vw_anomalias_completas 
            WHERE status_correcao = 'PENDENTE'
        """)
        
        corrigidas = []
        erros = []
        
        for _, row in anomalias.iterrows():
            try:
                result = run_query("""
                    SELECT * FROM corrigir_anomalia(:pedido_id, :usuario, 'Correção em lote')
                """, {
                    'pedido_id': row['id_pedido'],
                    'usuario': session.get('username', 'SISTEMA')
                })
                corrigidas.append(row['id_pedido'])
            except Exception as e:
                erros.append({'pedido': row['id_pedido'], 'erro': str(e)})
        
        return jsonify({
            'success': True,
            'total_corrigidas': len(corrigidas),
            'total_erros': len(erros),
            'corrigidas': corrigidas,
            'erros': erros
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/anomalias/historico/<int:pedido_id>')
@login_required
def api_historico_correcoes(pedido_id):
    """Retorna histórico de correções de um pedido"""
    if not DB_AVAILABLE:
        return jsonify([])
    
    df = run_query("""
        SELECT 
            id_correcao,
            campo_corrigido,
            valor_anterior,
            valor_novo,
            tipo_correcao,
            usuario_correcao,
            motivo_correcao,
            TO_CHAR(data_correcao, 'DD/MM/YYYY HH24:MI') as data_formatada
        FROM log_correcoes
        WHERE id_pedido = :pedido_id
        ORDER BY data_correcao DESC
    """, {'pedido_id': pedido_id})
    
    return jsonify(df.to_dict('records'))

# ============================================
# APIs - COMPRA COMPARTILHADA
# ============================================
@app.route('/api/compra-compartilhada/grupos')
@login_required
def api_listar_grupos():
    """Lista todos os grupos de compra"""
    if not DB_AVAILABLE:
        return jsonify([])
    
    df = run_query("""
        SELECT g.*, 
               c.nome as representante,
               (SELECT COUNT(*) FROM cliente_grupo cg WHERE cg.id_grupo = g.id_grupo) as total_membros
        FROM grupos_compra g
        LEFT JOIN clientes c ON g.representante_id = c.id_cliente
        WHERE g.ativo = TRUE
        ORDER BY g.nome_grupo
    """)
    return jsonify(df.to_dict('records'))

@app.route('/api/compra-compartilhada/grupo/<int:grupo_id>/membros')
@login_required
def api_grupo_membros(grupo_id):
    """Lista membros de um grupo"""
    if not DB_AVAILABLE:
        return jsonify([])
    
    df = run_query("""
        SELECT 
            c.id_cliente,
            c.nome,
            c.tipo_cliente,
            c.regiao,
            cg.percentual_participacao,
            cg.data_entrada
        FROM cliente_grupo cg
        JOIN clientes c ON cg.id_cliente = c.id_cliente
        WHERE cg.id_grupo = :grupo_id AND cg.ativo = TRUE
        ORDER BY cg.percentual_participacao DESC
    """, {'grupo_id': grupo_id})
    return jsonify(df.to_dict('records'))

@app.route('/api/compra-compartilhada/criar', methods=['POST'])
@login_required
def api_criar_pedido_compartilhado():
    """Cria um novo pedido compartilhado"""
    if not DB_AVAILABLE:
        return jsonify({'success': False, 'error': 'Banco não disponível'})
    
    try:
        data = request.json
        
        # Preparar JSON de proprietários
        proprietarios = []
        for p in data.get('proprietarios', []):
            proprietarios.append({
                'cliente_id': p['cliente_id'],
                'percentual': p['percentual'],
                'tipo': p.get('tipo', 'COMPRADOR')
            })
        
        # Executar função do banco
        result = run_query("""
            SELECT criar_pedido_compartilhado(
                :data_pedido, :data_entrega, :tipo_contrato,
                :regiao_origem, :regiao_destino, :proprietarios::jsonb
            ) as pedido_id
        """, {
            'data_pedido': data['data_pedido'],
            'data_entrega': data['data_entrega'],
            'tipo_contrato': data['tipo_contrato'],
            'regiao_origem': data['regiao_origem'],
            'regiao_destino': data['regiao_destino'],
            'proprietarios': json.dumps(proprietarios)
        })
        
        if not result.empty:
            pedido_id = int(result.iloc[0]['pedido_id'])
            
            # Inserir itens do pedido
            for item in data.get('itens', []):
                run_query("""
                    INSERT INTO itens_pedido (id_pedido, id_produto, quantidade, preco_unitario, subtotal)
                    VALUES (:pedido_id, :produto_id, :quantidade, :preco_unitario, :subtotal)
                """, {
                    'pedido_id': pedido_id,
                    'produto_id': item['produto_id'],
                    'quantidade': item['quantidade'],
                    'preco_unitario': item['preco_unitario'],
                    'subtotal': item['quantidade'] * item['preco_unitario']
                })
            
            # Atualizar valor total do pedido
            run_query("""
                UPDATE pedidos 
                SET valor_total = (SELECT SUM(subtotal) FROM itens_pedido WHERE id_pedido = :pedido_id)
                WHERE id_pedido = :pedido_id
            """, {'pedido_id': pedido_id})
            
            return jsonify({
                'success': True,
                'pedido_id': pedido_id,
                'message': f'Pedido compartilhado #{pedido_id} criado com sucesso'
            })
        else:
            return jsonify({'success': False, 'error': 'Erro ao criar pedido'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/compra-compartilhada/pedido/<int:pedido_id>')
@login_required
def api_pedido_compartilhado_detalhe(pedido_id):
    """Retorna detalhes de um pedido compartilhado"""
    if not DB_AVAILABLE:
        return jsonify({})
    
    # Dados do pedido
    pedido = run_query("""
        SELECT * FROM vw_pedidos_completo WHERE id_pedido = :pedido_id
    """, {'pedido_id': pedido_id})
    
    # Co-proprietários
    coproprietarios = run_query("""
        SELECT 
            pc.*,
            c.nome as cliente_nome,
            c.tipo_cliente
        FROM pedido_coproprietario pc
        JOIN clientes c ON pc.id_cliente = c.id_cliente
        WHERE pc.id_pedido = :pedido_id
    """, {'pedido_id': pedido_id})
    
    # Itens
    itens = run_query("""
        SELECT 
            i.*,
            p.nome as produto_nome
        FROM itens_pedido i
        JOIN produtos p ON i.id_produto = p.id_produto
        WHERE i.id_pedido = :pedido_id
    """, {'pedido_id': pedido_id})
    
    return jsonify({
        'pedido': pedido.to_dict('records')[0] if not pedido.empty else None,
        'coproprietarios': coproprietarios.to_dict('records'),
        'itens': itens.to_dict('records')
    })

# ============================================
# APIs - EXPLORER DE DADOS
# ============================================
@app.route('/api/explorer/clientes')
@login_required
def api_explorer_clientes():
    """Retorna todos os clientes para DataTable"""
    if not DB_AVAILABLE:
        return jsonify({'data': MOCK_CLIENTES})
    
    df = run_query("""
        SELECT id_cliente, nome, tipo_cliente, regiao, estado, 
               TO_CHAR(data_cadastro, 'DD/MM/YYYY') as data_cadastro,
               COALESCE(limite_credito, 0) as limite_credito
        FROM clientes 
        ORDER BY id_cliente
    """)
    return jsonify({'data': df.to_dict('records')})

@app.route('/api/explorer/produtos')
@login_required
def api_explorer_produtos():
    """Retorna todos os produtos para DataTable"""
    if not DB_AVAILABLE:
        return jsonify({'data': MOCK_PRODUTOS})
    
    df = run_query("""
        SELECT id_produto, nome, categoria, subcategoria, unidade, 
               COALESCE(preco_unitario, 0) as preco_unitario
        FROM produtos 
        ORDER BY id_produto
    """)
    return jsonify({'data': df.to_dict('records')})

@app.route('/api/explorer/pedidos')
@login_required
def api_explorer_pedidos():
    """Retorna todos os pedidos para DataTable com filtros opcionais"""
    inicio = request.args.get('inicio')
    fim = request.args.get('fim')
    
    if not DB_AVAILABLE:
        return jsonify({'data': MOCK_PEDIDOS})
    
    where_clause = ""
    params = {}
    if inicio:
        where_clause += " WHERE p.data_pedido >= :inicio"
        params['inicio'] = inicio
    if fim:
        where_clause += " AND" if inicio else " WHERE"
        where_clause += " p.data_pedido <= :fim"
        params['fim'] = fim
    
    df = run_query(f"""
        SELECT p.id_pedido, 
               TO_CHAR(p.data_pedido, 'DD/MM/YYYY') as data_pedido,
               TO_CHAR(p.data_entrega, 'DD/MM/YYYY') as data_entrega,
               c.nome as cliente_nome,
               p.tipo_contrato,
               p.status,
               COALESCE(p.valor_total, 0) as valor_total,
               p.regiao_origem,
               p.regiao_destino
        FROM pedidos p
        JOIN clientes c ON p.id_cliente = c.id_cliente
        {where_clause}
        ORDER BY p.data_pedido DESC
    """, params)
    return jsonify({'data': df.to_dict('records')})

@app.route('/api/explorer/itens')
@login_required
def api_explorer_itens():
    """Retorna todos os itens de pedido para DataTable"""
    if not DB_AVAILABLE:
        return jsonify({'data': MOCK_ITENS})
    
    df = run_query("""
        SELECT i.id_item, i.id_pedido, p.nome as produto_nome,
               i.quantidade, 
               COALESCE(i.preco_unitario, 0) as preco_unitario,
               COALESCE(i.subtotal, 0) as subtotal
        FROM itens_pedido i
        JOIN produtos p ON i.id_produto = p.id_produto
        ORDER BY i.id_item DESC
        LIMIT 5000
    """)
    return jsonify({'data': df.to_dict('records')})

@app.route('/api/explorer/resumo')
@login_required
def api_explorer_resumo():
    """Retorna resumo estatístico para dashboard"""
    if not DB_AVAILABLE:
        return jsonify({
            'total_clientes': 847,
            'total_produtos': 25,
            'total_pedidos': 1248,
            'faturamento_total': 5200000,
            'status_labels': ['Executado', 'Pendente', 'Cancelado', 'Em Andamento'],
            'status_values': [850, 250, 100, 48],
            'top_clientes_nomes': ['Cooperativa Agricola MT', 'Agropecuaria Sul LTDA', 'Fazenda Boa Vista'],
            'top_clientes_valores': [2450000, 1890000, 1240000]
        })
    
    # Totais
    clientes = run_query("SELECT COUNT(*) as total FROM clientes")
    produtos = run_query("SELECT COUNT(*) as total FROM produtos")
    pedidos = run_query("SELECT COUNT(*) as total FROM pedidos")
    faturamento = run_query("SELECT COALESCE(SUM(valor_total), 0) as total FROM pedidos WHERE status != 'Cancelado'")
    
    # Pedidos por status
    status_data = run_query("""
        SELECT status, COUNT(*) as total 
        FROM pedidos 
        GROUP BY status 
        ORDER BY total DESC
    """)
    
    # Top 10 clientes
    top_clientes = run_query("""
        SELECT c.nome, SUM(p.valor_total) as total
        FROM pedidos p
        JOIN clientes c ON p.id_cliente = c.id_cliente
        WHERE p.status != 'Cancelado'
        GROUP BY c.id_cliente, c.nome
        ORDER BY total DESC
        LIMIT 10
    """)
    
    return jsonify({
        'total_clientes': int(clientes['total'].iloc[0]) if not clientes.empty else 0,
        'total_produtos': int(produtos['total'].iloc[0]) if not produtos.empty else 0,
        'total_pedidos': int(pedidos['total'].iloc[0]) if not pedidos.empty else 0,
        'faturamento_total': float(faturamento['total'].iloc[0]) if not faturamento.empty else 0,
        'status_labels': status_data['status'].tolist() if not status_data.empty else [],
        'status_values': status_data['total'].tolist() if not status_data.empty else [],
        'top_clientes_nomes': top_clientes['nome'].tolist() if not top_clientes.empty else [],
        'top_clientes_valores': [float(v) for v in top_clientes['total'].tolist()] if not top_clientes.empty else []
    })

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
