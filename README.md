# 🚀 Agente Autônomo de Vagas, Auto-Apply e Otimização de CV (AI-Driven ATS)

Agente autônomo em **Python 3.10+** desenvolvido para buscar, filtrar, analisar e aplicar automaticamente para vagas de Tecnologia no Brasil (com foco em **COBOL, Mainframe, Java, Analista de Sistemas e Automação / n8n**).

O sistema utiliza a API da **Groq** (`llama-3.3-70b-versatile`) para calcular o score de aderência ATS (Match %), gerar currículos customizados em PDF via **ReportLab**, criar dossiês de preparação para entrevista e cartas de apresentação, enviando candidaturas automáticas por e-mail, registrando todo o histórico no **Supabase** (PostgreSQL) e fornecendo uma interface interativa completa via **Bot no Telegram**.

---

## 🏗️ Arquitetura do Repositório

```text
agente-vagaas/
├── .github/
│   └── workflows/
│       ├── cron_agente.yml        # Varredura automática 8x ao dia (08h às 22h BRT)
│       ├── cron_daily_report.yml  # Relatório diário de desempenho (Daily Digest às 20h BRT)
│       └── cron_weekly_report.yml # Relatório semanal de analytics (Domingo às 12h BRT)
├── modules/
│   ├── __init__.py
│   ├── scraper.py             # Varredura multicanal (SerpAPI, Programathor, GitHub, RSS) + Deep Scraping
│   ├── tailor.py              # Análise de aderência e customização ATS via Groq LLM
│   ├── pdf_generator.py       # Gerador de currículo em PDF limpo via ReportLab
│   ├── dossier.py             # Gerador de Dossiê de Preparação para Entrevistas (Markdown)
│   ├── cover_letter.py        # Gerador de Carta de Apresentação Profissional (TXT)
│   ├── database.py            # Persistência, sanitização e sincronização de dados no Supabase
│   ├── notifier.py            # Envio de Auto-Apply por Gmail SMTP e notificações no Telegram
│   └── telegram_bot.py        # Bot Interativo do Telegram com Trava de Instância Única (Socket Lock)
├── master_profile.json        # Perfil profissional mestre do candidato (Fonte da Verdade)
├── vagas_processadas.json     # Cache local anti-duplicata
├── schema_supabase.sql        # Script DDL completo de tabelas e permissões do Supabase
├── weekly_report.py           # Script de geração do relatório semanal (E-mail + Telegram)
├── main.py                    # Orquestrador principal do pipeline
├── requirements.txt           # Dependências do projeto
└── README.md                  # Documentação completa do projeto
```

---

## ✨ Principais Funcionalidades

### 🌐 Multi-Fonte de Coleta (Gratuita e Otimizada)
1. **Google Jobs (SerpAPI Otimizada)**: Pesquisas direcionadas por tecnologia (`Java Junior`, `Analista de Sistemas`, `COBOL Mainframe`, `n8n`). Indexa automaticamente portais como **Remotar**, **Gupy**, **Catho**, **InfoJobs**, **LinkedIn**, **WhatJobs** e portais de empresas.
2. **Programathor**: Scraper direto do portal de vagas tech no Brasil (**0 consumo de cota**).
3. **Fóruns & Comunidades Dev no GitHub**: Coleta em tempo real via API REST nos maiores repositórios de TI do Brasil (**0 consumo de cota**):
   - `backend-br/vagas` (Backend / Microserviços / Java / Python / COBOL / Node)
   - `frontendbr/vagas` (Frontend / Fullstack / Web)
   - `react-brasil/vagas` (React / Fullstack / Node)
   - `qa-brasil/vagas` (QA / Automação / Testes)
   - `androiddevbr/vagas` (Mobile Android)
   - `phpdevbr/vagas` (Backend PHP/Fullstack)
   - `flutterbr/vagas` (Mobile Flutter)
   - `vuejs-br/vagas` (Frontend/Fullstack Vue.js)
4. **Feeds RSS Tech**: Varredura contínua em feeds de vagas remotas (RemoteOK, WeWorkRemotely, Remotive, Jobspress, WorkingNomads).

---

