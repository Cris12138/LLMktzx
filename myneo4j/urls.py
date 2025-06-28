from django.urls import re_path
from django.urls import path, re_path
from .views import *

urlpatterns = [
    re_path(r"^$", wenda, name="wenda"),
    re_path(r"^index$", index, name="index"),
    re_path(r"^wenda$", wenda, name="wenda"),
    re_path(r"^health-assessment/$", health_assessment, name="health-assessment"),  # 确保无空格
]