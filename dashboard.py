"""
Agromercantil Analytics — Dashboard
Streamlit + HTML/CSS/JS (visual Stitch) + PostgreSQL + Gemini AI
"""
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

st.set_page_config(page_title="Agromercantil Analytics", page_icon="🌾", layout="wide", initial_sidebar_state="collapsed")

# ── Esconder TUDO do Streamlit ──
st.markdown("""<style>
    #MainMenu, header, footer, [data-testid="stHeader"],
    [data-testid="stToolbar"], [data-testid="stDecoration"],
    .stDeployButton, div.block-container { padding: 0 !important; margin: 0 !important; max-width: 100% !important; }
    [data-testid="stSidebar"] { display: none !important; }
    .main .block-container { padding: 0 !important; }
    section.main { padding: 0 !important; }
    .stApp { background: #F5F5F0; }
</style>""", unsafe_allow_html=True)

# ═══════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════
DB_URL = os.getenv('DATABASE_URL', 'postgresql://agro_user:agro123456@localhost:5432/agromercantil')

@st.cache_resource
def get_engine():
    return create_engine(DB_URL)

def query(sql):
    try:
        with get_engine().connect() as c:
            r = c.execute(text(sql))
            df = pd.DataFrame(r.fetchall(), columns=r.keys())
            for col in df.select_dtypes(include='object').columns:
                try: df[col] = pd.to_numeric(df[col])
                except: pass
            return df
    except Exception as e:
        return pd.DataFrame()

# ═══════════════════════════════════════
# SQL QUERIES
# ═══════════════════════════════════════
def get_kpis():
    df = query("""
        SELECT
            COALESCE(SUM(valor_total),0) as faturamento,
            COALESCE(AVG(valor_total),0) as ticket_medio,
            COUNT(*) as contratos,
            COUNT(DISTINCT id_cliente) as clientes
        FROM pedidos WHERE status != 'Cancelado'
    """)
    if df.empty: return {'faturamento':0,'ticket_medio':0,'contratos':0,'clientes':0}
    return df.iloc[0].to_dict()

def get_vendas_mensais():
    df = query("""
        SELECT TO_CHAR(data_pedido,'YYYY-MM') as mes, SUM(valor_total) as total
        FROM pedidos WHERE status != 'Cancelado'
        GROUP BY TO_CHAR(data_pedido,'YYYY-MM') ORDER BY mes
    """)
    return df

def get_vendas_regiao():
    df = query("""
        SELECT c.regiao, SUM(p.valor_total) as total
        FROM pedidos p JOIN clientes c ON p.id_cliente=c.id_cliente
        WHERE p.status != 'Cancelado' GROUP BY c.regiao ORDER BY total DESC
    """)
    return df

def get_rfv():
    return query("""
        WITH uc AS (
            SELECT id_cliente, MAX(data_pedido) as ultima, CURRENT_DATE - MAX(data_pedido) as dias
            FROM pedidos WHERE status != 'Cancelado' GROUP BY id_cliente
        ), m AS (
            SELECT id_cliente, COUNT(*) as pedidos, ROUND(AVG(valor_total)::numeric,2) as ticket,
                   ROUND(SUM(valor_total)::numeric,2) as valor
            FROM pedidos WHERE status != 'Cancelado' GROUP BY id_cliente
        )
        SELECT c.nome, c.tipo_cliente, c.regiao, uc.dias as dias_inativo,
               m.pedidos, m.ticket as ticket_medio, m.valor as valor_total,
               CASE WHEN uc.dias<=30 AND m.pedidos>=5 THEN 'Campeão'
                    WHEN uc.dias<=60 AND m.pedidos>=3 THEN 'Fiel'
                    WHEN uc.dias<=90 THEN 'Ativo' ELSE 'Em Risco' END as segmento
        FROM clientes c JOIN uc ON c.id_cliente=uc.id_cliente JOIN m ON c.id_cliente=m.id_cliente
        ORDER BY m.valor DESC
    """)

def get_top5():
    return query("""
        WITH rp AS (
            SELECT p.nome, p.categoria, SUM(i.quantidade*i.preco_unitario) as receita,
                   SUM(i.quantidade) as volume, COUNT(DISTINCT ped.id_pedido) as contratos
            FROM itens_pedido i JOIN produtos p ON i.id_produto=p.id_produto
            JOIN pedidos ped ON i.id_pedido=ped.id_pedido
            WHERE ped.data_pedido >= CURRENT_DATE - INTERVAL '1 year' AND ped.status!='Cancelado'
            GROUP BY p.nome, p.categoria
        )
        SELECT nome, categoria, ROUND(receita::numeric,2) as receita,
               ROUND(volume::numeric,0) as volume, contratos FROM rp ORDER BY receita DESC LIMIT 5
    """)

def get_tendencias():
    return query("""
        WITH mensal AS (
            SELECT DATE_TRUNC('month',data_pedido) as mes, SUM(valor_total) as total, COUNT(*) as n
            FROM pedidos WHERE status!='Cancelado' GROUP BY DATE_TRUNC('month',data_pedido)
        )
        SELECT TO_CHAR(mes,'YYYY-MM') as mes_ano, ROUND(total::numeric,2) as vendas, n as contratos,
               ROUND(((total-LAG(total) OVER(ORDER BY mes))/NULLIF(LAG(total) OVER(ORDER BY mes),0)*100)::numeric,1) as crescimento
        FROM mensal ORDER BY mes
    """)

def get_anomalias():
    return query("""
        WITH si AS (SELECT id_pedido, SUM(quantidade*preco_unitario) as calc FROM itens_pedido GROUP BY id_pedido)
        SELECT p.id_pedido, TO_CHAR(p.data_pedido,'DD/MM/YYYY') as data, c.nome as cliente,
               ROUND(p.valor_total::numeric,2) as registrado, ROUND(si.calc::numeric,2) as calculado,
               ROUND(ABS(p.valor_total-si.calc)::numeric,2) as diferenca
        FROM pedidos p JOIN si ON p.id_pedido=si.id_pedido JOIN clientes c ON p.id_cliente=c.id_cliente
        WHERE ABS(p.valor_total-si.calc) > 0.01 ORDER BY ABS(p.valor_total-si.calc) DESC
    """)

