"""全站模板上下文：站点设置 + 导航里的独立页面。"""
from django.db import OperationalError, ProgrammingError

from .models import BlogSettings, Post


def blog_context(request):
    """每个模板都能拿到 `site`（站点设置）和 `nav_pages`（导航页面）。"""
    try:
        site = BlogSettings.load()
        # 导航里的独立页面也要遵守可见性：草稿 / 定时未到点的页面不能出现
        nav_pages = list(
            Post.objects.visible()
            .filter(is_page=True)
            .only('id', 'title')[:10]
        )
    except (OperationalError, ProgrammingError):
        # 还没跑迁移（比如刚 clone 下来执行 check）时不至于整站报错
        site = BlogSettings()
        nav_pages = []

    return {'site': site, 'nav_pages': nav_pages}
