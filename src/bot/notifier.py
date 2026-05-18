import asyncio
from datetime import date

from telegram import Bot
from telegram.constants import ParseMode

from src.db.users import get_all_users, mark_sent, FREQ_NOVIDADES
from src.etl.doe_ba import scrape_doe
from src.etl.pipeline import run_pipeline


def _matches(pub: dict, interests: list[str]) -> bool:
    text = f"{pub['title']} {pub['content']}".lower()
    return any(term.lower() in text for term in interests)


def _format_pub(pub: dict) -> str:
    title = pub["title"].replace("|", "·")
    snippet = pub["content"][:200].strip().replace("\n", " ")
    return f"*{title}*\n_{snippet}..._\n[Ver fonte]({pub['source_url']})"


async def run_etl_and_notify(bot: Bot) -> None:
    loop = asyncio.get_event_loop()

    print("[Notifier] Rodando ETL...")
    indexed = await loop.run_in_executor(None, lambda: run_pipeline(days=2))
    print(f"[Notifier] {indexed} documentos indexados.")

    publications = await loop.run_in_executor(None, lambda: scrape_doe(days=2))
    if not publications:
        print("[Notifier] Nenhuma publicacao encontrada.")
        return

    # Prioriza publicações de hoje; fallback para o que vier
    today = date.today().isoformat()
    todays_pubs = [p for p in publications if p["date"] == today] or publications

    users = get_all_users()
    notified = 0

    for user in users:
        if not user["interests"]:
            continue

        # filtra por interesse
        matches = [p for p in todays_pubs if _matches(p, user["interests"])]
        if not matches:
            continue

        # modo "novidades": remove o que já foi enviado
        if user["frequency"] == FREQ_NOVIDADES:
            matches = [p for p in matches if p["materia_id"] not in user["sent_ids"]]
            if not matches:
                continue

        header = (
            f"*Novidades do DOE-BA — {today}*\n"
            f"_{len(matches)} publicacao(oes) para seus interesses_\n\n"
        )
        body = "\n\n---\n\n".join(_format_pub(p) for p in matches[:5])
        if len(matches) > 5:
            body += f"\n\n_...e mais {len(matches) - 5}. Pergunte-me para detalhes._"

        try:
            await bot.send_message(
                chat_id=user["chat_id"],
                text=header + body,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
            )
            mark_sent(user["user_id"], [p["materia_id"] for p in matches])
            notified += 1
        except Exception as e:
            print(f"[Notifier] Erro ao notificar user {user['user_id']}: {e}")

    print(f"[Notifier] {notified} usuarios notificados.")
