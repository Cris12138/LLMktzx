from openai import OpenAI  # 需要先安装SDK: pip install openai
from . import settings
from .settings import DEEPSEEK_API_KEY


class GetDeepSeekResponse:
    def __init__(self):
        # 初始化DeepSeek客户端
        self.client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

    def get_response(self, prompt):
        # 调用DeepSeek API
        response = self.client.chat.completions.create(
            model="deepseek-chat",  # DeepSeek模型
            messages=[
                {"role": "system", "content": "你以简明扼要著称，所有回答都用最精炼的语言表达"},
                {"role": "user", "content": f"【请用1-2句话回答】{prompt}"},  # 双重提示
            ],
            temperature=0.3,  # 降低随机性
            max_tokens=150,  # 限制最大长度
            stream=False,
        )
        return response.choices[0].message.content