#!/usr/bin/env python3
"""Deploy automatizado Agromercantil na VPS"""
import paramiko
import os
import time

VPS_IP = '173.212.205.8'
VPS_USER = 'mateus'
VPS_PASS = '231181mateu$'

def main():
    print("=" * 60)
    print("DEPLOY AGROMERCANTIL - VPS")
    print("=" * 60)
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=VPS_IP, username=VPS_USER, password=VPS_PASS, timeout=30)
    print("Conectado!")
    
    def run(cmd, timeout=300):
        print(f"CMD: {cmd[:70]}...")
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode('utf-8', errors='ignore')[-300:]
        if out.strip():
            print(f"  -> {out.strip()[-200:]}")
        return exit_code
    
    # PASSO 1: Atualizar sistema
    print("\n[1/8] Atualizando sistema...")
    run("sudo apt update -y", 180)
    
    # PASSO 2: Instalar pacotes
    print("\n[2/8] Instalando PostgreSQL e Python...")
    run("sudo apt install -y postgresql postgresql-contrib python3 python3-pip python3-venv python3-pandas libpq-dev build-essential nginx", 300)
    
    # PASSO 3: Configurar PostgreSQL
    print("\n[3/8] Configurando PostgreSQL...")
    run("sudo -u postgres psql -c \"CREATE USER agro_user WITH PASSWORD 'agro123456' SUPERUSER;\" 2>/dev/null || echo 'User exists'")
    run("sudo -u postgres psql -c \"CREATE DATABASE agromercantil OWNER agro_user;\" 2>/dev/null || echo 'DB exists'")
    run("sudo -u postgres psql -c \"ALTER USER agro_user WITH LOGIN;\"")
    run("sudo sed -i \"s/#listen_addresses = 'localhost'/listen_addresses = '*'/g\" /etc/postgresql/*/main/postgresql.conf")
    run("echo \"host all all 0.0.0.0/0 md5\" | sudo tee -a /etc/postgresql/*/main/pg_hba.conf")
    run("sudo systemctl restart postgresql")
    
    # PASSO 4: Criar estrutura
    print("\n[4/8] Criando estrutura do projeto...")
    run("mkdir -p ~/agromercantil/{data,sql,src,app,docs}")
    
    # PASSO 5: Criar schema SQL
    print("\n[5/8] Criando schema SQL...")
    schema = """CREATE TABLE IF NOT EXISTS clientes (
    id_cliente SERIAL PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    tipo_cliente VARCHAR(50) NOT NULL CHECK (tipo_cliente IN ('Produtor Rural', 'Cooperativa', 'Trading Company', 'Processadora', 'Atacadista')),
    regiao VARCHAR(50) NOT NULL,
    estado CHAR(2) NOT NULL,
    data_cadastro DATE NOT NULL,
    limite_credito NUMERIC(15,2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_cliente_tipo ON clientes(tipo_cliente);
CREATE INDEX IF NOT EXISTS idx_cliente_regiao ON clientes(regiao);
CREATE INDEX IF NOT EXISTS idx_cliente_cadastro ON clientes(data_cadastro);

CREATE TABLE IF NOT EXISTS produtos (
    id_produto SERIAL PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    categoria VARCHAR(50) NOT NULL CHECK (categoria IN ('Commodity', 'Serviço')),
    subcategoria VARCHAR(50) NOT NULL,
    unidade VARCHAR(20) NOT NULL,
    preco_unitario NUMERIC(12,2) NOT NULL CHECK (preco_unitario > 0),
    custo_referencia NUMERIC(12,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_produto_categoria ON produtos(categoria);

CREATE TABLE IF NOT EXISTS pedidos (
    id_pedido SERIAL PRIMARY KEY,
    data_pedido DATE NOT NULL,
    data_entrega DATE NOT NULL,
    id_cliente INTEGER NOT NULL REFERENCES clientes(id_cliente) ON DELETE RESTRICT,
    tipo_contrato VARCHAR(20) NOT NULL CHECK (tipo_contrato IN ('Spot', 'A Termo', 'Futuro')),
    status VARCHAR(30) NOT NULL CHECK (status IN ('Executado', 'Pendente', 'Cancelado', 'Em Andamento')),
    regiao_origem VARCHAR(50) NOT NULL,
    regiao_destino VARCHAR(50) NOT NULL,
    valor_total NUMERIC(15,2) NOT NULL CHECK (valor_total >= 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_pedido_data ON pedidos(data_pedido);
CREATE INDEX IF NOT EXISTS idx_pedido_cliente_data ON pedidos(id_cliente, data_pedido DESC);
CREATE INDEX IF NOT EXISTS idx_pedido_status ON pedidos(status) WHERE status != 'Cancelado';

CREATE TABLE IF NOT EXISTS itens_pedido (
    id_item SERIAL PRIMARY KEY,
    id_pedido INTEGER NOT NULL REFERENCES pedidos(id_pedido) ON DELETE CASCADE,
    id_produto INTEGER NOT NULL REFERENCES produtos(id_produto) ON DELETE RESTRICT,
    quantidade NUMERIC(12,2) NOT NULL CHECK (quantidade > 0),
    preco_unitario NUMERIC(12,2) NOT NULL CHECK (preco_unitario >= 0),
    unidade VARCHAR(20) NOT NULL,
    subtotal NUMERIC(15,2) GENERATED ALWAYS AS (quantidade * preco_unitario) STORED,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_item_pedido ON itens_pedido(id_pedido);
CREATE INDEX IF NOT EXISTS idx_item_produto ON itens_pedido(id_produto);

CREATE TABLE IF NOT EXISTS pedido_clientes (
    id_pedido INTEGER NOT NULL REFERENCES pedidos(id_pedido) ON DELETE CASCADE,
    id_cliente INTEGER NOT NULL REFERENCES clientes(id_cliente) ON DELETE RESTRICT,
    percentual_rateio NUMERIC(5,2) NOT NULL CHECK (percentual_rateio > 0 AND percentual_rateio <= 100),
    valor_rateado NUMERIC(15,2) NOT NULL,
    PRIMARY KEY (id_pedido, id_cliente)
);
CREATE INDEX IF NOT EXISTS idx_pedclient_cliente ON pedido_clientes(id_cliente);"""
    
    # Salvar schema em arquivo temporário e executar
    run(f"cat > /tmp/schema.sql << 'EOFSchema'\n{schema}\nEOFSchema")
    run("sudo -u postgres psql -d agromercantil -f /tmp/schema.sql")
    
    # PASSO 6: Criar ambiente Python
    print("\n[6/8] Criando ambiente Python...")
    run("cd ~/agromercantil && python3 -m venv venv")
    run("cd ~/agromercantil && source venv/bin/activate && pip install --upgrade pip && pip install pandas sqlalchemy psycopg2-binary openpyxl streamlit plotly python-dotenv tqdm", 300)
    
    # PASSO 7: Criar script de ingestão
    print("\n[7/8] Criando script de ingestão...")
    ingestao = '''import pandas as pd
from sqlalchemy import create_engine, text
from tqdm import tqdm
import os

DATABASE_URL = "postgresql://agro_user:agro123456@localhost:5432/agromercantil"
engine = create_engine(DATABASE_URL)

def ler_excel():
    caminho = '/home/mateus/agromercantil/data/dados_agromercantil_commodities.xlsx'
    if not os.path.exists(caminho):
        print(f"Arquivo nao encontrado: {caminho}")
        return None, None, None, None
    print(f"Lendo {caminho}...")
    df_clientes = pd.read_excel(caminho, sheet_name='clientes')
    df_produtos = pd.read_excel(caminho, sheet_name='produtos')
    df_pedidos = pd.read_excel(caminho, sheet_name='pedidos')
    df_itens = pd.read_excel(caminho, sheet_name='itens_pedido')
    print(f"Clientes: {len(df_clientes)}, Produtos: {len(df_produtos)}, Pedidos: {len(df_pedidos)}, Itens: {len(df_itens)}")
    return df_clientes, df_produtos, df_pedidos, df_itens

def limpar_tabelas():
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE itens_pedido, pedidos, produtos, clientes RESTART IDENTITY CASCADE;"))
        conn.commit()
    print("Tabelas limpas")

def inserir_batch(tabela, df, batch_size=500):
    print(f"Inserindo {tabela} ({len(df)} registros)...")
    for i in tqdm(range(0, len(df), batch_size)):
        batch = df.iloc[i:i+batch_size]
        batch.to_sql(tabela, engine, if_exists='append', index=False, method='multi')

def main():
    df_clientes, df_produtos, df_pedidos, df_itens = ler_excel()
    if df_clientes is None: return
    limpar_tabelas()
    inserir_batch('clientes', df_clientes, 500)
    inserir_batch('produtos', df_produtos, 500)
    inserir_batch('pedidos', df_pedidos, 1000)
    inserir_batch('itens_pedido', df_itens, 1000)
    print("Ingestao concluida!")

if __name__ == "__main__":
    main()'''
    
    run(f"cat > ~/agromercantil/src/ingestao_dados.py << 'EOFIngestao'\n{ingestao}\nEOFIngestao")
    
    # PASSO 8: Configurar nginx
    print("\n[8/8] Configurando nginx...")
    nginx_conf = '''server {
    listen 80;
    server_name _;
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}'''
    run(f"echo '{nginx_conf}' | sudo tee /etc/nginx/sites-available/agromercantil")
    run("sudo ln -sf /etc/nginx/sites-available/agromercantil /etc/nginx/sites-enabled/")
    run("sudo rm -f /etc/nginx/sites-enabled/default")
    run("sudo nginx -t && sudo systemctl restart nginx")
    run("sudo ufw allow 22/tcp && sudo ufw allow 80/tcp && sudo ufw allow 8501/tcp && sudo ufw --force enable")
    
    ssh.close()
    print("\n" + "=" * 60)
    print("SETUP CONCLUIDO!")
    print("=" * 60)
    print("\nProximos passos:")
    print("1. Enviar Excel: scp dados_agromercantil_commodities.xlsx mateus@173.212.205.8:~/agromercantil/data/")
    print("2. Ingerir dados: ssh mateus@173.212.205.8 'cd ~/agromercantil && source venv/bin/activate && python3 src/ingestao_dados.py'")
    print("3. Iniciar dashboard: ssh mateus@173.212.205.8 'cd ~/agromercantil && source venv/bin/activate && streamlit run app/dashboard.py --server.port 8501 --server.address 0.0.0.0'")

if __name__ == "__main__":
    main()
