import re
from django.shortcuts import render, HttpResponse,get_object_or_404
import os
import time
import json
import csv
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import JsonResponse, StreamingHttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from accounts.models import UserProfile
from xy_neo4j.settings import DEEPSEEK_API_KEY, DOUBAO_API_KEY
from .models import MyNode, MyWenda, ForumPost, PostReply, PostLike
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import ForumPost
from .forms import PostForm  # 需要先创建表单
from django.shortcuts import render, HttpResponse
import requests
from django.contrib.auth.decorators import login_required
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from .models import MyNode, MyWenda
from .pyneo_utils import get_all_relation
import logging
import math
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from django.conf import settings
from django.db.models import Q
import markdown
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# API配置常量
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"  # 正确的 API 地址
DEEPSEEK_API_KEY = "sk-97a2aab4b1d64834b4805c90b21933ef"  # 替换成你的 API Key
DOUBAO_API_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
DOUBAO_API_KEY = settings.DOUBAO_API_KEY


# 字体配置
# 字体配置
FONT_PATH = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'fs2312.ttf')

logger = logging.getLogger(__name__)


def init_pdf_fonts():
    """初始化PDF字体(项目启动时调用)"""
    try:
        if not os.path.exists(FONT_PATH):
            raise FileNotFoundError(f"字体文件不存在: {FONT_PATH}")
        pdfmetrics.registerFont(TTFont('fs2312', FONT_PATH))
        logger.info("PDF字体初始化成功")
    except Exception as e:
        logger.error(f"字体注册失败: {str(e)}")


def draw_header_footer(canvas_obj, page_num):
    """绘制PDF的页眉和页脚"""
    # 页眉设置 - 红色双线
    canvas_obj.setStrokeColorRGB(1, 0, 0)
    canvas_obj.setLineWidth(1)
    canvas_obj.line(50, 820, A4[0] - 50, 820)  # 第一条线
    canvas_obj.line(50, 815, A4[0] - 50, 815)  # 第二条线

    # 页眉文字居中
    canvas_obj.setFont("fs2312", 12)
    header_text = "康途个人健康评估报告"
    text_width = canvas_obj.stringWidth(header_text, "fs2312", 12)
    canvas_obj.drawString((A4[0] - text_width) / 2, 825, header_text)

    # 页脚设置 - 红色双线
    canvas_obj.setStrokeColorRGB(1, 0, 0)
    canvas_obj.setLineWidth(1)
    canvas_obj.line(50, 50, A4[0] - 50, 50)  # 第一条线

    # 页脚内容
    canvas_obj.setFont("fs2312", 10)
    # 左侧祝福语
    canvas_obj.drawString(50, 40, "祝您身体健康")

    # 右侧页码
    page_text = f"第{page_num}页"
    text_width = canvas_obj.stringWidth(page_text, "fs2312", 10)
    canvas_obj.drawString(A4[0] - 50 - text_width, 40, page_text)


def wrap_text(text, canvas_obj, max_width, font_name, font_size):
    """
    改进的文本换行处理函数：
    1. 完全保留原始文本中的换行符
    2. 仅对超出页面宽度的行进行自动换行
    3. 正确处理中英文混合文本
    """
    result = []

    # 首先按原始换行符分割文本
    original_lines = text.split('\n')

    for original_line in original_lines:
        # 空行直接保留
        if not original_line.strip():
            result.append('')
            continue

        # 检查当前行是否超出页面宽度
        if canvas_obj.stringWidth(original_line, font_name, font_size) <= max_width:
            # 如果不超过宽度，直接保留原行
            result.append(original_line)
        else:
            # 需要手动换行处理
            current_line = []
            current_width = 0

            for char in original_line:
                char_width = canvas_obj.stringWidth(char, font_name, font_size)

                if current_width + char_width > max_width:
                    # 当前行已满，添加到结果中
                    result.append(''.join(current_line))
                    current_line = [char]
                    current_width = char_width
                else:
                    current_line.append(char)
                    current_width += char_width

            # 添加最后一行
            if current_line:
                result.append(''.join(current_line))

    return result


