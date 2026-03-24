#!/usr/bin/env python3
import paramiko

VPS_IP = '173.212.205.8'
VPS_USER = 'mateus'
VPS_PASS = '231181mateu$'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname=VPS_IP, username=VPS_USER, password=VPS_PASS, timeout=30)

print('=== DIAGNOSTICO DE CONEXÃO ===')

# 1. Verificar Streamlit
print('\n1. Verificando Streamlit...')
stdin, stdout, stderr = ssh.exec_command('pgrep -f streamlit && echo "RODANDO" || echo "PARADO"')
result = stdout.read().decode().strip()
print(result)

# 2. Verificar porta
print('\n2. Verificando porta 8501...')
stdin, stdout, stderr = ssh.exec_command('ss -tlnp | grep 8501 || netstat -tlnp | grep 8501')
result = stdout.read().decode().strip()
print(result or 'Nenhum processo na porta 8501')

# 3. Firewall
print('\n3. Verificando firewall...')
stdin, stdout, stderr = ssh.exec_command('sudo -S ufw status 2>&1')
stdin.write(f'{VPS_PASS}\n')
stdin.flush()
result = stdout.read().decode().strip()
print(result[-500:])

# 4. IPs
print('\n4. IPs da VPS...')
stdin, stdout, stderr = ssh.exec_command("ip addr show | grep 'inet ' | head -3")
result = stdout.read().decode().strip()
print(result)

# 5. Testar local
print('\n5. Testando conexão local...')
stdin, stdout, stderr = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:8501')
result = stdout.read().decode().strip()
print('HTTP Status:', result)

ssh.close()
print('\n=== FIM DO DIAGNÓSTICO ===')
