from django.shortcuts import render, redirect
from .models import UserProfile
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout, login, authenticate
from .forms import LoginForm
# Create your views here.


def do_register(request):
    try:
        msg = ""
        if request.method == "GET":
            return render(request, "register.html", locals())
        if request.method == "POST":
            user = request.user
            datas = request.POST
            username = request.POST.get("username")
            password = request.POST.get("password")
            password2 = request.POST.get("password2")


            if len(username) < 3 or len(password) < 6 or len(password2) < 6:
                msg="账号必须大于3位，密码必须大于6位"
                return render(request, "register.html", locals())
            # 验证密码长度
            if len(password) < 6:
                msg = "密码长度必须至少6位"
                return render(request, "register.html", locals())

            # 验证确认密码长度
            if len(password2) < 6:
                msg = "确认密码长度必须至少6位"
                return render(request, "register.html", locals())

            # 验证一致性
            if password != password2:
                msg = "两次输入的密码不一致"
                return render(request, "register.html", locals())
            only = UserProfile.objects.filter(username=username)
            if len(only) > 0:
                msg = "用户名已经存在"
                return render(request, "register.html", locals())
            new_user = UserProfile()
            new_user.username = username
            new_user.set_password(password)
            new_user.mpassword = password
            new_user.save()
            return redirect("accounts:login")
        else:
            return render(request, "register.html", locals())
    except Exception as e:
        print(e)
        msg = "添加失败系统错误"
        return render(request, "register.html", locals())


def user_login(request):
    try:
        if request.user.is_authenticated:
            return redirect("/")
        if request.method == 'POST':
            login_form = LoginForm(request.POST)
            if login_form.is_valid():
                username = login_form.cleaned_data["username"]
                password = login_form.cleaned_data["password"]
                user = authenticate(username=username,password=password)
                if user is not None:
                    # user.backend = 'django.contrib.auth.backends.ModelBackend' # 指定默认的登录验证方式

                    login(request, user)
                else:
                    errorinfo = "账号或密码不正确"
                    return render(request, 'login.html', {'login_form': login_form, "errorinfo":errorinfo})
                return redirect("/")
            else:
                errorinfo = "账号或密码不正确或格式错误"
                return render(request, 'login.html', {'login_form': login_form, "errorinfo":errorinfo})
        else:
            login_form = LoginForm()
            return render(request, 'login.html', {'login_form': login_form})
    except Exception as e:
        login_form = LoginForm()
        print(e)
        errorinfo = "系统错误"
        return render(request, 'login.html', {'login_form': login_form, "errorinfo":errorinfo})

@login_required
def user_logout(request):
    try:
        logout(request)
        return redirect('accounts:login')
    except Exception as e:
        print(e)
    return render(request, "error.html", {"msg":"退出错误"})

@login_required
def modify(request):
    try:
        user = request.user
        if request.method == 'POST':
            oldpassword = request.POST.get("oldpassword")
            newpassword = request.POST.get("newpassword")
            conpassword = request.POST.get("conpassword")
            print(user.mpassword)
            print(oldpassword)
            if user.mpassword != oldpassword:
                errorinfo = "旧密码错误"
                return render(request, 'modify.html',  locals())
            if newpassword != conpassword:
                errorinfo = "新旧密码不一致"
                return render(request, 'modify.html',  locals())
            if len(newpassword) < 6:
                errorinfo = "密码大于6位"
                return render(request, 'modify.html', locals())
            user.mpassword = newpassword
            user.set_password(newpassword)
            user.save()
            logout(request)
            return redirect("/accounts/login")
        else:
            return render(request, 'modify.html', locals())
    except Exception as e:
        print(e)
        errorinfo = "系统错误"
        return render(request, 'modify.html',  locals())