def draw_star(canvas_obj, center_x, center_y, size):
    """绘制星形"""
    path = canvas_obj.beginPath()
    for i in range(5):
        angle = 2 * math.pi * i / 5 - math.pi / 2
        outer_x = center_x + size * math.cos(angle)
        outer_y = center_y + size * math.sin(angle)
        if i == 0:
            path.moveTo(outer_x, outer_y)
        else:
            path.lineTo(outer_x, outer_y)
        inner_angle = angle + math.pi / 5
        inner_x = center_x + size * 0.4 * math.cos(inner_angle)
        inner_y = center_y + size * 0.4 * math.sin(inner_angle)
        path.lineTo(inner_x, inner_y)
    path.close()
    canvas_obj.drawPath(path, fill=1)


def generate_pdf(health_data, model_suggestion, user, filename):
    """生成健康评估PDF报告（完整版）

    参数:
        health_data: dict - 用户健康数据
        model_suggestion: str - AI生成的Markdown格式建议
        user: User - 用户对象
        filename: str - 输出PDF文件名

    返回:
        str - 生成的PDF文件路径
    """

    def clean_markdown_content(md_text):
        """清理和格式化Markdown内容"""
        # 将Markdown转换为HTML
        html_content = markdown.markdown(md_text, extensions=[
            'extra',  # 支持表格等扩展
            'nl2br'  # 将换行符转换为<br>
        ])
        soup = BeautifulSoup(html_content, 'html.parser')

        # 提取格式化文本，保留结构但更简洁
        formatted_text = []

        # 处理标题
        for i in range(1, 7):
            for header in soup.find_all(f'h{i}'):
                formatted_text.append(f"\n{header.get_text()}\n")

        # 处理段落
        for para in soup.find_all('p'):
            formatted_text.append(f"{para.get_text()}\n")

        # 处理列表
        for ul in soup.find_all('ul'):
            for li in ul.find_all('li'):
                formatted_text.append(f"  • {li.get_text()}\n")
            formatted_text.append("\n")

        for ol in soup.find_all('ol'):
            for i, li in enumerate(ol.find_all('li')):
                formatted_text.append(f"  {i + 1}. {li.get_text()}\n")
            formatted_text.append("\n")

        # 处理代码块
        for pre in soup.find_all('pre'):
            formatted_text.append(f"\n[代码示例]:\n{pre.get_text()}\n\n")

        # 处理引用
        for blockquote in soup.find_all('blockquote'):
            formatted_text.append(f"引用: {blockquote.get_text()}\n\n")

        # 合并并清理文本
        result = "".join(formatted_text)
        result = re.sub(r'\n{3,}', '\n\n', result).strip()

        return result if result else md_text

    # 处理AI建议内容
    formatted_text = clean_markdown_content(model_suggestion)

    pdf_path = os.path.join(settings.MEDIA_ROOT, filename)
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    c = canvas.Canvas(pdf_path, pagesize=A4)

    # 设置安全边距
    left_margin = 60
    right_margin = 60
    effective_width = A4[0] - left_margin - right_margin

    # 当前页码
    current_page = 1
    draw_header_footer(c, current_page)

    # 封面设计
    # 移除背景色块
    # 顶部装饰条
    c.setFillColorRGB(0.2, 0.4, 0.8)  # 深蓝色装饰条
    c.rect(0, A4[1] - 100, A4[0], 100, fill=1, stroke=0)

    # 底部装饰条
    c.setFillColorRGB(0.2, 0.4, 0.8)  # 深蓝色装饰条
    c.rect(0, 0, A4[0], 80, fill=1, stroke=0)

    # 中间装饰圆形
    c.setFillColorRGB(0.9, 0.9, 1.0)  # 浅蓝色圆形
    c.circle(A4[0] / 2, A4[1] / 2, 150, fill=1, stroke=0)
    c.setFillColorRGB(0.8, 0.8, 1.0)  # 稍深一点的蓝色圆形
    c.circle(A4[0] / 2, A4[1] / 2, 120, fill=1, stroke=0)

    # 文档标题
    c.setFillColorRGB(1, 1, 1)  # 白色文字
    c.setFont("fs2312", 28)
    title = "个人健康报告"
    title_width = c.stringWidth(title, "fs2312", 28)
    c.drawString((A4[0] - title_width) / 2, A4[1] - 60, title)

    # 用户信息
    c.setFillColorRGB(0.2, 0.2, 0.2)  # 深灰色文字
    c.setFont("fs2312", 16)
    user_text = f"用户: {user.username}"
    user_width = c.stringWidth(user_text, "fs2312", 16)
    c.drawString((A4[0] - user_width) / 2, A4[1] / 2, user_text)

    # 日期
    c.setFont("fs2312", 14)
    date_text = f"生成日期: {datetime.now().strftime('%Y年%m月%d日')}"
    date_width = c.stringWidth(date_text, "fs2312", 14)
    c.drawString((A4[0] - date_width) / 2, A4[1] / 2 - 30, date_text)

    # 底部公司信息
    c.setFillColorRGB(1, 1, 1)  # 白色文字
    c.setFont("fs2312", 12)
    company = "康途智选责任有限公司"
    company_width = c.stringWidth(company, "fs2312", 12)
    c.drawString((A4[0] - company_width) / 2, 40, company)

    # 添加新页 - 内容页
    c.showPage()
    current_page += 1
    draw_header_footer(c, current_page)

    # 内容页设计 - 健康数据部分
    y_pos = 780

    # 标题
    c.setFillColorRGB(0.2, 0.4, 0.8)  # 深蓝色标题
    c.setFont("fs2312", 18)
    section_title = "身体基本指标"
    c.drawString(left_margin, y_pos, section_title)
    # 装饰线
    c.setStrokeColorRGB(0.2, 0.4, 0.8)
    c.setLineWidth(2)
    c.line(left_margin, y_pos - 10, left_margin + 150, y_pos - 10)
    y_pos -= 40
    # 创建数据表格样式
    data_box_height = 30
    data_box_width = (effective_width - 20) / 2  # 两列布局，中间留间隔
    # 按照模板顺序显示数据（移除了sleep-status）
    template_order = [
        'height', 'weight', 'age',
        'sleep-quality',
        'blood-pressure', 'blood-sugar', 'blood-lipid'
    ]
    display_names = {
        'height': '身高',
        'weight': '体重',
        'age': '年龄',
        'sleep-quality': '睡眠质量',
        'blood-pressure': '血压',
        'blood-sugar': '血糖',
        'blood-lipid': '血脂'
    }
    display_units = {
        'height': ' cm',
        'weight': ' kg',
        'age': ' 岁',
        'blood-pressure': ' mmHg',
        'blood-sugar': ' mmol/L',
        'blood-lipid': ' mmol/L'
    }
    # 两列布局显示数据
    col = 0
    for k in template_order:
        if k in health_data and health_data[k]:
            # 计算位置
            box_x = left_margin + col * (data_box_width + 20)
            # 移除背景框绘制
            # 绘制标签
            c.setFillColorRGB(0.2, 0.4, 0.8)  # 深蓝色标签
            c.setFont("fs2312", 12)
            label = display_names.get(k, k)
            c.drawString(box_x + 10, y_pos, label)
            # 绘制数值
            c.setFillColorRGB(0.2, 0.2, 0.2)  # 深灰色数值
            c.setFont("fs2312", 14)
            value = f"{health_data[k]}{display_units.get(k, '')}"
            c.drawString(box_x + 10, y_pos - 20, value)
            # 更新列位置
            col = (col + 1) % 2
            # 如果换到第一列，则更新y位置
            if col == 0:
                y_pos -= data_box_height + 10
                # 检查是否需要新页
                if y_pos < 150:
                    c.showPage()
                    current_page += 1
                    draw_header_footer(c, current_page)
                    y_pos = 780

    # 如果最后一行只有一个数据，需要调整位置
    if col == 1:
        y_pos -= data_box_height + 10
        # ==============================================
        # 第二部分：近期身体状况（新增独立大项）
        # ==============================================
    y_pos -= 30  # 留出间距
    # 检查是否需要新页
    if y_pos < 200:
        c.showPage()
        current_page += 1
        draw_header_footer(c, current_page)
        y_pos = 780
    # 标题
    c.setFillColorRGB(0.2, 0.4, 0.8)  # 深蓝色标题
    c.setFont("fs2312", 18)
    section_title = "近期身体状况"
    c.drawString(left_margin, y_pos, section_title)
    # 装饰线
    c.setStrokeColorRGB(0.2, 0.4, 0.8)
    c.setLineWidth(2)
    c.line(left_margin, y_pos - 10, left_margin + 150, y_pos - 10)
    y_pos -= 40
    # 获取近期身体状况内容
    sleep_status = health_data.get('sleep-status', '')
    if sleep_status:
        # 移除背景框绘制
        # 使用wrap_text处理文本
        lines = wrap_text(sleep_status, c, effective_width, "fs2312", 12)
        line_height = 20

        # 绘制标题
        c.setFont("fs2312", 12)
        c.setFillColorRGB(0.2, 0.4, 0.8)  # 深蓝色
        c.drawString(left_margin, y_pos, "身体状况描述:")

        # 绘制内容
        c.setFillColorRGB(0.2, 0.2, 0.2)  # 深灰色文字
        y_pos -= 25  # 标题与内容之间的间距

        for i, line in enumerate(lines):
            if y_pos < 100:
                c.showPage()
                current_page += 1
                draw_header_footer(c, current_page)
                y_pos = 780
                # 移除在新页的背景绘制
                c.setFillColorRGB(0.2, 0.2, 0.2)

            c.drawString(left_margin, y_pos, line)
            y_pos -= line_height
    else:
        c.setFillColorRGB(0.5, 0.5, 0.5)  # 灰色文字
        c.setFont("fs2312", 12)
        c.drawString(left_margin, y_pos - 20, "暂无近期身体状况信息")
        y_pos -= 50  # 调整位置
    # ==============================================
    # 第三部分：AI健康评测分析
    # ==============================================
    y_pos -= 30  # 留出间距
    # 检查是否需要新页
    if y_pos < 200:
        c.showPage()
        current_page += 1
        draw_header_footer(c, current_page)
        y_pos = 780

    # 标题
    c.setFillColorRGB(0.2, 0.4, 0.8)  # 深蓝色标题
    c.setFont("fs2312", 18)
    section_title = "AI健康评测分析"
    c.drawString(left_margin, y_pos, section_title)

    # 装饰线
    c.setStrokeColorRGB(0.2, 0.4, 0.8)
    c.setLineWidth(2)
    c.line(left_margin, y_pos - 10, left_margin + 150, y_pos - 10)

    y_pos -= 40

    # 移除分析内容背景绘制

    # 使用处理后的Markdown内容
    lines = wrap_text(formatted_text, c, effective_width, "fs2312", 12)
    line_height = 20
    paragraph_spacing = 10

    c.setFont("fs2312", 12)
    c.setFillColorRGB(0.2, 0.2, 0.2)  # 深灰色文字

    for i, line in enumerate(lines):
        if y_pos < 100:
            c.showPage()
            current_page += 1
            draw_header_footer(c, current_page)
            y_pos = 780

            # 移除继续内容背景
            c.setFont("fs2312", 12)
            c.setFillColorRGB(0.2, 0.2, 0.2)

        if not line.strip():
            y_pos -= line_height
            continue

        # 检测是否为标题行（通过检查前后是否有空行）
        is_header = False
        if i > 0 and i < len(lines) - 1:
            if not lines[i - 1].strip() and line.strip():
                is_header = True

        if is_header:
            c.setFillColorRGB(0.2, 0.4, 0.8)  # 深蓝色标题
            c.setFont("fs2312", 14)
        else:
            c.setFillColorRGB(0.2, 0.2, 0.2)  # 深灰色文字
            c.setFont("fs2312", 12)

        # 列表项缩进处理
        indent = 0
        if line.startswith('  •'):
            indent = 10
            c.setFillColorRGB(0.2, 0.4, 0.8)  # 深蓝色项目符号
            c.drawString(left_margin, y_pos, '•')
            c.setFillColorRGB(0.2, 0.2, 0.2)  # 恢复文字颜色
            line = line[3:]  # 移除项目符号

        c.drawString(left_margin + indent, y_pos, line)
        y_pos -= line_height

        if is_header:
            c.setFillColorRGB(0.2, 0.4, 0.8)
            c.setLineWidth(1)
            c.line(left_margin, y_pos + 5, left_margin + 100, y_pos + 5)
            c.setFillColorRGB(0.2, 0.2, 0.2)

        if i < len(lines) - 1 and not lines[i + 1].strip():
            y_pos -= paragraph_spacing

    # 添加结束页
    c.showPage()
    current_page += 1
    draw_header_footer(c, current_page)

    # 结束页设计
    # 背景
    c.setFillColorRGB(0.95, 0.95, 1.0)  # 浅蓝色背景
    c.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)

    # 中心圆形
    c.setFillColorRGB(0.9, 0.9, 1.0)
    c.circle(A4[0] / 2, A4[1] / 2, 150, fill=1, stroke=0)

    # 感谢文字
    c.setFillColorRGB(0.2, 0.4, 0.8)
    c.setFont("fs2312", 24)
    thanks_text = "感谢您使用康途健康评估"
    thanks_width = c.stringWidth(thanks_text, "fs2312", 24)
    c.drawString((A4[0] - thanks_width) / 2, A4[1] / 2 + 20, thanks_text)

    c.setFont("fs2312", 18)
    ending_text = "祝您身体健康，生活愉快！"
    ending_width = c.stringWidth(ending_text, "fs2312", 18)
    c.drawString((A4[0] - ending_width) / 2, A4[1] / 2 - 20, ending_text)

    # 印章
    stamp_radius = 75
    stamp_x = A4[0] - 150
    stamp_y = 100

    c.setStrokeColorRGB(1, 0, 0)
    c.setLineWidth(2)
    c.circle(stamp_x + stamp_radius / 2, stamp_y + stamp_radius / 2, stamp_radius / 2)

    c.setFillColorRGB(1, 0, 0)
    draw_star(c, stamp_x + stamp_radius / 2, stamp_y + stamp_radius / 2, stamp_radius / 2 * 0.3)

    company_name = "康途智选责任有限公司"
    char_count = len(company_name)
    c.setFont("fs2312", 9)

    text_radius = stamp_radius / 2 * 0.85
    text_start_angle = math.pi - 0.1 * math.pi
    text_end_angle = 0.1 * math.pi
    text_angle_step = (text_start_angle - text_end_angle) / (char_count - 1)

    for i, char in enumerate(company_name):
        angle = text_start_angle - i * text_angle_step
        char_x = stamp_x + stamp_radius / 2 + text_radius * math.cos(angle)
        char_y = stamp_y + stamp_radius / 2 + text_radius * math.sin(angle)
        c.saveState()
        c.translate(char_x, char_y)
        text_angle = angle * 180 / math.pi
        if math.pi / 2 < angle <= math.pi:
            c.rotate(text_angle - 180)
        else:
            c.rotate(text_angle)
        char_width = c.stringWidth(char, "fs2312", 9)
        c.drawString(-char_width / 2, -5, char)
        c.restoreState()

    serial_number = datetime.now().strftime('%Y%m%d%H%M%S')
    char_count = len(serial_number)
    c.setFont("fs2312", 6)

    number_radius = stamp_radius / 2 * 0.85
    number_start_angle = math.pi + 0.15 * math.pi
    number_end_angle = 2 * math.pi - 0.15 * math.pi
    number_angle_step = (number_end_angle - number_start_angle) / (char_count - 1)

    for i, char in enumerate(serial_number):
        angle = number_start_angle + i * number_angle_step
        char_x = stamp_x + stamp_radius / 2 + number_radius * math.cos(angle)
        char_y = stamp_y + stamp_radius / 2 + number_radius * math.sin(angle)
        c.saveState()
        c.translate(char_x, char_y)
        text_angle = angle * 180 / math.pi
        if math.pi <= angle < 3 * math.pi / 2:
            c.rotate(text_angle - 180)
        else:
            c.rotate(text_angle)
        char_width = c.stringWidth(char, "fs2312", 6)
        c.drawString(-char_width / 2, -3, char)
        c.restoreState()

    c.save()

    return pdf_path


