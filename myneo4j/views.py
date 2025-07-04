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
from .models import MyNode, MyWenda, ForumPost, PostReply, PostLike, ChatSession
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
import base64
from PIL import Image
from io import BytesIO
import uuid
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
import logging
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404, HttpResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.files.storage import default_storage
from django.conf import settings
import os
from .models import (
    PatientProfile, MedicalRecord, Medication,
    LabReport, VitalSigns, DoctorAccess
)

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

        # 处理所有元素，按顺序保留结构
        for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'pre', 'blockquote']):
            if element.name.startswith('h'):
                # 标题使用特殊标记，以便后续处理
                level = int(element.name[1])
                formatted_text.append(f"\n##HEADER{level}## {element.get_text()}\n")
            elif element.name == 'p':
                formatted_text.append(f"{element.get_text()}\n\n")
            elif element.name == 'ul':
                for li in element.find_all('li'):
                    formatted_text.append(f"  • {li.get_text()}\n")
                formatted_text.append("\n")
            elif element.name == 'ol':
                for i, li in enumerate(element.find_all('li')):
                    formatted_text.append(f"  {i + 1}. {li.get_text()}\n")
                formatted_text.append("\n")
            elif element.name == 'pre':
                formatted_text.append(f"\n[代码示例]:\n{element.get_text()}\n\n")
            elif element.name == 'blockquote':
                formatted_text.append(f"引用: {element.get_text()}\n\n")

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
    # 使用处理后的Markdown内容
    lines = wrap_text(formatted_text, c, effective_width, "fs2312", 12)
    line_height = 20
    paragraph_spacing = 10

    c.setFont("fs2312", 12)
    c.setFillColorRGB(0.2, 0.2, 0.2)  # 深灰色文字

    # 标记是否处于标题状态
    in_header = False

    for i, line in enumerate(lines):
        if y_pos < 100:
            c.showPage()
            current_page += 1
            draw_header_footer(c, current_page)
            y_pos = 780
            c.setFont("fs2312", 12)
            c.setFillColorRGB(0.2, 0.2, 0.2)

        if not line.strip():
            y_pos -= line_height
            continue

        # 检测是否为标题行 - 使用新的标题标记
        header_match = re.match(r'^##HEADER(\d)## (.*)', line.strip())

        if header_match:
            # 提取标题级别和文本
            header_level = int(header_match.group(1))
            header_text = header_match.group(2)

            # 根据标题级别设置字体大小
            font_size = 16 - (header_level - 1) * 0.5  # h1=16, h2=15.5, ...
            font_size = max(12, font_size)  # 不小于12

            c.setFillColorRGB(0.2, 0.4, 0.8)  # 深蓝色标题
            c.setFont("fs2312", font_size)
            c.drawString(left_margin, y_pos, header_text)

            if header_level <= 2:  # 只有h1和h2有下划线
                text_width = c.stringWidth(header_text, "fs2312", font_size)
                y_pos -= 5  # 下移一点绘制下划线
                c.setLineWidth(1)
                c.line(left_margin, y_pos, left_margin + text_width, y_pos)
                y_pos += 5  # 恢复位置
            # 标题后额外增加间距
            y_pos -= 10  # 标题后额外间距

            # 设置标题状态
            in_header = True
        else:
            # 列表项缩进处理
            indent = 0
            if line.startswith('  •'):
                indent = 10
                c.setFillColorRGB(0.2, 0.4, 0.8)  # 深蓝色项目符号
                c.drawString(left_margin, y_pos, '•')
                c.setFillColorRGB(0.2, 0.2, 0.2)  # 恢复文字颜色
                line = line[3:]  # 移除项目符号

            c.setFillColorRGB(0.2, 0.2, 0.2)  # 深灰色文字
            c.setFont("fs2312", 12)
            c.drawString(left_margin + indent, y_pos, line)

            # 重置标题状态
            in_header = False

        y_pos -= line_height

        # 如果当前行后面跟着空行，添加额外间距
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
    """同步调用大模型API - 修复版本"""
    headers = {
        "Authorization": f"Bearer {DOUBAO_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "doubao-1.5-vision-lite-250315",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5,
        "max_tokens": 16384,  # 增加到16384，确保内容完整
    }
    try:
        response = requests.post(
            DOUBAO_API_URL,
            headers=headers,
            json=data,
            timeout=120  # 增加超时时间到120秒
        )
        response.raise_for_status()

        result = response.json()
        content = result["choices"][0]["message"]["content"]

        # 检查内容完整性
        finish_reason = result["choices"][0].get("finish_reason")
        if finish_reason == "length":
            logger.warning("AI响应因长度限制被截断")
            # 尝试重新请求，增加max_tokens
            data["max_tokens"] = 32768
            try:
                response = requests.post(DOUBAO_API_URL, headers=headers, json=data, timeout=120)
                if response.ok:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    logger.info("重新请求获取完整响应成功")
                else:
                    content += "\n\n*注：响应内容可能不完整，建议重新提问。*"
            except Exception as e:
                logger.error(f"重新请求失败: {e}")
                content += "\n\n*注：响应内容可能不完整，建议重新提问。*"

        return content

    except requests.exceptions.Timeout:
        logger.error("API请求超时")
        return "AI 服务响应超时，请稍后重试"
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

@login_required
def first_view(request):
    return render(request, 'first.html')
def about_view(request):
    return render(request, 'about.html')
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

            # 获取评测类型
            evaluation_type = request.GET.get('evaluation_type', 'fast')

            # 构建提示语
            prompt = f"""你作为专业健康顾问，请分析以下用户数据：  
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
            - 给出的回答要保证质量，内容尽量丰富、严谨
            """

            # 检查是否需要流式输出
            stream = request.GET.get('stream', 'false').lower() == 'true'
            if stream:
                # 返回流式响应
                return stream_response(get_spark_response_stream(prompt))
            else:
                # 常规响应处理
                model_suggestion = get_spark_response(prompt)

                # 如果是AJAX请求，返回JSON响应
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'model_suggestion': model_suggestion
                    })
                else:
                    # 生成PDF文件
                    pdf_filename = f"health_report_{request.user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
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

        error_message = f"系统繁忙，请稍后重试（错误: {str(e)}）"

        # 如果是AJAX请求，返回JSON错误

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':

            return JsonResponse({

                'error': error_message

            }, status=500)

        else:

            return render(request, 'health_assessment.html', {

                'error': error_message

            })


