"""视图（View）—— 接收请求、取数据、返回响应。

列表页的筛选（都走 URL 查询参数，同一个视图）：
  /                    全部文章
  /?category=Django    只看某个分类
  /?tag=部署           只看某个标签
  /?q=饼图             搜索标题或正文
  /?page=2             第二页
可以叠加：/?category=Django&tag=部署&q=模板&page=2

2026-11-16 新增：标签筛选、阅读量计数、相关文章、归档页、关于页。
"""

from django.core.paginator import Paginator
from django.db.models import Count, F, Q, Sum
from django.shortcuts import get_object_or_404, render

from .markdown_render import extract_toc
from .models import Category, Post, Tag

# 每页显示几篇。放成常量，以后想改只改这一处。
PAGE_SIZE = 5


def _page_numbers(page_obj):
    """分页条要显示哪些页码。

    页数少（≤7）就全显示；多了只显示首尾两页 + 当前页附近两页，
    中间用 None 表示省略号，由模板渲染成「…」。
    """
    total = page_obj.paginator.num_pages
    current = page_obj.number
    if total <= 7:
        return list(range(1, total + 1))

    candidates = {1, 2, total - 1, total, current - 1, current, current + 1}
    numbers, previous = [], 0
    for number in sorted(candidates):
        if not 1 <= number <= total:
            continue
        if previous and number - previous > 1:
            numbers.append(None)   # 省略号占位
        numbers.append(number)
        previous = number
    return numbers


def _tag_queryset():
    """有已发布文章的标签，带文章数（标签云/筛选条用）。"""
    return Tag.objects.annotate(
        post_count=Count('posts', filter=Q(posts__is_published=True)),
    ).filter(post_count__gt=0)


def post_list(request):
    """首页：列出已发布的文章，支持分类 / 标签 / 搜索 / 分页。"""
    # 1. 先把「只显示已发布」这个底线定下来，后面的筛选都在它之上叠加
    posts = Post.objects.filter(is_published=True).select_related('category')

    # 2. 搜索：标题或正文包含关键词。Q 对象用来表达「或」。
    q = request.GET.get('q', '').strip()
    if q:
        posts = posts.filter(Q(title__icontains=q) | Q(body__icontains=q))

    # 3. 分类筛选。分类名不存在时给空结果，而不是把全部文章倒出来。
    category_name = request.GET.get('category', '').strip()
    category = None
    if category_name:
        category = Category.objects.filter(name=category_name).first()
        posts = posts.filter(category=category) if category else posts.none()

    # 4. 标签筛选（多对多；标签不存在同样给空结果）。
    tag_name = request.GET.get('tag', '').strip()
    tag = None
    if tag_name:
        tag = Tag.objects.filter(name=tag_name).first()
        posts = posts.filter(tags=tag) if tag else posts.none()

    # 5. 分页。get_page 会把非法页码（0 / 999 / abc）兜底成第一页或最后一页。
    paginator = Paginator(posts, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page'))

    # 6. 「第 2 页」这类链接要保留当前的搜索词、分类和标签，
    #    所以把 page 从现有参数里拿掉，剩下的拼回去。
    params = request.GET.copy()
    params.pop('page', None)
    querystring = params.urlencode()

    context = {
        'page_obj': page_obj,
        'posts': page_obj.object_list,
        'categories': Category.objects.all(),
        'tags': _tag_queryset(),
        'current_category': category,
        'current_tag': tag,
        'q': q,
        'querystring': querystring,
        'page_numbers': _page_numbers(page_obj),
        'total_count': paginator.count,
        # 首页头图只在「没有任何筛选、第一页」时出现
        'show_hero': not q and not category and not tag and page_obj.number == 1,
        'published_count': Post.objects.filter(is_published=True).count(),
        'category_count': Category.objects.count(),
        'tag_count': _tag_queryset().count(),
        'total_views': Post.objects.filter(is_published=True).aggregate(
            total=Sum('views'))['total'] or 0,
        'latest_post': Post.objects.filter(is_published=True).first(),
    }
    return render(request, 'blog/post_list.html', context)


def _related_posts(post, limit=3):
    """相关文章：先按共同标签，再按同分类，最多 limit 篇。"""
    base = (
        Post.objects.filter(is_published=True)
        .exclude(pk=post.pk)
        .select_related('category')
    )

    related = []
    if post.tags.exists():
        related = list(
            base.filter(tags__in=post.tags.all()).distinct()[:limit]
        )

    if len(related) < limit and post.category_id:
        exclude_ids = [p.pk for p in related] + [post.pk]
        related += list(
            base.filter(category=post.category).exclude(pk__in=exclude_ids)
            [:limit - len(related)]
        )
    return related


def post_detail(request, pk):
    """文章详情页。

    注意这里把 is_published=True 也写进了查询条件：
    未发布的文章直接 404，而不是让人通过改 URL 里的数字看到草稿。
    """
    post = get_object_or_404(Post, pk=pk, is_published=True)

    # 阅读量 +1：用 F 表达式在数据库里自增，避免「读出来加一再写回」的并发覆盖
    Post.objects.filter(pk=post.pk).update(views=F('views') + 1)
    post.refresh_from_db(fields=['views'])

    published = Post.objects.filter(is_published=True)

    # 上一篇 = 更早的一篇（pk 更小）；下一篇 = 更新的一篇
    prev_post = published.filter(pk__lt=post.pk).order_by('-pk').first()
    next_post = published.filter(pk__gt=post.pk).order_by('pk').first()

    context = {
        'post': post,
        'toc': extract_toc(post.body_html),
        'prev_post': prev_post,
        'next_post': next_post,
        'related_posts': _related_posts(post),
    }
    return render(request, 'blog/post_detail.html', context)


def archive(request):
    """归档页：按年月把已发布文章分组。"""
    posts = Post.objects.filter(is_published=True).only('title', 'created_at', 'pk')

    groups = []
    for post in posts:
        key = (post.created_at.year, post.created_at.month)
        if not groups or groups[-1]['key'] != key:
            groups.append({
                'key': key,
                'year': key[0],
                'month': key[1],
                'posts': [],
            })
        groups[-1]['posts'].append(post)

    return render(request, 'blog/archive.html', {
        'groups': groups,
        'total_count': len(posts),
    })


def about(request):
    """关于页：这个博客是什么、用了什么技术、怎么搭的。"""
    return render(request, 'blog/about.html', {
        'published_count': Post.objects.filter(is_published=True).count(),
        'category_count': Category.objects.count(),
        'tag_count': _tag_queryset().count(),
    })
