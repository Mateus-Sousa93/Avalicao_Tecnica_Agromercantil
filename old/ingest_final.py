#!/usr/bin/env python3
import paramiko

VPS_IP = '173.212.205.8'
VPS_USER = 'mateus'
VPS_PASS = '231181mateu$'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname=VPS_IP, username=VPS_USER, password=VPS_PASS, timeout=30)

# Instalar tqdm
print('Instalando tqdm...')
stdin, stdout, stderr = ssh.exec_command('python3 -m pip install tqdm', timeout=60)
exit_code = stdout.channel.recv_exit_status()
print('Instalado!')

# Executar ingestão
print('\nIngerindo dados...')
cmd = 'cd ~/agromercantil && python3 src/ingestao_dados.py'
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=180)
exit_code = stdout.channel.recv_exit_status()
output = stdout.read().decode()
print('Saida:')
print(output[-1000:])

# Verificar
print('\nVerificando dados:')
cmd = "PGPASSWORD=agro123456 psql -h localhost -U agro_user -d agromercantil -t -c 'SELECT COUNT(*) FROM clientes;'"
stdin, stdout, stderr = ssh.exec_command(cmd)
print('Clientes:', stdout.read().decode().strip())

cmd = "PGPASSWORD=agro123456 psql -h localhost -U agro_user -d agromercantil -t -c 'SELECT COUNT(*) FROM pedidos;'"
stdin, stdout, stderr = ssh.exec_command(cmd)
print('Pedidos:', stdout.read().decode().strip())

ssh.close()