@login_required
def generate_health_report_pdf(request):
    """生成健康报告PDF文件"""
    try:
        if request.method == 'POST':
            # 从POST数据中获取健康数据和模型建议
            health_data = json.loads(request.POST.get('health_data', '{}'))
            model_suggestion = request.POST.get('model_suggestion', '')

            # 确保model_suggestion不为空
            if not model_suggestion:
                return JsonResponse({
                    'success': False,
                    'error': '缺少AI分析内容'
                }, status=400)

            # 生成PDF文件
            pdf_filename = f"health_report_{request.user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            pdf_path = generate_pdf(health_data, model_suggestion, request.user, pdf_filename)

            # 检查PDF文件是否生成成功
            if not os.path.exists(pdf_path):
                raise Exception('PDF文件生成失败')

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
        }, status=500)


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

        # 获取URL参数
        key = request.GET.get("key", "")
        clean = request.GET.get("clean", "")
        new_chat = request.GET.get("new", "")
        chat_id = request.GET.get("chat", "")
        search = request.GET.get("search", "")
        clear_all = request.GET.get("clear_all", "")

        # 处理清空所有聊天记录
        if clear_all:
            MyWenda.objects.filter(user=user).delete()
            ChatSession.objects.filter(user=user).delete()
            return redirect('/wenda')

        # 处理清空当前对话
        if clean:
            if chat_id:
                # 清空指定对话的问答记录
                MyWenda.objects.filter(user=user, chat_session_id=chat_id).delete()
            else:
                # 清空所有无会话ID的问答记录
                MyWenda.objects.filter(user=user, chat_session_id__isnull=True).delete()
            return redirect(f'/wenda?chat={chat_id}' if chat_id else '/wenda')

        # 获取或创建当前对话会话
        current_session = None

        if new_chat:
            # 创建新对话
            current_session = ChatSession.objects.create(
                title="新对话",
                user=user
            )
            return redirect(f'/wenda?chat={current_session.id}')

        elif chat_id:
            # 获取指定对话会话
            try:
                current_session = ChatSession.objects.get(id=chat_id, user=user)
            except ChatSession.DoesNotExist:
                # 如果指定的会话不存在，创建新会话
                current_session = ChatSession.objects.create(
                    title="新对话",
                    user=user
                )
                return redirect(f'/wenda?chat={current_session.id}')

        else:
            # 获取最新的对话会话，如果没有则创建一个
            current_session = ChatSession.objects.filter(user=user).first()
            if not current_session:
                current_session = ChatSession.objects.create(
                    title="新对话",
                    user=user
                )
                return redirect(f'/wenda?chat={current_session.id}')

        # 处理搜索功能
        if search:
            search_results = MyWenda.objects.filter(
                user=user,
                question__icontains=search
            ).order_by("-id")[:50]

            # 获取所有对话会话用于侧边栏显示
            all_sessions = ChatSession.objects.filter(user=user).order_by('-updated_at')

            return render(request, "wenda.html", {
                'all_wendas': search_results,
                'current_session': current_session,
                'all_sessions': all_sessions,
                'search_keyword': search,
                'is_search_result': True
            })

        # 处理问答逻辑
        if key and request.method == "GET":
            daan = ''

            # 简单的问候语处理
            if key.lower() in {'你好', '您好', 'hello', '你好！'}:
                daan = '你好👋！我是您的医疗小助手！很高兴见到你，欢迎问我任何有关疾病的问题。'
            else:
                # 使用现有的AI处理逻辑
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
                # 清理AI回复文本 - 这里是关键修改
                cleaned_daan = clean_ai_response(daan)
                # 创建问答记录，关联到当前对话会话
                wenda = MyWenda.objects.create(
                    user=user,
                    question=key,
                    anster=cleaned_daan,
                    chat_session_id=current_session.id
                )

                # 更新对话会话的标题和更新时间
                if current_session.title == "新对话":
                    # 使用问题的前20个字符作为标题
                    title = key[:20] + "..." if len(key) > 20 else key
                    current_session.title = title

                current_session.save()  # 这会自动更新updated_at字段

                # 重定向到当前会话，避免重复提交
                return redirect(f'/wenda?chat={current_session.id}')

        # 获取当前会话的问答记录
        current_wendas = MyWenda.objects.filter(
            user=user,
            chat_session_id=current_session.id
        ).order_by("id")[:50]

        # 获取所有对话会话用于侧边栏显示
        all_sessions = ChatSession.objects.filter(user=user).order_by('-updated_at')

        # 按月份分组会话
        sessions_by_month = {}
        for session in all_sessions:
            month_key = session.created_at.strftime('%Y-%m')
            if month_key not in sessions_by_month:
                sessions_by_month[month_key] = []
            sessions_by_month[month_key].append(session)

        return render(request, "wenda.html", {
            'all_wendas': current_wendas,
            'current_session': current_session,
            'all_sessions': all_sessions,
            'sessions_by_month': sessions_by_month,
            'is_search_result': False
        })

    except Exception as e:
        logger.exception("问答系统错误")
        return render(request, "wenda.html", {
            'error': f"系统错误: {str(e)}",
            'all_wendas': [],
            'current_session': None,
            'all_sessions': [],
            'sessions_by_month': {}
        })

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


@login_required
@require_POST
def rename_chat(request, session_id):
    """重命名对话会话"""
    try:
        import json
        data = json.loads(request.body)
        title = data.get('title', '').strip()

        if not title:
            return JsonResponse({'success': False, 'error': '标题不能为空'})

        # 获取用户的对话会话
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        session.title = title
        session.save()

        return JsonResponse({'success': True, 'message': '重命名成功'})

    except Exception as e:
        logger.exception("重命名对话失败")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def delete_chat(request, session_id):
    """删除对话会话"""
    if request.method != 'DELETE':
        return JsonResponse({'success': False, 'error': '不支持的请求方法'})

    try:
        # 获取用户的对话会话
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)

        # 删除该会话的所有问答记录
        MyWenda.objects.filter(chat_session_id=session_id, user=request.user).delete()

        # 删除会话
        session.delete()

        return JsonResponse({'success': True, 'message': '删除成功'})

    except Exception as e:
        logger.exception("删除对话失败")
        return JsonResponse({'success': False, 'error': str(e)})


def clean_ai_response(text):
    """清理AI回复文本，确保正常显示 - 修复版本"""
    if not text:
        return ""

    # 如果text是列表，先转换为字符串
    if isinstance(text, list):
        text = '\n'.join(str(item) for item in text if item)

    # 确保text是字符串
    text = str(text)

    # 移除可能导致显示问题的特殊字符
    text = text.replace('\u200b', '')  # 移除零宽空格
    text = text.replace('\ufeff', '')  # 移除BOM字符
    text = text.replace('\u00a0', ' ')  # 替换不间断空格

    # 处理单字符换行问题 - 核心修复
    lines = text.split('\n')
    cleaned_lines = []
    buffer = ""

    for line in lines:
        stripped = line.strip()
        # 如果是单字符且不是标点符号
        if len(stripped) == 1 and stripped.isalnum():
            buffer += stripped
        else:
            if buffer:
                cleaned_lines.append(buffer)
                buffer = ""
            cleaned_lines.append(stripped)

    # 添加最后缓冲的内容
    if buffer:
        cleaned_lines.append(buffer)

    # 重新组合文本
    text = ' '.join(cleaned_lines)

    # 规范化换行符
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # 替换多个连续的换行符，但保留内容
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 移除开头和结尾的空白，但保留内容完整性
    text = text.strip()

    return text



