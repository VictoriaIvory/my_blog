"""视图（View）—— 接收请求、取数据、返回响应。

第一阶段只有两个页面：文章列表、文章详情。
"""

from django.shortcuts import get_object_or_404, render

from .models import Post


def post_list(request):
    """首页：列出所有已发布的文章。"""
    posts = Post.objects.filter(is_published=True)
    return render(request, 'blog/post_list.html', {'posts': posts})


def post_detail(request, pk):
    """文章详情页。

    注意这里把 is_published=True 也写进了查询条件：
    未发布的文章直接 404，而不是让人通过改 URL 里的 id 看到草稿。
    """
    post = get_object_or_404(Post, pk=pk, is_published=True)
    return render(request, 'blog/post_detail.html', {'post': post})