### 🕵️‍♂️ Deep Scraping & Auto-Apply Inteligente
- **Deep Scraping de Contatos**: Investiga o HTML da página oficial da vaga para extrair e-mails diretos de recrutadores (`recrutamento@`, `rh@`, `vagas@`, `talent@`).
- **Auto-Apply por E-mail**: Se o e-mail de RH for identificado, o robô dispara a candidatura **100% no automático**, anexando o PDF `CV_Felipe_Santana_[Empresa].pdf` e enviando uma cópia de confirmação para o e-mail do próprio candidato (`felipestartt@gmail.com`).
- **Gestão de Limpeza**: Deleta os PDFs e arquivos temporários do disco local após a notificação, mantendo a cópia e o histórico salvos 100% no Supabase.

---

### 🛡️ Filtros Estritos de Qualificação e Localidade

- ✅ **Aprovados**:
  - **Localização**: 100% Remoto (Home Office / Remote em qualquer lugar do Brasil) OU Híbrido/Presencial localizado **estritamente no Estado do Rio de Janeiro (RJ)**.
  - **Cargos**: COBOL, Mainframe, Analista de Sistemas, Java (**Júnior / Trainee / Estágio**); Automação / n8n (**Júnior, Trainee ou Pleno**).
  - **Candidatura**: 100% Gratuita.
- ❌ **Descartados**:
  - **Localização Incompatível**: 100% de descarte de vagas presenciais ou híbridas fora do RJ (ex: São Paulo, Barueri, Alphaville, Belo Horizonte, Curitiba, Porto Alegre, Brasília, etc.).
  - **Sites Pagos / Paywall VIP**: Portais com cobrança *"Seja VIP"* ou cadastro pago (ex: Bebee, TrabalhaES).
  - **Vagas Afirmativas Restritas**: Anúncios exclusivos para públicos específicos aos quais você não pertence (*Elas in Tech*, *Women in Tech*, *Exclusiva PCD*).
  - **Tecnologias Fora do Escopo**: PHP, Mobile / Flutter, .NET, C++, Firmware, TOTVS Protheus.
  - **Áreas Fora do Escopo**: Suporte Técnico, Helpdesk, Engenharia de Dados, Vendas, Comercial, Marketing, RH.
  - **Senioridade Alta**: Níveis *Sênior, Sr, Lead, Principal, Architect, Especialista*.

---

### 🔒 Trava de Instância Única & UTF-8 no Windows
- **Socket Process Lock (`garantir_instancia_unica`)**: O bot do Telegram utiliza um socket binding na porta `47891` em `modules/telegram_bot.py` que impede a execução de instâncias duplicadas simultâneas. Se um novo processo for aberto, ele encerra automaticamente para evitar mensagens repetidas no Telegram.
- **Proteção UTF-8 (`sys.stdout.reconfigure`)**: Reconfigura o console no Windows para prevenir falhas de `UnicodeEncodeError` com emojis presentes nos títulos das vagas.

---

## 🗄️ Configuração do Banco de Dados no Supabase

