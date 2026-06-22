from pydantic_settings import BaseSettings


class Config(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./agent_harness.db"
    temporal_host: str = "localhost:7233"
    spire_socket_path: str = "/tmp/spire-agent/api.sock"
    opa_url: str = "http://localhost:8181"
    otel_service_name: str = "agent-harness"
    otel_endpoint: str = "http://localhost:4318"
    log_level: str = "INFO"

    model_config = {"env_prefix": "AH_", "env_file": ".env"}


config = Config()
