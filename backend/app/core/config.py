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
    # Application environment: "development" (default) or "production". In
    # production the development-only demo-admin fallback password is disabled.
    app_env: str = "development"
    # Demo admin bootstrap. BOOTSTRAP_ADMIN_PASSWORD is REQUIRED for
    # production (APP_ENV=production). When unset outside production, the
    # bootstrap module falls back to a clearly-labeled DEVELOPMENT-ONLY
    # password; never treat that fallback as a real credential.
    bootstrap_admin_email: str = "admin@demo.com"
    bootstrap_admin_password: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
settings = Settings()
