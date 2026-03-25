"""
tests/test_queries.py
======================
Testes de integração para as queries SQL críticas do projeto Agromercantil.

Requer banco PostgreSQL acessível via DATABASE_URL.
Execute com:
    pytest tests/test_queries.py -v

Se o banco não estiver disponível os testes são pulados automaticamente
(pytest.mark.skipif com verificação de conexão).
"""

import os
import pytest
import pandas as pd
from sqlalchemy import create_engine, text

# ─── Conexão ──────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://agro_user:agro123456@localhost:5432/agromercantil"
)

@pytest.fixture(scope="session")
def engine():
    """Engine compartilhada por todos os testes da sessão."""
    eng = create_engine(DATABASE_URL)
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        pytest.skip(f"Banco indisponível: {e}")
    yield eng
    eng.dispose()


def run(engine, sql: str, params: dict = None) -> pd.DataFrame:
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        return pd.DataFrame(result.fetchall(), columns=result.keys())


# ─── Q2: RFV ──────────────────────────────────────────────────────────────────
class TestRFV:
    """Questão 2 — Análise RFV com NTILE(5) e LAG."""

    QUERY = """
        WITH base AS (
            SELECT id_cliente,
                   MAX(data_pedido)                          AS ultima_compra,
                   COUNT(*)                                  AS frequencia,
                   SUM(valor_total)                          AS valor_total,
                   CURRENT_DATE - MAX(data_pedido)           AS recencia_dias
            FROM pedidos
            WHERE status != 'Cancelado'
            GROUP BY id_cliente
        ),
        scores AS (
            SELECT *,
                   NTILE(5) OVER (ORDER BY recencia_dias ASC)  AS score_r,
                   NTILE(5) OVER (ORDER BY frequencia    DESC) AS score_f,
                   NTILE(5) OVER (ORDER BY valor_total   DESC) AS score_v
            FROM base
        )
        SELECT *,
               score_r + score_f + score_v                   AS score_rfv,
               LAG(valor_total) OVER (ORDER BY valor_total DESC) AS valor_anterior
        FROM scores
        ORDER BY score_rfv DESC
    """

    def test_colunas_rfv(self, engine):
        """Resultado deve conter as colunas score_r, score_f, score_v, score_rfv."""
        df = run(engine, self.QUERY)
        assert not df.empty, "RFV retornou resultado vazio"
        for col in ("score_r", "score_f", "score_v", "score_rfv"):
            assert col in df.columns, f"Coluna '{col}' ausente no resultado RFV"

    def test_scores_entre_1_e_5(self, engine):
        """Todos os scores NTILE devem estar no intervalo [1, 5]."""
        df = run(engine, self.QUERY)
        for col in ("score_r", "score_f", "score_v"):
            assert df[col].between(1, 5).all(), f"Score '{col}' fora do intervalo [1, 5]"

    def test_score_rfv_range(self, engine):
        """score_rfv = soma de 3 NTILEs → range [3, 15]."""
        df = run(engine, self.QUERY)
        assert df["score_rfv"].between(3, 15).all(), "score_rfv fora do intervalo esperado [3, 15]"

    def test_lag_valor_anterior(self, engine):
        """Coluna lag deve ser NULL apenas na primeira linha, numérica nas demais."""
        df = run(engine, self.QUERY)
        assert pd.isna(df["valor_anterior"].iloc[0]), "Primeira linha do LAG deveria ser NULL"
        assert df["valor_anterior"].iloc[1:].notna().all(), "LAG não deveria ter NULL após a primeira linha"


