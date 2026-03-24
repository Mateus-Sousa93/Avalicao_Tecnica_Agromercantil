#!/usr/bin/env python3
import paramiko

VPS_IP = '173.212.205.8'
VPS_USER = 'mateus'
VPS_PASS = '231181mateu$'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname=VPS_IP, username=VPS_USER, password=VPS_PASS, timeout=30)

# Testar acesso
print('Testando acesso HTTP:')
stdin, stdout, stderr = ssh.exec_command('curl -s http://localhost:8501 -o /dev/null -w "%{http_code}"')
print('HTTP Status:', stdout.read().decode())

# Verificar sintaxe
print('\nVerificando sintaxe:')
stdin, stdout, stderr = ssh.exec_command('cd ~/agromercantil && python3 -m py_compile app/dashboard.py 2>&1')
err = stderr.read().decode()
if err:
    print('ERRO:', err)
else:
    print('Sintaxe OK')

# Ver logs detalhados
print('\nUltimos logs:')
stdin, stdout, stderr = ssh.exec_command('tail -20 ~/agromercantil/streamlit.log')
print(stdout.read().decode())

ssh.close()
