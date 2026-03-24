# Instrucoes para Atualizar o GitHub

## Preparar o repositorio

```bash
# Navegar ate a pasta do projeto
cd Avalicao_Tecnica_Agromercantil

# Verificar status do git
git status

# Adicionar todos os arquivos novos e modificados
git add .

# Commit das mudancas
git commit -m "Refactor: Migra de Streamlit para Flask

- Substitui Streamlit por Flask 3.1 para maior controle de layout
- Implementa arquitetura MVC com templates Jinja2
- Adiciona design system Material 3 com Tailwind CSS
- Mantem todas as queries SQL com CTEs e window functions
- Inclui modulo de chatbot para consultas em linguagem natural
- Adiciona documentacao tecnica completa"

# Push para o repositorio
git push origin main
```

## Caso precise forcar atualizacao (se houver conflitos)

```bash
# Se o repositorio remoto estiver desatualizado
# e voce quiser substituir completamente:

git add .
git commit -m "Refactor: Completo para Flask"
git push origin main --force
```

## Atualizar descricao no GitHub (via interface web)

Apos o push, acesse o repositorio no GitHub e atualize:

1. **About / Description**:
```
Sistema de analise de commodities agricolas com dashboard interativo, 
segmentacao RFV de clientes e deteccao de anomalias. 
Desenvolvido com Flask, PostgreSQL e Plotly.
```

2. **Topics/Tags**:
```
flask, python, postgresql, pandas, data-analysis, dashboard, 
business-intelligence, plotly, tailwindcss
```

## Verificar se subiu corretamente

Acesse: `https://github.com/Mateus-Sousa93/Avalicao_Tecnica_Agromercantil`

Arquivos que devem aparecer na raiz:
- app.py
- README.md
- requirements.txt
- schema.sql
- templates/ (pasta)
- static/ (pasta)
