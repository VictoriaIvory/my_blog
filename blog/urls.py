"""blog 应用的路由。

app_name 给路由命名空间，模板里就能写 {% url 'blog:detail' post.pk %}
"""

from django.urls import path

from . import views
from .feeds import LatestPostsFeed
from .sitemap import sitemap

app_name = 'blog'

urlpatterns = [
    # 首页：http://127.0.0.1:8000/
    path('', views.post_list, name='list'),
    # 详情：http://127.0.0.1:8000/post/3/
    path('post/<int:pk>/', views.post_detail, name='detail'),
    # 归档：http://127.0.0.1:8000/archive/
    path('archive/', views.archive, name='archive'),
    # 关于：http://127.0.0.1:8000/about/
    path('about/', views.about, name='about'),
    # RSS 订阅：http://127.0.0.1:8000/feed/
    path('feed/', LatestPostsFeed(), name='feed'),
    # 站点地图：http://127.0.0.1:8000/sitemap.xml
    path('sitemap.xml', sitemap, name='sitemap'),
]
