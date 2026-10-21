from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    groq_api_key: str
    gemini_api_key: str = ""
    gee_project: str

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()