# ─── Q4: Top 5 Produtos ───────────────────────────────────────────────────────
class TestTop5Produtos:
    """Questão 4 — Top 5 produtos por receita no último ano."""

    QUERY = """
        WITH vendas_ano AS (
            SELECT p.id_produto,
                   p.nome,
                   p.categoria,
                   SUM(i.quantidade * i.preco_unitario) AS total_vendas,
                   SUM(i.quantidade)                    AS volume_total,
                   COUNT(DISTINCT ped.id_pedido)        AS total_contratos
            FROM itens_pedido i
            JOIN produtos p   ON p.id_produto  = i.id_produto
            JOIN pedidos  ped ON ped.id_pedido = i.id_pedido
            WHERE ped.data_pedido >= CURRENT_DATE - INTERVAL '12 months'
              AND ped.status != 'Cancelado'
            GROUP BY p.id_produto, p.nome, p.categoria
        )
        SELECT *, ROUND(total_vendas * 100.0 / SUM(total_vendas) OVER (), 2) AS percentual
        FROM vendas_ano
        ORDER BY total_vendas DESC
        LIMIT 5
    """

    def test_retorna_no_maximo_5_linhas(self, engine):
        """Query deve retornar entre 1 e 5 linhas."""
        df = run(engine, self.QUERY)
        assert 1 <= len(df) <= 5, f"Esperado até 5 produtos, obtido {len(df)}"

    def test_percentual_entre_0_e_100(self, engine):
        """Percentual de participação deve estar entre 0 e 100."""
        df = run(engine, self.QUERY)
        assert df["percentual"].between(0, 100).all(), "Percentual fora do intervalo [0, 100]"

    def test_total_vendas_positivo(self, engine):
        """total_vendas deve ser sempre positivo."""
        df = run(engine, self.QUERY)
        assert (df["total_vendas"] > 0).all(), "total_vendas contém valores não positivos"

    def test_ordenado_decrescente(self, engine):
        """Resultado deve estar ordenado por total_vendas decrescente."""
        df = run(engine, self.QUERY)
        valores = df["total_vendas"].tolist()
        assert valores == sorted(valores, reverse=True), "Top 5 não está em ordem decrescente"


# ─── Q5: Tendências com LAG ───────────────────────────────────────────────────
class TestTendencias:
    """Questão 5 — Tendências mensais com crescimento_percentual via LAG."""

    QUERY = """
        WITH mensal AS (
            SELECT DATE_TRUNC('month', data_pedido) AS mes,
                   SUM(valor_total)                 AS receita_mes,
                   COUNT(*)                         AS total_pedidos
            FROM pedidos
            WHERE status != 'Cancelado'
            GROUP BY 1
        )
        SELECT mes,
               receita_mes,
               total_pedidos,
               LAG(receita_mes) OVER (ORDER BY mes) AS receita_anterior,
               ROUND(
                   (receita_mes - LAG(receita_mes) OVER (ORDER BY mes)) * 100.0
                   / NULLIF(LAG(receita_mes) OVER (ORDER BY mes), 0),
               2) AS crescimento_percentual
        FROM mensal
        ORDER BY mes
    """

    def test_colunas_crescimento(self, engine):
        """Deve conter crescimento_percentual e receita_anterior."""
        df = run(engine, self.QUERY)
        assert "crescimento_percentual" in df.columns
        assert "receita_anterior" in df.columns

    def test_primeiro_mes_lag_nulo(self, engine):
        """Primeiro mês: crescimento_percentual e receita_anterior devem ser NULL."""
        df = run(engine, self.QUERY)
        assert pd.isna(df["crescimento_percentual"].iloc[0]), "Primeiro mês deveria ter crescimento NULL"
        assert pd.isna(df["receita_anterior"].iloc[0]), "Primeiro mês deveria ter receita_anterior NULL"

    def test_receita_mes_positiva(self, engine):
        """Receita de cada mês deve ser positiva."""
        df = run(engine, self.QUERY)
        assert (df["receita_mes"] > 0).all(), "Receita mensal contém valores não positivos"