def debug_ai_response(original_response):
    """调试函数：打印AI响应的详细信息"""
    logger.info(f"AI响应类型: {type(original_response)}")
    logger.info(f"AI响应长度: {len(str(original_response))}")
    logger.info(f"AI响应前50个字符: {repr(str(original_response)[:50])}")

    if isinstance(original_response, str):
        # 检查是否包含大量换行符
        newline_count = original_response.count('\n')
        char_count = len(original_response.replace('\n', '').replace(' ', ''))
        if newline_count > char_count * 0.5:  # 如果换行符数量超过字符数量的50%
            logger.warning(f"检测到异常的换行符密度: {newline_count} 换行符 vs {char_count} 字符")

    return original_response


@login_required
def wenda_ajax(request):
    """Ajax方式处理问答请求（支持图片上传）- 修复版本"""
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': '仅支持POST请求'
        })

    try:
        user = request.user
        key = request.POST.get("key", "").strip()
        chat_id = request.POST.get("chat", "")
        image_file = request.FILES.get("image")  # 获取上传的图片

        logger.info(f"用户 {user.username} 发起请求")
        logger.info(f"问题文本: {key[:50]}...")
        logger.info(f"聊天ID: {chat_id}")
        logger.info(f"是否有图片: {bool(image_file)}")

        # 检查是否有问题或图片
        if not key and not image_file:
            logger.warning("用户未提供问题文本或图片")
            return JsonResponse({
                'success': False,
                'error': '请输入问题或上传图片'
            })

        # 如果只有图片没有文字，设置默认问题
        if not key and image_file:
            key = "请帮我分析这张图片中的医疗相关内容"

        # 验证图片文件
        if image_file and not validate_image_file(image_file):
            return JsonResponse({
                'success': False,
                'error': '图片格式不支持或文件过大'
            })

        # 获取或创建当前对话会话
        session_info = get_or_create_chat_session(user, chat_id)
        current_session = session_info['session']
        is_new_session = session_info['is_new']
        old_title = session_info['old_title']

        # 处理AI回复
        logger.info("开始调用AI处理...")
        response_data = process_ai_response_with_image(key, image_file)
        logger.info(f"AI处理完成，回答长度: {len(response_data.get('answer', ''))}")

        # 创建问答记录，保存图片
        wenda = MyWenda.objects.create(
            user=user,
            question=key,
            anster=response_data['answer'],
            chat_session_id=current_session.id,
            image=image_file if image_file else None,  # 保存图片文件
            has_image=bool(image_file)  # 标记是否包含图片
        )
        logger.info(f"创建问答记录成功，ID: {wenda.id}")

        # 更新对话会话标题
        title_changed = update_session_title(current_session, key)
        current_session.save()

        # 准备返回数据
        response_json = {
            'success': True,
            'answer': response_data['answer'],
            'has_kg_source': response_data.get('has_kg_source', False),
            'kg_source': response_data.get('kg_source', ''),
            'chat_id': current_session.id,
            'session_title': current_session.title,
            'is_new_session': is_new_session,
            'title_changed': title_changed,
            'old_title': old_title,
            'has_image': bool(image_file)
        }

        # 如果有图片，添加图片URL
        if image_file and wenda.image:
            response_json['image_url'] = wenda.image.url
            logger.info(f"图片已保存，URL: {wenda.image.url}")

        return JsonResponse(response_json)

    except Exception as e:
        logger.exception("Ajax问答系统错误")
        return JsonResponse({
            'success': False,
            'error': f"系统错误: {str(e)}"
        })




def get_or_create_chat_session(user, chat_id):
    """获取或创建聊天会话"""
    is_new_session = False
    old_title = None
    current_session = None

    if chat_id:
        try:
            current_session = ChatSession.objects.get(id=chat_id, user=user)
            old_title = current_session.title
        except ChatSession.DoesNotExist:
            current_session = ChatSession.objects.create(
                title="新对话",
                user=user
            )
            is_new_session = True
    else:
        current_session = ChatSession.objects.create(
            title="新对话",
            user=user
        )
        is_new_session = True

    return {
        'session': current_session,
        'is_new': is_new_session,
        'old_title': old_title
    }


def update_session_title(session, question):
    """更新会话标题"""
    title_changed = False
    if session.title == "新对话":
        title = question[:20] + "..." if len(question) > 20 else question
        session.title = title
        title_changed = True
    return title_changed


def process_ai_response(question):
    """处理AI回复的主要逻辑"""
    # 简单的问候语处理
    if question.lower() in {'你好', '您好', 'hello', '你好！'}:
        return {
            'answer': '你好👋！我是您的**医疗小助手**！很高兴见到你，欢迎问我任何有关疾病的问题。',
            'has_kg_source': False
        }

    try:
        # 1. 先尝试知识图谱查询
        kg_results = query_knowledge_graph(question)

        if kg_results:
            # 2. 如果有知识图谱结果，让AI润色这些结果
            polished_answer = get_ai_polished_response(question, kg_results)

            # 3. 格式化知识图谱结果作为依据
            kg_source = format_kg_results_as_source(kg_results)

            # 4. 将润色回答和依据结合
            final_answer = combine_answer_with_source(polished_answer, kg_source)

            return {
                'answer': final_answer,
                'has_kg_source': True,
                'kg_source': kg_source
            }
        else:
            # 5. 如果没有知识图谱结果，直接调用AI
            direct_answer = get_ai_direct_response(question)
            return {
                'answer': direct_answer,
                'has_kg_source': False
            }

    except Exception as e:
        logger.error(f"AI处理错误: {e}")
        return {
            'answer': "**系统提示**: AI 服务暂时不可用，请稍后重试。",
            'has_kg_source': False
        }


def combine_answer_with_source(polished_answer, kg_source):
    """将润色答案与知识图谱依据结合"""
    if not kg_source:
        return polished_answer

    # 使用更美观的Markdown格式显示依据
    combined_answer = f"{polished_answer}\n\n---\n\n### 📚 回答依据\n\n{kg_source}"
    return combined_answer


def query_knowledge_graph(question):
    """查询知识图谱"""
    try:
        # 使用现有的分类器和解析器
        res_classify = settings.CLASSIFIER.classify(question)

        if res_classify:
            res_sql = settings.PARSER.parser_main(res_classify)
            final_answers = settings.SEACHER.search_main(res_sql)
            return final_answers if final_answers else None

        return None
    except Exception as e:
        logger.error(f"知识图谱查询错误: {e}")
        return None


