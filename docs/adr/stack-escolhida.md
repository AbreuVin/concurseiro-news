# ADR-0001: Stack Escolhida

**Data:** 2026-05-18
**Autor:** Vinícius Abreu

---

## Contexto

Bot de Telegram que responde perguntas sobre concursos públicos na Bahia usando o DOE-BA como fonte.
Arquitetura central: RAG com chunking hierárquico (ParentDocumentRetriever), vector store local e LLM via API.

Critérios de decisão: custo zero ou mínimo, stack Python simples, sem servidores externos.

---

## Decisões

### 1. Framework RAG: LangChain 1.x (LCEL)

**Decisão:** LangChain com LCEL + `langchain-classic` para `ParentDocumentRetriever`.

**Justificativa:**
- Ecossistema maduro, documentado, integração nativa com LanceDB e HuggingFace
- LCEL compõe o pipeline como chain legível (`retriever | prompt | llm | parser`)
- `langchain-classic` mantém componentes legados (`ParentDocumentRetriever`, `LocalFileStore`) compatíveis com LangChain 1.x

---

### 2. LLM: Llama 3.3 70B via Groq

**Decisão:** `llama-3.3-70b-versatile` via `langchain-groq`.

**Justificativa:**
- Free tier generoso: 14.400 requisições/dia, hardware dedicado (sem rate limit compartilhado)
- Groq descartou a dependência do Google AI Studio, que exige billing ativo

---

### 3. Embeddings: HuggingFace local (`paraphrase-multilingual-MiniLM-L12-v2`)

**Decisão:** Embeddings rodando localmente via `sentence-transformers`.

**Justificativa:**
- Zero custo e zero rate limit — modelo carregado em memória, sem chamada de API
- Suporte nativo a português com boa qualidade para buscas semânticas

---

### 4. Base Vetorial: LanceDB embedded

**Decisão:** LanceDB com arquivos em `./db/`.

**Justificativa:**
- Roda embedded (sem servidor), persiste em disco
- Suporte nativo a metadados e modo `overwrite` para reindexação limpa

---

### 5. Chunking: ParentDocumentRetriever (hierárquico)

**Decisão:** Chunks filhos de 200 chars para busca vetorial; chunks pais de 1500 chars enviados ao LLM.

**Justificativa:**
- Precisão na recuperação (chunks pequenos) + contexto rico para o LLM (chunks grandes)
- Chunks pais persistidos em `./db/parent_docs/` via `LocalFileStore`

---

### 6. Interface: Telegram + `python-telegram-bot` v21+

**Decisão:** Telegram com JobQueue nativo para agendamento.

**Justificativa:**
- API gratuita e estável; público-alvo (concurseiros) já usa Telegram
- JobQueue integrado elimina a necessidade de APScheduler ou Celery

---

### 7. Scraping: httpx + BeautifulSoup4

**Decisão:** Requisições diretas à API não oficial do DOOL (`/apifront/portal/...`).

**Justificativa:**
- A API é pública (sem autenticação obrigatória), retorna JSON estruturado
- `httpx` + `bs4` suficiente — sem necessidade de browser headless

---

## Consequências

**Positivas:**
- Stack inteiramente Python, deploy em processo único
- Sem serviços externos pagos além do Telegram
- Embeddings locais: sem custo e sem rate limit

**Riscos:**
- LanceDB embedded não escala horizontalmente (sem impacto no escopo atual)
- Mudança na estrutura da API do DOOL quebra o scraper
- Groq free tier tem limite diário; pico de uso pode exigir migração de provedor
