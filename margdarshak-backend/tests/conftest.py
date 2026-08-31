import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:test@localhost:5432/margdarshak_test",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("AGORA_APP_ID", "test-app-id")
os.environ.setdefault("AGORA_APP_CERTIFICATE", "test-app-certificate")
os.environ.setdefault("AGORA_AI_AGENT", "test-agent")
