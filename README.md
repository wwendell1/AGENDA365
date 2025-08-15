# Produtiva - Plataforma de Gestão de Tarefas e Finanças

## Sobre o Projeto

Produtiva é uma plataforma SaaS para organização pessoal de tarefas, finanças e projetos colaborativos. O sistema oferece funcionalidades como autenticação, dashboard personalizado, gerenciamento de tarefas, grupos de trabalho, controle financeiro e notificações.

## Tecnologias Utilizadas

- Django (Backend)
- HTML, Bulma CSS, JavaScript (Frontend)
- SQLite (Desenvolvimento) / PostgreSQL (Produção)
- Django Crispy Forms com Bulma template pack

## Configuração do Ambiente

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/produtiva.git
cd produtiva
```

2. Crie e ative um ambiente virtual:
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure as variáveis de ambiente:
- Copie o arquivo `.env.example` para `.env`
- Preencha as variáveis com seus valores

### Configuração do Email

Para utilizar o sistema de recuperação de senha, você precisa configurar um servidor de email. Se estiver usando Gmail:

1. Ative a autenticação de duas etapas na sua conta Google
2. Gere uma senha de aplicativo:
   - Acesse sua conta Google
   - Vá para Segurança > Senhas de app
   - Selecione "Email" e "Outro (nome personalizado)"
   - Use a senha gerada no `EMAIL_HOST_PASSWORD`

3. Configure as variáveis no arquivo `.env`:
```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=seu-email@gmail.com
EMAIL_HOST_PASSWORD=sua-senha-de-aplicativo
```

## Executando o Projeto

1. Aplique as migrações:
```bash
python manage.py migrate
```

2. Crie um superusuário:
```bash
python manage.py createsuperuser
```

3. Inicie o servidor de desenvolvimento:
```bash
python manage.py runserver
```

4. Acesse o sistema em `http://localhost:8000`

## Funcionalidades

- **Autenticação**:
  - Login/Registro
  - Recuperação de senha
  - Exclusão de conta

- **Dashboard**:
  - Visão geral de tarefas
  - Resumo financeiro
  - Atividades recentes

- **Tarefas**:
  - Criação e gerenciamento
  - Atribuição a usuários
  - Comentários e anexos
  - Filtros e organização

- **Grupos**:
  - Criação de equipes
  - Gerenciamento de membros
  - Compartilhamento de tarefas

- **Finanças**:
  - Registro de receitas/despesas
  - Categorização
  - Relatórios e gráficos

- **Notificações**:
  - Alertas por email
  - Notificações no sistema
  - Preferências personalizáveis

## Contribuindo

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`)
3. Faça commit das mudanças (`git commit -m 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

## Licença

Este projeto está licenciado sob a [MIT License](LICENSE).