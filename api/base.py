from abc import ABC, abstractmethod
import requests
from typing import Dict, Any
from .config import API_CONFIGS

class BaseAPIClient(ABC):
    def __init__(self, api_name: str):
        self.config = API_CONFIGS.get(api_name, {})
        self.base_url = self.config.get('base_url')
        self.api_key = self.config.get('api_key')

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[Any, Any]:
        """
        Make HTTP request to the API
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        response = requests.request(
            method=method,
            url=url,
            headers={**headers, **kwargs.get('headers', {})},
            **{k: v for k, v in kwargs.items() if k != 'headers'}
        )
        
        response.raise_for_status()
        return response.json()

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the API is accessible"""
        pass