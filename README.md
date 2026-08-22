# 🚀 Agente Autônomo de Vagas, Auto-Apply e Otimização de CV (AI-Driven ATS)

Agente autônomo em **Python 3.10+** desenvolvido para buscar, filtrar, analisar e aplicar automaticamente para vagas de Tecnologia no Brasil (com foco em **COBOL, Mainframe, Java Junior, Python Junior, Trainee TI, Analista de Sistemas e Automação / n8n / Low-code / No-code / Vibe Code**).

O sistema utiliza a API da **Groq** (`llama-3.3-70b-versatile`) para calcular o score de aderência ATS (Match %), gerar currículos customizados em PDF via **ReportLab**, criar dossiês de preparação para entrevista e cartas de apresentação. **Todas as gerações de IA são estritamente orientadas a resultados e entregas (impacto real, métricas, valor gerado).**

O agente envia candidaturas automáticas por e-mail, registrando todo o histórico no **Supabase** (PostgreSQL com Row Level Security ativo) e fornecendo uma interface interativa completa via **Bot no Telegram**, mantendo total observabilidade através de Logs Estruturados.

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
│   ├── scraper.py             # Varredura multicanal (SerpAPI, Programathor, GitHub, RSS) + Session HTTP + Regexes
│   ├── tailor.py              # Análise de aderência, customização ATS, isolamento contra Prompt Injection via Groq
│   ├── pdf_generator.py       # Gerador de currículo em PDF limpo, com html.escape para ReportLab
│   ├── dossier.py             # Gerador de Dossiê de Preparação para Entrevistas (Markdown)
│   ├── cover_letter.py        # Gerador de Carta de Apresentação Profissional (TXT)
│   ├── database.py            # Persistência, cache local e cliente Singleton no Supabase
│   ├── notifier.py            # Envio de Auto-Apply por Gmail SMTP e relatórios discriminados no Telegram
│   └── telegram_bot.py        # Bot Interativo do Telegram com execução assíncrona (Thread Workers) e Socket Lock
├── master_profile.sample.json # Modelo de perfil sem informações sensíveis (Template)
├── master_profile.json        # Perfil mestre real do candidato (No .gitignore / Dados Sensíveis)
├── vagas_processadas.json     # Cache local anti-duplicata
├── schema_supabase.sql        # Script DDL completo de tabelas e permissões RLS do Supabase
├── keep_alive_ping.py         # Monitoramento Keep-Alive 24/7 (Pings automáticos a cada 5m com Self-Healing)
├── weekly_report.py           # Script de geração do relatório semanal de 7 dias (E-mail + Telegram)
├── main.py                    # Orquestrador principal do pipeline (Delay otimizado de 3s)
├── iniciar_bot.bat            # Script Batch Watchdog com loop de auto-restart
├── iniciar_bot_silencioso.vbs # Launcher em segundo plano sem janela de console (Windows)
├── Procfile                   # Configuração de Worker para deploy 24/7 na nuvem (Render/Railway)
├── requirements.txt           # Dependências do projeto
└── README.md                  # Documentação completa do projeto
```

---

## ✨ Principais Funcionalidades

### 🌐 Multi-Fonte de Coleta (Gratuita e Otimizada)
1. **Google Jobs (SerpAPI Otimizada & Controle Dinâmico de Cota)**: Pesquisas direcionadas por tecnologia (`Java Junior`, `Python Junior`, `Analista de Sistemas`, `COBOL Mainframe`, `Trainee TI`, `n8n automacao`, `low code no code`). Possui **Gerenciador Dinâmico de Cota Diária** (`serpapi_daily_tracker.json`), que calcula dinamicamente o ritmo ideal (atualmente ajustado para **1 disparo por dia com rotação de termos de busca**) para garantir sustentabilidade total até a renovação do plano em **03/09/2026** (39 disparos restantes em 25 dias, retendo 14 disparos de margem de segurança para buscas manuais). Indexa automaticamente portais como **Remotar**, **Gupy**, **Catho**, **InfoJobs**, **LinkedIn**, **WhatJobs** e portais de empresas.
2. **LinkedIn (Scraper Público NATIVO / 0 Cota)**: Extração automatizada e gratuita via API pública Guest do LinkedIn (`jobs-guest/jobs/api`), capturando vagas e raspando a descrição técnica completa de cada publicação diretamente do LinkedIn sem necessidade de login.
3. **Programathor**: Scraper direto do portal de vagas tech no Brasil (**0 consumo de cota**).
4. **Fóruns & Comunidades Dev no GitHub**: Coleta em tempo real via API REST nos maiores repositórios de TI do Brasil (**0 consumo de cota**):
   - `backend-br/vagas` (Backend / Microserviços / Java / Python / COBOL / Node)
   - `frontendbr/vagas` (Frontend / Fullstack / Web)
   - `react-brasil/vagas` (React / Fullstack / Node)
   - `qa-brasil/vagas` (QA / Automação / Testes)
   - `androiddevbr/vagas` (Mobile Android)
   - `phpdevbr/vagas` (Backend PHP/Fullstack)
   - `flutterbr/vagas` (Mobile Flutter)
   - `vuejs-br/vagas` (Frontend/Fullstack Vue.js)
5. **Feeds RSS Tech**: Varredura contínua em feeds de vagas remotas (RemoteOK, WeWorkRemotely, Remotive, Jobspress, WorkingNomads).

> 💳 **Gestão Automática de Cota SerpAPI**: O robô calcula dinamicamente a cota diária permitida baseando-se no saldo ao vivo retornado pela API SerpAPI (`total_searches_left / dias_ate_renovacao`). Caso o limite diário seja atingido (ex: 1 disparo/dia), as varreduras automáticas adicionais do dia pulam o Google Jobs e continuam executando 100% normalmente em todas as outras fontes gratuitas (LinkedIn, Programathor, GitHub e RSS).

---

### 🛡️ Regra de Veracidade Absoluta (Zero Mentiras / Zero Alucinação)
- **Fonte Única da Verdade (`master_profile.json`)**: O gerador de currículos e cartas de apresentação é estritamente limitado ao histórico factual do candidato.
- **Foco Absoluto em Resultados**: Os currículos, cartas de apresentação e dossiês gerados pelo Groq são parametrizados para destacar entregas, métricas e o impacto real gerado nos projetos anteriores.
- **Bloqueio Factual de Ferramentas**: É terminantemente proibida a invenção de ferramentas ou linguagens inexistentes no perfil mestre (ex: *Cypress, Playwright, Selenium, RestAssured, React Native, Angular, Kubernetes* nunca são inseridos no currículo).
- **Higienização em Camadas (Python Post-Processing)**: Em `modules/tailor.py` e `modules/pdf_generator.py`, qualquer habilidade sugerida pela IA que não esteja presente no conjunto de competências reais do candidato é sumariamente descartada pelo código antes da geração do PDF.

---

### 🕵️‍♂️ Deep Scraping, Análise Direta no Telegram & Auto-Apply Inteligente
- **Deep Scraping de Contatos**: Investiga o HTML da página oficial da vaga para extrair e-mails diretos de recrutadores (`recrutamento@`, `rh@`, `vagas@`, `talent@`).
- **Análise Direta de Vagas via Telegram**: Envie a descrição de qualquer vaga diretamente no chat do Telegram (ou com `/vaga <descrição>`). A IA (Groq) extrai automaticamente o Nome da Empresa e a Tecnologia Principal da vaga pelo texto. O bot calcula o match de aderência e gera o **Currículo em PDF** (nomeado inteligentemente com a empresa ou a tecnologia), **Dossiê em Markdown** e **Carta de Apresentação em Texto**, retornando todos anexados no chat.
- **Auto-Apply por E-mail**: Se o e-mail de RH for identificado na varredura web ou na descrição enviada pelo Telegram, o robô dispara a candidatura **100% no automático**, anexando o PDF `CV_[Nome]_[Empresa_Ou_Tech].pdf` e enviando uma cópia de confirmação para o e-mail do próprio candidato.
- **Gestão de Limpeza**: Deleta os PDFs e arquivos temporários do disco local após a notificação, mantendo a cópia e o histórico salvos 100% no Supabase.

---

### 🛡️ Filtros Estritos de Qualificação e Localidade

- ✅ **Aprovados**:
  - **Localização**: 100% Remoto (Home Office / Remote em qualquer lugar do Brasil) OU Híbrido/Presencial localizado **estritamente no Estado do Rio de Janeiro (RJ)**.
  - **Cargos**: COBOL, Mainframe, Automação / n8n / Low-code / No-code / Vibe Code (**Júnior, Trainee ou Pleno**); Analista de Sistemas, Java, Python (**Júnior / Trainee / Estágio**).
  - **Candidatura**: 100% Gratuita.
- ❌ **Descartados**:
  - **Localização Incompatível**: 100% de descarte de vagas presenciais ou híbridas fora do RJ (ex: São Paulo, Barueri, Alphaville, Belo Horizonte, Curitiba, Porto Alegre, Brasília, etc.).
  - **Sites Pagos / Paywall VIP**: Portais com cobrança *"Seja VIP"* ou cadastro pago (ex: Bebee, TrabalhaES).
  - **Vagas Afirmativas Restritas**: Anúncios exclusivos para públicos específicos aos quais você não pertence (*Elas in Tech*, *Women in Tech*, *Exclusiva PCD*).
  - **Tecnologias Fora do Escopo**: PHP, Mobile / Flutter, .NET, C++, Firmware, TOTVS Protheus.
  - **Áreas Fora do Escopo**: Suporte Técnico, Helpdesk, Engenharia de Dados, Vendas, Comercial, Marketing, RH.
  - **Senioridade Alta**: Níveis *Sênior, Sr, Lead, Principal, Architect, Especialista*.

---

### 🔒 Trava de Instância Única, UTF-8 & Proteção de Caminhos no Windows
- **Socket Process Lock (`garantir_instancia_unica`)**: O bot do Telegram utiliza um socket binding na porta `47891` em `modules/telegram_bot.py` que impede a execução de instâncias duplicadas simultâneas. Se um novo processo for aberto, ele encerra automaticamente para evitar mensagens repetidas no Telegram.
- **Proteção UTF-8 (`sys.stdout.reconfigure`)**: Reconfigura o console no Windows para prevenir falhas de `UnicodeEncodeError` com emojis presentes nos títulos das vagas.
- **Higienização e Limite de Caminhos de Arquivo (Windows MAX_PATH)**: Trunca automaticamente nomes sanitizados de empresas e títulos de vagas para um limite seguro (máximo 30/35 caracteres), eliminando completamente erros `OSError: [Errno 22] Invalid argument` no Windows ao salvar PDFs, Dossiês e Cartas de Apresentação.

---

### 📲 Notificação Universal & Transparência em 100% das Execuções
- **Feedback em 100% das Execuções**: Seja em execuções automáticas na nuvem (GitHub Actions 8x ao dia) ou manuais via Telegram (`/buscar`), o robô **sempre envia uma notificação de retorno no Telegram**.
- **Relatório de Rodada Sem Vagas Novas**: Caso nenhuma vaga nova qualificada seja encontrada (vagas coletadas já processadas anteriormente ou descartadas pelos filtros), o bot avisa expressamente:
  `🔍 [VARREDURA CONCLUÍDA - Automática (Cron 8x/dia) / Manual]`
  `ℹ️ Resultado: Nenhuma vaga nova qualificada encontrada nesta rodada.`
  `🤖 O agente continuará monitorando automaticamente na próxima execução agendada!`
- **Anexo Instantâneo de Documentos**: Quando vagas qualificadas inéditas são encontradas ou enviadas pelo chat, o Telegram recebe automaticamente a notificação individual acompanhada de **3 arquivos em anexo**: PDF do CV customizado, Dossiê de Entrevista (.md) e Carta de Apresentação (.txt).

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

-- 6. Permissões de Leitura e Escrita e RLS (Row Level Security)
ALTER TABLE public.vagas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.vagas_processadas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.curriculos_gerados ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.prep_dossies ENABLE ROW LEVEL SECURITY;

-- Removemos o acesso anon, permitindo apenas acessos autenticados ou service_role
GRANT ALL ON public.vagas TO authenticated, service_role;
GRANT ALL ON public.vagas_processadas TO authenticated, service_role;
GRANT ALL ON public.curriculos_gerados TO authenticated, service_role;
GRANT ALL ON public.prep_dossies TO authenticated, service_role;
```


