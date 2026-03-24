#!/usr/bin/env python3
"""
Dashboard Agromercantil com LOGIN
Layout Split-Screen - Design Material 3
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
import hashlib
import base64
from pathlib import Path

# Carregar imagens como base64
def get_image_base64(filename):
    img_path = Path(__file__).parent / filename
    if img_path.exists():
        return base64.b64encode(img_path.read_bytes()).decode()
    return None

LOGO_BASE64 = get_image_base64("logo.png")
HERO_BG_BASE64 = get_image_base64("hero_bg.png")

# ============================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================
st.set_page_config(
    page_title="Login | Agromercantil Analytics",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================
# CSS - DESIGN SPLIT SCREEN
# ============================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&family=Inter:wght@400;500;600&family=Montserrat:wght@400;600;700&display=swap');
    
    /* ===== RESET E VARIÁVEIS ===== */
    * { 
        font-family: 'Inter', sans-serif; 
        box-sizing: border-box;
    }
    
    :root {
        --primary: #112800;
        --primary-dark: #253f0f;
        --secondary: #436900;
        --tertiary: #F58220;
        --tertiary-hover: #e67610;
        --surface: #fcf9f8;
        --surface-container: #f0eded;
        --surface-container-low: #f6f3f2;
        --surface-container-lowest: #ffffff;
        --on-surface: #1b1c1c;
        --on-surface-variant: #44483e;
        --outline: #74796c;
        --outline-variant: #c4c8ba;
        --error: #ba1a1a;
        --white: #ffffff;
    }
    
    /* ===== ESTILOS STREAMLIT ===== */
    .stApp {
        background: var(--surface) !important;
    }
    
    /* Esconde elementos padrão do Streamlit */
    .stApp > header { display: none !important; }
    .stApp [data-testid="stToolbar"] { display: none !important; }
    .stApp .stDeployButton { display: none !important; }
    .stApp [data-testid="stSidebar"] { display: none !important; }
    
    /* ===== LOGIN WRAPPER - SPLIT SCREEN ===== */
    .login-wrapper {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        display: flex;
        z-index: 9999;
        overflow: hidden;
    }
    
    /* ===== LADO ESQUERDO - HERO ===== */
    .hero-section {
        width: 50%;
        background: linear-gradient(135deg, #112800 0%, #253f0f 100%);
        position: relative;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        padding: 64px;
        overflow: hidden;
    }
    
    /* Efeitos decorativos */
    .hero-decoration {
        position: absolute;
        top: 0;
        right: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        opacity: 0.1;
    }
    
    .hero-blob-1 {
        position: absolute;
        top: -96px;
        right: -96px;
        width: 384px;
        height: 384px;
        background: #cbedab;
        border-radius: 50%;
        filter: blur(80px);
    }
    
    .hero-blob-2 {
        position: absolute;
        bottom: 25%;
        left: -48px;
        width: 256px;
        height: 256px;
        background: #b9f467;
        border-radius: 50%;
        filter: blur(80px);
    }
    
    /* Logo area */
    .hero-logo-area {
        position: relative;
        z-index: 10;
        display: flex;
        align-items: center;
        gap: 16px;
    }
    
    .hero-logo-icon {
        background: rgba(255,255,255,0.1);
        backdrop-filter: blur(12px);
        padding: 12px;
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.2);
    }
    
    .hero-logo-icon img {
        width: 40px;
        height: 40px;
        object-fit: contain;
    }
    
    .hero-logo-text h1 {
        font-family: 'Montserrat', sans-serif;
        font-weight: 700;
        font-size: 28px;
        color: white;
        letter-spacing: -0.02em;
        margin: 0;
    }
    
    .hero-logo-text p {
        font-family: 'Montserrat', sans-serif;
        font-size: 11px;
        color: rgba(203, 237, 171, 0.8);
        letter-spacing: 0.15em;
        text-transform: uppercase;
        margin: 4px 0 0 0;
    }
    
    /* Hero content */
    .hero-content {
        position: relative;
        z-index: 10;
        max-width: 600px;
    }
    
    .hero-accent-line {
        width: 64px;
        height: 6px;
        background: #ffddb4;
        margin-bottom: 32px;
    }
    
    .hero-title {
        font-family: 'Manrope', sans-serif;
        font-weight: 800;
        font-size: 56px;
        color: white;
        line-height: 1.1;
        margin-bottom: 24px;
    }
    
    .hero-title span {
        color: #cbedab;
    }
    
    .hero-subtitle {
        font-family: 'Inter', sans-serif;
        font-size: 18px;
        color: rgba(255,255,255,0.7);
        line-height: 1.6;
        max-width: 480px;
    }
    
    /* Hero image */
    .hero-image {
        position: absolute;
        bottom: 0;
        right: 0;
        width: 75%;
        height: 66%;
        z-index: 0;
        opacity: 0.4;
    }
    
    .hero-image img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        border-top-left-radius: 120px;
    }
    
    /* Hero footer */
    .hero-footer {
        position: relative;
        z-index: 10;
        font-family: 'Inter', sans-serif;
        font-size: 12px;
        color: rgba(255,255,255,0.4);
        letter-spacing: 0.1em;
        text-transform: uppercase;
    }
    
    /* ===== LADO DIREITO - FORM ===== */
    .form-section {
        width: 50%;
        background: var(--surface-container-low);
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        padding: 48px 96px;
        position: relative;
    }
    
    .form-container {
        width: 100%;
        max-width: 440px;
    }
    
    /* Header do form */
    .form-header {
        margin-bottom: 40px;
        position: relative;
    }
    
    .form-accent-line {
        position: absolute;
        left: -24px;
        top: 50%;
        transform: translateY(-50%);
        width: 6px;
        height: 48px;
        background: #ffddb4;
    }
    
    .form-header h2 {
        font-family: 'Montserrat', sans-serif;
        font-weight: 700;
        font-size: 32px;
        color: var(--primary);
        margin: 0 0 8px 0;
    }
    
    .form-header p {
        font-family: 'Inter', sans-serif;
        font-size: 16px;
        color: var(--on-surface-variant);
        margin: 0;
    }
    
    /* Card do formulário */
    .form-card {
        background: var(--surface-container-lowest);
        padding: 40px 48px;
        border-radius: 16px;
        box-shadow: 0 40px 80px -20px rgba(27, 28, 28, 0.06);
        border: 1px solid rgba(196, 200, 186, 0.3);
    }
    
    /* Campos de input estilo Streamlit override */
    .stTextInput > div {
        margin-bottom: 24px;
    }
    
    .stTextInput > label {
        font-family: 'Inter', sans-serif;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--on-surface-variant) !important;
        margin-bottom: 8px !important;
    }
    
    .stTextInput > div > div {
        border: none !important;
        border-bottom: 2px solid rgba(196, 200, 186, 0.5) !important;
        border-radius: 0 !important;
        background: transparent !important;
        padding: 12px 0 12px 36px !important;
        position: relative;
    }
    
    .stTextInput > div > div:focus-within {
        border-bottom-color: var(--secondary) !important;
        box-shadow: none !important;
    }
    
    .stTextInput input {
        font-family: 'Inter', sans-serif;
        font-size: 15px;
        color: var(--on-surface) !important;
        background: transparent !important;
    }
    
    .stTextInput input::placeholder {
        color: rgba(116, 121, 108, 0.5) !important;
    }
    
    /* Checkbox */
    .stCheckbox > label {
        font-family: 'Inter', sans-serif;
        font-size: 14px !important;
        color: var(--on-surface-variant) !important;
    }
    
    .stCheckbox > div > div {
        background: transparent !important;
    }
    
    /* Botão primário */
    .stButton > button {
        width: 100% !important;
        padding: 16px 24px !important;
        background: #F58220 !important;
        color: white !important;
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 700 !important;
        font-size: 15px !important;
        border: none !important;
        border-radius: 12px !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 10px 30px -10px rgba(245, 130, 32, 0.4) !important;
        margin-top: 16px !important;
    }
    
    .stButton > button:hover {
        background: #e67610 !important;
        transform: translateY(-1px);
        box-shadow: 0 14px 36px -10px rgba(245, 130, 32, 0.5) !important;
    }
    
    .stButton > button:active {
        transform: scale(0.98);
    }
    
    /* Divider */
    .divider {
        margin-top: 32px;
        padding-top: 32px;
        border-top: 1px solid rgba(196, 200, 186, 0.3);
        text-align: center;
    }
    
    .divider span {
        font-family: 'Inter', sans-serif;
        font-size: 11px;
        font-weight: 600;
        color: var(--outline);
        letter-spacing: 0.15em;
        text-transform: uppercase;
    }
    
    /* Footer links */
    .form-footer {
        margin-top: 32px;
        display: flex;
        justify-content: center;
        gap: 32px;
    }
    
    .form-footer a {
        font-family: 'Inter', sans-serif;
        font-size: 12px;
        color: var(--outline);
        text-decoration: none;
        display: flex;
        align-items: center;
        gap: 4px;
        transition: color 0.2s;
    }
    
    .form-footer a:hover {
        color: var(--secondary);
    }
    
    /* Mensagens de erro/sucesso */
    .stAlert {
        border-radius: 10px !important;
        border: none !important;
        padding: 16px !important;
    }
    
    .stAlert[data-baseweb="notification"] {
        background: #fef2f2 !important;
        border: 1px solid #fecaca !important;
    }
    
    /* ===== RESPONSIVIDADE ===== */
    @media (max-width: 1024px) {
        .hero-section {
            display: none !important;
        }
        .form-section {
            width: 100%;
            padding: 48px 24px;
        }
    }
    
    /* Input icons */
    .input-wrapper {
        position: relative;
    }
    
    .input-icon {
        position: absolute;
        left: 0;
        bottom: 14px;
        color: var(--outline);
        font-size: 20px;
        z-index: 10;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# SISTEMA DE AUTENTICAÇÃO
# ============================================
USERS = {
    "admin": hashlib.sha256("admin123".encode()).hexdigest(),
    "avaliador": hashlib.sha256("agro2024".encode()).hexdigest(),
    "mateus": hashlib.sha256("231181mateu$".encode()).hexdigest()
}

def check_password():
    """Verifica se usuário está logado"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "username" not in st.session_state:
        st.session_state.username = None
    return st.session_state.authenticated

