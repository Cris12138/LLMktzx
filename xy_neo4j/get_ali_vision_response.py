import os
import base64
import logging
import mimetypes
from openai import OpenAI

logger = logging.getLogger(__name__)


class GetAliVisionResponse:
    def __init__(self, api_key=None):
        """
        初始化阿里云通义千问视觉模型客户端
        """
        self.api_key = api_key or 'sk-90150b755c654c4d9765798ef995c540'
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )

    def encode_image_to_base64(self, image_file):
        """
        将图片文件编码为base64字符串 - 修复版本
        """
        try:
            # 获取文件内容和MIME类型
            if hasattr(image_file, 'read'):
                # 如果是Django UploadedFile对象
                image_data = image_file.read()
                # 重置文件指针
                image_file.seek(0)

                # 获取MIME类型
                if hasattr(image_file, 'content_type'):
                    mime_type = image_file.content_type
                elif hasattr(image_file, 'name'):
                    mime_type, _ = mimetypes.guess_type(image_file.name)
                else:
                    mime_type = 'image/jpeg'  # 默认类型
            else:
                # 如果是文件路径
                with open(image_file, 'rb') as f:
                    image_data = f.read()
                mime_type, _ = mimetypes.guess_type(image_file)

            # 确保MIME类型有效
            if not mime_type or not mime_type.startswith('image/'):
                mime_type = 'image/jpeg'

            # 编码为base64
            base64_string = base64.b64encode(image_data).decode('utf-8')
            return f"data:{mime_type};base64,{base64_string}"

        except Exception as e:
            logger.error(f"图片编码失败: {e}")
            return None

    def get_medical_image_analysis(self, text_prompt, image_file=None, image_url=None):
        """
        获取医疗图像分析结果 - 增强错误处理
        """
        try:
            logger.info(f"开始图片分析，文本提示: {text_prompt[:50]}...")

            # 构建消息内容
            message_content = []

            # 添加图片
            if image_file:
                logger.info("正在编码图片...")
                image_data = self.encode_image_to_base64(image_file)
                if image_data:
                    message_content.append({
                        "type": "image_url",
                        "image_url": {"url": image_data}
                    })
                    logger.info("图片编码成功")
                else:
                    logger.error("图片编码失败")
                    return "**图片编码失败**\n\n无法处理上传的图片，请检查图片格式是否正确。"

            elif image_url:
                message_content.append({
                    "type": "image_url",
                    "image_url": {"url": image_url}
                })

            # 构建医疗专业的提示词
            medical_prompt = f"""你是一位专业的医疗AI助手，请仔细分析用户上传的图片。

用户问题：{text_prompt}

请按照以下要求进行分析：

## 📋 图片内容识别
- 详细描述图片中看到的内容
- 识别可能的伤势、症状或医疗相关信息

## 🔍 医疗专业分析
- 基于图片内容，提供初步的医疗评估
- 说明可能的原因和性质
- 评估严重程度（轻微/中等/严重）

## 💡 处理建议
- **立即措施**：需要立刻采取的处理方法
- **护理方法**：日常护理和注意事项
- **用药建议**：可能需要的药物（仅供参考）

## ⚠️ 重要提醒
- 明确指出是否需要立即就医
- 说明AI分析的局限性
- 强调不能替代专业医疗诊断

## 🏥 就医建议
- 什么情况下需要看医生
- 推荐的科室
- 需要准备的检查

请用温馨、专业的语调回答，使用Markdown格式让内容更易读。如果图片不清晰或无法识别医疗内容，请诚实说明。

**特别注意**：如果发现严重外伤、大量出血、骨折等紧急情况，请特别强调立即就医的重要性。"""

            message_content.append({
                "type": "text",
                "text": medical_prompt
            })

            logger.info("正在调用阿里云视觉API...")

            # 调用API
            completion = self.client.chat.completions.create(
                model="qwen-vl-plus",  # 使用视觉模型
                messages=[{
                    "role": "user",
                    "content": message_content
                }],
                temperature=0.3,  # 降低温度以获得更稳定的医疗建议
                max_tokens=2048
            )

            # 提取回复内容
            response_content = completion.choices[0].message.content
            logger.info("API调用成功，收到回复")

            # 添加免责声明
            disclaimer = "\n\n---\n\n**⚠️ 免责声明**\n\n本AI分析仅供参考，不能替代专业医疗诊断。如有疑问或症状加重，请及时就医咨询专业医生。"

            return response_content + disclaimer

        except Exception as e:
            logger.error(f"阿里云视觉API调用失败: {e}")
            logger.error(f"错误类型: {type(e).__name__}")
            logger.error(f"错误详情: {str(e)}")

            # 根据错误类型返回不同的错误信息
            if "authentication" in str(e).lower() or "api_key" in str(e).lower():
                return f"**API密钥错误**\n\n请检查阿里云API密钥是否正确配置。错误信息：{str(e)}"
            elif "network" in str(e).lower() or "timeout" in str(e).lower():
                return f"**网络连接错误**\n\n无法连接到阿里云服务，请检查网络连接。错误信息：{str(e)}"
            elif "model" in str(e).lower():
                return f"**模型错误**\n\n指定的AI模型不可用，请联系技术支持。错误信息：{str(e)}"
            else:
                return f"**图像分析失败**\n\n很抱歉，图像分析服务暂时不可用：{str(e)}\n\n请稍后重试或直接咨询医生。"

    def get_response_with_image(self, text_prompt, image_file):
        """
        兼容原有接口的图像分析方法
        """
        return self.get_medical_image_analysis(text_prompt, image_file=image_file)