"""自定义模板标签：侧边栏。"""
from django import template
from django.db.models import Count, Q

from blog.models import BlogSettings, Post, Tag, visible_condition
from comments.models import Comment

register = template.Library()


@register.inclusion_tag('blog/_sidebar.html')
def sidebar():
    """侧边栏：最新文章、最多阅读、标签云、最新评论、页面入口。

    每一块都只取「前台可见」的内容：草稿、还没到发布时间的定时文章，
    以及它们下面的评论，都不能出现在侧边栏。
    """
    site = BlogSettings.load()
    article_count = site.sidebar_article_count
    comment_count = site.sidebar_comment_count

    latest_posts = list(
        Post.objects.visible()
        .filter(is_page=False)
        .only('id', 'title', 'pub_time')[:article_count]
    )
    popular_posts = list(
        Post.objects.visible()
        .filter(is_page=False)
        .only('id', 'title', 'views', 'pub_time')
        .order_by('-views', '-pub_time')[:article_count]
    )
    tags = list(
        Tag.objects
        .annotate(post_count=Count(
            'posts', filter=visible_condition('posts__') & Q(posts__is_page=False)))
        .filter(post_count__gt=0)
        .order_by('-post_count', 'name')[:20]
    )
    # 评论是通过外键反查文章，用 visible_condition('post__') 加上同样的可见性条件
    latest_comments = list(
        Comment.objects
        .filter(Q(is_approved=True) & visible_condition('post__'))
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