---

## 👤 Modelo do Perfil Mestre (`master_profile.sample.json`)

Por conter dados pessoais sensíveis (como telefone, e-mail, histórico profissional e links), o arquivo **`master_profile.json`** está presente no `.gitignore` e **NÃO é commitado no repositório**.

Para uso local, crie o arquivo `master_profile.json` na raiz do projeto utilizando a estrutura base abaixo:

```json
{
  "nome": "Seu Nome Completo",
  "cargo_atual": "Seu Cargo Atual / Área de Atuação",
  "localizacao": "Cidade, Estado",
  "contato": {
    "email": "seu_email@exemplo.com",
    "phone": "5521999999999",
    "linkedin": "https://linkedin.com/in/seu_perfil",
    "github": "https://github.com/seu_usuario"
  },
  "cargos_alvo": [
    "Cargo Alvo 1",
    "Cargo Alvo 2",
    "Cargo Alvo 3"
  ],
  "modalidades_aceitas": [
    "Remoto",
    "Híbrido (Sua Cidade)"
  ],
  "resumo_profissional": "Resumo factual do seu perfil profissional, descrevendo suas principais experiências e competências...",
  "habilidades_tecnicas": {
    "linguagens": ["Python", "JavaScript", "Java"],
    "bancos_de_dados": ["Postgres", "Supabase", "Redis"],
    "ia_e_automacao": ["n8n", "OpenAI API", "Groq API"],
    "devops_e_infra": ["Docker", "Linux", "Git", "GitHub"],
    "mainframe_e_alm": [],
    "gestao_e_metodologias": ["Scrum", "Kanban", "Jira"]
  },
  "experiencias": [
    {
      "empresa": "Nome da Empresa",
      "cargo": "Seu Cargo",
      "periodo": "01/2024 - Atual",
      "detalhes": [
        "Descrição detalhada da atividade ou conquista 1.",
        "Descrição detalhada da atividade ou conquista 2."
      ],
      "tecnologias": ["Tecnologia1", "Tecnologia2"]
    }
  ],
  "formacao": [
    {
      "curso": "Nome do Curso / Graduação",
      "instituicao": "Nome da Instituição de Ensino",
      "conclusao": "MM/AAAA"
    }
  ],
  "idiomas": [
    {
      "idioma": "Português",
      "nivel": "Nativo"
    },
    {
      "idioma": "Inglês",
      "nivel": "Intermediário"
    }
  ],
  "soft_skills": [
    "Atenção aos Detalhes",
    "Resolução de Problemas",
    "Trabalho em Equipe"
  ]
}
```