# 初始化字体（在实际项目中应在应用启动时调用）
init_pdf_fonts()


# API请求函数
def get_spark_response(prompt):
    """同步调用大模型API"""
    headers = {
        "Authorization": f"Bearer {DOUBAO_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "doubao-1.5-vision-lite-250315",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5,
        "max_tokens": 2048,
    }
    try:
        response = requests.post(DOUBAO_API_URL, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"API错误: {e}")
        return "AI 服务暂时不可用"


def stream_response(response_generator):
    """将生成器转换为流式HTTP响应"""
    return StreamingHttpResponse(
        (f"data: {chunk}\n\n" for chunk in response_generator),
        content_type='text/event-stream'
    )


def get_spark_response_stream(prompt):
    """流式调用API并格式化Markdown输出"""
    headers = {
        "Authorization": f"Bearer {DOUBAO_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "doubao-1.5-vision-lite-250315",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5,
        "max_tokens": 2048,
        "stream": True,
    }

    try:
        response = requests.post(
            DOUBAO_API_URL,
            headers=headers,
            json=data,
            stream=True,
            timeout=30,
        )
        response.raise_for_status()

        # 跟踪内容状态
        buffer = ""
        current_paragraph = ""
        is_first_chunk = True

        for line in response.iter_lines():
            if not line:
                continue

            line = line.decode('utf-8')
            if not line.startswith('data:'):
                continue

            data_str = line[5:].strip()
            if data_str == "[DONE]":
                break

            try:
                json_data = json.loads(data_str)
                content = json_data.get("choices", [{}])[0].get("delta", {}).get("content", "")

                if content:
                    # 处理第一个块
                    if is_first_chunk:
                        is_first_chunk = False
                        # 如果内容以#开头但没有空格，添加空格
                        if content.startswith('#') and not content.startswith('# '):
                            content = re.sub(r'^(#+)', r'\1 ', content)

                    # 检测并处理标题
                    if re.search(r'(?:^|\n)(#+)(?!\s)', content):
                        content = re.sub(r'(?:^|\n)(#+)(?!\s)', r'\n\n\1 ', content)

                    # 处理特殊标记 ###
                    if '###' in content and not re.search(r'#+\s', content):
                        content = content.replace('###', '\n\n### ')

                    buffer += content

                    # 发送处理后的内容
                    yield content

            except json.JSONDecodeError as e:
                logger.warning(f"JSON 解析失败: {data_str}")
                continue

    except Exception as e:
        logger.error(f"流式响应错误: {str(e)}")
        yield f"AI 服务错误: {str(e)}"


