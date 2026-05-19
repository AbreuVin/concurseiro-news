from datetime import datetime
from zoneinfo import ZoneInfo

from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
from langchain_core.documents import Document

from src.config import settings
from src.rag.retriever import build_parent_retriever

LLM_MODEL = "llama-3.3-70b-versatile"
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
_TZ = ZoneInfo("America/Bahia")

_DAYS_PT = [
    "Segunda-feira", "Terça-feira", "Quarta-feira",
    "Quinta-feira", "Sexta-feira", "Sábado", "Domingo",
]
_MONTHS_PT = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def _today_pt() -> str:
    now = datetime.now(_TZ)
    return f"{_DAYS_PT[now.weekday()]}, {now.day} de {_MONTHS_PT[now.month - 1]} de {now.year}"


NO_RELEVANT_DOCS_MSG = (
    "Não encontrei publicações relevantes no Diário Oficial da Bahia "
    "para responder sua pergunta no período indexado.\n\n"
    "Tente reformular com termos como nome do órgão, cargo ou tipo de edital."
)

PROMPT_TEMPLATE = """Você é um assistente especializado exclusivamente em concursos públicos \
e editais do estado da Bahia, com base nas publicações do Diário Oficial (DOE-BA).

Data atual: {today}

REGRAS ESTRITAS:
- Responda apenas perguntas sobre concursos públicos, editais, vagas, inscrições, resultados \
ou assuntos diretamente relacionados ao serviço público estadual da Bahia.
- Se a pergunta não estiver relacionada a concursos públicos ou ao DOE-BA, recuse educadamente \
e lembre ao usuário qual é o seu escopo.
- Use APENAS os documentos fornecidos abaixo. Não invente informações.
- Se a informação não estiver nos documentos, diga que não encontrou nada publicado sobre isso \
no período indexado.
- Ao mencionar datas, use a data atual como referência para expressões como "esta semana" ou "recente".
- Sempre informe a data de publicação de cada documento ao citá-lo (ex: "publicado em 16 de maio de 2026").
{history}
Documentos relevantes do DOE-BA:
{context}

Pergunta: {question}

Resposta:"""


def _fmt_date(iso: str) -> str:
    try:
        from datetime import date as _date
        d = _date.fromisoformat(iso)
        return f"{d.day} de {_MONTHS_PT[d.month - 1]} de {d.year}"
    except Exception:
        return iso


def _format_docs(docs: list[Document]) -> str:
    parts = []
    for doc in docs:
        meta = doc.metadata
        date_str = _fmt_date(meta.get("date", ""))
        header = f"[Publicado em {date_str} | {meta.get('title', '')}]"
        parts.append(f"{header}\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)


def build_rag_chain():
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    retriever = build_parent_retriever(embeddings)

    llm = ChatGroq(
        model=LLM_MODEL,
        groq_api_key=settings.GROQ_API_KEY,
        temperature=0.2,
        max_tokens=4096,
    )

    prompt = PromptTemplate.from_template(PROMPT_TEMPLATE)
    llm_chain = prompt | llm | StrOutputParser()

    def _answer(inputs: dict | str) -> str:
        if isinstance(inputs, str):
            question, history_str = inputs, ""
        else:
            question = inputs["question"]
            history_str = inputs.get("history", "")

        try:
            docs = retriever.invoke(question)
        except Exception:
            return NO_RELEVANT_DOCS_MSG
        if not docs:
            return NO_RELEVANT_DOCS_MSG

        return llm_chain.invoke({
            "context": _format_docs(docs),
            "question": question,
            "history": history_str,
            "today": _today_pt(),
        })

    return RunnableLambda(_answer)