def get_ai_polished_response(question, kg_results):
    """基于知识图谱结果，让AI润色并返回用户友好的回答"""
    # 将知识图谱结果格式化为文本
    kg_text = format_kg_results_for_ai(kg_results)

    prompt = f"""你是一个专业的医疗健康助手。用户问了一个问题，我已经从医疗知识图谱中找到了相关的专业信息。请你基于这些信息，用温馨、专业、易懂的语言回答用户的问题。

用户问题：{question}

知识图谱中的相关信息：
{kg_text}

请按照以下要求回答：
1. 使用Markdown格式回复，让内容更易读
2. 用温馨、专业的语调，避免生硬的医学术语
3. 基于知识图谱的信息进行回答，但要润色得更加人性化
4. 使用适当的标题（##）、加粗（**）、列表等格式
5. 如果涉及药物治疗，要提醒用户咨询医生
6. 如果是严重症状，要建议及时就医
7. 字数控制在200字以内
8. 不要在回答中重复显示依据信息，因为系统会自动添加

格式示例：
## 关于您的问题

根据医疗资料显示...

## 建议和注意事项

**日常护理**：
- 建议...
- 注意...

**重要提醒**：以上信息仅供参考，如有疑问请咨询专业医生。
"""

    try:
        response = get_spark_response(prompt)
        return clean_markdown_response(response)
    except Exception as e:
        logger.error(f"AI润色失败: {e}")
        # 如果AI润色失败，返回格式化的知识图谱结果作为备用
        return format_kg_result_to_markdown(kg_results)


def get_ai_direct_response(question):
    """直接调用AI回答用户问题（当知识图谱没有相关信息时）"""
    prompt = f"""你是一个专业的医疗健康助手，请用中文回答以下问题：

问题：{question}

请按照以下要求回答：
1. 使用Markdown格式回复
2. 使用适当的标题（##）、加粗（**）、列表等格式
3. 回答要专业、准确、易懂，语调要温馨友好
4. 如果涉及药物，要提醒用户咨询医生
5. 如果是紧急情况，要建议立即就医
6. 如果问题超出医疗范围，要礼貌地说明并引导到合适的话题
7. 字数控制在200字以内

格式示例：
## 关于您的问题

针对您提到的...

## 建议措施
- **立即措施**：...
- **日常护理**：...

## 注意事项
**重要提醒**：如果症状持续或加重，请及时就医咨询专业医生。
"""

    try:
        response = get_spark_response(prompt)
        return clean_markdown_response(response)
    except Exception as e:
        logger.error(f"AI直接回答失败: {e}")
        return "**系统提示**: AI服务暂时不可用，请稍后重试。"


def format_kg_results_for_ai(results):
    """将知识图谱结果格式化为供AI处理的文本"""
    if not results:
        return ""

    formatted_text = ""
    for i, result in enumerate(results, 1):
        if isinstance(result, str):
            formatted_text += f"{i}. {result}\n"
        elif isinstance(result, dict):
            # 如果结果是字典，尝试提取有用信息
            for key, value in result.items():
                formatted_text += f"{i}. {key}: {value}\n"
        else:
            formatted_text += f"{i}. {str(result)}\n"

    return formatted_text.strip()


def format_kg_results_as_source(results):
    """将知识图谱结果格式化为依据展示文本 - 修复版本"""
    if not results:
        return ""

    formatted_source = ""
    for i, result in enumerate(results, 1):
        if isinstance(result, str):
            # 不限制长度，显示完整内容
            formatted_source += f"**{i}.** {result}\n\n"
        elif isinstance(result, dict):
            # 如果结果是字典，提取关键信息，但不截断
            dict_text = ""
            for key, value in result.items():
                dict_text += f"{key}: {value}; "
            dict_text = dict_text.rstrip("; ")
            formatted_source += f"**{i}.** {dict_text}\n\n"
        else:
            result_text = str(result)
            formatted_source += f"**{i}.** {result_text}\n\n"

    return formatted_source.strip()


def format_kg_result_to_markdown(results):
    """将知识图谱结果格式化为Markdown（备用方法）"""
    if not results:
        return "## 抱歉\n\n暂时无法获取相关医疗信息，请稍后重试或咨询专业医生。"

    formatted_result = "## 相关医疗信息\n\n"

    for i, result in enumerate(results, 1):
        if isinstance(result, str):
            formatted_result += f"### {i}. 医疗建议\n"
            formatted_result += f"{result}\n\n"
        else:
            formatted_result += f"### {i}. 相关信息\n"
            formatted_result += f"{str(result)}\n\n"

    formatted_result += "---\n"
    formatted_result += "**重要提醒**: 以上信息仅供参考，具体诊断和治疗请咨询专业医生。"

    return formatted_result


def clean_markdown_response(text):
    """清理Markdown回复，保留格式"""
    if not text:
        return ""

    # 如果是列表，转换为字符串
    if isinstance(text, list):
        text = '\n'.join(str(item) for item in text if item)

    # 确保是字符串
    text = str(text)

    # 移除有害字符但保留Markdown格式
    text = text.replace('\u200b', '')  # 移除零宽空格
    text = text.replace('\ufeff', '')  # 移除BOM字符
    text = text.replace('\u00a0', ' ')  # 替换不间断空格

    # 规范化换行符
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # 清理过多的空行，但保留Markdown所需的双换行
    text = re.sub(r'\n{4,}', '\n\n\n', text)

    # 移除开头和结尾的空白
    text = text.strip()

    return text


def get_spark_response(prompt):
    """调用Spark AI服务的包装函数"""
    try:
        # 这里应该是实际的Spark AI调用
        # 假设settings.ALI是Spark AI的接口
        return settings.ALI.get_response(prompt)
    except Exception as e:
        logger.error(f"Spark AI调用失败: {e}")
        raise


@login_required
def new_chat_ajax(request):
    """Ajax方式创建新聊天会话"""
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': '仅支持POST请求'
        })

    try:
        user = request.user

        # 创建新的对话会话
        new_session = ChatSession.objects.create(
            title="新对话",
            user=user
        )

        # 返回成功响应
        return JsonResponse({
            'success': True,
            'chat_id': new_session.id,
            'session_title': new_session.title
        })

    except Exception as e:
        logger.exception("创建新聊天会话错误")
        return JsonResponse({
            'success': False,
            'error': f"系统错误: {str(e)}"
        })


