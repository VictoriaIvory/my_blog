"""数据模型（Model）—— 博客文章。

一个类 = 一张表，一个字段 = 一列。
写完这里执行 makemigrations + migrate，Django 自动建表。
"""

from django.db import models


class Post(models.Model):
    """一篇博客文章。"""

    title = models.CharField('标题', max_length=100)
    body = models.TextField('正文')
    is_published = models.BooleanField('已发布', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '文章'
        verbose_name_plural = '文章'
        ordering = ['-created_at']  # 默认最新的在最前面

    def __str__(self):
        return self.title

    @property
    def summary(self):
        """列表页用的摘要：取正文前 80 个字，超出的加省略号。"""
        text = self.body.strip().replace('\n', ' ')
        return text if len(text) <= 80 else text[:80] + '…'
