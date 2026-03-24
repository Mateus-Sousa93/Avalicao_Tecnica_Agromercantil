  Me forneça:

  VPS_IP: 173.212.205.8    USUARIO: mateus   SENHA: 231181mateu$


não tenho dominio , vamos usar ngix ou algo do tipo, quero ter um nome pro dashboard de acesso tbm se nao for possivel na vps subimos o front na vercel

---

## Como Conectar na VPS (Windows)

### Via PuTTY (plink)

O `plink` vem instalado com o PuTTY. Para conectar via terminal:

```powershell
# Comando básico
plink -ssh -pw "SENHA" USUARIO@VPS_IP -P 22 "comando_a_executar"

# Exemplo - Ver hostname e uptime
plink -ssh -pw "231181mateu$" mateus@173.212.205.8 -P 22 "hostname && uptime"

# Se der erro de host key, aceite a nova chave:
plink -ssh -pw "231181mateu$" mateus@173.212.205.8 -P 22 -hostkey "SHA256:IM26KcTq2mpr4cEwnXPybllxbbBDi+HsqNmHOSudJhI" "hostname"
```

### Via OpenSSH (Windows 10/11)

```powershell
# Conectar interativamente
ssh mateus@173.212.205.8

# Executar comando direto
ssh mateus@173.212.205.8 "hostname && uptime"
```

### Info da VPS

- **IP:** 173.212.205.8
- **Usuário:** mateus
- **Hostname atual:** vmi3088905
- **Chave SSH fingerprint:** `SHA256:IM26KcTq2mpr4cEwnXPybllxbbBDi+HsqNmHOSudJhI` 




# 1. Achar o dashboard atual
find /home -name "dashboard.py" 2>/dev/null

# 2. Matar streamlit rodando
pkill -f streamlit

# 3. Instalar dependências novas
pip install plotly sqlalchemy psycopg2-binary google-generativeai python-dotenv tqdm openpyxl numpy pandas streamlit

# 4. Substituir o dashboard.py pelo novo (do PC local, rodar no PowerShell do Windows):
# scp "c:\Users\Mateus Cesar\Desktop\avaliação agromercantil\dashboard.py" mateus@173.212.205.8:/CAMINHO_DO_FIND/dashboard.py

# 5. Subir streamlit de novo (na VPS, substituir CAMINHO pelo resultado do find)
cd /CAMINHO_DO_FIND/../
nohup streamlit run dashboard.py --server.port 8501 --server.address 0.0.0.0 > /dev/null 2>&1 &

# 6. Verificar se subiu
curl -s http://localhost:8501 | head -5
