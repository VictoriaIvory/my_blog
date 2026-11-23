"""评论应用（仿 DjangoBlog 的 comments app）。

功能：
- 登录用户才能评论
- 支持无限嵌套回复（parent 指向另一条评论）
- 审核开关在「站点设置」里：开了审核，新评论默认不显示，管理员在后台批准
- 管理员/员工的评论自动通过，不用自己审自己
"""

from django.conf import settings
from django.db import models

from blog.models import BlogSettings, Post


class Comment(models.Model):
    post = models.ForeignKey(
        Post, verbose_name='文章', on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='作者',
        on_delete=models.CASCADE, related_name='comments')
    body = models.TextField('内容', max_length=1000)
    parent = models.ForeignKey(
        'self', verbose_name='回复给', null=True, blank=True,
        on_delete=models.CASCADE, related_name='replies')
    is_approved = models.BooleanField('已通过审核', default=True)
    created_at = models.DateTimeField('发表时间', auto_now_add=True)

    class Meta:
        verbose_name = '评论'
        verbose_name_plural = '评论'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.author} 评论了《{self.post.title}》'

    @property
    def is_reply(self):
        return self.parent_id is not None


def comment_needs_review(user):
    """这条评论是否要进审核队列。管理员/员工直接通过。"""
    if user.is_authenticated and user.is_staff:
        return False
    return BlogSettings.load().comment_need_review