def get_inativos():
    return query("""
        WITH ua AS (SELECT id_cliente, MAX(data_pedido) as ult, CURRENT_DATE-MAX(data_pedido) as dias FROM pedidos GROUP BY id_cliente)
        SELECT c.nome, c.tipo_cliente, c.regiao, ua.dias as dias_inativo, TO_CHAR(ua.ult,'DD/MM/YYYY') as ultima_compra
        FROM clientes c JOIN ua ON c.id_cliente=ua.id_cliente WHERE ua.dias>180 ORDER BY ua.dias DESC
    """)

def get_tabela(tabela):
    return query(f"SELECT * FROM {tabela} LIMIT 200")

# ═══════════════════════════════════════
# HTML BASE (Visual Stitch)
# ═══════════════════════════════════════
def base_css():
    return """
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800&display=swap');
    * { margin:0; padding:0; box-sizing:border-box; }
    body { font-family:'Montserrat',sans-serif; background:#F5F5F0; color:#333; }
    :root {
        --green:#2E5A27; --green-dark:#1D3D1A; --green-light:#8DC140;
        --orange:#F58220; --bg:#F5F5F0; --white:#FFF; --gray:#4A5568; --red:#E53E3E;
    }

    /* SIDEBAR */
    .sidebar { position:fixed; left:0; top:0; bottom:0; width:240px; background:linear-gradient(180deg,var(--green),var(--green-dark));
        color:#fff; padding:20px 0; z-index:100; display:flex; flex-direction:column; }
    .sidebar .logo { text-align:center; padding:20px; border-bottom:1px solid rgba(255,255,255,.1); }
    .sidebar .logo h2 { font-size:1.1rem; font-weight:800; letter-spacing:1px; }
    .sidebar .logo h2 span { color:var(--orange); }
    .sidebar .logo small { font-size:.7rem; opacity:.6; display:block; margin-top:4px; }
    .sidebar nav { flex:1; padding:20px 0; }
    .sidebar nav a { display:flex; align-items:center; gap:10px; padding:12px 24px; color:rgba(255,255,255,.7);
        text-decoration:none; font-size:.85rem; font-weight:500; transition:all .2s; border-left:3px solid transparent; }
    .sidebar nav a:hover { background:rgba(255,255,255,.05); color:#fff; }
    .sidebar nav a.active { color:#fff; background:rgba(255,255,255,.08); border-left-color:var(--orange); font-weight:700; }
    .sidebar .user { padding:16px 24px; border-top:1px solid rgba(255,255,255,.1); }
    .sidebar .user .name { font-size:.85rem; font-weight:600; }
    .sidebar .user small { opacity:.5; font-size:.7rem; }

    /* MAIN */
    .main-content { margin-left:240px; padding:30px 40px; min-height:100vh; }

    /* HEADER */
    .page-header h1 { font-size:1.6rem; font-weight:800; color:var(--green); }
    .page-header .bar { width:60px; height:4px; background:var(--orange); border-radius:2px; margin:8px 0 4px; }
    .page-header p { color:var(--gray); font-size:.85rem; margin-bottom:24px; }

    /* KPI CARDS */
    .kpi-row { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:20px; margin-bottom:30px; }
    .kpi { background:var(--white); border-radius:12px; padding:20px 24px; box-shadow:0 2px 8px rgba(0,0,0,.05);
        border-left:4px solid var(--orange); }
    .kpi .label { font-size:.78rem; font-weight:600; color:var(--gray); text-transform:uppercase; letter-spacing:.5px; }
    .kpi .value { font-size:1.6rem; font-weight:800; color:var(--green); margin-top:6px; }
    .kpi .sub { font-size:.75rem; color:var(--green-light); margin-top:4px; }

    /* CHARTS */
    .chart-container { background:var(--white); border-radius:12px; padding:24px; box-shadow:0 2px 8px rgba(0,0,0,.05); margin-bottom:24px; }
    .chart-container h3 { font-size:1rem; font-weight:700; color:var(--green); margin-bottom:16px; }
    .chart-row { display:grid; grid-template-columns:1fr 1fr; gap:24px; margin-bottom:24px; }

    /* TABLE */
    .data-table { width:100%; border-collapse:collapse; font-size:.82rem; }
    .data-table thead th { background:var(--green); color:#fff; padding:12px 16px; text-align:left; font-weight:600;
        font-size:.75rem; text-transform:uppercase; letter-spacing:.5px; }
    .data-table tbody td { padding:10px 16px; border-bottom:1px solid #eee; }
    .data-table tbody tr:hover { background:#f0f7ee; }
    .data-table tbody tr:nth-child(even) { background:#fafaf8; }

    /* BADGES */
    .badge { padding:4px 10px; border-radius:20px; font-size:.7rem; font-weight:600; display:inline-block; }
    .badge-green { background:#e6f4e1; color:var(--green); }
    .badge-gold { background:#fef3cd; color:#856404; }
    .badge-gray { background:#e2e8f0; color:var(--gray); }
    .badge-red { background:#fed7d7; color:var(--red); }

    /* ALERT */
    .alert { padding:14px 20px; border-radius:10px; font-size:.85rem; font-weight:500; margin-bottom:16px; display:flex; align-items:center; gap:10px; }
    .alert-success { background:#e6f4e1; color:var(--green); border:1px solid #c6e6bc; }
    .alert-warning { background:#fff3cd; color:#856404; border:1px solid #ffeeba; }
    .alert-danger { background:#fed7d7; color:var(--red); border:1px solid #feb2b2; }

    /* TABS */
    .tabs { display:flex; gap:0; border-bottom:2px solid #e2e8f0; margin-bottom:24px; }
    .tab { padding:10px 24px; font-size:.85rem; font-weight:600; color:var(--gray); cursor:pointer; border-bottom:3px solid transparent; margin-bottom:-2px; }
    .tab.active { color:var(--green); border-bottom-color:var(--orange); }
    .tab:hover { color:var(--green); }

    /* LOGIN */
    .login-page { min-height:100vh; background:linear-gradient(135deg,#2E5A27 0%,#1D3D1A 50%,#2E5A27 100%);
        display:flex; align-items:center; justify-content:center; }
    .login-box { background:var(--white); border-radius:16px; padding:40px; width:400px; box-shadow:0 20px 60px rgba(0,0,0,.3); }
    .login-logo { text-align:center; margin-bottom:30px; }
    .login-logo .icon { font-size:3rem; }
    .login-logo h1 { font-size:1.4rem; font-weight:800; color:var(--green); }
    .login-logo h1 span { color:var(--orange); }
    .login-logo p { font-size:.8rem; color:var(--gray); margin-top:4px; }
    .login-logo .bar { width:40px; height:3px; background:var(--orange); margin:12px auto; }
    .form-group { margin-bottom:16px; }
    .form-group label { display:block; font-size:.8rem; font-weight:600; color:var(--gray); margin-bottom:6px; }
    .form-group input { width:100%; padding:12px 16px; border:2px solid #e2e8f0; border-radius:8px; font-family:inherit;
        font-size:.9rem; outline:none; transition:border-color .2s; }
    .form-group input:focus { border-color:var(--green); }
    .btn-primary { width:100%; padding:14px; background:var(--orange); color:#fff; border:none; border-radius:8px;
        font-family:inherit; font-size:.95rem; font-weight:700; cursor:pointer; transition:all .2s; }
    .btn-primary:hover { background:#e0731a; transform:translateY(-1px); box-shadow:0 4px 12px rgba(245,130,32,.4); }
    .login-footer { text-align:center; margin-top:24px; font-size:.75rem; color:rgba(255,255,255,.4); }

    canvas { max-height: 300px !important; }
    """

