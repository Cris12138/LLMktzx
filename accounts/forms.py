#coding:utf-8
from django import forms
from accounts.models import UserProfile
import re
import sys
import os

#登录表单
class LoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={"placeholder": "用户名", "required": "required","id":"user","name":"username"}),
                              max_length=100,error_messages={"required": "username不能为空",})

    password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "密码", "required": "required","id":"password","name":"password"}),
                              max_length=200,error_messages={"required": "password不能为空",})

#注册表单
class RegForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={"placeholder": "用户名", "required": "required",}),
                              max_length=50,error_messages={"required": "用户名不能为空",})
    email = forms.EmailField(widget=forms.TextInput(attrs={"placeholder": "邮箱", "required": "required",}),
                              max_length=50,error_messages={"required": "邮件不能为空",})
    password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "密码", "required": "required",}),
                              max_length=20,error_messages={"required": "密码不能为空",})
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "确认密码", "required": "required",}),
                              max_length=20,error_messages={"required": "确认密码不能为空",})

    def clean(self):
        if not self.is_valid():
             raise forms.ValidationError('所有项都为必填项')
        elif self.cleaned_data['confirm_password'] != self.cleaned_data['password']:
            raise forms.ValidationError('两次输入密码不一致')
        else:
            cleaned_data = super(RegForm,self).clean()
        username = self.cleaned_data['username']
        is_email_exist = UserProfile.objects.filter(email=username).exists()
        is_username_exist = UserProfile.objects.filter(username=username).exists()
        if is_username_exist or is_email_exist:
            raise forms.ValidationError(u"该账号已被注册")

        return cleaned_data

#注册表单
class RegPhoneForm(forms.Form):
    # username = forms.CharField(widget=forms.TextInput(attrs={"placeholder": "用户名", "required": "required",}),
    #                           max_length=50,error_messages={"required": "用户名不能为空",})
    phone = forms.CharField(widget=forms.TextInput(attrs={"placeholder": "手机", "required": "required",}),
                              max_length=50,error_messages={"required": "手机不能为空",})
    # email = forms.EmailField(widget=forms.TextInput(attrs={"placeholder": "邮箱", }),
    #                          max_length=50, )
    # password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "密码", "required": "required",}),
    #                           max_length=20,error_messages={"required": "密码不能为空",})
    # confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "确认密码", "required": "required",}),
    #                           max_length=20,error_messages={"required": "确认密码不能为空",})

    def clean(self):
        if not self.is_valid():
             raise forms.ValidationError('所有项都为必填项')
        else:
            cleaned_data = super(RegPhoneForm,self).clean()
        phone = self.cleaned_data['phone']
        is_mobile_exist = UserProfile.objects.filter(mobile=phone).exists()
        if is_mobile_exist:
            raise forms.ValidationError(u"该手机号已被注册")
        p2 = r'^0\d{2,3}\d{7,8}$|^1[3578]\d{9}$|^147\d{8}'
        phonematch = re.findall(r'^0\d{2,3}\d{7,8}$|^1[358]\d{9}$|^147\d{8}', phone)
        if len(phonematch) == 0 or phonematch==None or phonematch=="" :
            raise forms.ValidationError(u"该手机号格式错误")
        return cleaned_data


