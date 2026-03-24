#!/usr/bin/env python3
"""
Dashboard Agromercantil com LOGIN
VPS Edition - Avaliação Técnica
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
import hashlib

# Configuração da página
st.set_page_config(
    page_title="Agromercantil Analytics",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Customizado
st.markdown("""
<style>
    .main { background-color: #F7F5F0; }
    h1, h2, h3 { color: #1B4D3E !important; }
    .stButton>button {
        background-color: #1B4D3E; color: white; border-radius: 8px;
        border: none; padding: 10px 24px; font-weight: 600;
    }
    .stButton>button:hover { background-color: #143d31; }
    .login-container {
        max-width: 400px; margin: 100px auto; padding: 40px;
        background: white; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    }
    .login-title { text-align: center; color: #1B4D3E; margin-bottom: 30px; }
    .login-logo { text-align: center; font-size: 60px; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# ============================================
# SISTEMA DE LOGIN
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
    """Página de login"""
    st.markdown("""
    <div class="login-container">
        <div class="login-logo">🌾</div>
        <h1 class="login-title">Agromercantil</h1>
        <p style="text-align: center; color: #666; margin-bottom: 30px;">
            Sistema de Análise de Commodities<br>
            <small>Avaliação Técnica - Analista de Dados</small>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        username = st.text_input("👤 Usuário", placeholder="Digite seu usuário")
        password = st.text_input("🔒 Senha", type="password", placeholder="Digite sua senha")
        
        if st.button("Entrar", use_container_width=True):
            if username in USERS:
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                if password_hash == USERS[username]:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.success("✅ Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("❌ Senha incorreta!")
            else:
                st.error("❌ Usuário não encontrado!")
        
        st.markdown("""
        <div style="margin-top: 30px; padding: 15px; background: #f0f0f0; border-radius: 8px; font-size: 12px;">
            <b>Usuários de teste:</b><br>
            • admin / admin123<br>
            • avaliador / agro2024<br>
            • mateus / 231181mateu$
        </div>
        """, unsafe_allow_html=True)

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
# QUERIES SQL (REQUISITOS DO PDF)
# ============================================
def calcular_rfv():
    """Questão 2: RFV - Usa CTE + Window Functions"""
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
    """Questão 5: Tendências - Usa CTE + LAG"""
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
    """Questão 7: Anomalias - Usa CTE"""
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
    """Questão 6: Clientes Inativos - Usa CTE"""
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
    """Questão 4: Top 5 Produtos - Usa CTE"""
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
        fig.update_traces(line_color='#1B4D3E', line_width=3)
        st.plotly_chart(fig, use_container_width=True)

def page_rfv():
    st.title("👥 Questão 2: Análise RFV")
    st.markdown("*Usa CTE + Window Functions (SUM OVER, COUNT OVER, LAG)*")
    
    rfv = calcular_rfv()
    if not rfv.empty:
        col1, col2 = st.columns([1, 2])
        with col1:
            dist = rfv['segmento'].value_counts()
            colors = {'Campeão': '#1B4D3E', 'Fiel': '#B8860B', 'Ativo': '#4A5568', 'Em Risco': '#E53E3E'}
            fig = px.pie(values=dist.values, names=dist.index, color=dist.index, color_discrete_map=colors)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.subheader("Top 10 Clientes")
            st.dataframe(rfv.nlargest(10, 'valor_total')[['nome', 'valor_total', 'segmento']], hide_index=True)
        st.subheader("Base Completa RFV")
        st.dataframe(rfv, use_container_width=True, hide_index=True)

def page_tendencias():
    st.title("📈 Questão 5: Tendências de Mercado")
    st.markdown("*Usa CTE + Window Functions + LAG para crescimento percentual*")
    
    tend = tendencias_mensais()
    if not tend.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=tend['mes_ano'], y=tend['vendas'], name='Vendas', marker_color='#1B4D3E'))
        fig.add_trace(go.Scatter(x=tend['mes_ano'], y=tend['crescimento'], name='% Crescimento',
                                yaxis='y2', line=dict(color='#B8860B', width=3)))
        fig.update_layout(yaxis2=dict(overlaying='y', side='right', title='%'), template='plotly_white')
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(tend, use_container_width=True)

def page_produtos():
    st.title("🌾 Questão 4: Top 5 Produtos Mais Rentáveis")
    st.markdown("*Usa CTE - Último ano*")
    
    top = top_produtos()
    if not top.empty:
        fig = px.bar(top, x='total_vendas', y='nome', orientation='h', color_discrete_sequence=['#1B4D3E'])
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(top, hide_index=True)

def page_anomalias():
    st.title("⚠️ Questão 7: Detecção de Anomalias")
    st.markdown("*Usa CTE - Detecta valor_total ≠ soma dos itens*")
    
    anom = detectar_anomalias()
    if not anom.empty:
        st.error(f"🔴 {len(anom)} contratos com divergências!")
        st.dataframe(anom, hide_index=True)
    else:
        st.success("✅ Nenhuma anomalia detectada!")

def page_inativos():
    st.title("😴 Questão 6: Clientes Inativos > 6 meses")
    st.markdown("*Usa CTE + Window Functions*")
    
    inativos = clientes_inativos()
    if not inativos.empty:
        st.warning(f"⚠️ {len(inativos)} clientes sem compras há +6 meses")
        st.dataframe(inativos, hide_index=True)
    else:
        st.success("✅ Todos os clientes ativos!")

def page_modelo_expandido():
    st.title("🔀 Questão 3: Modelo Expandido")
    st.markdown("*Múltiplos Clientes por Pedido (Compras Compartilhadas)*")
    
    st.info("""
    **Conceito:** Permite que cooperativas ou grupos de produtores 
    comprem conjuntamente com rateio de custos.
    
    **Tabela criada:** `pedido_clientes`
    - `id_pedido` + `id_cliente` (PK composta)
    - `percentual_rateio` (0-100%)
    - `valor_rateado`
    """)
    
    # Mostrar exemplo
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
    # Verificar login
    if not check_password():
        login_page()
        return
    
    # Sidebar com navegação
    st.sidebar.title(f"🌾 Agromercantil")
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
    
    # Info do sistema
    st.sidebar.markdown("**🖥️ Ambiente:**")
    st.sidebar.markdown("• VPS: PostgreSQL + Streamlit")
    st.sidebar.markdown("• Dados: Excel Real (1.500 contratos)")
    st.sidebar.markdown("• Usuário: " + st.session_state.username)
    
    if st.sidebar.button("🚪 Sair"):
        st.session_state.authenticated = False
        st.session_state.username = None
        st.rerun()
    
    # Renderizar página
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
