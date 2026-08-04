# 🚀 Agente Autônomo de Vagas, Auto-Apply e Otimização de CV (AI-Driven ATS)

Agente autônomo em **Python 3.10+** desenvolvido para buscar, filtrar, analisar e aplicar automaticamente para vagas de Tecnologia no Brasil (com foco em **COBOL, Mainframe, Java, Analista de Sistemas e Automação/n8n**). 

O sistema utiliza a API da **Groq** (`llama-3.3-70b-versatile`) para calcular o score de aderência ATS (Match %), gerar currículos customizados em PDF via **ReportLab**, criar dossiês de preparação para entrevista e cartas de apresentação, enviando candidaturas automáticas por e-mail, registrando todo o histórico no **Supabase** (PostgreSQL) e fornecendo uma interface interativa completa via **Bot no Telegram**.

---

## 🏗️ Arquitetura do Repositório

```text
agente-vagaas/
├── .github/
│   └── workflows/
│       ├── cron_agente.yml        # Varredura automática 8x ao dia (08h às 22h BRT)
│       ├── cron_daily_report.yml  # Relatório diário de desempenho (Daily Digest às 20h BRT)
│       └── cron_weekly_report.yml# Relatório semanal de analytics (Domingo)
├── modules/
│   ├── __init__.py
│   ├── scraper.py             # Varredura multicanal (SerpAPI, Programathor, GitHub, RSS) + Deep Scraping
│   ├── tailor.py              # Análise de aderência e customização ATS via Groq LLM
│   ├── pdf_generator.py       # Gerador de currículo em PDF limpo via ReportLab
│   ├── dossier.py             # Gerador de Dossiê de Preparação para Entrevistas (Markdown)
│   ├── cover_letter.py        # Gerador de Carta de Apresentação Profissional (TXT)
│   ├── database.py            # Persistência e sincronização de dados no Supabase
│   ├── notifier.py            # Envio de Auto-Apply por Gmail SMTP e notificações no Telegram
│   └── telegram_bot.py        # Bot Interativo do Telegram (/status, /relatorio, /buscar, /ajuda)
├── master_profile.json        # Perfil profissional mestre do candidato (Fonte da Verdade)
├── vagas_processadas.json     # Cache local anti-duplicata
├── main.py                    # Orquestrador do pipeline de busca e candidatura
├── requirements.txt           # Dependências do projeto
├── .gitignore                 # Arquivos ignorados pelo Git
└── README.md                  # Documentação completa do projeto
```

---

### 🌐 Multi-Fonte de Coleta (Gratuita e Otimizada)

1. **Google Jobs (SerpAPI Otimizada)**: 1 pesquisa unificada por execução (`1 cota por rodada = 8 rodadas/dia`).
2. **Programathor**: Scraper direto do portal de vagas de TI no Brasil (**0 cota**).
3. **Fóruns & Comunidades Dev no GitHub**: Coleta direta via API REST nos repositórios `backend-br/vagas` e `soujava/vagas` (**0 cota**).
4. **Feeds RSS Tech**: Varredura em feeds de vagas remotas (**0 cota**).

---

### 🕵️‍♂️ Deep Scraping & Auto-Apply Inteligente

- **Deep Scraping em Tempo Real**: Investiga o HTML da página oficial da vaga para extrair e-mails diretos de recrutadores (`recrutamento@`, `rh@`, `vagas@`).
- **Auto-Apply por E-mail**: Se o e-mail de RH for identificado, o robô dispara a candidatura **100% no automático**, anexando o PDF `CV_Felipe_Santana_[Empresa].pdf` e a Carta de Apresentação.
- **Gestão de Limpeza**: Deleta arquivos temporários do disco local após a notificação, mantendo o histórico 100% salvo no Supabase.

---

### 🛡️ Filtros Estritos de Qualificação

- ✅ **Aprovados**:
  - **Localização**: Brasil (Remoto ou Presencial/Híbrido no Rio de Janeiro - RJ). Aceita anúncios em inglês se a vaga for no Brasil.
  - **Cargos**: COBOL, Mainframe, Analista de Sistemas, Java (**Júnior / Trainee / Estágio**); Automação / n8n (**Júnior, Trainee ou Pleno**).
  - **Candidatura**: 100% Gratuita.
- ❌ **Descartados**:
  - **Sites Pagos / Paywall VIP**: 100% do portal **Bebee** (`bebee.com`), TrabalhaES, anúncios com cobrança *"Seja VIP"*.
  - **Vagas Afirmativas Restritas**: *Elas in Tech*, *Women in Tech*, *Exclusiva PCD*, *PCD - ...* (vagas reservadas para públicos específicos).
  - **Fora do Escopo**: Cloud, DevOps, SRE, Analista de Dados, Suporte Técnico, Professores, Vendas, PO/Scrum Master.
  - **Senioridade Alta**: Níveis *Sênior, Lead, Especialista, Gerente, Architect*.

