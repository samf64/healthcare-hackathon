from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Lab Requisition Reminder API"
    database_url: str = "sqlite:///./app.db"
    token_secret: str = "change-me-in-env"
    token_salt: str = "review-link"
    token_expiry_seconds: int = 60 * 60 * 24 * 7
    base_review_url: str = "http://localhost:8000/review"
    from_email: str = "noreply@example.com"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    requisition_pdf_path: str = ""
    template_library_dir: str = "template_library"
    generated_pdf_dir: str = "generated_forms"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