# 视图函数
@login_required
def health_assessment(request):
    """健康评估主视图"""
    try:
        if request.method == 'POST':
            # 收集健康数据
            health_data = {
                'height': request.POST.get('height'),
                'weight': request.POST.get('weight'),
                'age': request.POST.get('age'),
                'blood-pressure': request.POST.get('blood-pressure'),
                'blood-sugar': request.POST.get('blood-sugar'),
                'blood-lipid': request.POST.get('blood-lipid'),
                'sleep-status': request.POST.get('sleep-status'),
                'sleep-quality': request.POST.get('sleep-quality')
            }

            # 构建提示语
            prompt = f"""作为专业健康顾问，请分析以下用户数据：  
            - 身高: {health_data['height']}cm  
            - 体重: {health_data['weight']}kg  
            - 年龄: {health_data['age']}岁  
            - 血压: {health_data['blood-pressure']}mmHg  
            - 血糖: {health_data['blood-sugar']}mmol/L  
            - 血脂: {health_data['blood-lipid']}mmol/L  
            - 身体状况: {health_data['sleep-status']}（质量: {health_data['sleep-quality']}）  

            请用中文提供：  
            1. **关键健康指标分析**  
            2. **潜在风险预警**  
            3. **具体改善建议**  
            4. **推荐的健康管理方案**  
            5. **推荐使用的药品**  

            **重要格式要求**：
            - 使用Markdown格式回复
            - 每个标题后必须有两个换行符
            - 每个段落结束后必须有两个换行符
            - 列表项后必须有一个换行符
            - 确保标题与内容之间有明显的视觉分隔
            """

            # 检查是否需要流式输出
            stream = request.GET.get('stream', 'false').lower() == 'true'

            if stream:
                # 返回流式响应
                return stream_response(get_spark_response_stream(prompt))
            else:
                # 常规响应处理
                model_suggestion = get_spark_response(prompt)

                # 生成PDF文件
                pdf_filename = f"health_report_{request.user.username}_{datetime.now().strftime('%Y%m%d')}.pdf"
                generate_pdf(health_data, model_suggestion, request.user, pdf_filename)

                # 渲染页面
                return render(request, 'health_assessment.html', {
                    'assessment_result': "您的健康评估已完成",
                    'model_suggestion': model_suggestion,
                    'pdf_url': f"{settings.MEDIA_URL}{pdf_filename}"
                })

        # GET请求时渲染空表单
        return render(request, 'health_assessment.html')

    except Exception as e:
        logger.exception("健康评估错误")
        return render(request, 'health_assessment.html', {
            'error': f"系统繁忙，请稍后重试（错误: {str(e)}）"
        })


