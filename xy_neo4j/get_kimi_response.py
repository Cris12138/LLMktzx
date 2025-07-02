from openai import OpenAI  # 暗月API与OpenAI兼容
from . import settings
import requests

# 备选方案：使用requests直接调用
class GetKimiResponse:
    def __init__(self):
        self.api_key = settings.ANYUE_API_KEY
        self.api_url = "https://api.moonshot.cn/v1/chat/completions"

    def get_response(self, prompt):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "moonshot-v1-8k",
            "messages": [
                {"role": "system", "content": "你是一名专业的医疗助手，回答要简明准确"},
                {"role": "user", "content": f"【请用2-3句话回答】{prompt}"}
            ],
            "temperature": 0.3,
            "max_tokens": 200
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data['choices'][0]['message']['content']

        except requests.exceptions.RequestException as e:
            print(f"API请求失败: {str(e)}")
            return "抱歉，服务暂时不可用，请稍后再试。"