@login_required
def get_chat_history_ajax(request):
    """Ajax方式获取聊天历史（支持图片显示）"""
    if request.method != 'GET':
        return JsonResponse({
            'success': False,
            'error': '仅支持GET请求'
        })

    try:
        user = request.user
        chat_id = request.GET.get('chat_id')

        if not chat_id:
            return JsonResponse({
                'success': True,
                'chat_history': [],
                'session_title': '医疗问答智能助手'
            })

        try:
            session = ChatSession.objects.get(id=chat_id, user=user)
            history = MyWenda.objects.filter(
                chat_session_id=session.id
            ).order_by('create_time')

            chat_data = []
            for record in history:
                record_data = {
                    'question': record.question,
                    'answer': record.anster,
                    'create_time': record.create_time.strftime('%Y-%m-%d %H:%M'),
                    'has_image': record.has_image
                }

                # 如果有图片，添加图片URL
                if record.has_image and record.image:
                    try:
                        record_data['image_url'] = record.image.url
                        logger.info(f"加载图片URL: {record.image.url}")
                    except Exception as e:
                        logger.warning(f"图片URL生成失败: {e}")
                        record_data['has_image'] = False

                chat_data.append(record_data)

            return JsonResponse({
                'success': True,
                'chat_history': chat_data,
                'session_title': session.title
            })

        except ChatSession.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': '会话不存在'
            })

    except Exception as e:
        logger.exception("获取聊天历史错误")
        return JsonResponse({
            'success': False,
            'error': f"系统错误: {str(e)}"
        })


@login_required
@require_POST
def rename_chat(request, session_id):
    """重命名对话会话"""
    try:
        import json
        data = json.loads(request.body)
        title = data.get('title', '').strip()

        if not title:
            return JsonResponse({'success': False, 'error': '标题不能为空'})

        # 获取用户的对话会话
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        session.title = title
        session.save()

        return JsonResponse({'success': True, 'message': '重命名成功'})

    except Exception as e:
        logger.exception("重命名对话失败")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def delete_chat(request, session_id):
    """删除对话会话"""
    if request.method != 'DELETE':
        return JsonResponse({'success': False, 'error': '不支持的请求方法'})

    try:
        # 获取用户的对话会话
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)

        # 删除该会话的所有问答记录
        MyWenda.objects.filter(chat_session_id=session_id, user=request.user).delete()

        # 删除会话
        session.delete()

        return JsonResponse({'success': True, 'message': '删除成功'})

    except Exception as e:
        logger.exception("删除对话失败")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def new_chat_ajax(request):
    """Ajax方式创建新聊天会话"""
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': '仅支持POST请求'
        })

    try:
        user = request.user

        # 创建新的对话会话
        new_session = ChatSession.objects.create(
            title="新对话",
            user=user
        )

        # 返回成功响应
        return JsonResponse({
            'success': True,
            'chat_id': new_session.id,
            'session_title': new_session.title
        })

    except Exception as e:
        logger.exception("创建新聊天会话错误")
        return JsonResponse({
            'success': False,
            'error': f"系统错误: {str(e)}"
        })


def encode_image_to_base64(image_file):
    """将图片文件编码为base64字符串"""
    try:
        # 读取图片
        image = Image.open(image_file)

        # 如果图片过大，进行压缩
        max_size = (1024, 1024)
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            image.thumbnail(max_size, Image.Resampling.LANCZOS)

        # 转换为RGB（去除透明通道）
        if image.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')

        # 保存为bytes
        buffer = BytesIO()
        image.save(buffer, format='JPEG', quality=85)
        image_bytes = buffer.getvalue()

        # 编码为base64
        base64_string = base64.b64encode(image_bytes).decode('utf-8')
        return base64_string

    except Exception as e:
        logger.error(f"图片编码失败: {e}")
        return None


def get_spark_response_with_image(prompt, image_base64=None):
    """调用支持视觉的AI API分析图片和文本"""
    headers = {
        "Authorization": f"Bearer {DOUBAO_API_KEY}",
        "Content-Type": "application/json",
    }

    # 构建消息内容
    message_content = []

    # 添加文本内容
    if prompt:
        message_content.append({
            "type": "text",
            "text": prompt
        })

    # 添加图片内容
    if image_base64:
        message_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{image_base64}"
            }
        })

    data = {
        "model": "doubao-1.5-vision-lite-250315",  # 使用视觉模型
        "messages": [
            {
                "role": "user",
                "content": message_content
            }
        ],
        "temperature": 0.5,
        "max_tokens": 8192,
    }

    try:
        response = requests.post(
            DOUBAO_API_URL,
            headers=headers,
            json=data,
            timeout=60
        )
        response.raise_for_status()

        result = response.json()
        content = result["choices"][0]["message"]["content"]

        # 检查响应完整性
        finish_reason = result["choices"][0].get("finish_reason")
        if finish_reason == "length":
            logger.warning("AI响应可能因长度限制被截断")
            content += "\n\n*注：响应内容可能不完整，建议重新提问或联系技术支持。*"

        return content

    except requests.exceptions.Timeout:
        logger.error("AI API请求超时")
        return "AI 服务响应超时，请稍后重试"
    except Exception as e:
        logger.error(f"AI API错误: {e}")
        return "AI 服务暂时不可用，请稍后重试"


