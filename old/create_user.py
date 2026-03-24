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

# Criar usuário
print('Criando usuario agro_user...')
out, err = sudo('-u postgres psql -c "CREATE USER agro_user WITH PASSWORD \'agro123456\' SUPERUSER;"')
print('Resultado:', out[-300:])
print('Erros:', err[-300:])

# Alterar dono do banco
print('Alterando dono do banco...')
out, err = sudo('-u postgres psql -c "ALTER DATABASE agromercantil OWNER TO agro_user;"')
print('Resultado:', out[-300:])

ssh.close()
