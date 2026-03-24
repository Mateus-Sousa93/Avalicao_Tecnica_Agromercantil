#!/usr/bin/env python3
import paramiko

VPS_IP = '173.212.205.8'
VPS_USER = 'mateus'
VPS_PASS = '231181mateu$'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname=VPS_IP, username=VPS_USER, password=VPS_PASS, timeout=30)

def sudo(cmd, timeout=60):
    stdin, stdout, stderr = ssh.exec_command(f'sudo -S {cmd}', timeout=timeout)
    stdin.write(f'{VPS_PASS}\n')
    stdin.flush()
    exit_code = stdout.channel.recv_exit_status()
    return stdout.read().decode(), stderr.read().decode()

# Criar banco
print('Criando banco...')
out, err = sudo('-u postgres psql -c "CREATE DATABASE agromercantil OWNER agro_user;"')
print('Resultado:', out[-300:])

# Executar schema
print('Executando schema...')
out, err = sudo('-u postgres psql -d agromercantil -f /tmp/schema.sql')
print('Schema executado!')

ssh.close()
