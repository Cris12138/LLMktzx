from django.urls import re_path, path
from .views import *
from . import views
from django.urls import path, include
from django.urls import path
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # 原有路由保持不变
    re_path(r"^$", index, name="index"),
    re_path(r"^index$", index, name="index"),
    re_path(r"^wenda$", wenda, name="wenda"),

    # 论坛相关路由（新增）
    re_path(r"^forum$", forum, name="forum"),  # 论坛首页
    re_path(r"^health-assessment/$", health_assessment, name="health-assessment"),  # 确保无空格
    path('forum/post/new/', create_post, name='create_post'),  # 新建帖子
    path('forum/post/<int:post_id>/', post_detail, name='post_detail'),  # 帖子详情
    # myneo4j/urls.py
    path('user/<int:user_id>/posts/', user_posts, name='user_posts'),
    path('user/<int:user_id>/replies/', user_replies, name='user_replies'),
    path('forum/post/<int:post_id>/edit/', edit_post, name='edit_post'),
    path('forum/post/<int:post_id>/delete/', delete_post, name='delete_post'),
    path('toggle_like/<int:post_id>/', toggle_like, name='toggle_like'),
    path('delete_reply/<int:reply_id>/', delete_reply, name='delete_reply'),
    path('health-assessment/', views.health_assessment, name='health-assessment'),
    # 新增PDF生成端点
    path('generate-health-report-pdf/', views.generate_health_report_pdf, name='generate-health-report-pdf'),
]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # 添加媒体文件路由