def sidebar_html(active_page, user="Admin"):
    nav_items = [
        ("📊","Visão Geral","visao_geral"),
        ("👥","Análise RFV","rfv"),
        ("🌾","Produtos","produtos"),
        ("📈","Tendências","tendencias"),
        ("⚠️","Anomalias","anomalias"),
        ("🔬","Exploratória","exploratoria"),
        ("🗄️","Base de Dados","dados"),
    ]
    links = ""
    for icon, label, key in nav_items:
        cls = "active" if key == active_page else ""
        links += f'<a href="?page={key}" target="_parent" class="{cls}">{icon} {label}</a>'

    return f"""
    <div class="sidebar">
        <div class="logo">
            <div style="font-size:2rem">🌾</div>
            <h2>AGRO<span>MERCANTIL</span></h2>
            <small>Analytics Dashboard</small>
        </div>
        <nav>{links}</nav>
        <div class="user">
            <div class="name">👤 {user}</div>
            <small>Gestor de Dados</small>
            <br><br>
            <a href="?page=logout" target="_parent" style="color:var(--orange); font-size:.8rem; text-decoration:none;">🚪 Sair</a>
        </div>
    </div>
    """

def fmt(v, prefix="R$ ", decimals=0):
    try:
        n = float(v)
        if n >= 1_000_000: return f"{prefix}{n/1_000_000:,.1f}M"
        elif n >= 1_000: return f"{prefix}{n/1_000:,.1f}K"
        return f"{prefix}{n:,.{decimals}f}"
    except: return f"{prefix}0"

