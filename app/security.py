from itsdangerous import URLSafeTimedSerializer

from app.config import settings


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.token_secret, salt=settings.token_salt)


def generate_review_token(user_id: int, reminder_stage: str) -> str:
    return _serializer().dumps({"user_id": user_id, "stage": reminder_stage})


def verify_review_token(token: str) -> dict:
    return _serializer().loads(token, max_age=settings.token_expiry_seconds)