def login_page():
    """Página de login - Split Screen Design"""
    
    # Logo HTML
    logo_html = f'<img src="data:image/png;base64,{LOGO_BASE64}" alt="Agromercantil">' if LOGO_BASE64 else '🌾'
    
    # Hero background image
    hero_img_html = f'<img src="data:image/png;base64,{HERO_BG_BASE64}" alt="Soy plants">' if HERO_BG_BASE64 else ''
    
    # Container principal split-screen
    st.markdown(f"""
    <div class="login-wrapper">
        <!-- LADO ESQUERDO: HERO -->
        <div class="hero-section">
            <div class="hero-decoration">
                <div class="hero-blob-1"></div>
                <div class="hero-blob-2"></div>
            </div>
            
            <!-- Logo -->
            <div class="hero-logo-area">
                <div class="hero-logo-icon">
                    {logo_html}
                </div>
                <div class="hero-logo-text">
                    <h1>AGROMERCANTIL</h1>
                    <p>Soluções Inteligentes para o Agro</p>
                </div>
            </div>
            
            <!-- Conteúdo -->
            <div class="hero-content">
                <div class="hero-accent-line"></div>
                <h2 class="hero-title">
                    A inteligência de dados que cultiva o seu <span>sucesso.</span>
                </h2>
                <p class="hero-subtitle">
                    Analise commodities globais com precisão institucional. 
                    Onde a tradição do campo encontra a tecnologia do futuro.
                </p>
            </div>
            
            <!-- Imagem de fundo -->
            <div class="hero-image">
                {hero_img_html}
            </div>
            
            <!-- Footer -->
            <div class="hero-footer">
                Market Analytics Platform v4.2
            </div>
        </div>
        
        <!-- LADO DIREITO: FORMULÁRIO -->
        <div class="form-section">
            <div class="form-container">
                <!-- Header -->
                <div class="form-header">
                    <div class="form-accent-line"></div>
                    <h2>Analytics Dashboard</h2>
                    <p>Plataforma de Análise de Commodities</p>
                </div>
                
                <!-- Card do formulário -->
                <div class="form-card">
    """, unsafe_allow_html=True)
    
    # Formulário Streamlit
    col1, col2 = st.columns([1, 6])
    with col2:
        # Usuário
        st.markdown('<div class="input-wrapper"><span class="input-icon">✉️</span></div>', unsafe_allow_html=True)
        username = st.text_input(
            "Usuário",
            placeholder="Digite seu usuário",
            label_visibility="visible",
            key="login_user"
        )
        
        # Senha
        st.markdown('<div class="input-wrapper"><span class="input-icon">🔒</span></div>', unsafe_allow_html=True)
        password = st.text_input(
            "Senha",
            type="password",
            placeholder="Digite sua senha",
            label_visibility="visible",
            key="login_pass"
        )
        
        # Lembrar-me
        remember = st.checkbox("Manter conectado por 30 dias", key="remember_me")
        
        # Botão Entrar
        login_pressed = st.button("Entrar →", key="login_btn")
        
        # Validação
        if login_pressed:
            if username in USERS:
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                if password_hash == USERS[username]:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("❌ Senha incorreta!")
            else:
                st.error("❌ Usuário não encontrado!")
    
    # Fechar card e mostrar footer
    st.markdown("""
                    <!-- Divider -->
                    <div class="divider">
                        <span>Acesso Restrito</span>
                    </div>
                </div>
                
                <!-- Footer links -->
                <div class="form-footer">
                    <a href="#">❓ Suporte</a>
                    <a href="#">🌐 PT-BR</a>
                </div>
            </div>
            
            <!-- Footer copyright -->
            <footer style="
                position: absolute;
                bottom: 0;
                left: 0;
                right: 0;
                padding: 24px 48px;
                border-top: 1px solid rgba(196, 200, 186, 0.3);
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-family: 'Inter', sans-serif;
                font-size: 12px;
                color: #74796c;
            ">
                <span>Agromercantil © 2025 - Soluções Inteligentes para o Agro</span>
                <div style="display: flex; gap: 24px;">
                    <a href="#" style="color: #74796c; text-decoration: none;">Privacidade</a>
                    <a href="#" style="color: #74796c; text-decoration: none;">Termos</a>
                    <a href="#" style="color: #74796c; text-decoration: none;">Contato</a>
                </div>
            </footer>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.stop()

# ============================================
# CONEXÃO COM BANCO
# ============================================
@st.cache_resource
def get_engine():
    return create_engine("postgresql://agro_user:agro123456@localhost:5432/agromercantil")

def run_query(query, params=None):
    try:
        with get_engine().connect() as conn:
            result = conn.execute(text(query), params or {})
            return pd.DataFrame(result.fetchall(), columns=result.keys())
    except Exception as e:
        st.error(f"Erro na query: {e}")
        return pd.DataFrame()

# ============================================
# QUERIES SQL
# ============================================
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
# PÁGINAS DO DASHBOARD
# ============================================
def page_visao_geral():
    st.title("📊 Dashboard Agromercantil")
    st.markdown("*Análise de Commodities Agrícolas*")
    
    df_pedidos = run_query("SELECT COUNT(*) as total, SUM(valor_total) as valor FROM pedidos WHERE status != 'Cancelado'")
    df_clientes = run_query("SELECT COUNT(*) as total FROM clientes")
    
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("💰 Faturamento", f"R$ {df_pedidos['valor'].iloc[0]/1e6:.1f}M")
    with col2: st.metric("📋 Contratos", f"{df_pedidos['total'].iloc[0]}")
    with col3: st.metric("👥 Clientes", f"{df_clientes['total'].iloc[0]}")
    
    tend = tendencias_mensais()
    if not tend.empty:
        st.subheader("📈 Evolução de Vendas")
        fig = px.line(tend, x='mes_ano', y='vendas', template='plotly_white')
        fig.update_traces(line_color='#112800', line_width=3)
        st.plotly_chart(fig, use_container_width=True)

def page_rfv():
    st.title("👥 Questão 2: Análise RFV")
    rfv = calcular_rfv()
    if not rfv.empty:
        col1, col2 = st.columns([1, 2])
        with col1:
            dist = rfv['segmento'].value_counts()
            colors = {'Campeão': '#112800', 'Fiel': '#436900', 'Ativo': '#4A5568', 'Em Risco': '#E53E3E'}
            fig = px.pie(values=dist.values, names=dist.index, color=dist.index, color_discrete_map=colors)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.subheader("Top 10 Clientes")
            st.dataframe(rfv.nlargest(10, 'valor_total')[['nome', 'valor_total', 'segmento']], hide_index=True)
        st.subheader("Base Completa RFV")
        st.dataframe(rfv, use_container_width=True, hide_index=True)

def page_tendencias():
    st.title("📈 Questão 5: Tendências de Mercado")
    tend = tendencias_mensais()
    if not tend.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=tend['mes_ano'], y=tend['vendas'], name='Vendas', marker_color='#112800'))
        fig.add_trace(go.Scatter(x=tend['mes_ano'], y=tend['crescimento'], name='% Crescimento',
                                yaxis='y2', line=dict(color='#F58220', width=3)))
        fig.update_layout(yaxis2=dict(overlaying='y', side='right', title='%'), template='plotly_white')
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(tend, use_container_width=True)

def page_produtos():
    st.title("🌾 Questão 4: Top 5 Produtos")
    top = top_produtos()
    if not top.empty:
        fig = px.bar(top, x='total_vendas', y='nome', orientation='h', color_discrete_sequence=['#112800'])
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(top, hide_index=True)

def page_anomalias():
    st.title("⚠️ Questão 7: Detecção de Anomalias")
    anom = detectar_anomalias()
    if not anom.empty:
        st.error(f"🔴 {len(anom)} contratos com divergências!")
        st.dataframe(anom, hide_index=True)
    else:
        st.success("✅ Nenhuma anomalia detectada!")

def page_inativos():
    st.title("😴 Questão 6: Clientes Inativos > 6 meses")
    inativos = clientes_inativos()
    if not inativos.empty:
        st.warning(f"⚠️ {len(inativos)} clientes sem compras há +6 meses")
        st.dataframe(inativos, hide_index=True)
    else:
        st.success("✅ Todos os clientes ativos!")

def page_modelo_expandido():
    st.title("🔀 Questão 3: Modelo Expandido")
    st.info("Múltiplos Clientes por Pedido (Compras Compartilhadas)")
    exemplo = run_query("""
    SELECT pc.id_pedido, c.nome as cliente, pc.percentual_rateio, pc.valor_rateado
    FROM pedido_clientes pc
    JOIN clientes c ON pc.id_cliente = c.id_cliente
    LIMIT 10;
    """)
    if not exemplo.empty:
        st.dataframe(exemplo, hide_index=True)
    else:
        st.write("*Nenhum pedido compartilhado registrado ainda.*")

# ============================================
# MAIN
# ============================================
def main():
    if not check_password():
        login_page()
        return
    
    st.sidebar.title("🌾 Agromercantil")
    st.sidebar.markdown(f"*Bem-vindo, **{st.session_state.username}**!*")
    st.sidebar.markdown("---")
    
    pagina = st.sidebar.radio("Navegação:", [
        "📊 Visão Geral",
        "👥 Q2: Análise RFV", 
        "📈 Q5: Tendências",
        "🌾 Q4: Produtos",
        "⚠️ Q7: Anomalias",
        "😴 Q6: Clientes Inativos",
        "🔀 Q3: Modelo Expandido"
    ])
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("**🖥️ Ambiente:**")
    st.sidebar.markdown("• VPS: PostgreSQL + Streamlit")
    st.sidebar.markdown("• Usuário: " + st.session_state.username)
    
    if st.sidebar.button("🚪 Sair"):
        st.session_state.authenticated = False
        st.session_state.username = None
        st.rerun()
    
    if pagina == "📊 Visão Geral":
        page_visao_geral()
    elif pagina == "👥 Q2: Análise RFV":
        page_rfv()
    elif pagina == "📈 Q5: Tendências":
        page_tendencias()
    elif pagina == "🌾 Q4: Produtos":
        page_produtos()
    elif pagina == "⚠️ Q7: Anomalias":
        page_anomalias()
    elif pagina == "😴 Q6: Clientes Inativos":
        page_inativos()
    elif pagina == "🔀 Q3: Modelo Expandido":
        page_modelo_expandido()

if __name__ == "__main__":
    main()
