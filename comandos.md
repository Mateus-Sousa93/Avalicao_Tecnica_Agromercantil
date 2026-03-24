# Comandos para Gerenciar a VPS - Agromercantil

## 📡 Info de Conexão

- **IP:** 173.212.205.8
- **Usuário:** mateus
- **Senha:** 231181mateu$
- **Hostname:** vmi3088905

---

## 🔧 Como Conectar (Windows)

### Opção 1: PuTTY (plink) - Recomendado

Baixe o PuTTY em: https://www.putty.org/

```powershell
# Verificar conexão (executar comando)
plink -ssh -pw "231181mateu$" mateus@173.212.205.8 -P 22 "hostname && uptime"

# Se der erro de host key, aceite a chave:
plink -ssh -pw "231181mateu$" mateus@173.212.205.8 -P 22 -hostkey "SHA256:IM26KcTq2mpr4cEwnXPybllxbbBDi+HsqNmHOSudJhI" "comando_aqui"
```

### Opção 2: OpenSSH (Windows 10/11 nativo)

```powershell
# Conectar interativamente
ssh mateus@173.212.205.8

# Executar comando direto
ssh mateus@173.212.205.8 "hostname && uptime"
```

---

## 📤 Enviar Arquivos para VPS

### Usando pscp (PuTTY SCP)

```powershell
# Enviar dashboard.py
pscp -pw "231181mateu$" "c:\Users\Mateus Cesar\Desktop\avaliação agromercantil\dashboard.py" mateus@173.212.205.8:/home/mateus/agromercantil/app/dashboard.py

# Se der erro de host key, use -hostkey:
pscp -pw "231181mateu$" -hostkey "SHA256:IM26KcTq2mpr4cEwnXPybllxbbBDi+HsqNmHOSudJhI" "c:\Users\Mateus Cesar\Desktop\avaliação agromercantil\dashboard.py" mateus@173.212.205.8:/home/mateus/agromercantil/app/dashboard.py
```

### Usando scp (OpenSSH)

```powershell
scp "c:\Users\Mateus Cesar\Desktop\avaliação agromercantil\dashboard.py" mateus@173.212.205.8:/home/mateus/agromercantil/app/dashboard.py
```

---

## 🚀 Reiniciar Dashboard

### Via plink (PuTTY)

```powershell
plink -ssh -pw "231181mateu$" mateus@173.212.205.8 -P 22 "pkill -f streamlit; cd /home/mateus/agromercantil/app && nohup streamlit run dashboard.py --server.port 8501 --server.address 0.0.0.0 > /dev/null 2>&1 &"
```

### Via ssh (OpenSSH)

```powershell
ssh mateus@173.212.205.8 "pkill -f streamlit; cd /home/mateus/agromercantil/app && nohup streamlit run dashboard.py --server.port 8501 --server.address 0.0.0.0 > /dev/null 2>&1 &"
```

---

## ⚡ Comandos Rápidos (Copiar e Colar)

### 1. Enviar dashboard.py
```powershell
pscp -pw "231181mateu$" "c:\Users\Mateus Cesar\Desktop\avaliação agromercantil\dashboard.py" mateus@173.212.205.8:/home/mateus/agromercantil/app/dashboard.py
```

### 2. Reiniciar Streamlit
```powershell
plink -ssh -pw "231181mateu$" mateus@173.212.205.8 -P 22 "pkill -f streamlit; cd /home/mateus/agromercantil/app && nohup streamlit run dashboard.py --server.port 8501 --server.address 0.0.0.0 > /dev/null 2>&1 &"
```

### 3. Verificar se está rodando
```powershell
plink -ssh -pw "231181mateu$" mateus@173.212.205.8 -P 22 "curl -s http://localhost:8501 | head -5"
```

---

## 🌐 Acessar Dashboard

Abra no navegador:
```
http://173.212.205.8:8501
```

---

## 🛠️ Comandos Úteis na VPS

```bash
# Ver logs do streamlit
tail -f /home/mateus/agromercantil/app/nohup.out

# Ver processos rodando
ps aux | grep streamlit

# Matar processos streamlit
pkill -f streamlit

# Ver espaço em disco
df -h

# Ver uso de memória
free -h

# Verificar porta 8501
netstat -tlnp | grep 8501
```
