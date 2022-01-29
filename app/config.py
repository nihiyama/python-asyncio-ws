from pydantic import BaseSettings, AnyUrl

class Settings(BaseSettings):
    WS_SERVER_URL: AnyUrl = "ws://localhost:8000/events/ws"
    WS_SERVER_TOKEN_1: str = "changeme1"
    WS_SERVER_TOKEN_2: str = "changeme2"
    WS_SERVER_KEY: str = "changeme"


settings = Settings()
