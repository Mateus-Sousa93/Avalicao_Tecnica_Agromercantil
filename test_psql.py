#!/usr/bin/env python3
import paramiko

VPS_IP = '173.212.205.8'
VPS_USER = 'mateus'
VPS_PASS = '231181mateu$'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname=VPS_IP, username=VPS_USER, password=VPS_PASS, timeout=30)

print('Testando psql com agro_user:')
cmd = "PGPASSWORD=agro123456 psql -h localhost -U agro_user -d agromercantil -t -c 'SELECT COUNT(*) FROM clientes;'"
stdin, stdout, stderr = ssh.exec_command(cmd)
print('Saida:', stdout.read().decode())
print('Erro:', stderr.read().decode())

print('\nTestando psql com sudo:')
cmd = "sudo -u postgres psql -d agromercantil -t -c 'SELECT COUNT(*) FROM clientes;'"
stdin, stdout, stderr = ssh.exec_command(cmd)
print('Saida:', stdout.read().decode())
print('Erro:', stderr.read().decode())

ssh.close()
