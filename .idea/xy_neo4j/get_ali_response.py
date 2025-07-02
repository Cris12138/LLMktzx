import sqlite3
import requests
import os
from . import settings

class GetAliResponse:
    def __init__(self):
        import dashscope
        dashscope.api_key = settings.ALIBABA_API_KEY
        try:
            self.history = self.load_recent_wendas()
        except Exception as e:
            print(f"加载历史记录时出错: {e}")
            self.history = []

    def load_recent_wendas(self):
        """从数据库加载最近的问答对"""
        current_file_path = os.path.dirname(os.path.abspath(__file__))
        parent_directory_path = os.path.abspath(os.path.join(current_file_path, '..'))
        db_path = os.path.join(parent_directory_path, 'db.sqlite3')

        conn = None
        try:
            # 连接到数据库
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT question, anster FROM myneo4j_mywenda ORDER BY id DESC LIMIT 5")
            recent_wendas = cursor.fetchall()

            # 将查询结果转换为适合API的格式
            formatted_history = []
            for question, answer in recent_wendas:
                if question and answer:  # 确保问题和回答都不为空
                    formatted_history.append({"role": "user", "content": question})
                    formatted_history.append({"role": "assistant", "content": answer})

            return formatted_history

        except sqlite3.Error as e:
            print(f"数据库错误: {e}")
            return []  # 出错时返回空列表
        finally:
            if conn:
                conn.close()

    def get_response(self, prompt):
        """获取AI回复"""
        from dashscope import Generation
        self.history = self.load_recent_wendas()
        if not prompt:
            return "请输入有效的问题"

        # 添加用户问题到历史
        self.history.append({"role": "user", "content": prompt})

        try:
            response = Generation.call(
                model="qwen-max",
                messages=self.history + [
                    {"role": "system", "content": "你以简明扼要著称，根据我给你的最近的历史记录分析回答，用精炼的语言表达"}
                ],
                temperature=0.3,
                max_tokens=150,
                result_format='message'
            )

            # 检查响应结构
            if response and hasattr(response, 'output') and response.output and hasattr(response.output,
                                                                                        'choices') and response.output.choices:
                generated_message = response.output.choices[0].message['content']
                # 添加回复到历史
                self.history.append({"role": "assistant", "content": generated_message})
                return generated_message
            else:
                error_msg = "API返回了意外的响应结构"
                print(f"错误: {error_msg}, 响应: {response}")
                return f"抱歉，处理请求时遇到问题。请稍后再试。"

        except Exception as e:
            error_msg = str(e)
            print(f"API调用异常: {error_msg}")
            return f"抱歉，AI服务暂时不可用: {error_msg}"

    def save_qa_to_db(self, question, answer):
        """将问答对保存到数据库"""
        current_file_path = os.path.dirname(os.path.abspath(__file__))
        parent_directory_path = os.path.abspath(os.path.join(current_file_path, '..'))
        db_path = os.path.join(parent_directory_path, 'db.sqlite3')

        conn = None
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO myneo4j_mywenda (question, anster) VALUES (?, ?)",
                (question, answer)
            )
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"保存到数据库时出错: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()