Execute o arquivo **`schema_supabase.sql`** no **SQL Editor** do seu painel Supabase (https://supabase.com/dashboard):

```sql
-- 1. Habilita extensões para UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 2. Tabela vagas (Vagas qualificadas com match >= 80%)
CREATE TABLE IF NOT EXISTS public.vagas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    titulo TEXT NOT NULL,
    empresa TEXT,
    link TEXT UNIQUE,
    descricao TEXT,
    match_score INT,
    status TEXT DEFAULT 'QUALIFICADA',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- 3. Tabela vagas_processadas (Histórico completo de análise)
CREATE TABLE IF NOT EXISTS public.vagas_processadas (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    titulo_vaga TEXT NOT NULL,
    empresa TEXT,
    link_vaga TEXT,
    match_score INT,
    justificativa TEXT,
    resumo_adaptado TEXT,
    status_candidatura TEXT DEFAULT 'alerta_manual',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- 4. Tabela curriculos_gerados
CREATE TABLE IF NOT EXISTS public.curriculos_gerados (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vaga_id UUID REFERENCES public.vagas(id) ON DELETE CASCADE,
    pdf_url TEXT,
    conteudo_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- 5. Tabela prep_dossies
CREATE TABLE IF NOT EXISTS public.prep_dossies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vaga_id UUID REFERENCES public.vagas(id) ON DELETE CASCADE,
    resumo_empresa TEXT,
    perguntas_sugeridas JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- 6. Permissões de Leitura e Escrita
ALTER TABLE public.vagas DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.vagas_processadas DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.curriculos_gerados DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.prep_dossies DISABLE ROW LEVEL SECURITY;

GRANT ALL ON public.vagas TO anon, authenticated, service_role;
GRANT ALL ON public.vagas_processadas TO anon, authenticated, service_role;
GRANT ALL ON public.curriculos_gerados TO anon, authenticated, service_role;
GRANT ALL ON public.prep_dossies TO anon, authenticated, service_role;
```

---

## ⚙️ Variáveis de Ambiente (`.env`)

Crie o arquivo `.env` na raiz do projeto (e cadastre as mesmas chaves em **GitHub Settings ➔ Secrets ➔ Actions**):

```env
GROQ_API_KEY=gsk_sua_chave_groq_aqui
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua_chave_anon_ou_service_role
GMAIL_USER=seu_email@gmail.com
GMAIL_APP_PASSWORD=sua_senha_de_aplicativo_gmail
NOTIFY_EMAIL=seu_email@gmail.com
SERPAPI_KEY=sua_chave_serpapi_aqui
TELEGRAM_BOT_TOKEN=seu_token_bot_telegram
TELEGRAM_CHAT_ID=seu_chat_id_telegram
```

---

## 📱 Comandos Interativos do Telegram

Interaja com o robô em tempo real enviando os comandos:

- **`/relatorio`**: Exibe o relatório sob demanda (`⚡ [RELATÓRIO SOB DEMANDA - /relatorio]`).
- **`/status`**: Exibe a cota ao vivo da SerpAPI e estatísticas de vagas do Supabase.
- **`/buscar`**: Dispara uma varredura completa por novas vagas na web.
- **`/ajuda`**: Exibe o menu com todos os comandos disponíveis.

---

## ⏰ Disparos Automáticos Agendados (CI/CD)

| Automação | Cron | Horário (BRT) | Descrição |
| :--- | :--- | :--- | :--- |
| **Varredura & Auto-Apply** | `0 1,11,13,15,17,19,21,23 * * *` | 8x ao dia (08h, 10h, 12h, 14h, 16h, 18h, 20h, 22h) | Varre a web, filtra, gera CV/Dossiê/Carta, faz Auto-Apply e notifica no Telegram. |
| **Relatório Diário** | `0 23 * * *` | Diariamente às 20:00 | Envia o Digest Diário com a marca visual `🤖 [RELATÓRIO DIÁRIO AUTOMÁTICO]`. |
| **Relatório Semanal** | `0 12 * * 0` | Todo domingo às 12:00 | Envia o relatório semanal de Analytics por **E-mail** e **Telegram**. |

---

## 🛡️ Conformidade & Auditoria GRC (Governance, Risk & Compliance)

- **Sincronização de Fuso Horário**: Todos os relatórios utilizam o Horário de Brasília (BRT / UTC-3), garantindo que as contagens de vagas batam 100% entre a nuvem (GitHub Actions) e o seu Telegram.
- **Proteção contra Injeção HTML**: Aplicação obrigatoria de `html.escape` nas entradas web para prevenir erros de parse na API do Telegram.
- **Sanitização de URLs de Banco**: O sistema higieniza URLs e chaves removendo aspas e adicionando `https://` automaticamente.
- **Formatação ATS-Friendly**: PDF gerado sem tabelas complexas ou elementos gráficos que prejudiquem a pontuação em robôs leitores de currículos.
- **Zero Alucinação**: A IA gera adaptações limitando-se estritamente às informações factuais de `master_profile.json`.

---

## 🚀 Como Executar Localmente

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/GTNFelipe/agente-vagaas.git
   cd agente-vagaas
   ```

2. **Crie e ative um ambiente virtual Python:**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```

3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Execute uma busca completa de vagas:**
   ```bash
   python main.py
   ```

5. **Inicie o Bot Interativo do Telegram:**
   ```bash
   python modules/telegram_bot.py
   ```
