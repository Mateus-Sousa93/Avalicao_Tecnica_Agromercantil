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

# Upload schema
print('Enviando schema...')
schema = open('schema.sql', encoding='utf-8').read()
sftp = ssh.open_sftp()
with sftp.file('/tmp/schema.sql', 'w') as f:
    f.write(schema)
sftp.close()
print('Schema enviado!')

# Executar como postgres user
print('Executando schema...')
out, err = sudo('-u postgres psql -d agromercantil -f /tmp/schema.sql', 60)
print('Resultado:', out[-500:])
print('Erros:', err[-300:])

# Verificar tabelas
print('\nVerificando tabelas:')
cmd = "PGPASSWORD=agro123456 psql -h localhost -U agro_user -d agromercantil -t -c \"SELECT table_name FROM information_schema.tables WHERE table_schema='public';\""
stdin, stdout, stderr = ssh.exec_command(cmd)
print('Tabelas:', stdout.read().decode())

ssh.close()