@login_required
def generate_health_report_pdf(request):
    """生成健康报告PDF文件"""
    try:
        if request.method == 'POST':
            # 从POST数据中获取健康数据和模型建议
            health_data = json.loads(request.POST.get('health_data', '{}'))
            model_suggestion = request.POST.get('model_suggestion', '')

            # 生成PDF文件
            pdf_filename = f"health_report_{request.user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            generate_pdf(health_data, model_suggestion, request.user, pdf_filename)

            # 返回PDF URL
            return JsonResponse({
                'success': True,
                'pdf_url': f"{settings.MEDIA_URL}{pdf_filename}"
            })

    except Exception as e:
        logger.exception("PDF生成错误")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

# 初始化字体 (可以在apps.py或项目启动时调用)
init_pdf_fonts()

@login_required
def index(request):
    try:
        start = request.GET.get("start", "")
        relation = request.GET.get("relation", "")
        end = request.GET.get("end", "")
        all_datas = get_all_relation(start, relation, end)
        links = json.dumps(all_datas["links"])
        datas = json.dumps(all_datas["datas"])
        categories = json.dumps(all_datas["categories"])
        legend_data = json.dumps(all_datas["legend_data"])

        print(categories)
        print(legend_data)
    except Exception as e:
        print(e)
    return render(request, "index.html", locals())


