import redis
import os
import json
from backend.utils.env_loader import load_env

load_env()

class RedisCacheService:
    def __init__(self, host: str, port: int, db: int):
        self.client = redis.StrictRedis(host=host, port=port, db=db)

    def set_json(self, key: str, data: dict, ex: int = None):
        """Sets a key with a JSON-serializable dictionary."""
        try:
            self.client.set(key, json.dumps(data), ex=ex)
        except Exception as e:
            print(f"Error setting Redis key {key}: {e}")

    def get_json(self, key: str) -> dict | None:
        """Gets and deserializes a JSON dictionary from a key."""
        try:
            data = self.client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            print(f"Error getting Redis key {key}: {e}")
            return None

    def set_flag(self, key: str, value: bool = True, ex: int = None):
        """Sets a simple flag (e.g., for readiness status)."""
        self.client.set(key, "true" if value else "false", ex=ex)

    def get_flag(self, key: str) -> bool:
        """Checks if a flag exists and is set to true."""
        return self.client.get(key) == b"true"

    def delete_keys(self, *keys: str):
        """Deletes one or more keys from the cache."""
        if keys:
            self.client.delete(*keys)

def get_redis_cache_service():
    """Dependency injection for the RedisCacheService."""
    return RedisCacheService(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=0,
    )