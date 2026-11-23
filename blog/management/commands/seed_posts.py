"""造演示数据：python manage.py seed_posts

第一次跑起来时页面是空的，用这个命令建：
- 站点设置（一行）
- 几个分类 / 标签
- 一篇占位文章
- 一个「留言板」独立页面（可以直接体验评论功能）

内容请自己替换成真实文章。历史：
（原先造三篇，2026-11-09 按需求只保留第一篇；
 2026-11-15 阶段 2 加分类；2026-11-16 功能扩展加标签；
 2026-11-23 复现 DjangoBlog 加站点设置、独立页面、评论。）
"""

from django.core.management.base import BaseCommand

from blog.models import STATUS_PUBLISHED, BlogSettings, Category, Post, Tag

DEMO_CATEGORIES = ['Django', '踩坑记录', '生活']

DEMO_TAGS = ['Django', 'Markdown', '踩坑']

DEMO_POSTS = [
    (
        '我做记账本时踩的坑：图表为什么是空白的',
        '这是占位文章，等内容写好后替换。\n\n'
        '可以先按这个结构写：问题是什么 → 我一开始怎么做的 → 为什么不对 → 最后怎么解决的。',
        '踩坑记录',
        ['踩坑'],
    ),
]

DEMO_PAGES = [
    (
        '留言板',
        '有什么想说的、想问的，都可以写在下面。\n\n'
        '留言需要登录，注册一个账号就行。',
    ),
]


class Command(BaseCommand):
    help = '建站点设置、演示分类/标签/文章/页面（已存在则跳过）'

    def handle(self, *args, **options):
        site = BlogSettings.load()
        self.stdout.write(f'站点设置：{site.site_name}')

        for name in DEMO_CATEGORIES:
            Category.objects.get_or_create(name=name)
        for name in DEMO_TAGS:
            Tag.objects.get_or_create(name=name)

        created = 0
        for title, body, category_name, tag_names in DEMO_POSTS:
            category = Category.objects.filter(name=category_name).first()
            defaults = {'body': body, 'category': category}
            post, is_new = Post.objects.get_or_create(title=title, defaults=defaults)
            if is_new:
                post.tags.set(Tag.objects.filter(name__in=tag_names))
                created += 1

        pages = 0
        for title, body in DEMO_PAGES:
            _, is_new = Post.objects.get_or_create(
                title=title,
                defaults={
                    'body': body,
                    'is_page': True,
                    # 2026-11-23：is_published 拆成「状态 + 发布时间」，演示页面直接发布
                    'status': STATUS_PUBLISHED,
                    'allow_comments': True,
                },
            )
            pages += int(is_new)

        if created:
            self.stdout.write(self.style.SUCCESS('已创建 %d 篇演示文章' % created))
            self.stdout.write(self.style.WARNING('记得去后台把它换成你自己的真实文章'))
        else:
            self.stdout.write(self.style.WARNING('演示文章已存在，未重复创建'))

        if pages:
            self.stdout.write(self.style.SUCCESS('已创建 %d 个页面' % pages))