@login_required
def wenda(request):
    try:
        user = request.user

        if request.method == "GET":
            key = request.GET.get("key", "")
            clean = request.GET.get("clean", "")
            if clean:
                all_wendas111 = MyWenda.objects.filter(user=user).order_by("id")
                print(all_wendas111)
                for js in all_wendas111:
                    js.delete()
            daan = ''
            if key.lower() in {'你好', '您好', 'hello', '你好！'}:
                daan = '你 好 👋 ！ 我 是 您 的 医 疗 小 助 手 ！ 很 高 兴 见 到 你 ， 欢 迎 问 我 任 何 有 关 疾 病 的 问 题 。'
            elif key:
                res_classify = settings.CLASSIFIER.classify(key)
                final_answers = []

                if res_classify:
                    res_sql = settings.PARSER.parser_main(res_classify)
                    final_answers = settings.SEACHER.search_main(res_sql)

                daan = '\n'.join(
                    final_answers if final_answers
                    else settings.ALI.get_response(key)
                )

            if daan:
                wenda = MyWenda.objects.filter(user=user, question=key, anster=daan)
                if len(wenda) > 0:
                    for w in wenda:
                        w.delete()
                wenda = MyWenda()
                wenda.user = user
                wenda.question = key
                wenda.anster = daan
                wenda.save()
            all_wendas = MyWenda.objects.filter(user=user).order_by("id")[:50]
            return render(request, "wenda.html", locals())
    except Exception as e:
        print(e)
        return render(request, "wenda.html", locals())