def process_ai_response_with_image(question, image_file=None):
    """处理包含图片的AI回复逻辑 - 增强调试版本"""
    logger.info(f"开始处理AI回复，问题: {question[:50]}..., 有图片: {bool(image_file)}")

    # 简单的问候语处理
    if not image_file and question.lower() in {'你好', '您好', 'hello', '你好！'}:
        logger.info("识别为问候语，返回标准回复")
        return {
            'answer': '你好👋！我是您的**医疗小助手**！很高兴见到你，欢迎问我任何有关疾病的问题，也可以上传相关图片让我帮您分析。',
            'has_kg_source': False
        }

    try:
        # 如果有图片，优先使用阿里云视觉分析
        if image_file:
            logger.info("检测到图片，开始使用阿里云视觉模型分析")

            # 验证图片
            if not validate_image_file(image_file):
                logger.warning("图片验证失败")
                return {
                    'answer': "**图片格式错误**：请上传JPG、PNG、GIF、WEBP或BMP格式的图片文件。",
                    'has_kg_source': False,
                    'has_image': True
                }

            # 构建图片分析提示
            if not question.strip():
                question = "请分析这张图片中的医疗相关内容，包括可能的伤势、症状或健康问题，并给出专业建议。"

            # 调用阿里云视觉模型
            try:
                logger.info("正在调用阿里云视觉模型...")

                # 检查ALI_VISION实例是否存在
                if not hasattr(settings, 'ALI_VISION'):
                    logger.error("ALI_VISION实例未找到")
                    return {
                        'answer': "**系统配置错误**：视觉分析模块未正确初始化，请联系技术支持。",
                        'has_kg_source': False,
                        'has_image': True
                    }

                ai_response = settings.ALI_VISION.get_medical_image_analysis(
                    text_prompt=question,
                    image_file=image_file
                )
                logger.info("阿里云视觉模型调用成功")

                return {
                    'answer': clean_markdown_response(ai_response),
                    'has_kg_source': False,
                    'has_image': True
                }

            except Exception as vision_error:
                logger.error(f"阿里云视觉模型调用失败: {vision_error}")
                logger.error(f"错误类型: {type(vision_error).__name__}")

                # 降级处理：使用豆包视觉模型作为备选
                try:
                    logger.info("尝试使用豆包视觉模型作为备选...")
                    image_base64 = encode_image_to_base64_backup(image_file)
                    if image_base64:
                        backup_prompt = f"""你是一个专业的医疗健康助手，请分析用户上传的图片并回答问题。

用户问题：{question}

请按照以下要求分析：
1. **图片内容识别**：描述看到的内容
2. **医疗分析**：基于图片的医疗评估
3. **处理建议**：具体的建议和注意事项
4. **就医建议**：是否需要就医

使用Markdown格式回复，如果图片显示紧急情况，请特别强调立即就医。"""

                        backup_response = get_spark_response_with_image(backup_prompt, image_base64)
                        logger.info("备选模型调用成功")

                        return {
                            'answer': clean_markdown_response(backup_response),
                            'has_kg_source': False,
                            'has_image': True
                        }
                except Exception as backup_error:
                    logger.error(f"备用视觉模型也失败: {backup_error}")

                # 最终降级：提示用户重试
                return {
                    'answer': f"**图片分析暂时不可用**\n\n很抱歉，图片分析服务暂时遇到问题。详细错误信息：{str(vision_error)}\n\n请稍后重试，或者：\n\n1. 🔄 重新上传图片\n2. 📝 详细描述症状让我文字分析\n3. 🏥 如情况紧急，请立即就医\n\n感谢您的理解！",
                    'has_kg_source': False,
                    'has_image': True
                }

        # 如果没有图片，使用原有的文字处理逻辑
        else:
            logger.info("没有图片，使用文字处理逻辑")
            # 1. 先尝试知识图谱查询
            kg_results = query_knowledge_graph(question)

            if kg_results:
                logger.info("找到知识图谱结果，进行AI润色")
                # 如果有知识图谱结果，让AI润色这些结果
                polished_answer = get_ai_polished_response(question, kg_results)
                kg_source = format_kg_results_as_source(kg_results)
                final_answer = combine_answer_with_source(polished_answer, kg_source)

                return {
                    'answer': final_answer,
                    'has_kg_source': True,
                    'kg_source': kg_source
                }
            else:
                logger.info("未找到知识图谱结果，使用直接AI回答")
                # 如果没有知识图谱结果，直接调用AI
                direct_answer = get_ai_direct_response(question)
                return {
                    'answer': direct_answer,
                    'has_kg_source': False
                }

    except Exception as e:
        logger.error(f"AI处理错误: {e}")
        logger.exception("AI处理异常详情")
        return {
            'answer': f"**系统提示**: AI 服务暂时不可用，错误信息：{str(e)}",
            'has_kg_source': False
        }


logger = logging.getLogger(__name__)


@csrf_protect
@require_http_methods(["POST"])
def clear_all_chats_ajax(request):
    """Ajax方式清空所有聊天记录 - 修复版本"""

    # 1. 检查用户是否登录 - 返回JSON而不是重定向
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': '用户未登录',
            'login_required': True
        }, status=401)

    # 2. 检查请求方法
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': '仅支持POST请求'
        }, status=405)

    # 3. 检查AJAX请求
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': False,
            'error': '仅支持AJAX请求'
        }, status=400)

    try:
        user = request.user

        # 记录操作开始
        logger.info(f"用户 {user.username} 开始清空所有聊天记录")

        # 4. 删除用户的所有问答记录
        wenda_deleted = MyWenda.objects.filter(user=user).delete()
        wenda_count = wenda_deleted[0] if wenda_deleted else 0

        # 5. 删除用户的所有聊天会话
        session_deleted = ChatSession.objects.filter(user=user).delete()
        session_count = session_deleted[0] if session_deleted else 0

        # 记录操作结果
        logger.info(f"用户 {user.username} 清空聊天记录完成: 删除{wenda_count}条问答记录, {session_count}个会话")

        return JsonResponse({
            'success': True,
            'message': '所有聊天记录已清空',
            'deleted_counts': {
                'wenda': wenda_count,
                'sessions': session_count
            }
        }, status=200)

    except Exception as e:
        # 6. 详细的错误日志
        logger.exception(
            f"用户 {request.user.username if request.user.is_authenticated else 'Anonymous'} 清空聊天记录时发生错误")

        # 返回通用错误信息，避免泄露系统细节
        return JsonResponse({
            'success': False,
            'error': '系统内部错误，请稍后重试'
        }, status=500)


@login_required
def clear_current_chat_ajax(request):
    """Ajax方式清空当前对话记录"""
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': '仅支持POST请求'
        })

    try:
        import json
        user = request.user

        # 获取请求数据
        data = json.loads(request.body)
        chat_id = data.get('chat_id', '').strip()

        if chat_id:
            try:
                # 验证会话是否属于当前用户
                session = ChatSession.objects.get(id=chat_id, user=user)

                # 清空指定对话的问答记录
                deleted_count = MyWenda.objects.filter(
                    user=user,
                    chat_session_id=chat_id
                ).delete()[0]

                return JsonResponse({
                    'success': True,
                    'message': f'已清空 {deleted_count} 条对话记录',
                    'chat_id': chat_id
                })

            except ChatSession.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': '指定的对话会话不存在'
                })
        else:
            # 清空所有无会话ID的问答记录
            deleted_count = MyWenda.objects.filter(
                user=user,
                chat_session_id__isnull=True
            ).delete()[0]

            return JsonResponse({
                'success': True,
                'message': f'已清空 {deleted_count} 条对话记录'
            })

    except Exception as e:
        logger.exception("清空当前对话错误")
        return JsonResponse({
            'success': False,
            'error': f"系统错误: {str(e)}"
        })


def validate_image_file(image_file):
    """验证图片文件"""
    try:
        # 检查文件大小
        if hasattr(image_file, 'size') and image_file.size > settings.MAX_IMAGE_SIZE:
            logger.warning(f"图片过大: {image_file.size} > {settings.MAX_IMAGE_SIZE}")
            return False

        # 检查文件类型
        if hasattr(image_file, 'content_type'):
            is_valid = image_file.content_type in settings.ALLOWED_IMAGE_TYPES
            if not is_valid:
                logger.warning(f"不支持的图片类型: {image_file.content_type}")
            return is_valid

        return True

    except Exception as e:
        logger.error(f"图片验证失败: {e}")
        return False