# ═══════════════════════════════════════
# PAGES
# ═══════════════════════════════════════
def render_login():
    FIELD_BG = "https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=1200&q=80"
    html = f"""<!DOCTYPE html><html><head>
    <style>
    {base_css()}
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ font-family:'Montserrat',sans-serif; height:100vh; overflow:hidden; }}
    .login-split {{ display:grid; grid-template-columns:1fr 480px; height:100vh; }}
    .login-left {{
        background: linear-gradient(135deg, rgba(29,61,26,.92) 0%, rgba(46,90,39,.85) 100%),
                    url('{FIELD_BG}') center/cover no-repeat;
        display:flex; flex-direction:column; justify-content:flex-end; padding:60px;
        color:#fff; position:relative;
    }}
    .login-left .brand {{ display:flex; align-items:center; gap:14px; position:absolute; top:40px; left:60px; }}
    .login-left .brand .logo-icon {{ width:44px; height:44px; background:var(--orange); border-radius:10px;
        display:flex; align-items:center; justify-content:center; font-size:1.4rem; }}
    .login-left .brand .brand-name {{ font-size:1.1rem; font-weight:800; color:#fff; letter-spacing:1px; }}
    .login-left .brand .brand-sub {{ font-size:.65rem; opacity:.7; display:block; margin-top:2px; }}
    .login-left .hero {{ margin-bottom:60px; }}
    .login-left .hero .tag {{ background:rgba(245,130,32,.2); border:1px solid rgba(245,130,32,.4);
        color:var(--orange); font-size:.72rem; font-weight:700; padding:5px 14px; border-radius:20px;
        display:inline-block; margin-bottom:20px; letter-spacing:1px; text-transform:uppercase; }}
    .login-left .hero h1 {{ font-size:2.4rem; font-weight:800; line-height:1.2; margin-bottom:16px; }}
    .login-left .hero h1 span {{ color:var(--green-light); }}
    .login-left .hero p {{ font-size:.9rem; opacity:.75; line-height:1.6; max-width:460px; }}
    .login-left .version {{ font-size:.7rem; opacity:.4; margin-top:30px; letter-spacing:1px; text-transform:uppercase; }}
    .login-right {{ background:#fff; display:flex; flex-direction:column; justify-content:center;
        padding:60px 52px; position:relative; }}
    .login-right h2 {{ font-size:1.5rem; font-weight:800; color:var(--green); margin-bottom:6px; }}
    .login-right .subtitle {{ font-size:.85rem; color:var(--gray); margin-bottom:36px; }}
    .form-label {{ font-size:.72rem; font-weight:700; color:var(--gray); text-transform:uppercase;
        letter-spacing:.5px; margin-bottom:8px; display:block; }}
    .form-input {{ width:100%; padding:14px 16px; border:2px solid #e8edf0; border-radius:10px;
        font-family:inherit; font-size:.9rem; outline:none; transition:border-color .2s;
        background:#fafbfc; color:#333; margin-bottom:20px; }}
    .form-input:focus {{ border-color:var(--green); background:#fff; box-shadow:0 0 0 4px rgba(46,90,39,.08); }}
    .form-row {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }}
    .forgot {{ font-size:.78rem; color:var(--orange); text-decoration:none; font-weight:600; }}
    .forgot:hover {{ text-decoration:underline; }}
    .remember {{ display:flex; align-items:center; gap:8px; font-size:.8rem; color:var(--gray); margin-bottom:24px; }}
    .btn-login {{ width:100%; padding:15px; background:var(--orange); color:#fff; border:none; border-radius:10px;
        font-family:inherit; font-size:1rem; font-weight:700; cursor:pointer; transition:all .2s;
        display:flex; align-items:center; justify-content:center; gap:8px; }}
    .btn-login:hover {{ background:#e0731a; transform:translateY(-2px); box-shadow:0 6px 20px rgba(245,130,32,.35); }}
    .access-tag {{ text-align:center; margin-top:24px; font-size:.75rem; color:var(--gray); letter-spacing:.5px; text-transform:uppercase; }}
    .login-footer-bottom {{ position:absolute; bottom:30px; left:52px; right:52px; display:flex;
        justify-content:space-between; font-size:.72rem; color:#bbb; }}
    .login-footer-bottom a {{ color:#bbb; text-decoration:none; }}
    .login-footer-bottom a:hover {{ color:var(--gray); }}
    </style></head><body>
    <div class="login-split">
        <!-- LEFT PANEL -->
        <div class="login-left">
            <div class="brand">
                <div class="logo-icon">🌾</div>
                <div>
                    <div class="brand-name">AGROMERCANTIL</div>
                    <span class="brand-sub">Soluções Inteligentes para o Agro</span>
                </div>
            </div>
            <div class="hero">
                <div class="tag">Market Analytics Platform v4.9</div>
                <h1>A inteligência de<br>dados que cultiva o<br>seu <span>sucesso.</span></h1>
                <p>Analise commodities globais com precisão institucional. Onde a tradição do campo encontra a tecnologia do futuro.</p>
                <div class="version">Market Analytics Platform V4.9</div>
            </div>
        </div>
        <!-- RIGHT PANEL -->
        <div class="login-right">
            <h2>Analytics Dashboard</h2>
            <p class="subtitle">Plataforma de Análise de Commodities</p>
            <form id="loginForm">
                <label class="form-label">E-mail</label>
                <input class="form-input" type="text" id="email" placeholder="nome@empresa.com.br">
                <div class="form-row">
                    <label class="form-label" style="margin:0">Senha</label>
                    <a href="#" class="forgot">Esqueci minha senha</a>
                </div>
                <input class="form-input" type="password" id="senha" placeholder="••••••••">
                <label class="remember">
                    <input type="checkbox"> Manter conectado por 30 dias
                </label>
                <button type="submit" class="btn-login">Entrar →</button>
                <div class="access-tag">Acesso Restrito</div>
            </form>
            <div class="login-footer-bottom">
                <div>Agromercantil © 2025 — Soluções Inteligentes para o Agro</div>
                <div><a href="#">Privacidade</a> · <a href="#">Termos de Uso</a> · <a href="#">Contato</a></div>
            </div>
        </div>
    </div>
    <script>
    document.getElementById('loginForm').onsubmit = function(e) {{
        e.preventDefault();
        var email = document.getElementById('email').value;
        var senha = document.getElementById('senha').value;
        if(email && senha) {{ window.parent.location.href = '?page=visao_geral&user=' + encodeURIComponent(email.split('@')[0]); }}
        else {{ alert('Preencha e-mail e senha'); }}
    }};
    </script>
    </body></html>"""
    components.html(html, height=800, scrolling=False)


def render_visao_geral(user):
    kpis = get_kpis()
    vendas = get_vendas_mensais()
    regioes = get_vendas_regiao()

    labels_v = json.dumps(vendas['mes'].tolist()) if not vendas.empty else '[]'
    data_v = json.dumps(vendas['total'].astype(float).tolist()) if not vendas.empty else '[]'
    labels_r = json.dumps(regioes['regiao'].tolist()) if not regioes.empty else '[]'
    data_r = json.dumps(regioes['total'].astype(float).tolist()) if not regioes.empty else '[]'

    anomalias = get_anomalias()
    inativos = get_inativos()
    n_anom = len(anomalias)
    n_inat = len(inativos)

    alert_anom = f'<div class="alert alert-warning">⚠️ <b>{n_anom} contratos</b> com divergência de valores</div>' if n_anom > 0 else '<div class="alert alert-success">✅ Nenhuma anomalia detectada</div>'
    alert_inat = f'<div class="alert alert-danger">🚨 <b>{n_inat} clientes</b> inativos há mais de 6 meses</div>' if n_inat > 0 else '<div class="alert alert-success">✅ Todos os clientes ativos</div>'

    html = f"""<!DOCTYPE html><html><head>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
    <style>{base_css()}</style></head><body>
    {sidebar_html('visao_geral', user)}
    <div class="main-content">
        <div class="page-header"><h1>📊 Dashboard Agromercantil</h1><div class="bar"></div>
            <p>Trading de Commodities — Análise em Tempo Real</p></div>

        <div class="kpi-row">
            <div class="kpi"><div class="label">💰 Faturamento Total</div><div class="value">{fmt(kpis['faturamento'])}</div></div>
            <div class="kpi"><div class="label">📋 Ticket Médio</div><div class="value">{fmt(kpis['ticket_medio'])}</div></div>
            <div class="kpi"><div class="label">📄 Contratos</div><div class="value">{int(kpis['contratos']):,}</div></div>
            <div class="kpi"><div class="label">👥 Clientes Ativos</div><div class="value">{int(kpis['clientes'])}</div></div>
        </div>

        <div class="chart-container"><h3>Evolução de Vendas Mensais</h3><canvas id="chartVendas"></canvas></div>

        <div class="chart-row">
            <div class="chart-container"><h3>Distribuição por Região</h3><canvas id="chartRegiao"></canvas></div>
            <div class="chart-container"><h3>🚨 Alertas do Sistema</h3>{alert_anom}{alert_inat}</div>
        </div>
    </div>
    <script>
    new Chart(document.getElementById('chartVendas'),{{type:'line',data:{{labels:{labels_v},
        datasets:[{{label:'Vendas (R$)',data:{data_v},borderColor:'#2E5A27',backgroundColor:'rgba(141,193,64,.12)',
        fill:true,tension:.3,borderWidth:3,pointRadius:4,pointBackgroundColor:'#2E5A27'}}]}},
        options:{{responsive:true,plugins:{{legend:{{display:false}}}},scales:{{y:{{ticks:{{callback:v=>v>=1e6?(v/1e6).toFixed(1)+'M':(v/1e3).toFixed(0)+'K'}}}}}}}}}});
    new Chart(document.getElementById('chartRegiao'),{{type:'doughnut',data:{{labels:{labels_r},
        datasets:[{{data:{data_r},backgroundColor:['#2E5A27','#8DC140','#F58220','#B8860B','#4A5568','#1D3D1A']}}]}},
        options:{{responsive:true,plugins:{{legend:{{position:'bottom'}}}}}}}});
    </script></body></html>"""
    components.html(html, height=1000, scrolling=True)


