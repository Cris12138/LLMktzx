from django.urls import re_path, include
from .views import *

urlpatterns = [
    re_path(r"^modify$", modify, name="modify"),
    re_path(r"^login$", user_login, name="login"),
    re_path(r"^logout$", user_logout, name="logout"),
    re_path(r"^register$", do_register, name="register"),
]