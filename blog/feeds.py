"""RSS 订阅源（/feed/）。

用 Django 自带的 syndication 框架，不引第三方库：
浏览器/阅读器订阅后能看到最新 20 篇文章。

注意：Django 5.2 的 Feed 不再把 request 挂在 self 上，
要在 get_feed 里自己存一下，才能生成绝对 URL（RSS 要求绝对地址）。
"""

from django.contrib.syndication.views import Feed
from django.urls import reverse

from .models import Post


class LatestPostsFeed(Feed):
    title = '我的博客'
    description = '记录做过的事，和踩过的坑。'
    link = '/'

    def get_feed(self, obj, request):
        # 先存 request，后面的 link / item_link 都要用它拼绝对地址
        self._request = request
        return super().get_feed(obj, request)

    def link(self, obj):
        return self._request.build_absolute_uri('/')

    def items(self):
        # 只订阅前台可见的文章：草稿 / 还没到发布时间的文章不进 RSS
        return Post.objects.visible().filter(is_page=False)[:20]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.summary

    def item_link(self, item):
        path = reverse('blog:detail', args=[item.pk])
        return self._request.build_absolute_uri(path)

    def item_pubdate(self, item):
        # 发布时间（不是创建时间）：定时发布到点后，RSS 时间也才对得上
        return item.pub_time

    def item_updateddate(self, item):
        return item.updated_at
