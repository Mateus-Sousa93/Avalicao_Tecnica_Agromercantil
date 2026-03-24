bash
Copy
# Ver espaço em disco
df -h

# Ver uso de memória
free -h

# Ver processos PostgreSQL
ps aux | grep postgres

# Ver conexões ativas no banco
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;"

# Backup do banco
pg_dump -h localhost -U agro_user agromercantil > backup_$(date +%Y%m%d).sql

# Restaurar backup
psql -h localhost -U agro_user agromercantil < backup_20250323.sql
🆘 Troubleshooting
Erro: "Connection refused"
PostgreSQL não está rodando: sudo systemctl status postgresql
Verifique se está ouvindo na porta certa: sudo netstat -tlnp | grep 5432
Erro: "password authentication failed"
Senha incorreta no .env
Verifique: sudo -u postgres psql -c "\du" (lista usuários)
Erro: "database agromercantil does not exist"
Crie o banco: sudo -u postgres createdb agromercantil
Streamlit não acessível de fora
Verifique firewall: sudo ufw allow 8501
Verifique se rodou com --server.address 0.0.0.0
✅ Checklist Final
[ ] PostgreSQL instalado e rodando
[ ] Banco agromercantil criado
[ ] Usuário agro_user com senha segura
[ ] Schema SQL executado (tabelas criadas)
[ ] Dados ingeridos (Excel → PostgreSQL)
[ ] Streamlit acessível em http://vps-ip:8501
[ ] Firewall configurado (apenas portas necessárias)
[ ] Backup automático configurado (opcional)