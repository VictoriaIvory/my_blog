"""备份数据库和媒体文件：python manage.py backup

SQLite 的数据库就是一个文件，封面图都在 media/ 里——部署之后这两样
都不在 Git 里，出问题只能靠备份。

用法：
    python manage.py backup                 # 备份到 backups/时间戳/
    python manage.py backup --dir D:\\备份   # 指定备份根目录

备份里包含：
    db.sqlite3   数据库（文章、分类、标签、阅读量）
    media/       上传的封面图
"""

import shutil
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '把数据库和 media/ 复制到 backups/时间戳/ 目录'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dir',
            default=str(Path(settings.BASE_DIR) / 'backups'),
            help='备份根目录（默认项目下的 backups/）',
        )

    def handle(self, *args, **options):
        stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        target = Path(options['dir']) / stamp
        target.mkdir(parents=True, exist_ok=True)

        copied = 0
        total_bytes = 0

        db_path = Path(settings.DATABASES['default']['NAME'])
        if db_path.exists():
            shutil.copy2(db_path, target / db_path.name)
            size = (target / db_path.name).stat().st_size
            total_bytes += size
            copied += 1
            self.stdout.write(f'  数据库 -> {target / db_path.name}（{size / 1024:.1f} KB）')
        else:
            self.stdout.write(self.style.WARNING('  数据库文件不存在，跳过'))

        media_root = Path(settings.MEDIA_ROOT)
        if media_root.exists():
            shutil.copytree(media_root, target / 'media', dirs_exist_ok=True)
            for item in media_root.rglob('*'):
                if item.is_file():
                    total_bytes += item.stat().st_size
            copied += 1
            self.stdout.write(f'  媒体文件 -> {target / "media"}')
        else:
            self.stdout.write(self.style.WARNING('  media/ 不存在，跳过'))

        self.stdout.write(self.style.SUCCESS(
            f'备份完成：{copied} 项，共 {total_bytes / 1024:.1f} KB -> {target}'
        ))
        self.stdout.write('提醒：备份在项目目录里，最好再拷一份到网盘或移动硬盘。')