@login_required
@require_POST
def toggle_like(request, post_id):
    """点赞/取消点赞视图"""
    post = get_object_or_404(ForumPost, id=post_id)
    user = request.user

    # 检查是否已点赞
    like, created = PostLike.objects.get_or_create(
        post=post,
        user=user
    )

    if not created:
        like.delete()
        liked = False
    else:
        liked = True

    # 返回JSON响应
    return JsonResponse({
        'liked': liked,
        'likes_count': post.likes.count()
    })
# 修改现有的forum视图函数
# 修改现有的forum视图函数
def forum(request):
    # 获取搜索关键词
    search_query = request.GET.get('q', '')

    # 构建查询条件
    if search_query:
        post_list = ForumPost.objects.filter(
            Q(title__icontains=search_query) |
            Q(content__icontains=search_query)
        ).order_by('-created_at')
    else:
        post_list = ForumPost.objects.all().order_by('-created_at')

    # 保持原有优化查询
    post_list = post_list.select_related('author').prefetch_related('replies', 'likes')

    # 分页处理（每页10条）
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    posts = paginator.get_page(page_number)

    # 获取点赞信息
    liked_posts = set()
    if request.user.is_authenticated:
        liked_posts = set(PostLike.objects.filter(
            user=request.user,
            post__in=posts.object_list
        ).values_list('post_id', flat=True))

    return render(request, 'forum.html', {
        'posts': posts,
        'liked_posts': liked_posts,
        'search_query': search_query  # 传递搜索词到模板
    })

