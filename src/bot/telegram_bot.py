from datetime import time
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode
from langchain_core.runnables import Runnable

from src.config import settings
from src.db.users import (
    register_user, add_interest, remove_interest, get_interests,
    set_frequency, get_frequency, FREQ_DIARIO, FREQ_NOVIDADES, get_sent_ids,
    check_and_increment_daily,
)
from src.bot.notifier import run_etl_and_notify

_TZ = ZoneInfo("America/Bahia")
MAX_HISTORY_TURNS = 5
DAILY_QUESTION_LIMIT = 20


# ── Comandos ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    register_user(user.id, update.effective_chat.id)
    await update.message.reply_text(
        f"Ola, {user.first_name}! Sou o Concurseiro News Bot.\n\n"
        "Monitoro o Diario Oficial da Bahia e aviso quando sair algo "
        "nos cargos e areas que voce acompanha.\n\n"
        "Comandos:\n"
        "/interesse <termo>  — adiciona interesse (ex: analista, saude, professor)\n"
        "/remover <termo>    — remove um interesse\n"
        "/perfil             — seus interesses e configuracoes\n"
        "/frequencia         — define quando receber avisos (diario ou novidades)\n"
        "/vagas              — busca publicacoes recentes pelos seus interesses\n\n"
        "Ou me faca uma pergunta diretamente!\n\n"
        "Por padrao voce recebera um resumo todo dia as 07h. "
        "Use /frequencia novidades para receber so quando sair algo novo."
    )


async def cmd_interesse(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    register_user(user.id, update.effective_chat.id)

    termo = " ".join(context.args).strip() if context.args else ""
    if not termo:
        await update.message.reply_text(
            "Informe o cargo ou area. Exemplo:\n/interesse analista de sistemas"
        )
        return

    interests = add_interest(user.id, termo)
    lista = "\n".join(f"• {i}" for i in interests)
    await update.message.reply_text(
        f'Interesse "{termo}" adicionado!\n\nSeus interesses:\n{lista}'
    )


async def cmd_remover(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    termo = " ".join(context.args).strip() if context.args else ""
    if not termo:
        await update.message.reply_text("Informe o termo a remover. Exemplo:\n/remover professor")
        return

    interests = remove_interest(user.id, termo)
    if interests:
        lista = "\n".join(f"• {i}" for i in interests)
        await update.message.reply_text(f'Removido. Interesses restantes:\n{lista}')
    else:
        await update.message.reply_text("Nenhum interesse cadastrado.")


async def cmd_perfil(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    register_user(user.id, update.effective_chat.id)

    interests = get_interests(user.id)
    frequency = get_frequency(user.id)
    sent_count = len(get_sent_ids(user.id))

    freq_label = {
        FREQ_DIARIO:    "Diario — resumo todo dia as 07h",
        FREQ_NOVIDADES: "So novidades — avisa apenas quando sair algo novo",
    }.get(frequency, frequency)

    if not interests:
        await update.message.reply_text(
            "*Seu perfil*\n\n"
            "Interesses: nenhum cadastrado\n"
            f"Frequencia: {freq_label}\n\n"
            "Use /interesse <termo> para comecar a receber avisos.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    lista = "\n".join(f"• {i}" for i in interests)
    await update.message.reply_text(
        f"*Seu perfil*\n\n"
        f"*Interesses:*\n{lista}\n\n"
        f"*Frequencia:* {freq_label}\n"
        f"*Publicacoes ja vistas:* {sent_count}",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_frequencia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    register_user(user.id, update.effective_chat.id)

    opcao = context.args[0].lower() if context.args else ""
    if opcao not in {FREQ_DIARIO, FREQ_NOVIDADES}:
        freq_atual = get_frequency(user.id)
        await update.message.reply_text(
            f"Frequencia atual: *{freq_atual}*\n\n"
            "Opcoes:\n"
            "/frequencia diario — recebe digest toda manha as 07h\n"
            "/frequencia novidades — recebe so quando sair algo novo",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    set_frequency(user.id, opcao)
    descricao = {
        FREQ_DIARIO:    "voce recebera o digest toda manha as 07h.",
        FREQ_NOVIDADES: "voce so sera avisado quando sair uma publicacao nova.",
    }
    await update.message.reply_text(
        f"Frequencia atualizada: *{opcao}*\nAgora {descricao[opcao]}",
        parse_mode=ParseMode.MARKDOWN,
    )


# ── Handler de mensagem (RAG) ─────────────────────────────────────────────────

def _format_history(history: list[tuple[str, str]]) -> str:
    if not history:
        return ""
    lines = ["\nHistorico da conversa:"]
    for human, ai in history:
        lines.append(f"Usuario: {human}")
        lines.append(f"Assistente: {ai}")
    return "\n".join(lines) + "\n"


async def _invoke_chain(
    chain: Runnable,
    question: str,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
) -> str:
    if not check_and_increment_daily(user_id, DAILY_QUESTION_LIMIT):
        return (
            f"Você atingiu o limite de {DAILY_QUESTION_LIMIT} perguntas por dia. "
            "Volte amanhã!"
        )

    history: list[tuple[str, str]] = context.user_data.setdefault("history", [])
    try:
        answer = await chain.ainvoke({
            "question": question,
            "history": _format_history(history),
        })
    except Exception as e:
        answer = f"Erro ao consultar a base. Tente novamente. ({e})"

    history.append((question, answer))
    if len(history) > MAX_HISTORY_TURNS:
        history.pop(0)

    return answer


def make_message_handler(chain: Runnable):
    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text("Buscando no Diario Oficial...")
        answer = await _invoke_chain(chain, update.message.text, context, update.effective_user.id)
        await update.message.reply_text(answer)

    return handle_message


def make_vagas_handler(chain: Runnable):
    async def cmd_vagas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        interests = get_interests(update.effective_user.id)
        if not interests:
            await update.message.reply_text(
                "Voce nao tem interesses cadastrados. Use /interesse <termo> primeiro."
            )
            return

        termos = ", ".join(interests)
        await update.message.reply_text(f"Buscando publicacoes recentes para: {termos}...")

        question = f"Quais as publicacoes mais recentes do DOE-BA sobre {termos}?"
        answer = await _invoke_chain(chain, question, context, update.effective_user.id)
        await update.message.reply_text(answer)

    return cmd_vagas


# ── Job agendado (ETL + notificações) ────────────────────────────────────────

async def _job_etl_notify(context: ContextTypes.DEFAULT_TYPE) -> None:
    await run_etl_and_notify(context.bot)


# ── Factory ───────────────────────────────────────────────────────────────────

def create_app(chain: Runnable) -> Application:
    app = Application.builder().token(settings.TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("interesse", cmd_interesse))
    app.add_handler(CommandHandler("remover", cmd_remover))
    app.add_handler(CommandHandler("perfil", cmd_perfil))
    app.add_handler(CommandHandler("frequencia", cmd_frequencia))
    app.add_handler(CommandHandler("vagas", make_vagas_handler(chain)))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, make_message_handler(chain)))

    jq = app.job_queue
    jq.run_daily(_job_etl_notify, time=time(7, 0, tzinfo=_TZ),  name="etl_07h")
    jq.run_daily(_job_etl_notify, time=time(19, 0, tzinfo=_TZ), name="etl_19h")

    return app
