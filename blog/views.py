"""视图（View）—— 接收请求、取数据、返回响应。

阶段 1：文章列表、文章详情。
阶段 2：列表页加上分类筛选、关键词搜索、分页。

三个功能都通过 URL 查询参数实现（同一个视图，路由不用改）：
  /                    全部文章
  /?category=Django    只看某个分类
  /?q=饼图             搜索标题或正文
  /?page=2             第二页
可以叠加：/?category=Django&q=模板&page=2
"""

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import Category, Post

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


def post_list(request):
    """首页：列出已发布的文章，支持分类筛选、搜索、分页。"""
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

    # 4. 分页。get_page 会把非法页码（0 / 999 / abc）兜底成第一页或最后一页，
    #    不用自己处理越界。
    paginator = Paginator(posts, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page'))

    # 5. 「第 2 页」这类链接要保留当前的搜索词和分类，
    #    所以把 page 从现有参数里拿掉，剩下的拼回去。
    params = request.GET.copy()
    params.pop('page', None)
    querystring = params.urlencode()

    context = {
        'page_obj': page_obj,
        'posts': page_obj.object_list,   # 保留这个名字，阶段 1 的模板/测试不用大改
        'categories': Category.objects.all(),
        'current_category': category,
        'q': q,
        'querystring': querystring,
        'page_numbers': _page_numbers(page_obj),
        'total_count': paginator.count,
    }
    return render(request, 'blog/post_list.html', context)


def post_detail(request, pk):
    """文章详情页。

    注意这里把 is_published=True 也写进了查询条件：
    未发布的文章直接 404，而不是让人通过改 URL 里的 id 看到草稿。
    """
    post = get_object_or_404(Post, pk=pk, is_published=True)
    return render(request, 'blog/post_detail.html', {'post': post})