@login_required
def create_post(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        if title and content:
            ForumPost.objects.create(
                title=title,
                content=content,
                author=request.user
            )
            return redirect('myneo4j:forum')
    return render(request, 'create_post.html')


def post_detail(request, post_id):
    post = get_object_or_404(
        ForumPost.objects.select_related('author')
                       .prefetch_related('replies__author', 'likes'),
        id=post_id
    )
    post.views += 1
    post.save()

    # 检查当前用户是否点赞过
    is_liked = False
    if request.user.is_authenticated:
        is_liked = PostLike.objects.filter(
            post=post,
            user=request.user
        ).exists()

    if request.method == 'POST' and request.user.is_authenticated:
        content = request.POST.get('content')
        if content:
            PostReply.objects.create(
                post=post,
                author=request.user,
                content=content
            )
            return redirect('myneo4j:post_detail', post_id=post.id)

    return render(request, 'post_detail.html', {
        'post': post,
        'is_liked': is_liked,
        'likes_count': post.likes.count()  # 确保传递点赞总数
    })

def user_posts(request, user_id):
    user = get_object_or_404(UserProfile, id=user_id)
    posts = ForumPost.objects.filter(author=user).order_by('-created_at')
    return render(request, 'user_posts.html', {'user': user, 'posts': posts})

def user_replies(request, user_id):
    user = get_object_or_404(UserProfile, id=user_id)
    replies = PostReply.objects.filter(author=user).order_by('-created_at')
    return render(request, 'user_replies.html', {
        'user': user,
        'replies': replies,
        'is_owner': request.user == user  # 添加这个变量用于模板判断
    })
@login_required
def edit_post(request, post_id):
    post = get_object_or_404(ForumPost, id=post_id, author=request.user)

    if request.method == 'POST':
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, '帖子修改成功')
            return redirect('myneo4j:user_posts', user_id=request.user.id)
    else:
        form = PostForm(instance=post)

    return render(request, 'edit_post.html', {
        'form': form,
        'post': post
    })


@login_required
def delete_post(request, post_id):
    post = get_object_or_404(ForumPost, id=post_id, author=request.user)

    if request.method == 'POST':
        post.delete()
        messages.success(request, '帖子已删除')
        return redirect('myneo4j:user_posts', user_id=request.user.id)

    return redirect('myneo4j:post_detail', post_id=post_id)
@login_required
@require_POST
def delete_reply(request, reply_id):
    reply = get_object_or_404(PostReply, id=reply_id, author=request.user)
    reply.delete()
    messages.success(request, '回复已删除')
    return redirect('myneo4j:user_replies', user_id=request.user.id)

