from redis import Redis
from typing import Optional, Any
import json
from functools import wraps
import os
from dotenv import load_dotenv

load_dotenv()
class RedisCache:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'client'):
            self.client = Redis(
                host=os.getenv('REDIS_HOST'),
                port=6379,
                db=0,
                decode_responses=True,
                socket_timeout=10 
            )
            print("Redis client initialized", self.client)

    def set(self, key: str, data: dict, expire_time: int = 3600) -> None:
        """Store itinerary data with expiration time"""
        self.client.setex(
            key,
            expire_time,
            json.dumps(data)
        )

    def get(self, key: str) -> Optional[dict]:
        """Retrieve itinerary data"""
        data = self.client.get(key)
        return json.loads(data) if data else None

    def delete(self, key: str) -> None:
        """Delete itinerary data"""
        self.client.delete(key)
    
    def get_ttl(self, key: str) -> int:
        """Get remaining time to live for an itinerary in seconds"""
        return self.client.ttl(key)

    def debug_info(self, key: str = None) -> dict:
        """Get debug information about cache"""
        if key:
            return {
                'key': key,
                'exists': self.client.exists(key),
                'ttl': self.client.ttl(key),
                'type': self.client.type(key),
                'value': self.get(key)
            }