# ─── Q6: Clientes Inativos ────────────────────────────────────────────────────
class TestClientesInativos:
    """Questão 6 — Clientes sem pedidos nos últimos 6 meses."""

    QUERY = """
        SELECT c.id_cliente,
               c.nome,
               c.tipo_cliente,
               c.regiao,
               MAX(p.data_pedido)               AS ultimo_pedido,
               CURRENT_DATE - MAX(p.data_pedido) AS dias_inativo
        FROM clientes c
        LEFT JOIN pedidos p ON p.id_cliente = c.id_cliente AND p.status != 'Cancelado'
        GROUP BY c.id_cliente, c.nome, c.tipo_cliente, c.regiao
        HAVING MAX(p.data_pedido) < CURRENT_DATE - INTERVAL '6 months'
            OR MAX(p.data_pedido) IS NULL
        ORDER BY dias_inativo DESC NULLS LAST
    """

    def test_todos_inativos(self, engine):
        """Todos os clientes retornados devem ter último pedido > 6 meses ou nunca comprado."""
        df = run(engine, self.QUERY)
        if df.empty:
            pytest.skip("Nenhum cliente inativo no período — verifique a data dos dados")
        validos = df["ultimo_pedido"].isna() | (
            pd.to_datetime(df["ultimo_pedido"]) < pd.Timestamp.now() - pd.DateOffset(months=6)
        )
        assert validos.all(), "Clientes ativos estão aparecendo no resultado de inativos"


# ─── Q7: Anomalias ────────────────────────────────────────────────────────────
class TestAnomalias:
    """Questão 7 — Detecção de pedidos com valor inconsistente vs soma de itens."""

    QUERY = """
        WITH base AS (
            SELECT p.id_pedido,
                   p.valor_total                   AS valor_cabecalho,
                   SUM(i.quantidade * i.preco_unitario) AS valor_calculado,
                   ABS(p.valor_total - SUM(i.quantidade * i.preco_unitario)) AS diferenca
            FROM pedidos p
            JOIN itens_pedido i ON i.id_pedido = p.id_pedido
            GROUP BY p.id_pedido, p.valor_total
        )
        SELECT *,
               ROUND(diferenca * 100.0 / NULLIF(valor_calculado, 0), 2) AS diferenca_pct,
               CASE
                   WHEN valor_cabecalho > valor_calculado THEN 'Superfaturado'
                   ELSE 'Subfaturado'
               END AS tipo_anomalia
        FROM base
        WHERE diferenca > valor_calculado * 0.05
        ORDER BY diferenca DESC
    """

    def test_colunas_anomalia(self, engine):
        """Deve conter tipo_anomalia e diferenca_pct."""
        df = run(engine, self.QUERY)
        assert "tipo_anomalia" in df.columns
        assert "diferenca_pct" in df.columns

    def test_tipos_validos(self, engine):
        """tipo_anomalia deve ser apenas 'Superfaturado' ou 'Subfaturado'."""
        df = run(engine, self.QUERY)
        if df.empty:
            return  # sem anomalias é válido
        assert df["tipo_anomalia"].isin(["Superfaturado", "Subfaturado"]).all()

    def test_diferenca_positiva(self, engine):
        """diferenca deve ser sempre positiva."""
        df = run(engine, self.QUERY)
        if df.empty:
            return
        assert (df["diferenca"] > 0).all(), "diferenca contém valores não positivos"


# ─── Q3: pedido_clientes ─────────────────────────────────────────────────────
class TestPedidoClientes:
    """Questão 3 — Tabela de compras compartilhadas."""

    def test_tabela_existe(self, engine):
        """Tabela pedido_clientes deve existir."""
        df = run(engine, """
            SELECT COUNT(*) AS n FROM information_schema.tables
            WHERE table_name = 'pedido_clientes'
        """)
        assert int(df["n"].iloc[0]) == 1, "Tabela pedido_clientes não encontrada"

    def test_rateio_soma_100_por_pedido(self, engine):
        """Para pedidos compartilhados, a soma dos percentuais deve ser 100."""
        df = run(engine, """
            SELECT id_pedido, ROUND(SUM(percentual_rateio), 2) AS soma_pct
            FROM pedido_clientes
            GROUP BY id_pedido
            HAVING COUNT(*) > 1
        """)
        if df.empty:
            pytest.skip("Sem pedidos compartilhados registrados")
        tolerancia = 0.01
        assert (abs(df["soma_pct"] - 100) <= tolerancia).all(), \
            "Percentuais de rateio não somam 100% em pedidos compartilhados"
