#!/usr/bin/env python3
import paramiko

VPS_IP = '173.212.205.8'
VPS_USER = 'mateus'
VPS_PASS = '231181mateu$'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname=VPS_IP, username=VPS_USER, password=VPS_PASS, timeout=30)

def sudo(cmd, timeout=60):
    stdin, stdout, stderr = ssh.exec_command(f'sudo -S {cmd} 2>&1', timeout=timeout)
    stdin.write(f'{VPS_PASS}\n')
    stdin.flush()
    exit_code = stdout.channel.recv_exit_status()
    return stdout.read().decode(), stderr.read().decode()

print('Configurando PostgreSQL...')

# Criar usuário
print('Criando usuario agro_user...')
out, err = sudo("psql -c \"CREATE USER agro_user WITH PASSWORD 'agro123456' SUPERUSER;\" 2>/dev/null || echo 'User exists'")
print(out[-200:])

# Criar banco
print('Criando banco agromercantil...')
out, err = sudo("psql -c \"CREATE DATABASE agromercantil OWNER agro_user;\" 2>/dev/null || echo 'DB exists'")
print(out[-200:])

# Configurar acesso
print('Configurando acesso...')
out, err = sudo("sed -i \"s/#listen_addresses = 'localhost'/listen_addresses = '*'/g\" /etc/postgresql/14/main/postgresql.conf")
out, err = sudo("bash -c 'echo host all all 0.0.0.0/0 md5 >> /etc/postgresql/14/main/pg_hba.conf'")
out, err = sudo("systemctl restart postgresql")

print('Configuracao concluida!')

ssh.close()
