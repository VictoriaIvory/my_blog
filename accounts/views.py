"""登录 / 注册 / 退出 / 个人中心。"""
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import RegisterForm


def login_view(request):
    """登录；支持 ?next= 登录后跳回原页面。"""
    if request.user.is_authenticated:
        return redirect('blog:list')

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password'],
        )
        if user is not None:
            login(request, user)
            messages.success(request, f'欢迎回来，{user.username}。')

            next_url = request.POST.get('next') or request.GET.get('next') or ''
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}
            ):
                return redirect(next_url)
            return redirect('blog:list')
        messages.error(request, '用户名或密码不对。')

    return render(request, 'accounts/login.html', {
        'form': form,
        'next': request.GET.get('next', ''),
    })


def register_view(request):
    """注册：成功后直接登录。"""
    if request.user.is_authenticated:
        return redirect('blog:list')

    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f'注册成功，欢迎你，{user.username}。')
        return redirect('blog:list')

    return render(request, 'accounts/register.html', {'form': form})


@require_POST
def logout_view(request):
    """退出：Django 5 要求 POST，避免被 GET 链接误触发。"""
    logout(request)
    messages.info(request, '你已退出登录。')
    return redirect(reverse('blog:list'))


@login_required
def profile(request):
    """个人中心：账号信息 + 我发过的评论。"""
    comments = (
        request.user.comments
        .select_related('post')
        .order_by('-created_at')
    )
    return render(request, 'accounts/profile.html', {
        'comments': comments,
        'comment_count': comments.count(),
    })
