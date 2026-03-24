#!/usr/bin/env python3
import paramiko

VPS_IP = '173.212.205.8'
VPS_USER = 'mateus'
VPS_PASS = '231181mateu$'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname=VPS_IP, username=VPS_USER, password=VPS_PASS, timeout=30)

dashboard = '''import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text

st.set_page_config(page_title="Agromercantil Analytics", page_icon="🌾", layout="wide")
st.markdown("""
<style>
.main { background-color: #F7F5F0; }
h1, h2, h3 { color: #1B4D3E !important; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_engine():
    return create_engine("postgresql://agro_user:agro123456@localhost:5432/agromercantil")

def run_query(query, params=None):
    try:
        with get_engine().connect() as conn:
            result = conn.execute(text(query), params or {})
            return pd.DataFrame(result.fetchall(), columns=result.keys())
    except Exception as e:
        st.error(f"Erro: {e}")
        return pd.DataFrame()

def calcular_rfv():
    q = """
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
    """
    return run_query(q)

def tendencias_mensais():
    q = """
    WITH mensal AS (
        SELECT DATE_TRUNC('month', data_pedido) as mes,
               SUM(valor_total) as total, COUNT(*) as contratos
        FROM pedidos WHERE status != 'Cancelado'
        GROUP BY DATE_TRUNC('month', data_pedido) ORDER BY mes
    )
    SELECT 
        TO_CHAR(mes, 'YYYY-MM') as mes_ano, 
        ROUND(total, 2) as vendas,
        contratos,
        ROUND(((total - LAG(total) OVER (ORDER BY mes)) / 
        NULLIF(LAG(total) OVER (ORDER BY mes), 0)) * 100, 2) as crescimento
    FROM mensal ORDER BY mes DESC;
    """
    return run_query(q)

def detectar_anomalias():
    q = """
    WITH soma_itens AS (
        SELECT id_pedido, SUM(subtotal) as valor_calculado
        FROM itens_pedido GROUP BY id_pedido
    )
    SELECT 
        p.id_pedido, p.data_pedido, c.nome as cliente,
        p.valor_total as registrado, si.valor_calculado,
        ROUND(ABS(p.valor_total - si.valor_calculado), 2) as diferenca
    FROM pedidos p
    JOIN soma_itens si ON p.id_pedido = si.id_pedido
    JOIN clientes c ON p.id_cliente = c.id_cliente
    WHERE ABS(p.valor_total - si.valor_calculado) > 0.01
    ORDER BY diferenca DESC;
    """
    return run_query(q)

def clientes_inativos():
    q = """
    WITH ultima_atividade AS (
        SELECT id_cliente, MAX(data_pedido) as ultima_compra,
               CURRENT_DATE - MAX(data_pedido) as dias_inativo
        FROM pedidos GROUP BY id_cliente
    )
    SELECT 
        c.id_cliente, c.nome, c.tipo_cliente, c.regiao,
        ua.dias_inativo, ua.ultima_compra
    FROM clientes c
    JOIN ultima_atividade ua ON c.id_cliente = ua.id_cliente
    WHERE ua.dias_inativo > 180
    ORDER BY ua.dias_inativo DESC;
    """
    return run_query(q)

def top_produtos():
    q = """
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
    """
    return run_query(q)

st.sidebar.title("🌾 Agromercantil")
pagina = st.sidebar.radio("Navegação:", [
    "📊 Visão Geral", "👥 Análise RFV", "📈 Tendências", 
    "🌾 Produtos", "⚠️ Anomalias", "😴 Clientes Inativos"
])
st.sidebar.markdown("---")

if pagina == "📊 Visão Geral":
    st.title("Dashboard Agromercantil")
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

elif pagina == "👥 Análise RFV":
    st.title("Questão 2: Segmentação RFV (CTE + Window Functions)")
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

elif pagina == "📈 Tendências":
    st.title("Questão 5: Tendências de Mercado (CTE + LAG)")
    tend = tendencias_mensais()
    if not tend.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=tend['mes_ano'], y=tend['vendas'], name='Vendas', marker_color='#1B4D3E'))
        fig.add_trace(go.Scatter(x=tend['mes_ano'], y=tend['crescimento'], name='% Crescimento',
                                yaxis='y2', line=dict(color='#B8860B', width=3)))
        fig.update_layout(yaxis2=dict(overlaying='y', side='right', title='%'), template='plotly_white')
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(tend, use_container_width=True)

elif pagina == "🌾 Produtos":
    st.title("Questão 4: Top 5 Produtos Mais Rentáveis")
    top = top_produtos()
    if not top.empty:
        fig = px.bar(top, x='total_vendas', y='nome', orientation='h', color_discrete_sequence=['#1B4D3E'])
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(top, hide_index=True)

elif pagina == "⚠️ Anomalias":
    st.title("Questão 7: Detecção de Anomalias (CTE)")
    anom = detectar_anomalias()
    if not anom.empty:
        st.error(f"🔴 {len(anom)} contratos com divergências!")
        st.dataframe(anom, hide_index=True)
    else:
        st.success("✅ Nenhuma anomalia detectada!")

elif pagina == "😴 Clientes Inativos":
    st.title("Questão 6: Clientes Inativos > 6 meses (CTE)")
    inativos = clientes_inativos()
    if not inativos.empty:
        st.warning(f"⚠️ {len(inativos)} clientes sem compras há +6 meses")
        st.dataframe(inativos, hide_index=True)
    else:
        st.success("✅ Todos os clientes ativos!")
'''

# Salvar dashboard
sftp = ssh.open_sftp()
with sftp.file('/home/mateus/agromercantil/app/dashboard.py', 'w') as f:
    f.write(dashboard)
sftp.close()

print("Dashboard criado!")

# Ingerir dados
print("Ingerindo dados...")
stdin, stdout, stderr = ssh.exec_command('cd ~/agromercantil && ./venv/bin/python src/ingestao_dados.py', timeout=180)
exit_code = stdout.channel.recv_exit_status()
print("Saida:", stdout.read().decode()[-500:])

# Iniciar Streamlit
print("Iniciando Streamlit...")
stdin, stdout, stderr = ssh.exec_command('cd ~/agromercantil && nohup ./venv/bin/streamlit run app/dashboard.py --server.port 8501 --server.address 0.0.0.0 > streamlit.log 2>&1 &')
print("Streamlit iniciado!")

ssh.close()
print("=== DEPLOY CONCLUIDO ===")
print("Acesse: http://173.212.205.8:8501")

if __name__ == "__main__":
    main()
