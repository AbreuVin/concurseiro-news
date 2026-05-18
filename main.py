from src.rag.chain import build_rag_chain
from src.bot.telegram_bot import create_app


def main() -> None:
    print("[Bot] Carregando RAG chain...")
    chain = build_rag_chain()

    app = create_app(chain)
    print("[Bot] Iniciando polling (ETL agendado 07h/19h America/Bahia)...")
    app.run_polling()


if __name__ == "__main__":
    main()
