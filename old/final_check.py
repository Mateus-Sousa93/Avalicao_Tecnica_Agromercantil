#!/usr/bin/env python3
import paramiko

VPS_IP = '173.212.205.8'
VPS_USER = 'mateus'
VPS_PASS = '231181mateu$'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname=VPS_IP, username=VPS_USER, password=VPS_PASS, timeout=30)

print('=== VERIFICAÇÃO FINAL ===')

# Testar conexão HTTP
print('\n1. Testando acesso HTTP...')
stdin, stdout, stderr = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://173.212.205.8:8501')
print('Status HTTP:', stdout.read().decode())

# Verificar firewall
print('\n2. Firewall:')
stdin, stdout, stderr = ssh.exec_command('sudo -S ufw status | grep 8501')
stdin.write(f'{VPS_PASS}\n')
stdin.flush()
print(stdout.read().decode())

# Verificar processos
print('3. Processos Streamlit:')
stdin, stdout, stderr = ssh.exec_command('ps aux | grep streamlit | grep -v grep')
print(stdout.read().decode())

ssh.close()
print('\n=== VERIFICAÇÃO CONCLUÍDA ===')
