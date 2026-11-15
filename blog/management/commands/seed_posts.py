"""造演示数据：python manage.py seed_posts

第一次跑起来时页面是空的，用这个命令建几个分类、插一篇占位文章，
方便看到列表页、分类筛选的效果。内容请自己替换成真实文章。

（原先造三篇，2026-11-09 按需求只保留第一篇；
 2026-11-15 阶段 2 加上分类，这里顺手建好三个常用分类。）
"""

from django.core.management.base import BaseCommand

from blog.models import Category, Post

DEMO_CATEGORIES = ['Django', '踩坑记录', '生活']

DEMO_POSTS = [
    (
        '我做记账本时踩的坑：图表为什么是空白的',
        '这是占位文章，等内容写好后替换。\n\n'
        '可以先按这个结构写：问题是什么 → 我一开始怎么做的 → 为什么不对 → 最后怎么解决的。',
        '踩坑记录',
    ),
]


class Command(BaseCommand):
    help = '建演示分类、插一篇演示文章（已存在则跳过）'

    def handle(self, *args, **options):
        for name in DEMO_CATEGORIES:
            Category.objects.get_or_create(name=name)

        created = 0
        for title, body, category_name in DEMO_POSTS:
            category = Category.objects.filter(name=category_name).first()
            defaults = {'body': body, 'category': category}
            _, is_new = Post.objects.get_or_create(title=title, defaults=defaults)
            if is_new:
                created += 1

        if created:
            self.stdout.write(self.style.SUCCESS('已创建 %d 篇演示文章' % created))
            self.stdout.write(self.style.WARNING('记得去后台把它换成你自己的真实文章'))
        else:
            self.stdout.write(self.style.WARNING('演示文章已存在，未重复创建'))
