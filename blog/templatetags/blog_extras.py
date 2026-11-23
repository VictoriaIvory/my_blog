"""自定义模板标签：侧边栏。"""
from django import template
from django.db.models import Count, Q

from blog.models import BlogSettings, Post, Tag
from comments.models import Comment

register = template.Library()


@register.inclusion_tag('blog/_sidebar.html')
def sidebar():
    """侧边栏：最新文章、最多阅读、标签云、最新评论、页面入口。"""
    site = BlogSettings.load()
    article_count = site.sidebar_article_count
    comment_count = site.sidebar_comment_count

    latest_posts = list(
        Post.objects
        .filter(is_published=True, is_page=False)
        .only('id', 'title', 'created_at')[:article_count]
    )
    popular_posts = list(
        Post.objects
        .filter(is_published=True, is_page=False)
        .only('id', 'title', 'views')
        .order_by('-views', '-created_at')[:article_count]
    )
    tags = list(
        Tag.objects
        .annotate(post_count=Count(
            'posts', filter=Q(posts__is_published=True, posts__is_page=False)))
        .filter(post_count__gt=0)
        .order_by('-post_count', 'name')[:20]
    )
    latest_comments = list(
        Comment.objects
        .filter(is_approved=True, post__is_published=True)
        .select_related('author', 'post')
        .order_by('-created_at')[:comment_count]
    )

    return {
        'site': site,
        'latest_posts': latest_posts,
        'popular_posts': popular_posts,
        'tags': tags,
        'latest_comments': latest_comments,
    }