---

## 🛠️ Stack Tecnológica

- **Linguagem:** Python 3.10+
- **LLM Engine:** Groq API (`llama-3.3-70b-versatile` - 100% Gratuito)
- **Scraping & HTML Parsing:** `requests`, `beautifulsoup4`, `google-search-results`
- **Gerador de PDF:** ReportLab (`reportlab`)
- **Banco de Dados Cloud:** Supabase (`supabase-py`)
- **Notificações & Interface:** Telegram Bot API (`requests` Long-Polling) + Gmail SMTP (`smtplib`)
- **Orquestração CI/CD:** GitHub Actions (`cron` agendado 8x ao dia + Daily Digest às 20h)

---

## 🗄️ Estrutura das Tabelas no Supabase (SQL DDL)

Crie as seguintes tabelas no seu editor SQL do Supabase:

```sql
-- 1. Tabela Principal de Vagas Qualificadas
CREATE TABLE IF NOT EXISTS vagas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    titulo TEXT NOT NULL,
    empresa TEXT,
    link TEXT,
    descricao TEXT,
    match_score INT,
    status TEXT DEFAULT 'QUALIFICADA',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- 2. Tabela de Currículos Gerados (JSON Payload)
CREATE TABLE IF NOT EXISTS curriculos_gerados (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vaga_id UUID REFERENCES vagas(id) ON DELETE CASCADE,
    pdf_url TEXT,
    conteudo_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- 3. Tabela de Dossiês de Preparação para Entrevista
CREATE TABLE IF NOT EXISTS prep_dossies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vaga_id UUID REFERENCES vagas(id) ON DELETE CASCADE,
    resumo_empresa TEXT,
    perguntas_sugeridas JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- 4. Tabela de Histórico de Processamento
CREATE TABLE IF NOT EXISTS vagas_processadas (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    titulo_vaga TEXT NOT NULL,
    empresa TEXT,
    link_vaga TEXT,
    match_score INT,
    justificativa TEXT,
    resumo_adaptado TEXT,
    status_candidatura TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);
```

---

## ⚙️ Configuração das Variáveis de Ambiente (`.env`)

Para execução local, crie um arquivo `.env` na raiz do projeto:

```env
GROQ_API_KEY=gsk_sua_chave_groq_aqui
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua_chave_service_role_ou_anon
GMAIL_USER=seu_email@gmail.com
GMAIL_APP_PASSWORD=sua_senha_de_aplicativo_gmail
NOTIFY_EMAIL=seu_email@gmail.com
SERPAPI_KEY=sua_chave_serpapi_aqui
TELEGRAM_BOT_TOKEN=seu_token_telegram_bot_aqui
TELEGRAM_CHAT_ID=seu_chat_id_telegram_aqui
```

---

## 📱 Comandos Interativos do Bot no Telegram

Você pode conversar com seu robô diretamente no Telegram usando os comandos:

- **`/relatorio`**: Exibe o **Daily Digest (Balanço do Dia)** em tempo real.
- **`/status`**: Exibe a cota ao vivo da SerpAPI e estatísticas do Supabase.
- **`/buscar`**: Dispara uma varredura de vagas imediatamente.
- **`/ajuda`**: Exibe o menu com todas as instruções.

---

## 🚀 Como Executar Localmente

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/GTNFelipe/agente-vagaas.git
   cd agente-vagaas
   ```

2. **Crie e ative um ambiente virtual:**
   ```bash
   python -m venv .venv
   # No Windows:
   .venv\Scripts\activate
   # No Linux/macOS:
   source .venv/bin/activate
   ```

3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Execute o orquestrador principal:**
   ```bash
   python main.py
   ```

5. **Inicie o Bot Interativo do Telegram:**
   ```bash
   python modules/telegram_bot.py
   ```

---

## 🛡️ Garantias de Segurança & Qualidade ATS
- **Sanitização HTML**: Todas as mensagens formatadas para o Telegram possuem sanitização `html.escape` para evitar quebras ou erros de renderização.
- **Zero Alucinação**: A IA gera adaptações limitando-se estritamente ao histórico factual de `master_profile.json`.
- **Layout ATS-Friendly**: PDF limpo sem gráficos, imagens ou tabelas complexas que dificultem a leitura por robôs leitores de RH.
