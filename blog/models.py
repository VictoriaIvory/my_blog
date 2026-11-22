"""数据模型（Model）—— 博客文章、分类、标签。

一个类 = 一张表，一个字段 = 一列。
写完这里执行 makemigrations + migrate，Django 自动建表。
"""

from django.db import models
from django.utils.functional import cached_property


class Category(models.Model):
    """文章分类。

    阶段 2 加的第一个模型。故意不加 slug 字段：
    分类直接按名字筛选（/?category=Django），中文分类名由 Django 自动
    urlencode，URL 里不会出现拼音或一长串编码。
    """

    name = models.CharField('名称', max_length=30, unique=True)

    class Meta:
        verbose_name = '分类'
        verbose_name_plural = '分类'
        ordering = ['name']

    def __str__(self):
        return self.name


class Tag(models.Model):
    """文章标签（多对多，一篇可以贴多个）。

    和分类的分工：分类是「这篇属于哪个栏目」（一个），
    标签是「这篇提到了哪些关键词」（多个），也用来做相关文章推荐。
    """

    name = models.CharField('名称', max_length=20, unique=True)

    class Meta:
        verbose_name = '标签'
        verbose_name_plural = '标签'
        ordering = ['name']

    def __str__(self):
        return self.name


class Post(models.Model):
    """一篇博客文章。"""

    title = models.CharField('标题', max_length=100)
    body = models.TextField('正文')
    cover = models.ImageField(
        '封面图',
        upload_to='covers/%Y/%m/',
        null=True,
        blank=True,
        help_text='可选。列表页显示成卡片顶部的大图，建议 16:9。',
    )
    category = models.ForeignKey(
        Category,
        verbose_name='分类',
        null=True,          # 允许没有分类：老文章不用逼着补
        blank=True,
        on_delete=models.SET_NULL,   # 分类被删，文章还在，只是变回"未分类"
        related_name='posts',
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='标签',
        blank=True,
        related_name='posts',
    )
    is_published = models.BooleanField('已发布', default=True)
    views = models.PositiveIntegerField('阅读量', default=0, editable=False)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '文章'
        verbose_name_plural = '文章'
        ordering = ['-created_at']  # 默认最新的在最前面

    def __str__(self):
        return self.title

    # 封面图上传后自动压缩到 1600px 宽（手机照片动辄 4000px / 5MB）
    MAX_COVER_WIDTH = 1600

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._shrink_cover()

    def _shrink_cover(self):
        """把过宽的封面图缩到 1600px，失败（比如测试里的假图片）就跳过。"""
        if not self.cover:
            return
        try:
            from PIL import Image, UnidentifiedImageError

            image = Image.open(self.cover.path)
            if image.width <= self.MAX_COVER_WIDTH:
                return

            ratio = self.MAX_COVER_WIDTH / image.width
            image = image.resize(
                (self.MAX_COVER_WIDTH, round(image.height * ratio)),
                Image.LANCZOS,
            )
            if image.mode in ('RGBA', 'P'):
                image = image.convert('RGB')
            image.save(self.cover.path, optimize=True, quality=86)
        except (UnidentifiedImageError, OSError, ValueError):
            # 不是有效图片 / 存储后端不支持直接写文件 —— 跳过压缩，不影响保存
            pass

    @cached_property
    def body_html(self):
        """正文渲染成 HTML（阶段 3）。

        模板里写 {{ post.body_html|safe }}。
        用 cached_property：详情页要拿它生成目录 + 渲染正文，
        同一个实例只渲染一次；Markdown + bleach 不便宜。
        """
        from .markdown_render import render_markdown
        return render_markdown(self.body)

    @cached_property
    def summary(self):
        """列表页用的摘要：纯文本前 80 个字，超出的加省略号。"""
        from .markdown_render import make_summary
        return make_summary(self.body, 80)

    @cached_property
    def word_count(self):
        """正文有效字符数（去掉空白），用于阅读时间估算。"""
        from .markdown_render import count_chars
        return count_chars(self.body)

    @cached_property
    def reading_time(self):
        """估算阅读时间（分钟）：按中文 400 字/分钟，至少 1 分钟。"""
        return max(1, round(self.word_count / 400))
