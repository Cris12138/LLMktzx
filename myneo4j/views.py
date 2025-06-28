from django.shortcuts import render, HttpResponse
import os
import json
import requests
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.conf import settings
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from .models import MyNode, MyWenda
from .pyneo_utils import get_all_relation
import logging

logger = logging.getLogger(__name__)

# DeepSeek API 配置（替换原来的 Spark 配置）
DEEPSEEK_API_KEY = "4cb99985-8f4d-4a3e-a300-c89620fab2ae"  # 这个是豆包的
DEEPSEEK_API_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

# 字体配置 (OTF格式)
FONT_PATH = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'fs2312.ttf')


def get_spark_response(prompt):  # 保持函数名不变，但内部改用 DeepSeek
    """调用 DeepSeek API 替代原来的 Spark API"""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "doubao-1.5-vision-lite-250315",  # 豆包版本
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5,
        "max_tokens": 2048,
    }
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"DeepSeek API 错误: {e}")
        return "AI 服务暂时不可用"


def init_pdf_fonts():
    """初始化PDF字体(项目启动时调用)"""
    try:
        if not os.path.exists(FONT_PATH):
            raise FileNotFoundError(f"字体文件不存在: {FONT_PATH}")
        pdfmetrics.registerFont(TTFont('fs2312', FONT_PATH))
        logger.info("PDF字体初始化成功")
    except Exception as e:
        logger.error(f"字体注册失败: {str(e)}")


# 初始化字体 (可以在apps.py或项目启动时调用)
init_pdf_fonts()


@login_required
def index(request):
    try:
        start = request.GET.get("start", "")
        relation = request.GET.get("relation", "")
        end = request.GET.get("end", "")
        all_datas = get_all_relation(start, relation, end)

        context = {
            'links': json.dumps(all_datas["links"]),
            'datas': json.dumps(all_datas["datas"]),
            'categories': json.dumps(all_datas["categories"]),
            'legend_data': json.dumps(all_datas["legend_data"])
        }
        return render(request, "index.html", context)
    except Exception as e:
        print(f"首页错误: {e}")
        return render(request, "index.html")


@login_required
def wenda(request):
    try:
        user = request.user
        if request.method == "GET":
            key = request.GET.get("key", "")
            clean = request.GET.get("clean", "")

            if clean:
                MyWenda.objects.filter(user=user).delete()

            if key.lower() in {'你好', '您好', 'hello', '你好！'}:
                daan = '你 好 👋 ！ 我 是 您 的 医 疗 小 助 手 ！ 很 高 兴 见 到 你 ， 欢 迎 问 我 任 何 有 关 疾 病 的 问 题 。'
            elif key:
                res_classify = settings.CLASSIFIER.classify(key)
                final_answers = settings.SEACHER.search_main(
                    settings.PARSER.parser_main(res_classify)) if res_classify else []
                daan = '\n'.join(final_answers) if final_answers else settings.ALI.get_chatglm_response(key)

            if daan:
                MyWenda.objects.filter(user=user, question=key, anster=daan).delete()
                MyWenda.objects.create(user=user, question=key, anster=daan)

            context = {
                'all_wendas': MyWenda.objects.filter(user=user).order_by("id")[:10],
                'daan': daan if 'daan' in locals() else ''
            }
            return render(request, "wenda.html", context)
    except Exception as e:
        print(f"问答错误: {e}")
        return render(request, "wenda.html")


@login_required
def health_assessment(request):
    try:
        if request.method == 'POST':
            health_data = {
                'height': request.POST.get('height'),
                'weight': request.POST.get('weight'),
                'age': request.POST.get('age'),
                'blood_pressure': request.POST.get('blood-pressure'),
                'blood_sugar': request.POST.get('blood-sugar'),
                'blood_lipid': request.POST.get('blood-lipid'),
                'sleep_status': request.POST.get('sleep-status'),
                'sleep_quality': request.POST.get('sleep-quality')
            }

            prompt = f"""作为专业健康顾问，请分析以下用户数据：
            - 身高: {health_data['height']}cm
            - 体重: {health_data['weight']}kg
            - 年龄: {health_data['age']}岁
            - 血压: {health_data['blood_pressure']}mmHg
            - 血糖: {health_data['blood_sugar']}mmol/L
            - 血脂: {health_data['blood_lipid']}mmol/L
            - 睡眠: {health_data['sleep_status']}（质量: {health_data['sleep_quality']}）

            请用中文提供：
            1. 关键健康指标分析
            2. 潜在风险预警
            3. 具体改善建议
            4. 推荐的健康管理方案
            5. 推荐使用的药品"""

            model_suggestion = get_spark_response(prompt)

            pdf_filename = f"health_report_{request.user.username}_{datetime.now().strftime('%Y%m%d')}.pdf"
            pdf_path = os.path.join(settings.MEDIA_ROOT, pdf_filename)

            c = canvas.Canvas(pdf_path, pagesize=A4)
            c.setFont("fs2312", 16)
            c.drawString(50, 800, "个人健康测评报告")

            c.setFont("fs2312", 12)
            y_pos = 750
            c.drawString(50, y_pos, f"评估时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

            # 添加健康数据
            y_pos -= 30
            for k, v in health_data.items():
                if v:
                    c.drawString(50, y_pos, f"- {k.replace('_', ' ').title()}: {v}")
                    y_pos -= 20

            # 文本换行处理函数
            def wrap_text(text, canvas, max_width, font_name, font_size):
                words = []
                current_line = []
                current_width = 0
                for char in text:
                    char_width = canvas.stringWidth(char, font_name, font_size)
                    if current_width + char_width > max_width:
                        words.append(''.join(current_line))
                        current_line = [char]
                        current_width = char_width
                    else:
                        current_line.append(char)
                        current_width += char_width
                if current_line:
                    words.append(''.join(current_line))
                return words

            # 绘制AI建议
            y_pos -= 30
            c.setFont("fs2312", 14)
            c.drawString(50, y_pos, "AI健康建议:")

            y_pos -= 30
            c.setFont("fs2312", 12)
            max_width = 500  # A4页面宽度减去边距
            line_height = 20

            for paragraph in model_suggestion.split('\n'):
                if paragraph.strip():
                    lines = wrap_text(paragraph, c, max_width, "fs2312", 12)
                    for line in lines:
                        if y_pos < 50:
                            c.showPage()
                            y_pos = 800
                            c.setFont("fs2312", 12)
                        c.drawString(50, y_pos, line)
                        y_pos -= line_height
                    y_pos -= 5  # 段落间距

            c.save()

            return render(request, 'health_assessment.html', {
                'assessment_result': "您的健康评估已完成",
                'model_suggestion': model_suggestion,
                'pdf_url': f"{settings.MEDIA_URL}{pdf_filename}"
            })

        return render(request, 'health_assessment.html')

    except Exception as e:
        print(f"健康评估错误: {e}")
        return render(request, 'health_assessment.html', {
            'error': f"系统繁忙，请稍后重试（错误: {str(e)}）"
        })