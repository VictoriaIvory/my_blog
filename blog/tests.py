"""自动化测试。

跑法：python manage.py test
每个测试验证一条行为，改坏代码时能立刻发现。
"""

from django.test import TestCase
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
