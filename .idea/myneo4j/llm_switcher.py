# utils/llm_switcher.py
from django.conf import settings
import importlib
#切换大模型的选项，建设中....

class LLMSwitcher:
    @staticmethod
    def get_response(key, provider_name=None):
        """统一调用入口
        :param key: 用户问题
        :param provider_name: 指定模型名 (kimi/ali/zhipu/deepseek)
        :return: 模型返回结果
        """
        provider_name = provider_name or settings.DEFAULT_LLM

        # 获取模型配置
        module_name = settings.LLM_PROVIDERS.get(
            provider_name,
            settings.LLM_PROVIDERS[settings.DEFAULT_LLM]
        )

        try:
            # 动态调用 (等效于 settings.KIMI.get_response(key))
            module = getattr(settings, module_name)
            return module.get_response(key)
        except Exception as e:
            print(f'[LLM Switch] {provider_name} 调用失败: {str(e)}')
            # 降级到默认模型
            if provider_name != settings.DEFAULT_LLM:
                return LLMSwitcher.get_response(key)
            return f"【AI服务暂时不可用】"