---

## 🔑 Configuração no GitHub Secrets & Variables

Para que as automações no **GitHub Actions** funcionem na nuvem sem expor seus dados pessoais:

1. Acesse o seu repositório no GitHub.
2. Vá em **Settings** ➔ **Secrets and variables** ➔ **Actions**.
3. Em **Repository secrets**, clique no botão **New repository secret**.
4. Preencha os campos:
   - **Name**: `MASTER_PROFILE_JSON`
   - **Secret**: cole o conteúdo JSON completo do seu `master_profile.json` (formatado).
5. Clique em **Add secret**.

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

## 📱 Comandos Interativos do Telegram & Resiliência 24/7

Interaja com o robô em tempo real enviando os comandos:

- **`💬 Texto Livre de Vaga`**: Cole qualquer descrição completa de vaga no chat para receber o CV (PDF), Dossiê (MD) e Carta (TXT), com disparo de candidatura por e-mail se houver RH no texto.
- **`/vaga <descrição>`**: Comando explícito para analisar uma vaga enviada via texto.
- **`/relatorio`**: Exibe o relatório sob demanda (`⚡ [RELATÓRIO SOB DEMANDA - /relatorio]`).
- **`/status`**: Exibe a cota ao vivo da SerpAPI e estatísticas de vagas do Supabase.
- **`/buscar`**: Dispara uma varredura completa por novas vagas na web em **segundo plano (Assíncrono)**, permitindo que a conversa continue livre sem travamentos.
- **`/ajuda`**: Exibe o menu interativo de ajuda.

