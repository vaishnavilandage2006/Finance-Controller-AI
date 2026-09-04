from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    database_url: str = "sqlite:///./finance_controller.db"
    secret_key: str = "change-me-in-development"
    jwt_secret: str = "change-me-jwt"
    ai_provider: str = "mock"
    ai_api_key: str | None = None
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"
    razorpay_mode: str = "test"
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None
    cors_origins: str = "http://localhost:5173"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
settings = Settings()
