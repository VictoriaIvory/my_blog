"""总路由。

只做一件事：把 URL 前缀分给不同的地方。
具体哪个页面，由 blog/urls.py 决定。
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    # 根路径全部交给 blog 应用
    path('', include('blog.urls')),
]
