# Concurseiro News Bot

Bot de Telegram com IA que responde dúvidas sobre concursos públicos abertos na Bahia, usando como fonte oficial publicações do Diário Oficial do Estado (DOE-BA).

O bot faz ETL automatizado do DOE, indexa as publicações numa base vetorial, e responde perguntas em linguagem natural via RAG (Retrieval-Augmented Generation).

---

## Stack

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.11+ |
| Framework de agente | [Agno](https://docs.agno.com) |
| Modelo LLM | Google Gemini 2.0 Flash |
| Base vetorial | LanceDB |
| Interface | Telegram Bot API (`python-telegram-bot`) |
| ETL | `httpx` + `BeautifulSoup` |
| Scheduler | APScheduler |

---

## Arquitetura

```
┌─────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│   DOE Bahia     │ ───> │  ETL (scraper)   │ ───> │  LanceDB         │
│   (site oficial)│      │  beautifulsoup   │      │  (vector store)  │
└─────────────────┘      └──────────────────┘      └────────┬─────────┘
                                                            │
                                                            │ retrieval
                                                            ▼
┌─────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│  Usuário        │ <──> │  Telegram Bot    │ <──> │  Agno Agent      │
│  (Telegram)     │      │  (handler)       │      │  + Gemini        │
└─────────────────┘      └──────────────────┘      └──────────────────┘
```

O scheduler roda o ETL 2x ao dia (07h e 19h), atualizando a base com as publicações mais recentes.

---

## Funcionalidades

- [x] Raspagem automatizada de publicações do DOE-BA com filtro por palavras-chave (concurso, edital, seleção)
- [x] Indexação vetorial com embeddings via Gemini
- [x] Agente Agno com RAG nativo e citação de fonte (data + órgão)
- [x] Bot Telegram com `/start` e respostas em linguagem natural
- [x] Scheduler interno para ETL periódico
- [ ] Expansão para SAEB, TJBA, Prefeitura de Salvador (v1.1)
- [ ] Comando `/buscar <termo>` com filtro específico (v1.2)
- [ ] Notificação proativa de novos editais em tópicos inscritos (v2)

---

## Uso

### Primeira execução — indexar a base

```bash
# Roda o ETL + indexação (só precisa uma vez para bootstrap)
python -m src.etl.pipeline
```

### Subir o bot

```bash
python main.py
```

O bot ficará em modo `polling`. Abra seu Telegram, procure pelo nome do bot que você criou no BotFather, e comece a conversar.

### Exemplos de perguntas

- "Tem concurso aberto para analista de sistemas?"
- "O que foi publicado essa semana sobre SEFAZ?"
- "Quais os últimos editais da Secretaria de Educação?"
- "Tem concurso com salário acima de R$ 5000?"

---

## Estrutura do projeto

```
concurseiro-news/
├── .env.example
├── requirements.txt
├── README.md
├── main.py                  # entrypoint (sobe bot + scheduler)
├── assets/
│   └── demo.gif
├── data/
│   ├── raw/                 # HTML/JSON bruto do scraping
│   └── processed/           # texto limpo e chunked
├── db/                      # LanceDB (ignorado pelo git)
└── src/
    ├── config.py
    ├── etl/
    │   ├── doe_ba.py
    │   └── pipeline.py
    ├── knowledge/
    │   └── base.py
    ├── agent/
    │   └── concurseiro.py
    ├── bot/
    │   └── telegram_bot.py
    └── scheduler.py
```
## Roadmap

### v1.1 (próximas 2 semanas)
- Scraping do SAEB (Superintendência de Administração do Estado da Bahia)
- Scraping do TJBA (Tribunal de Justiça)
- Scraping da Prefeitura de Salvador

### v1.2
- Comando `/buscar <termo>` para busca específica
- Comando `/ultimos` para ver publicações da semana
- Histórico de conversa (memória do agente por usuário)

### v2
- Notificação push quando novos editais forem publicados em áreas de interesse
- Interface admin (Streamlit) para monitorar métricas de uso

---

## Autor

**Vinícius Abreu** — Desenvolvedor Python focado em automação e aplicações de IA.
Atualmente construindo soluções de IA no Tribunal de Justiça do Estado da Bahia.

- GitHub: [@AbreuVin](https://github.com/AbreuVin)
- LinkedIn: [viniciusabreu115](https://linkedin.com/in/viniciusabreu115)

---

## Licença

MIT
