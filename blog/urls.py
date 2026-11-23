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
    # 独立页面（关于/留言板等）：http://127.0.0.1:8000/page/2/
    path('page/<int:pk>/', views.page_detail, name='page_detail'),
    # 归档：http://127.0.0.1:8000/archive/
    path('archive/', views.archive, name='archive'),
    # 关于：http://127.0.0.1:8000/about/
    path('about/', views.about, name='about'),
    # RSS 订阅：http://127.0.0.1:8000/feed/
    path('feed/', LatestPostsFeed(), name='feed'),
    # 站点地图：http://127.0.0.1:8000/sitemap.xml
    path('sitemap.xml', sitemap, name='sitemap'),
    # 抓取规则：http://127.0.0.1:8000/robots.txt
    path('robots.txt', views.robots, name='robots'),
]
