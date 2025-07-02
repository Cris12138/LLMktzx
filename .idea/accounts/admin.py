from django.contrib import admin
from .models import UserProfile
# Register your models here.
from django.contrib.auth.hashers import make_password

from django.contrib.auth.models import Group

admin.site.unregister(Group)

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'username')
    search_fields = ['username']
    fieldsets = (
        ['用户信息', {
            'fields': ('username', 'mpassword', 'is_superuser'),
        }],

    )

    def save_model(self, request, obj, form, change):
        if form.is_valid():
            obj.password = make_password(obj.mpassword)
        super().save_model(request, obj, form, change)


admin.site.register(UserProfile, UserProfileAdmin)

admin.site.site_title = "医疗问答管理端"
admin.site.site_header = "医疗问答管理端"