> 🔄 **Monitor Keep-Alive Automático 24/7 (`keep_alive_ping.py`)**: O sistema executa um pinger autônomo a cada **5 minutos (300 segundos)** na API do Telegram. Caso ocorra qualquer oscilação de rede ou queda de processo, o monitoramento detecta a falha e **relança o bot automaticamente**, mantendo a aplicação acordada e operante 24 horas por dia.

---

## ⏰ Disparos Automáticos Agendados (CI/CD)

| Automação | Cron | Horário (BRT) | Descrição |
| :--- | :--- | :--- | :--- |
| **Varredura & Auto-Apply** | `0 1,11,13,15,17,19,21,23 * * *` | 8x ao dia (08h, 10h, 12h, 14h, 16h, 18h, 20h, 22h) | Varre a web, filtra, gera CV/Dossiê/Carta, faz Auto-Apply e notifica no Telegram. |
| **Relatório Diário** | `0 23 * * *` | Diariamente às 20:00 | Envia o Digest Diário com a marca visual `🤖 [RELATÓRIO DIÁRIO AUTOMÁTICO]`. |
| **Relatório Semanal** | `0 12 * * 0` | Todo domingo às 12:00 | Envia o relatório semanal de Analytics por **E-mail** e **Telegram**. |

---

## 🛡️ Conformidade & Auditoria GRC (Governance, Risk & Compliance)