def encode_image_to_base64(image_file):
    """将图片文件编码为base64字符串（备用方法）"""
    try:
        # 读取图片
        from PIL import Image
        import base64
        from io import BytesIO

        # 打开图片
        image = Image.open(image_file)

        # 如果图片过大，进行压缩
        max_size = (1024, 1024)
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            image.thumbnail(max_size, Image.Resampling.LANCZOS)

        # 转换为RGB（去除透明通道）
        if image.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')

        # 保存为bytes
        buffer = BytesIO()
        image.save(buffer, format='JPEG', quality=85)
        image_bytes = buffer.getvalue()

        # 编码为base64
        base64_string = base64.b64encode(image_bytes).decode('utf-8')
        return base64_string

    except Exception as e:
        logger.error(f"图片编码失败: {e}")
        return None


def encode_image_to_base64_backup(image_file):
    """备用图片编码函数"""
    try:
        from PIL import Image
        import base64
        from io import BytesIO

        logger.info("使用备用方法编码图片")

        # 打开图片
        image = Image.open(image_file)

        # 如果图片过大，进行压缩
        max_size = (1024, 1024)
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            logger.info(f"压缩图片从 {image.size} 到 {max_size}")
            image.thumbnail(max_size, Image.Resampling.LANCZOS)

        # 转换为RGB（去除透明通道）
        if image.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')

        # 保存为bytes
        buffer = BytesIO()
        image.save(buffer, format='JPEG', quality=85)
        image_bytes = buffer.getvalue()

        # 编码为base64
        base64_string = base64.b64encode(image_bytes).decode('utf-8')
        logger.info("图片编码成功")
        return base64_string

    except Exception as e:
        logger.error(f"备用图片编码失败: {e}")
        return None


@login_required
def electronic_medical_records(request):
    """电子病历管理主页面"""
    try:
        # 获取或创建患者档案
        patient_profile, created = PatientProfile.objects.get_or_create(
            user=request.user,
            defaults={
                'phone': getattr(request.user, 'phone', ''),
            }
        )

        # 获取统计数据
        medical_records_count = patient_profile.medical_records.count()
        medications_count = patient_profile.medications.filter(status='active').count()
        lab_reports_count = patient_profile.lab_reports.count()

        # 获取最近的记录
        recent_medical_records = patient_profile.medical_records.all()[:3]
        recent_lab_reports = patient_profile.lab_reports.all()[:3]
        recent_vital_signs = patient_profile.vital_signs.all()[:5]
        active_medications = patient_profile.medications.filter(status='active')[:5]

        # 获取最近的生命体征用于概览
        latest_vital_signs = patient_profile.vital_signs.first()

        context = {
            'patient_profile': patient_profile,
            'medical_records_count': medical_records_count,
            'medications_count': medications_count,
            'lab_reports_count': lab_reports_count,
            'recent_medical_records': recent_medical_records,
            'recent_lab_reports': recent_lab_reports,
            'recent_vital_signs': recent_vital_signs,
            'active_medications': active_medications,
            'latest_vital_signs': latest_vital_signs,
        }

        return render(request, 'electronic_medical_records.html', context)

    except Exception as e:
        messages.error(request, f'加载病历数据时出错: {str(e)}')
        return render(request, 'electronic_medical_records.html', {})


@login_required
def medical_records_ajax(request):
    """AJAX获取就诊记录"""
    try:
        patient_profile = PatientProfile.objects.get(user=request.user)
        records = patient_profile.medical_records.all()

        records_data = []
        for record in records:
            records_data.append({
                'id': record.id,
                'visit_date': record.visit_date.strftime('%Y-%m-%d'),
                'hospital': record.hospital,
                'department': record.department,
                'doctor': record.doctor,
                'diagnosis': record.diagnosis,
                'symptoms': record.symptoms or '',
                'treatment_plan': record.treatment_plan or '',
                'follow_up_plan': record.follow_up_plan or '',
            })

        return JsonResponse({'success': True, 'records': records_data})

    except PatientProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '患者档案不存在'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def medications_ajax(request):
    """AJAX获取用药记录"""
    try:
        patient_profile = PatientProfile.objects.get(user=request.user)
        medications = patient_profile.medications.all()

        medications_data = []
        for med in medications:
            medications_data.append({
                'id': med.id,
                'drug_name': med.drug_name,
                'dosage': med.dosage,
                'frequency': med.frequency,
                'start_date': med.start_date.strftime('%Y-%m-%d'),
                'end_date': med.end_date.strftime('%Y-%m-%d') if med.end_date else '长期',
                'status': med.get_status_display(),
                'side_effects': med.side_effects or '无',
                'route': med.get_route_display(),
            })

        return JsonResponse({'success': True, 'medications': medications_data})

    except PatientProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '患者档案不存在'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def lab_reports_ajax(request):
    """AJAX获取检查报告"""
    try:
        patient_profile = PatientProfile.objects.get(user=request.user)
        reports = patient_profile.lab_reports.all()

        reports_data = []
        for report in reports:
            abnormal_list = []
            if report.abnormal_indicators:
                abnormal_list = [item.strip() for item in report.abnormal_indicators.split(',') if item.strip()]

            reports_data.append({
                'id': report.id,
                'test_date': report.test_date.strftime('%Y-%m-%d'),
                'report_type': report.get_report_type_display(),
                'hospital': report.hospital,
                'status': report.get_status_display(),
                'abnormal_indicators': abnormal_list,
                'conclusion': report.conclusion or '',
                'has_file': bool(report.report_file),
                'file_url': report.report_file.url if report.report_file else None,
            })

        return JsonResponse({'success': True, 'reports': reports_data})

    except PatientProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '患者档案不存在'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def vital_signs_ajax(request):
    """AJAX获取生命体征"""
    try:
        patient_profile = PatientProfile.objects.get(user=request.user)
        vital_signs = patient_profile.vital_signs.all()[:20]  # 最近20条记录

        vital_signs_data = []
        for vital in vital_signs:
            vital_signs_data.append({
                'id': vital.id,
                'measurement_date': vital.measurement_date.strftime('%Y-%m-%d'),
                'blood_pressure': vital.blood_pressure,
                'heart_rate': vital.heart_rate,
                'temperature': vital.temperature,
                'weight': vital.weight,
                'blood_sugar': vital.blood_sugar,
                'oxygen_saturation': vital.oxygen_saturation,
                'measurement_method': vital.get_measurement_method_display(),
            })

        return JsonResponse({'success': True, 'vital_signs': vital_signs_data})

    except PatientProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '患者档案不存在'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@require_http_methods(["POST"])
