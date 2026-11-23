"""重建全文搜索索引：python manage.py rebuild_search_index

什么时候用：
- 第一次启用全文搜索（还没生成 search_index/ 目录）；
- 直接改了数据库里的文章（后台保存会自动同步索引，但命令行 / 脚本改库不会）；
- 索引文件损坏或想彻底重建。

只重建、不删除任何文章数据；索引文件在 settings.SEARCH_INDEX_DIR
（默认 myblog/search_index/），已加进 .gitignore。
"""

from django.core.management.base import BaseCommand, CommandError

from blog.search_index import rebuild_index


class Command(BaseCommand):
    help = '重建全文搜索索引（Whoosh + jieba），并打印入库文章数'

    def add_arguments(self, parser):
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='静默模式：成功时不打印任何内容（出错仍会报错）',
        )

    def handle(self, *args, **options):
        try:
            count = rebuild_index()
        except Exception as exc:  # 依赖没装 / 索引目录写不进去 —— 给出明确报错
            raise CommandError(f'重建全文索引失败：{exc}') from exc

        if not options['quiet']:
            self.stdout.write(self.style.SUCCESS(f'索引重建完成：{count} 篇'))