def render_rfv(user):
    rfv = get_rfv()
    if rfv.empty:
        components.html(f"<style>{base_css()}</style>{sidebar_html('rfv',user)}<div class='main-content'><h1>Sem dados RFV</h1></div>", height=400)
        return

    seg_counts = rfv['segmento'].value_counts().to_dict()
    seg_colors = {'Campeão':'green','Fiel':'gold','Ativo':'gray','Em Risco':'red'}

    badges_html = ""
    for seg, badge_cls in seg_colors.items():
        badges_html += f'<div class="kpi"><div class="label">{seg}</div><div class="value">{seg_counts.get(seg,0)}</div><div class="sub">clientes</div></div>'

    top10 = rfv.nlargest(10, 'valor_total')
    top_labels = json.dumps(top10['nome'].tolist())
    top_data = json.dumps(top10['valor_total'].astype(float).tolist())
    top_colors = json.dumps([{'Campeão':'#2E5A27','Fiel':'#B8860B','Ativo':'#4A5568','Em Risco':'#E53E3E'}.get(s,'#4A5568') for s in top10['segmento']])

    seg_labels = json.dumps(list(seg_counts.keys()))
    seg_data = json.dumps(list(seg_counts.values()))

    rows = ""
    for _, r in rfv.head(50).iterrows():
        badge_cls = {'Campeão':'badge-green','Fiel':'badge-gold','Ativo':'badge-gray','Em Risco':'badge-red'}.get(r['segmento'],'badge-gray')
        rows += f"<tr><td>{r['nome']}</td><td>{r['tipo_cliente']}</td><td>{r['regiao']}</td><td>{int(r['dias_inativo'])}d</td><td>{int(r['pedidos'])}</td><td>{fmt(r['ticket_medio'],decimals=0)}</td><td>{fmt(r['valor_total'],decimals=0)}</td><td><span class='badge {badge_cls}'>{r['segmento']}</span></td></tr>"

    html = f"""<!DOCTYPE html><html><head><script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
    <style>{base_css()}</style></head><body>
    {sidebar_html('rfv',user)}
    <div class="main-content">
        <div class="page-header"><h1>👥 Segmentação RFV</h1><div class="bar"></div>
            <p>Recência, Frequência e Valor — CTE + Window Functions</p></div>
        <div class="kpi-row">{badges_html}</div>
        <div class="chart-row">
            <div class="chart-container"><h3>Distribuição de Segmentos</h3><canvas id="cSeg"></canvas></div>
            <div class="chart-container"><h3>Top 10 Clientes por Valor</h3><canvas id="cTop"></canvas></div>
        </div>
        <div class="chart-container"><h3>Base Completa de Clientes</h3>
            <div style="overflow-x:auto"><table class="data-table"><thead><tr>
            <th>Nome</th><th>Tipo</th><th>Região</th><th>Inativo</th><th>Pedidos</th><th>Ticket</th><th>Valor Total</th><th>Segmento</th>
            </tr></thead><tbody>{rows}</tbody></table></div></div>
    </div>
    <script>
    new Chart(document.getElementById('cSeg'),{{type:'doughnut',data:{{labels:{seg_labels},datasets:[{{data:{seg_data},
        backgroundColor:['#2E5A27','#B8860B','#4A5568','#E53E3E']}}]}},options:{{cutout:'35%',plugins:{{legend:{{position:'bottom'}}}}}}}});
    new Chart(document.getElementById('cTop'),{{type:'bar',data:{{labels:{top_labels},datasets:[{{data:{top_data},
        backgroundColor:{top_colors},borderRadius:4}}]}},options:{{indexAxis:'y',plugins:{{legend:{{display:false}}}},
        scales:{{x:{{ticks:{{callback:v=>v>=1e6?(v/1e6).toFixed(1)+'M':(v/1e3).toFixed(0)+'K'}}}}}}}}}});
    </script></body></html>"""
    components.html(html, height=1400, scrolling=True)


def render_produtos(user):
    top5 = get_top5()
    if top5.empty:
        components.html(f"<style>{base_css()}</style>{sidebar_html('produtos',user)}<div class='main-content'><h1>Sem dados de produtos</h1></div>",height=400)
        return

    labels = json.dumps(top5['nome'].tolist())
    data = json.dumps(top5['receita'].astype(float).tolist())
    cats = json.dumps(top5['categoria'].tolist())

    rows = ""
    for _,r in top5.iterrows():
        rows += f"<tr><td><b>{r['nome']}</b></td><td>{r['categoria']}</td><td>{fmt(r['receita'])}</td><td>{int(r['volume']):,}</td><td>{int(r['contratos'])}</td></tr>"

    html = f"""<!DOCTYPE html><html><head><script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
    <style>{base_css()}</style></head><body>
    {sidebar_html('produtos',user)}
    <div class="main-content">
        <div class="page-header"><h1>🌾 Análise de Produtos e Commodities</h1><div class="bar"></div>
            <p>Top 5 Produtos Mais Rentáveis — CTE com INTERVAL</p></div>
        <div class="kpi-row">
            <div class="kpi"><div class="label">💰 Receita Top 5</div><div class="value">{fmt(top5['receita'].sum())}</div></div>
            <div class="kpi"><div class="label">📦 Volume Total</div><div class="value">{int(top5['volume'].sum()):,}</div></div>
            <div class="kpi"><div class="label">📄 Contratos</div><div class="value">{int(top5['contratos'].sum())}</div></div>
        </div>
        <div class="chart-container"><h3>Top 5 Produtos Mais Rentáveis (Último Ano)</h3><canvas id="cProd"></canvas></div>
        <div class="chart-container"><h3>Detalhamento</h3>
            <table class="data-table"><thead><tr><th>Produto</th><th>Categoria</th><th>Receita</th><th>Volume</th><th>Contratos</th></tr></thead>
            <tbody>{rows}</tbody></table></div>
    </div>
    <script>
    new Chart(document.getElementById('cProd'),{{type:'bar',data:{{labels:{labels},datasets:[{{data:{data},
        backgroundColor:['#2E5A27','#3D7A35','#8DC140','#F58220','#B8860B'],borderRadius:6}}]}},
        options:{{indexAxis:'y',plugins:{{legend:{{display:false}}}},scales:{{x:{{ticks:{{callback:v=>v>=1e6?(v/1e6).toFixed(1)+'M':(v/1e3).toFixed(0)+'K'}}}}}}}}}});
    </script></body></html>"""
    components.html(html, height=900, scrolling=True)