def add_medical_record(request):
    """添加就诊记录"""
    try:
        patient_profile = PatientProfile.objects.get(user=request.user)

        # 获取POST数据
        visit_date = request.POST.get('visit_date')
        hospital = request.POST.get('hospital')
        department = request.POST.get('department')
        doctor = request.POST.get('doctor')
        diagnosis = request.POST.get('diagnosis')
        symptoms = request.POST.get('symptoms', '')
        treatment_plan = request.POST.get('treatment_plan', '')
        follow_up_plan = request.POST.get('follow_up_plan', '')

        # 创建就诊记录
        medical_record = MedicalRecord.objects.create(
            patient=patient_profile,
            visit_date=datetime.strptime(visit_date, '%Y-%m-%d').date(),
            hospital=hospital,
            department=department,
            doctor=doctor,
            diagnosis=diagnosis,
            symptoms=symptoms,
            treatment_plan=treatment_plan,
            follow_up_plan=follow_up_plan
        )

        return JsonResponse({'success': True, 'message': '就诊记录添加成功', 'record_id': medical_record.id})

    except PatientProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '患者档案不存在'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'添加失败: {str(e)}'})


@login_required
@require_http_methods(["POST"])
def add_medication(request):
    """添加用药记录"""
    try:
        patient_profile = PatientProfile.objects.get(user=request.user)

        medication = Medication.objects.create(
            patient=patient_profile,
            drug_name=request.POST.get('drug_name'),
            dosage=request.POST.get('dosage'),
            frequency=request.POST.get('frequency'),
            route=request.POST.get('route', 'oral'),
            start_date=datetime.strptime(request.POST.get('start_date'), '%Y-%m-%d').date(),
            end_date=datetime.strptime(request.POST.get('end_date'), '%Y-%m-%d').date() if request.POST.get(
                'end_date') else None,
            status=request.POST.get('status', 'active'),
            side_effects=request.POST.get('side_effects', ''),
        )

        return JsonResponse({'success': True, 'message': '用药记录添加成功', 'medication_id': medication.id})

    except PatientProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '患者档案不存在'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'添加失败: {str(e)}'})


@login_required
@require_http_methods(["POST"])
def add_vital_signs(request):
    """添加生命体征记录"""
    try:
        patient_profile = PatientProfile.objects.get(user=request.user)

        # 处理可选字段
        def get_float_or_none(field_name):
            value = request.POST.get(field_name)
            return float(value) if value and value.strip() else None

        def get_int_or_none(field_name):
            value = request.POST.get(field_name)
            return int(value) if value and value.strip() else None

        vital_signs = VitalSigns.objects.create(
            patient=patient_profile,
            measurement_date=datetime.strptime(
                request.POST.get('measurement_date', timezone.now().strftime('%Y-%m-%d %H:%M')), '%Y-%m-%d %H:%M'),
            systolic_pressure=get_int_or_none('systolic_pressure'),
            diastolic_pressure=get_int_or_none('diastolic_pressure'),
            heart_rate=get_int_or_none('heart_rate'),
            temperature=get_float_or_none('temperature'),
            weight=get_float_or_none('weight'),
            blood_sugar=get_float_or_none('blood_sugar'),
            oxygen_saturation=get_int_or_none('oxygen_saturation'),
            measurement_method=request.POST.get('measurement_method', 'home'),
            notes=request.POST.get('notes', ''),
        )

        return JsonResponse({'success': True, 'message': '生命体征记录添加成功', 'vital_signs_id': vital_signs.id})

    except PatientProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '患者档案不存在'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'添加失败: {str(e)}'})


@login_required
@require_http_methods(["POST"])
def upload_lab_report(request):
    """上传检查报告"""
    try:
        patient_profile = PatientProfile.objects.get(user=request.user)

        # 处理文件上传
        report_file = request.FILES.get('report_file') if 'report_file' in request.FILES else None

        lab_report = LabReport.objects.create(
            patient=patient_profile,
            report_type=request.POST.get('report_type'),
            test_date=datetime.strptime(request.POST.get('test_date'), '%Y-%m-%d').date(),
            hospital=request.POST.get('hospital'),
            report_title=request.POST.get('report_title'),
            report_content=request.POST.get('report_content', ''),
            conclusion=request.POST.get('conclusion', ''),
            abnormal_indicators=request.POST.get('abnormal_indicators', ''),
            report_file=report_file,
            notes=request.POST.get('notes', ''),
        )

        return JsonResponse({'success': True, 'message': '检查报告上传成功', 'report_id': lab_report.id})

    except PatientProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '患者档案不存在'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'上传失败: {str(e)}'})


@login_required
@require_http_methods(["POST"])
def update_patient_profile(request):
    """更新患者基本信息"""
    try:
        patient_profile = PatientProfile.objects.get(user=request.user)

        # 更新基本信息
        patient_profile.blood_type = request.POST.get('blood_type', '')
        patient_profile.height = float(request.POST.get('height')) if request.POST.get('height') else None
        patient_profile.weight = float(request.POST.get('weight')) if request.POST.get('weight') else None
        patient_profile.phone = request.POST.get('phone', '')

        # 更新紧急联系人信息
        patient_profile.emergency_contact_name = request.POST.get('emergency_contact_name', '')
        patient_profile.emergency_contact_phone = request.POST.get('emergency_contact_phone', '')
        patient_profile.emergency_contact_relationship = request.POST.get('emergency_contact_relationship', '')

        # 更新医疗信息
        patient_profile.allergies = request.POST.get('allergies', '')
        patient_profile.chronic_diseases = request.POST.get('chronic_diseases', '')

        patient_profile.save()

        return JsonResponse({'success': True, 'message': '个人信息更新成功'})

    except PatientProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '患者档案不存在'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'更新失败: {str(e)}'})


@login_required
def get_patient_profile_ajax(request):
    """获取患者基本信息"""
    try:
        patient_profile = PatientProfile.objects.get(user=request.user)

        # 处理过敏信息和慢性疾病
        allergies_list = []
        if patient_profile.allergies:
            allergies_list = [item.strip() for item in patient_profile.allergies.split(',') if item.strip()]

        chronic_diseases_list = []
        if patient_profile.chronic_diseases:
            chronic_diseases_list = [item.strip() for item in patient_profile.chronic_diseases.split(',') if
                                     item.strip()]

        profile_data = {
            'name': request.user.username,  # 从用户模型获取
            'age': getattr(request.user, 'age', '') or '',
            'gender': getattr(request.user, 'gender', '') or '',
            'blood_type': patient_profile.blood_type or '',
            'height': f"{patient_profile.height}cm" if patient_profile.height else '',
            'weight': f"{patient_profile.weight}kg" if patient_profile.weight else '',
            'phone': patient_profile.phone or '',
            'emergency_contact': f"{patient_profile.emergency_contact_name} ({patient_profile.emergency_contact_relationship}) - {patient_profile.emergency_contact_phone}" if patient_profile.emergency_contact_name else '',
            'allergies': allergies_list,
            'chronic_diseases': chronic_diseases_list,
        }

        return JsonResponse({'success': True, 'profile': profile_data})

    except PatientProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '患者档案不存在'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})