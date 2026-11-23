"""评论应用的视图。"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from blog.models import BlogSettings, Post

from .forms import CommentForm
from .models import Comment, comment_needs_review


@login_required
@require_POST
def post_comment(request, post_id):
    """发表评论（登录后可用）。回复通过 hidden parent 字段传。

    用 Post.objects.visible()：给草稿、或还没到发布时间的定时文章发评论
    一律 404（和详情页口径一致，不能靠直接 POST 绕过）。
    """
    post = get_object_or_404(Post.objects.visible(), pk=post_id)
    site = BlogSettings.load()

    if not site.allow_site_comments or not post.allow_comments:
        messages.error(request, '这篇文章的评论已关闭。')
        return redirect(post.get_absolute_url())

    form = CommentForm(request.POST)
    if not form.is_valid():
        messages.error(request, '评论内容不能为空，也不能超过 1000 字。')
        return redirect(post.get_absolute_url() + '#comment-form')

    comment = form.save(commit=False)
    comment.post = post
    comment.author = request.user

    parent_id = request.POST.get('parent', '').strip()
    if parent_id.isdigit():
        parent = Comment.objects.filter(pk=int(parent_id), post=post).first()
        if parent:
            comment.parent = parent

    comment.is_approved = not comment_needs_review(request.user)
    comment.save()

    if comment.is_approved:
        messages.success(request, '评论发表成功。')
    else:
        messages.info(request, '评论已提交，管理员审核通过后显示。')
    return redirect(post.get_absolute_url() + '#comments')
