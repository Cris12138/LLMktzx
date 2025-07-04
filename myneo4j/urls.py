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
    re_path(r"^$", first_view, name="first"),
    re_path(r"^about$",about_view,name="about"),
    re_path(r"^index$", index, name="index"),
    re_path(r"^wenda$", wenda, name="wenda"),
    # AJAX问答路由
    path('wenda_ajax/', views.wenda_ajax, name='wenda_ajax'),

    # 论坛相关路由
    re_path(r"^forum$", forum, name="forum"),
    path('forum/post/new/', create_post, name='create_post'),
    path('forum/post/<int:post_id>/', post_detail, name='post_detail'),
    path('user/<int:user_id>/posts/', user_posts, name='user_posts'),
    path('user/<int:user_id>/replies/', user_replies, name='user_replies'),
    path('forum/post/<int:post_id>/edit/', edit_post, name='edit_post'),
    path('forum/post/<int:post_id>/delete/', delete_post, name='delete_post'),
    path('toggle_like/<int:post_id>/', toggle_like, name='toggle_like'),
    path('delete_reply/<int:reply_id>/', delete_reply, name='delete_reply'),

    # 健康评估路由
    re_path(r"^health-assessment/$", health_assessment, name="health-assessment"),
    path('health-assessment/', views.health_assessment, name='health-assessment'),
    path('generate-health-report-pdf/', views.generate_health_report_pdf, name='generate-health-report-pdf'),

    # 电子病历管理路由 - 新增
    path('electronic-medical-records/', views.electronic_medical_records, name='electronic-medical-records'),

    # 电子病历 AJAX 接口
    path('api/medical-records/', views.medical_records_ajax, name='medical_records_ajax'),
    path('api/medications/', views.medications_ajax, name='medications_ajax'),
    path('api/lab-reports/', views.lab_reports_ajax, name='lab_reports_ajax'),
    path('api/vital-signs/', views.vital_signs_ajax, name='vital_signs_ajax'),
    path('api/patient-profile/', views.get_patient_profile_ajax, name='get_patient_profile_ajax'),

    # 电子病历数据操作接口
    path('api/add-medical-record/', views.add_medical_record, name='add_medical_record'),
    path('api/add-medication/', views.add_medication, name='add_medication'),
    path('api/add-vital-signs/', views.add_vital_signs, name='add_vital_signs'),
    path('api/upload-lab-report/', views.upload_lab_report, name='upload_lab_report'),
    path('api/update-patient-profile/', views.update_patient_profile, name='update_patient_profile'),

    # AJAX 聊天管理路由（修复重复定义）
    path('new_chat_ajax/', views.new_chat_ajax, name='new_chat_ajax'),
    path('get_chat_history_ajax/', views.get_chat_history_ajax, name='get_chat_history_ajax'),
    path('clear_all_chats_ajax/', views.clear_all_chats_ajax, name='clear_all_chats_ajax'),
    path('clear_current_chat_ajax/', views.clear_current_chat_ajax, name='clear_current_chat_ajax'),

    # 对话管理路由
    path('api/rename_chat/<int:session_id>/', views.rename_chat, name='rename_chat'),
    path('api/delete_chat/<int:session_id>/', views.delete_chat, name='delete_chat'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)