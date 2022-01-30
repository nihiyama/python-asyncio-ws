from pydantic import BaseSettings, AnyUrl

class Settings(BaseSettings):
    WS_SERVER_URL: AnyUrl = "ws://localhost:8000/events/ws"
    CONCURRENT: int = 4


settings = Settings()
