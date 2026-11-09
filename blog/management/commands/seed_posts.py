"""造演示数据：python manage.py seed_posts

第一次跑起来时页面是空的，用这个命令插一篇占位文章，
方便看到列表页和详情页的效果。内容请自己替换成真实文章。

（原先造三篇，2026-11-09 按需求只保留第一篇。）
"""

from django.core.management.base import BaseCommand

from blog.models import Post

DEMO_POSTS = [
    (
        '我做记账本时踩的坑：图表为什么是空白的',
        '这是占位文章，等内容写好后替换。\n\n'
        '可以先按这个结构写：问题是什么 → 我一开始怎么做的 → 为什么不对 → 最后怎么解决的。',
    ),
]


class Command(BaseCommand):
    help = '插入一篇演示文章（已存在则跳过）'

    def handle(self, *args, **options):
        created = 0
        for title, body in DEMO_POSTS:
            _, is_new = Post.objects.get_or_create(title=title, defaults={'body': body})
            if is_new:
                created += 1

        if created:
            self.stdout.write(self.style.SUCCESS('已创建 %d 篇演示文章' % created))
            self.stdout.write(self.style.WARNING('记得去后台把它换成你自己的真实文章'))
        else:
            self.stdout.write(self.style.WARNING('演示文章已存在，未重复创建'))