def render_tendencias(user):
    tend = get_tendencias()
    inativos = get_inativos()

    labels = json.dumps(tend['mes_ano'].tolist()) if not tend.empty else '[]'
    vendas = json.dumps(tend['vendas'].astype(float).tolist()) if not tend.empty else '[]'
    cresc = json.dumps(tend['crescimento'].astype(float).fillna(0).tolist()) if not tend.empty else '[]'

    inat_rows = ""
    for _,r in inativos.head(20).iterrows():
        cls = "color:var(--red);font-weight:700" if r['dias_inativo']>365 else ""
        inat_rows += f"<tr><td>{r['nome']}</td><td>{r['tipo_cliente']}</td><td>{r['regiao']}</td><td style='{cls}'>{int(r['dias_inativo'])}d</td><td>{r['ultima_compra']}</td></tr>"

    n_inat = len(inativos)
    melhor = tend.loc[tend['vendas'].idxmax()] if not tend.empty else None
    cresc_medio = tend['crescimento'].dropna().mean() if not tend.empty else 0
    n_neg = int((tend['crescimento'].dropna() < 0).sum()) if not tend.empty else 0

    html = f"""<!DOCTYPE html><html><head><script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
    <style>{base_css()}</style></head><body>
    {sidebar_html('tendencias',user)}
    <div class="main-content">
        <div class="page-header"><h1>📈 Tendências de Mercado</h1><div class="bar"></div>
            <p>Análise Mensal com LAG — Window Functions</p></div>
        <div class="kpi-row">
            <div class="kpi"><div class="label">🏆 Melhor Mês</div><div class="value">{melhor['mes_ano'] if melhor is not None else '-'}</div><div class="sub">{fmt(melhor['vendas']) if melhor is not None else ''}</div></div>
            <div class="kpi"><div class="label">📊 Cresc. Médio</div><div class="value">{cresc_medio:.1f}%</div></div>
            <div class="kpi"><div class="label">📉 Meses Negativos</div><div class="value">{n_neg}</div></div>
        </div>
        <div class="chart-container"><h3>Evolução Mensal — Vendas + Crescimento (%)</h3><canvas id="cTend"></canvas></div>
        <div class="chart-container"><h3>⏰ Clientes Inativos &gt; 6 Meses ({n_inat} encontrados)</h3>
            {'<div class="alert alert-danger">🚨 '+str(n_inat)+' clientes sem atividade há mais de 180 dias</div>' if n_inat>0 else '<div class="alert alert-success">✅ Todos ativos</div>'}
            <div style="overflow-x:auto"><table class="data-table"><thead><tr><th>Nome</th><th>Tipo</th><th>Região</th><th>Dias</th><th>Última Compra</th></tr></thead>
            <tbody>{inat_rows}</tbody></table></div></div>
    </div>
    <script>
    new Chart(document.getElementById('cTend'),{{type:'bar',data:{{labels:{labels},datasets:[
        {{type:'bar',label:'Vendas (R$)',data:{vendas},backgroundColor:'rgba(46,90,39,.7)',borderRadius:4,yAxisID:'y'}},
        {{type:'line',label:'Crescimento %',data:{cresc},borderColor:'#F58220',borderWidth:3,pointRadius:3,tension:.3,yAxisID:'y1'}}
    ]}},options:{{responsive:true,plugins:{{legend:{{position:'top'}}}},scales:{{y:{{position:'left',ticks:{{callback:v=>v>=1e6?(v/1e6).toFixed(1)+'M':(v/1e3).toFixed(0)+'K'}}}},y1:{{position:'right',grid:{{drawOnChartArea:false}},ticks:{{callback:v=>v+'%'}}}}}}}}}});
    </script></body></html>"""
    components.html(html, height=1200, scrolling=True)


