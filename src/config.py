from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GROQ_API_KEY: str = ""
    TELEGRAM_TOKEN: str
    LANCEDB_PATH: str = "./db"
    TABLE_NAME: str = "doe_ba"
    DOOL_SESSION_COOKIE: str = ""
    DOOL_SESSION_COOKIE2: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
