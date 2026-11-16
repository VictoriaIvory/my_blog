"""总路由。

只做一件事：把 URL 前缀分给不同的地方。
具体哪个页面，由 blog/urls.py 决定。
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    # 根路径全部交给 blog 应用
    path('', include('blog.urls')),
]

# 开发环境由 Django 帮忙把上传的图片（封面图）送出去；
# 正式部署时这一步交给 Nginx / 部署平台处理（见 README「部署」一节）。
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