def render_anomalias(user):
    anom = get_anomalias()
    n = len(anom)

    rows = ""
    for _,r in anom.head(30).iterrows():
        rows += f"<tr><td>#{r['id_pedido']}</td><td>{r['data']}</td><td>{r['cliente']}</td><td>{fmt(r['registrado'])}</td><td>{fmt(r['calculado'])}</td><td style='color:var(--red);font-weight:700'>{fmt(r['diferenca'])}</td></tr>"

    reg = json.dumps(anom['registrado'].astype(float).tolist()) if not anom.empty else '[]'
    calc = json.dumps(anom['calculado'].astype(float).tolist()) if not anom.empty else '[]'

    html = f"""<!DOCTYPE html><html><head><script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
    <style>{base_css()}</style></head><body>
    {sidebar_html('anomalias',user)}
    <div class="main-content">
        <div class="page-header"><h1>⚠️ Detecção de Anomalias em Vendas</h1><div class="bar"></div>
            <p>Divergências entre valor_total e soma dos itens — CTE</p></div>
        {'<div class="alert alert-danger">🚨 <b>'+str(n)+' contratos</b> com divergência de valores detectados!</div>' if n>0 else '<div class="alert alert-success">✅ <b>Nenhuma anomalia detectada!</b> Todos os valores estão consistentes.</div>'}
        <div class="kpi-row">
            <div class="kpi"><div class="label">Total Anomalias</div><div class="value" style="color:var(--red)">{n}</div></div>
            <div class="kpi"><div class="label">Divergência Total</div><div class="value">{fmt(anom['diferenca'].sum()) if not anom.empty else 'R$ 0'}</div></div>
            <div class="kpi"><div class="label">Maior Divergência</div><div class="value">{fmt(anom['diferenca'].max()) if not anom.empty else 'R$ 0'}</div></div>
        </div>
        <div class="chart-container"><h3>Valor Registrado vs Calculado</h3><canvas id="cAnom"></canvas></div>
        <div class="chart-container"><h3>Contratos com Divergência</h3>
            <table class="data-table"><thead><tr><th>Pedido</th><th>Data</th><th>Cliente</th><th>Registrado</th><th>Calculado</th><th>Diferença</th></tr></thead>
            <tbody>{rows if rows else '<tr><td colspan="6" style="text-align:center;padding:30px;color:var(--green)">✅ Sem divergências</td></tr>'}</tbody></table></div>
    </div>
    <script>
    {'new Chart(document.getElementById("cAnom"),{type:"scatter",data:{datasets:[{label:"Pedidos",data:'+json.dumps([{"x":float(r["registrado"]),"y":float(r["calculado"])} for _,r in anom.iterrows()])+',backgroundColor:"rgba(229,62,62,.6)",pointRadius:6},{label:"Ref.",data:[{x:0,y:0},{x:'+str(max(anom["registrado"].max(),anom["calculado"].max()) if not anom.empty else 100)+',y:'+str(max(anom["registrado"].max(),anom["calculado"].max()) if not anom.empty else 100)+'}],type:"line",borderColor:"#8DC140",borderDash:[5,5],pointRadius:0}]},options:{plugins:{legend:{display:false}}}});' if not anom.empty else ''}
    </script></body></html>"""
    components.html(html, height=1100, scrolling=True)


def render_exploratoria(user):
    df = query("SELECT p.valor_total, p.data_pedido, c.tipo_cliente, c.regiao FROM pedidos p JOIN clientes c ON p.id_cliente=c.id_cliente WHERE p.status!='Cancelado'")
    if df.empty:
        components.html(f"<style>{base_css()}</style>{sidebar_html('exploratoria',user)}<div class='main-content'><h1>Sem dados</h1></div>",height=400)
        return

    import numpy as np
    # Histogram bins
    vals = df['valor_total'].astype(float)
    hist, edges = np.histogram(vals, bins=20)
    hist_labels = json.dumps([f"R${e/1000:.0f}K" for e in edges[:-1]])
    hist_data = json.dumps(hist.tolist())
    mean_val = float(vals.mean())

    # Boxplot by tipo_cliente
    tipos = df['tipo_cliente'].unique().tolist()
    box_data = {}
    for t in tipos:
        v = df[df['tipo_cliente']==t]['valor_total'].astype(float)
        box_data[t] = {'min':float(v.min()),'q1':float(v.quantile(.25)),'med':float(v.median()),'q3':float(v.quantile(.75)),'max':float(v.max())}

    box_table = ""
    for t, b in box_data.items():
        box_table += f"<tr><td><b>{t}</b></td><td>{fmt(b['min'])}</td><td>{fmt(b['q1'])}</td><td>{fmt(b['med'])}</td><td>{fmt(b['q3'])}</td><td>{fmt(b['max'])}</td></tr>"

    # Vendas por região
    reg = df.groupby('regiao')['valor_total'].agg(['sum','mean','count']).reset_index()
    reg_labels = json.dumps(reg['regiao'].tolist())
    reg_data = json.dumps(reg['sum'].astype(float).tolist())

    # Sazonalidade
    df['mes'] = pd.to_datetime(df['data_pedido']).dt.month
    saz = df.groupby('mes')['valor_total'].mean().reset_index()
    meses = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
    saz_labels = json.dumps([meses[int(m)-1] for m in saz['mes']])
    saz_data = json.dumps(saz['valor_total'].astype(float).tolist())

    html = f"""<!DOCTYPE html><html><head><script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
    <style>{base_css()}</style></head><body>
    {sidebar_html('exploratoria',user)}
    <div class="main-content">
        <div class="page-header"><h1>🔬 Análise Exploratória dos Dados</h1><div class="bar"></div>
            <p>Pandas + Plotly — Histogramas, Scatter Plots, Box Plots, Correlações</p></div>
        <div class="chart-row">
            <div class="chart-container"><h3>Distribuição de Valores (Histograma)</h3><canvas id="cHist"></canvas>
                <p style="font-size:.75rem;color:var(--gray);margin-top:8px">Média: <b>{fmt(mean_val)}</b> | Mediana: <b>{fmt(float(vals.median()))}</b></p></div>
            <div class="chart-container"><h3>Box Plot: Ticket por Tipo</h3>
                <table class="data-table"><thead><tr><th>Tipo</th><th>Mín</th><th>Q1</th><th>Mediana</th><th>Q3</th><th>Máx</th></tr></thead>
                <tbody>{box_table}</tbody></table></div>
        </div>
        <div class="chart-row">
            <div class="chart-container"><h3>Vendas por Região</h3><canvas id="cReg"></canvas></div>
            <div class="chart-container"><h3>Sazonalidade Mensal</h3><canvas id="cSaz"></canvas></div>
        </div>
        <div class="chart-container"><h3>📊 Estatísticas Descritivas</h3>
            <div class="kpi-row">
                <div class="kpi"><div class="label">Média</div><div class="value">{fmt(mean_val)}</div></div>
                <div class="kpi"><div class="label">Mediana</div><div class="value">{fmt(float(vals.median()))}</div></div>
                <div class="kpi"><div class="label">Std Dev</div><div class="value">{fmt(float(vals.std()))}</div></div>
                <div class="kpi"><div class="label">Min / Max</div><div class="value">{fmt(float(vals.min()))} — {fmt(float(vals.max()))}</div></div>
            </div></div>
    </div>
    <script>
    new Chart(document.getElementById('cHist'),{{type:'bar',data:{{labels:{hist_labels},datasets:[{{data:{hist_data},
        backgroundColor:'rgba(46,90,39,.7)',borderRadius:4}}]}},options:{{plugins:{{legend:{{display:false}}}}}}}});
    new Chart(document.getElementById('cReg'),{{type:'bar',data:{{labels:{reg_labels},datasets:[{{data:{reg_data},
        backgroundColor:['#2E5A27','#8DC140','#F58220','#B8860B','#4A5568'],borderRadius:6}}]}},
        options:{{plugins:{{legend:{{display:false}}}},scales:{{y:{{ticks:{{callback:v=>v>=1e6?(v/1e6).toFixed(1)+'M':(v/1e3).toFixed(0)+'K'}}}}}}}}}});
    new Chart(document.getElementById('cSaz'),{{type:'line',data:{{labels:{saz_labels},datasets:[{{data:{saz_data},
        borderColor:'#2E5A27',backgroundColor:'rgba(141,193,64,.15)',fill:true,tension:.4,borderWidth:3,pointBackgroundColor:'#F58220',pointRadius:5}}]}},
        options:{{plugins:{{legend:{{display:false}}}}}}}});
    </script></body></html>"""
    components.html(html, height=1200, scrolling=True)


