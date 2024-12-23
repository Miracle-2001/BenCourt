import json
from .base_client import BaseClient
from .api_pool.api_pool import api_pool

class ProxyClient(BaseClient):
    def __init__(self, model_name):
        if model_name not in api_pool:
            raise ValueError("Invalid model name")
        self.query_function = api_pool[model_name]

    def send_request(
        self,
        messages,
        temperature=0.7,
        max_tokens=4096,
        *args,
        **kwargs,
    ):
        # Prepare the payload
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Call the appropriate function from api_pool
        try:
            result, usage = self.query_function(**payload)
            # print(f"Result: {result}")
            # print(f"Usage: {usage}")
            return result
        except Exception as e:
            print(f"Error during API call: {str(e)}")
            return ""
        