"""自动化测试。

跑法：python manage.py test
每个测试验证一条行为，改坏代码时能立刻发现。
"""

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Category, Post


class PostListTests(TestCase):
    def test_list_shows_only_published(self):
        """首页只显示已发布的文章。"""
        Post.objects.create(title='公开的文章', body='正文', is_published=True)
        Post.objects.create(title='草稿文章', body='正文', is_published=False)

        response = self.client.get(reverse('blog:list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '公开的文章')
        self.assertNotContains(response, '草稿文章')

    def test_list_orders_newest_first(self):
        """首页按创建时间倒序。"""
        old = Post.objects.create(title='早的文章', body='x')
        new = Post.objects.create(title='晚的文章', body='x')
        # 手动改时间，模拟先后
        Post.objects.filter(pk=old.pk).update(created_at=timezone.now() - timezone.timedelta(days=1))

        response = self.client.get(reverse('blog:list'))
        titles = [p.title for p in response.context['posts']]

        self.assertEqual(titles, ['晚的文章', '早的文章'])

    def test_list_page_renders(self):
        response = self.client.get(reverse('blog:list'))
        self.assertEqual(response.status_code, 200)


class CategoryFilterTests(TestCase):
    """阶段 2：分类筛选。"""

    def setUp(self):
        self.django = Category.objects.create(name='Django')
        self.pit = Category.objects.create(name='踩坑记录')
        self.post_in_django = Post.objects.create(
            title='Django 的 MVT', body='x', category=self.django)
        self.post_in_pit = Post.objects.create(
            title='饼图画不出来', body='x', category=self.pit)

    def test_filter_by_category(self):
        """?category=Django 只显示这个分类的文章。"""
        response = self.client.get(reverse('blog:list'), {'category': 'Django'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Django 的 MVT')
        self.assertNotContains(response, '饼图画不出来')
        self.assertEqual(response.context['current_category'].pk, self.django.pk)

    def test_filter_ignores_drafts(self):
        """分类筛选同样不能漏出草稿。"""
        Post.objects.create(title='Django 草稿', body='x',
                            category=self.django, is_published=False)

        response = self.client.get(reverse('blog:list'), {'category': 'Django'})

        self.assertNotContains(response, 'Django 草稿')

    def test_unknown_category_returns_empty(self):
        """不存在的分类给空列表，而不是把所有文章倒出来。"""
        response = self.client.get(reverse('blog:list'), {'category': '不存在的分类'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_count'], 0)
        self.assertNotContains(response, 'Django 的 MVT')

    def test_category_and_keyword_together(self):
        """分类和搜索可以叠加：两个条件同时满足才显示。"""
        hit = self.client.get(reverse('blog:list'),
                              {'category': 'Django', 'q': 'MVT'})
        self.assertContains(hit, 'Django 的 MVT')

        miss = self.client.get(reverse('blog:list'),
                               {'category': 'Django', 'q': '饼图'})
        self.assertEqual(miss.context['total_count'], 0)


class SearchTests(TestCase):
    """阶段 2：关键词搜索（Q 查询）。"""

    def setUp(self):
        Post.objects.create(title='饼图踩坑', body='SVG 画环的时候遇到问题')
        Post.objects.create(title='分页', body='Paginator 的用法')

    def test_search_by_title(self):
        response = self.client.get(reverse('blog:list'), {'q': '饼图'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '饼图踩坑')
        self.assertNotContains(response, '分页')

    def test_search_by_body(self):
        """正文命中也要搜得到。"""
        response = self.client.get(reverse('blog:list'), {'q': 'Paginator'})

        self.assertContains(response, '分页')
        self.assertNotContains(response, '饼图踩坑')

    def test_search_is_case_insensitive(self):
        """icontains：大小写不敏感。"""
        response = self.client.get(reverse('blog:list'), {'q': 'paginator'})

        self.assertContains(response, '分页')

    def test_search_hides_drafts(self):
        Post.objects.create(title='饼图草稿', body='x', is_published=False)

        response = self.client.get(reverse('blog:list'), {'q': '饼图'})

        self.assertNotContains(response, '饼图草稿')

    def test_empty_keyword_shows_all(self):
        """只输入空格等于没搜索。"""
        response = self.client.get(reverse('blog:list'), {'q': '   '})

        self.assertEqual(response.context['total_count'], 2)


class PaginationTests(TestCase):
    """阶段 2：分页。"""

    def setUp(self):
        # PAGE_SIZE = 5，造 7 篇 → 第 1 页 5 篇、第 2 页 2 篇
        for i in range(1, 8):
            Post.objects.create(title=f'文章{i}', body='x')

    def test_first_page_has_page_size(self):
        response = self.client.get(reverse('blog:list'))

        self.assertEqual(len(response.context['posts']), 5)
        self.assertEqual(response.context['page_obj'].number, 1)
        self.assertEqual(response.context['page_obj'].paginator.num_pages, 2)

    def test_second_page_has_rest(self):
        response = self.client.get(reverse('blog:list'), {'page': 2})

        self.assertEqual(len(response.context['posts']), 2)
        self.assertEqual(response.context['page_obj'].number, 2)

    def test_invalid_page_falls_back(self):
        """非法页码不报错：非数字给第一页，超出范围给最后一页。

        Paginator.get_page 的官方兜底规则：
          page=abc  → PageNotAnInteger → 第一页
          page=999  → EmptyPage（超过总页数）→ 最后一页
          page=0    → EmptyPage（小于 1）→ 最后一页
        """
        first = self.client.get(reverse('blog:list'), {'page': 'abc'})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.context['page_obj'].number, 1)

        too_big = self.client.get(reverse('blog:list'), {'page': '999'})
        self.assertEqual(too_big.status_code, 200)
        self.assertEqual(too_big.context['page_obj'].number, 2)

        zero = self.client.get(reverse('blog:list'), {'page': '0'})
        self.assertEqual(zero.status_code, 200)
        self.assertEqual(zero.context['page_obj'].number, 2)

    def test_pagination_keeps_search_and_category(self):
        """翻页链接要带着搜索词，不能翻到第二页就丢了筛选条件。"""
        Category.objects.create(name='Django')
        response = self.client.get(reverse('blog:list'),
                                   {'q': '文章', 'page': 2})

        self.assertEqual(response.context['querystring'], 'q=%E6%96%87%E7%AB%A0')
        self.assertContains(response, 'q=%E6%96%87%E7%AB%A0')

    def test_total_count_with_filters(self):
        response = self.client.get(reverse('blog:list'), {'q': '文章1'})

        # 文章1 只有一篇（文章10 不存在）
        self.assertEqual(response.context['total_count'], 1)

    def test_pager_links_render(self):
        """7 篇文章 → 第一页有「下一页」链接、第二页有「上一页」。"""
        first = self.client.get(reverse('blog:list'))
        self.assertContains(first, '下一页')
        self.assertContains(first, 'page=2')

        second = self.client.get(reverse('blog:list'), {'page': 2})
        self.assertContains(second, '上一页')
        self.assertContains(second, 'page=1')


class PostDetailTests(TestCase):
    def test_detail_shows_published_post(self):
        post = Post.objects.create(title='一篇文章', body='这是正文内容')
        response = self.client.get(reverse('blog:detail', args=(post.pk,)))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '一篇文章')
        self.assertContains(response, '这是正文内容')

    def test_detail_returns_404_for_draft(self):
        """草稿直接 404，不能靠改 URL 看到。"""
        post = Post.objects.create(title='草稿', body='不该看到', is_published=False)
        response = self.client.get(reverse('blog:detail', args=(post.pk,)))

        self.assertEqual(response.status_code, 404)

    def test_detail_returns_404_for_missing(self):
        response = self.client.get(reverse('blog:detail', args=(9999,)))
        self.assertEqual(response.status_code, 404)


class CategoryAdminTests(TestCase):
    """后台注册了分类模型，能正常打开列表页即可。"""

    def test_category_admin_available(self):
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create_superuser(
            'admin', 'admin@example.com', 'pass12345')
        self.client.force_login(user)

        response = self.client.get(reverse('admin:blog_category_changelist'))

        self.assertEqual(response.status_code, 200)


class MarkdownRenderTests(TestCase):
    """阶段 3：正文 Markdown 渲染 + 安全清洗。"""

    def _detail_html(self, body):
        post = Post.objects.create(title='Markdown 测试', body=body)
        response = self.client.get(reverse('blog:detail', args=(post.pk,)))
        return response.content.decode()

    def test_bold_renders(self):
        html = self._detail_html('这是**粗体**，这是*斜体*')
        self.assertIn('<strong>粗体</strong>', html)
        self.assertIn('<em>斜体</em>', html)

    def test_heading_and_list_render(self):
        html = self._detail_html('## 小标题\n\n- 第一项\n- 第二项')
        self.assertIn('<h2 id="小标题">小标题</h2>', html)   # toc 扩展会给标题加锚点 id
        self.assertIn('<li>第一项</li>', html)

    def test_fenced_code_is_highlighted(self):
        html = self._detail_html('```python\nprint("hello")\n```')
        self.assertIn('codehilite', html)          # Pygments 外层容器
        self.assertIn('print', html)                # 代码内容在
        self.assertIn('<span class="nb">print</span>', html)  # 内置函数被高亮

    def test_table_renders(self):
        html = self._detail_html('| 名称 | 值 |\n| --- | --- |\n| a | 1 |')
        self.assertIn('<table>', html)
        self.assertIn('<th>名称</th>', html)

    def test_script_tag_is_stripped(self):
        """正文里混进 <script> 不会被执行，也不会出现在页面源码里。"""
        html = self._detail_html('正常文字 <script>alert("xss")</script> 结束')
        self.assertNotIn('<script', html)
        self.assertIn('正常文字', html)

    def test_img_onerror_is_stripped(self):
        html = self._detail_html('<img src="x" onerror="alert(1)">')
        self.assertNotIn('onerror', html)

    def test_summary_strips_markdown_marks(self):
        """列表页摘要不能把 **、`、[]() 这些记号原样显示。"""
        Post.objects.create(
            title='摘要测试',
            body='**粗体**和`代码`，还有 [链接](https://example.com)',
        )
        response = self.client.get(reverse('blog:list'))
        summary = response.context['posts'][0].summary

        for mark in ('**', '`', ']('):
            self.assertNotIn(mark, summary)
        self.assertIn('粗体', summary)

    def test_draft_body_not_rendered_to_public(self):
        """草稿即使写了 Markdown 也不该出现在前台。"""
        Post.objects.create(title='草稿', body='**秘密**', is_published=False)
        response = self.client.get(reverse('blog:list'))
        self.assertNotContains(response, '秘密')


class PagerNumbersTests(TestCase):
    """阶段 3 顺手补的：分页条显示页码，页数多了用省略号。"""

    def test_page_numbers_rendered(self):
        for i in range(1, 8):   # 7 篇 / 每页 5 → 2 页
            Post.objects.create(title=f'文章{i}', body='x')

        first = self.client.get(reverse('blog:list'))
        self.assertContains(first, 'pager-pages')
        self.assertContains(first, 'page=2')

        second = self.client.get(reverse('blog:list'), {'page': 2})
        self.assertContains(second, 'current')

    def test_many_pages_use_ellipsis(self):
        for i in range(1, 41):  # 40 篇 / 每页 5 → 8 页，需要省略号
            Post.objects.create(title=f'文章{i}', body='x')

        response = self.client.get(reverse('blog:list'), {'page': 5})
        self.assertContains(response, '…')


class NotFoundPageTests(TestCase):
    """阶段 3：生产模式下的 404 页用自己的模板，而不是 Django 默认页。"""

    def test_404_template_used_when_debug_off(self):
        with override_settings(
            DEBUG=False,
            ALLOWED_HOSTS=['testserver', '127.0.0.1', 'localhost'],
        ):
            response = self.client.get('/no-such-page/')

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, '页面走丢了', status_code=404)


class LayoutTests(TestCase):
    """视觉改版（2026-11-16）：头图、目录、阅读时间、上一篇/下一篇。"""

    def test_hero_only_on_clean_first_page(self):
        Post.objects.create(title='一篇文章', body='内容')

        home = self.client.get(reverse('blog:list'))
        self.assertContains(home, 'hero-title')
        self.assertContains(home, '篇文章')

        filtered = self.client.get(reverse('blog:list'), {'q': '一篇文章'})
        self.assertNotContains(filtered, 'hero-title')

    def test_toc_built_from_headings(self):
        body = '## 第一节\n\n内容\n\n### 小节\n\n内容\n\n## 第二节\n\n内容'
        post = Post.objects.create(title='带目录的文章', body=body)

        response = self.client.get(reverse('blog:detail', args=(post.pk,)))

        self.assertEqual(len(response.context['toc']), 3)
        self.assertContains(response, '本文目录')
        self.assertContains(response, 'toc-list')

    def test_reading_time_computed(self):
        post = Post.objects.create(title='长文', body='字' * 800)

        self.assertEqual(post.word_count, 800)
        self.assertEqual(post.reading_time, 2)

        response = self.client.get(reverse('blog:detail', args=(post.pk,)))
        self.assertContains(response, '分钟读完')

    def test_prev_and_next_links(self):
        first = Post.objects.create(title='第一篇', body='x')
        second = Post.objects.create(title='第二篇', body='x')
        third = Post.objects.create(title='第三篇', body='x')

        middle = self.client.get(reverse('blog:detail', args=(second.pk,)))
        self.assertContains(middle, '← 上一篇')
        self.assertContains(middle, '下一篇 →')
        self.assertContains(middle, first.title)
        self.assertContains(middle, third.title)

        oldest = self.client.get(reverse('blog:detail', args=(first.pk,)))
        self.assertNotContains(oldest, '← 上一篇')
        self.assertContains(oldest, '下一篇 →')