def render_dados(user):
    tabs_config = [
        ("clientes","👥 Clientes"),("produtos","📦 Produtos"),("pedidos","📋 Pedidos"),("itens_pedido","📄 Itens Pedido"),("pedido_clientes","🔗 Modelo Expandido")
    ]
    tab_btns = ""
    for i,(key,label) in enumerate(tabs_config):
        cls = "active" if i==0 else ""
        tab_btns += f'<div class="tab {cls}" onclick="showTab(\'{key}\')">{label}</div>'

    tab_contents = ""
    for key, label in tabs_config:
        df = get_tabela(key)
        if df.empty:
            tab_contents += f'<div id="tab-{key}" class="tab-content" style="display:{"block" if key=="clientes" else "none"}"><div class="alert alert-warning">Tabela {key} vazia ou não encontrada</div></div>'
            continue

        ths = "".join([f"<th>{c}</th>" for c in df.columns])
        trs = ""
        for _,r in df.head(50).iterrows():
            tds = "".join([f"<td>{v}</td>" for v in r.values])
            trs += f"<tr>{tds}</tr>"

        display = "block" if key == "clientes" else "none"
        tab_contents += f'<div id="tab-{key}" class="tab-content" style="display:{display}"><p style="margin-bottom:12px;font-size:.85rem;color:var(--gray)">📊 <b>{len(df)} registros</b> (exibindo primeiros 50)</p><div style="overflow-x:auto"><table class="data-table"><thead><tr>{ths}</tr></thead><tbody>{trs}</tbody></table></div></div>'

    html = f"""<!DOCTYPE html><html><head><style>{base_css()}
    .tab-content {{ display:none; }}
    </style></head><body>
    {sidebar_html('dados',user)}
    <div class="main-content">
        <div class="page-header"><h1>🗄️ Base de Dados</h1><div class="bar"></div>
            <p>Exploração das tabelas originais — Mock de dados e estrutura</p></div>
        <div class="tabs">{tab_btns}</div>
        {tab_contents}
        <div class="chart-container" style="margin-top:30px"><h3>📐 Estrutura do Banco (Schema)</h3>
            <pre style="background:#1D3D1A;color:#8DC140;padding:20px;border-radius:10px;font-size:.78rem;overflow-x:auto;line-height:1.6">
CREATE TABLE clientes (
    id_cliente SERIAL PRIMARY KEY,
    nome VARCHAR(150), tipo_cliente VARCHAR(50),
    regiao VARCHAR(50), estado CHAR(2),
    data_cadastro DATE, limite_credito NUMERIC(15,2)
);

CREATE TABLE produtos (
    id_produto SERIAL PRIMARY KEY,
    nome VARCHAR(150), categoria VARCHAR(50),
    subcategoria VARCHAR(50), unidade VARCHAR(20),
    preco_unitario NUMERIC(12,2)
);

CREATE TABLE pedidos (
    id_pedido SERIAL PRIMARY KEY, data_pedido DATE,
    data_entrega DATE, id_cliente INT REFERENCES clientes,
    tipo_contrato VARCHAR(20), status VARCHAR(30),
    valor_total NUMERIC(15,2)
);

CREATE TABLE itens_pedido (
    id_item SERIAL PRIMARY KEY,
    id_pedido INT REFERENCES pedidos,
    id_produto INT REFERENCES produtos,
    quantidade NUMERIC(12,2), preco_unitario NUMERIC(12,2),
    subtotal NUMERIC(15,2) GENERATED ALWAYS AS (quantidade * preco_unitario) STORED
);

-- Modelo Expandido: múltiplos clientes por pedido
CREATE TABLE pedido_clientes (
    id_pedido INT REFERENCES pedidos,
    id_cliente INT REFERENCES clientes,
    percentual_rateio NUMERIC(5,2),
    valor_rateado NUMERIC(15,2),
    PRIMARY KEY (id_pedido, id_cliente)
);</pre></div>
    </div>
    <script>
    function showTab(key) {{
        document.querySelectorAll('.tab-content').forEach(el => el.style.display='none');
        document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
        document.getElementById('tab-'+key).style.display='block';
        event.target.classList.add('active');
    }}
    </script></body></html>"""
    components.html(html, height=1400, scrolling=True)


# ═══════════════════════════════════════
# MAIN ROUTER
# ═══════════════════════════════════════
def main():
    params = st.query_params
    page = params.get("page", "login")
    user = params.get("user", "Admin")

    if page == "logout":
        st.query_params.clear()
        st.rerun()
    elif page == "login" or page is None:
        render_login()
    elif page == "visao_geral":
        render_visao_geral(user)
    elif page == "rfv":
        render_rfv(user)
    elif page == "produtos":
        render_produtos(user)
    elif page == "tendencias":
        render_tendencias(user)
    elif page == "anomalias":
        render_anomalias(user)
    elif page == "exploratoria":
        render_exploratoria(user)
    elif page == "dados":
        render_dados(user)
    else:
        render_login()

if __name__ == "__main__":
    main()