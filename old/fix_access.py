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

print('=== LIBERANDO PORTAS NO FIREWALL ===')

# Liberar portas
print('Liberando porta 8501 (Streamlit)...')
out, err = sudo('ufw allow 8501/tcp')
print(out[-200:])

print('Liberando porta 80 (nginx)...')
out, err = sudo('ufw allow 80/tcp')
print(out[-200:])

print('Liberando porta 443 (HTTPS)...')
out, err = sudo('ufw allow 443/tcp')
print(out[-200:])

# Verificar status
print('\nStatus do firewall:')
out, err = sudo('ufw status')
print(out)

ssh.close()
print('\n=== PORTAS LIBERADAS ===')
print('Acesse: http://173.212.205.8:8501')
