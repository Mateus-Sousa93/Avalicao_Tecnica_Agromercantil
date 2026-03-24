#!/usr/bin/env python3
import paramiko

VPS_IP = '173.212.205.8'
VPS_USER = 'mateus'
VPS_PASS = '231181mateu$'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname=VPS_IP, username=VPS_USER, password=VPS_PASS, timeout=30)

print('Verificando dados no PostgreSQL:')

commands = [
    ("Clientes", "SELECT COUNT(*) FROM clientes;"),
    ("Pedidos", "SELECT COUNT(*) FROM pedidos;"),
    ("Produtos", "SELECT COUNT(*) FROM produtos;"),
    ("Itens", "SELECT COUNT(*) FROM itens_pedido;")
]

needs_ingestion = False
for name, query in commands:
    cmd = f'sudo -u postgres psql -d agromercantil -t -c "{query}"'
    stdin, stdout, stderr = ssh.exec_command(cmd)
    result = stdout.read().decode().strip()
    print(f'{name}: {result}')
    if name == 'Clientes' and (result == '0' or result == ''):
        needs_ingestion = True

if needs_ingestion:
    print('\nIngerindo dados...')
    cmd = 'cd ~/agromercantil && python3 src/ingestao_dados.py'
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=180)
    exit_code = stdout.channel.recv_exit_status()
    print(stdout.read().decode())
else:
    print('\nDados já existem!')

ssh.close()
print('\nAcesse: http://173.212.205.8:8501')