- **Segurança de Dados e Acesso (RLS)**: O Supabase foi reconfigurado para exigir chaves de serviço ou autenticadas (`authenticated`, `service_role`), revogando permissões públicas (`anon`) e ativando o **Row Level Security (RLS)** em todas as tabelas.
- **Observabilidade Profissional**: Implementação robusta do módulo `logging` nativo do Python substituindo chamadas `print()`, garantindo rastreabilidade centralizada, formatação padronizada e captura de stack traces para facilitar debugging (ex: `logger.exception`).
- **Veracidade Factual Absoluta e Foco em Resultados**: Garantia de zero invenções de competências. Toda saída gerada pela IA (Currículos, Cartas e Pitches) é **focada em resultados entregues e valor gerado**, mantendo integridade factual perante o mercado e órgãos reguladores.
- **Sincronização de Fuso Horário**: Todos os relatórios utilizam o Horário de Brasília (BRT / UTC-3), garantindo que as contagens de vagas batam 100% entre a nuvem (GitHub Actions) e o seu Telegram.
- **Proteção contra Injeção HTML**: Aplicação obrigatória de `html.escape` nas entradas web para prevenir erros de parse na API do Telegram.
- **Sanitização de URLs de Banco**: O sistema higieniza URLs e chaves removendo aspas e adicionando `https://` automaticamente.
- **Formatação ATS-Friendly**: PDF gerado sem tabelas complexas ou elementos gráficos que prejudiquem a pontuação em robôs leitores de currículos.

---

## 🚀 Como Executar e Manter o Bot 24/7

### 1. Execução Local Simples
```bash
# Clone e entre no repositório
git clone https://github.com/GTNFelipe/agente-vagaas.git
cd agente-vagaas

# Crie e ative o ambiente virtual
python -m venv .venv
.venv\Scripts\activate

# Instale as dependências
pip install -r requirements.txt

# Execute a varredura manual de vagas:
python main.py

# Inicie o Bot Interativo do Telegram:
python modules/telegram_bot.py

# Ou inicie o Monitor Keep-Alive 24/7 (que cuida do Ping de 5m e auto-restart):
python keep_alive_ping.py
```

### 2. Modo Watchdog & Keep-Alive 24/7 (Local)
Para garantir que o bot nunca caia por oscilações na rede:
- **Monitor Autônomo Keep-Alive 5m**: Execute `python keep_alive_ping.py` (efetua pings de 5 em 5 minutos e relança o bot se cair).
- **Janela de Console Watchdog**: Clique duas vezes em `iniciar_bot.bat`.
- **Em Segundo Plano (Sem Janela)**: Clique duas vezes em `iniciar_bot_silencioso.vbs`.
- **Encerrar Bot em Segundo Plano**: Clique duas vezes em `parar_bot.bat`.

### 3. Início Automático com o Windows
Para o bot ligar automaticamente em segundo plano sempre que seu computador for ligado:
- **Ativar Início Automático**: Clique duas vezes em [`adicionar_ao_startup.bat`](file:///c:/Users/Felipe/Documents/GITHUB/agente-vagas/adicionar_ao_startup.bat).
- **Desativar Início Automático**: Clique duas vezes em [`remover_do_startup.bat`](file:///c:/Users/Felipe/Documents/GITHUB/agente-vagas/remover_do_startup.bat).
- *(Ou manualmente: Pressione `Win + R`, digite `shell:startup` e cole um atalho do `iniciar_bot_silencioso.vbs`).*

### 4. Deploy Gratuito 24/7 na Nuvem (Render / Railway)
Se preferir que o bot fique online **24 horas por dia sem precisar manter o PC ligado**:
1. Suba o repositório no GitHub.
2. Acesse [Render.com](https://render.com) e crie um **Background Worker** gratuito.
3. Conecte ao repositório (ele utilizará o [`Procfile`](file:///c:/Users/Felipe/Documents/GITHUB/agente-vagas/Procfile) automaticamente).
4. Configure as variáveis de ambiente (`.env`) no painel do Render.
