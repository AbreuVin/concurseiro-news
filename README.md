# Concurseiro News Bot

Bot de Telegram com IA que responde dúvidas sobre concursos públicos na Bahia e envia notificações personalizadas quando novos editais são publicados no Diário Oficial do Estado (DOE-BA).

---

## Stack

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.12+ |
| Framework RAG | LangChain 1.x (LCEL) + `langchain-classic` |
| LLM | Llama 3.3 70B via Groq (`langchain-groq`) |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` — local, sem custo de API |
| Base vetorial | LanceDB embedded (arquivos em `./db/`) |
| Chunking | `ParentDocumentRetriever` — filhos 200 chars (busca) / pais 1500 chars (contexto) |
| Interface | Telegram Bot API (`python-telegram-bot` v21+) |
| Agendamento | JobQueue nativo do `python-telegram-bot` |
| Scraping | `httpx` + `BeautifulSoup4` |
| Perfis de usuário | SQLite (`./db/users.db`) |

---

## Arquitetura

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────────────┐
│   DOE-BA        │────>│  ETL Pipeline        │────>│  LanceDB                │
│  (DOOL/apifront)│     │  httpx + BS4         │     │  chunks filhos (200c)   │
└─────────────────┘     │  filtro concursos    │     ├─────────────────────────┤
                        └──────────────────────┘     │  LocalFileStore         │
                                                      │  chunks pais (1500c)    │
                                                      └────────────┬────────────┘
                                                                   │ ParentDocumentRetriever
                                                                   ▼
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────────────┐
│  Usuário        │<───>│  Telegram Bot        │<───>│  RAG Chain              │
│  (Telegram)     │     │  + perfil SQLite     │     │  Groq / Llama 3.3 70B   │
└─────────────────┘     └──────────────────────┘     │  guardrail + threshold  │
                                                      │  memória 5 turnos       │
                                                      │  data atual no contexto │
                                                      └─────────────────────────┘
```

O JobQueue dispara o ETL 2× ao dia (07h e 19h, horário da Bahia), reindexando as publicações dos últimos 30 dias e notificando usuários conforme seus interesses.

---

## Funcionalidades

- [x] Raspagem automatizada do DOE-BA via API do DOOL (`/apifront/portal/...`)
- [x] Filtro por palavras-chave de concurso público (edital de abertura, nomeação, homologação, REDA, PSS...)
- [x] Chunking hierárquico: chunks pequenos para busca precisa, chunks grandes para resposta rica
- [x] Embeddings locais — zero custo, zero rate limit
- [x] LLM via Groq — free tier de 14.400 req/dia com hardware dedicado
- [x] Guardrail temático — recusa perguntas fora do escopo de concursos públicos baianos
- [x] Similarity threshold — não chama o LLM quando não há documentos relevantes
- [x] Memória de conversa por usuário (janela deslizante de 5 turnos)
- [x] Consciência temporal — data atual injetada no prompt para referenciar "esta semana", "recente"
- [x] Perfil de interesses por usuário com notificação diária ou por novidade
- [x] ETL + notificações agendados 07h/19h via JobQueue
- [ ] Expansão para SAEB, TJBA, Prefeitura de Salvador
- [ ] Comando `/buscar <termo>` para consulta direta ao índice

---

## Comandos do bot

| Comando | Descrição |
|---|---|
| `/start` | Apresentação e instruções |
| `/interesse <termo>` | Adiciona um interesse (ex: `/interesse analista`) |
| `/remover <termo>` | Remove um interesse |
| `/perfil` | Lista interesses, frequência e publicações já vistas |
| `/frequencia diario` | Recebe resumo todo dia às 07h |
| `/frequencia novidades` | Recebe aviso só quando sair algo novo |
| `/vagas` | Busca publicações recentes pelos seus interesses |
| _(mensagem livre)_ | Pergunta em linguagem natural ao RAG |

---

## Configuração

### 1. Copie e preencha o `.env`

```bash
cp .env.example .env
```

```env
GROQ_API_KEY=sua_chave_groq
TELEGRAM_TOKEN=token_do_botfather

# Opcionais
LANCEDB_PATH=./db
TABLE_NAME=doe_ba
DOOL_SESSION_COOKIE=valor_do_cookie_CAKEPHP
DOOL_SESSION_COOKIE2=valor_do_cookiesession1
```

- **Groq API Key:** [console.groq.com](https://console.groq.com) — conta gratuita, sem cartão
- **Telegram Token:** crie um bot no [@BotFather](https://t.me/BotFather)
- **Cookies do DOOL:** opcionais; melhoram acesso a edições restritas

### 2. Instale as dependências

```bash
pip install -r requirements.txt
```

### 3. Indexe a base vetorial

```bash
python -m src.etl.pipeline
```

Na primeira execução o modelo de embedding (~90 MB) é baixado automaticamente. As próximas execuções reutilizam o cache local.

### 4. Suba o bot

```bash
python main.py
```

O bot inicia em modo `polling` e agenda o ETL automaticamente. Procure o nome do bot no Telegram e comece a conversar.

---

## Exemplos de perguntas

- "Quais órgãos publicaram editais de concurso esta semana?"
- "Tem alguma nomeação recente na EMBASA?"
- "Houve retificação de edital da Secretaria de Educação?"
- "Quais concursos tiveram homologação publicada nos últimos dias?"

---

## Estrutura do projeto

```
concurseiro-news/
├── .env.example
├── requirements.txt
├── main.py                   # entrypoint — carrega chain e inicia o bot
└── src/
    ├── config.py             # pydantic-settings, lê o .env
    ├── etl/
    │   ├── doe_ba.py         # scraper DOE-BA (httpx + BS4)
    │   └── pipeline.py       # ETL → ParentDocumentRetriever → LanceDB
    ├── rag/
    │   ├── retriever.py      # ParentDocumentRetriever (child/parent chunks)
    │   └── chain.py          # RAG chain: guardrail, threshold, memória, data
    ├── bot/
    │   ├── telegram_bot.py   # handlers e agendamento JobQueue
    │   └── notifier.py       # ETL + push de notificações por interesse
    └── db/
        └── users.py          # perfis de usuário (SQLite)
```

---

## Roadmap

### v1.1
- Scraping do SAEB (Superintendência de Administração do Estado da Bahia)
- Scraping do TJBA (Tribunal de Justiça da Bahia)
- Scraping da Prefeitura de Salvador (SEMGE)

### v1.2
- Comando `/buscar <termo>` para busca direta no índice
- Comando `/ultimos` para listar publicações recentes por categoria

### v2
- Interface admin (Streamlit) para monitorar métricas de uso
- Suporte a múltiplos estados brasileiros

---

## Autor

**Vinícius Abreu** — Desenvolvedor Python focado em automação e aplicações de IA.
Atualmente construindo soluções de IA no Tribunal de Justiça do Estado da Bahia.

- GitHub: [@AbreuVin](https://github.com/AbreuVin)
- LinkedIn: [viniciusabreu115](https://linkedin.com/in/viniciusabreu115)

---

## Licença

MIT
