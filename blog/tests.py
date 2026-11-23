"""自动化测试。

跑法：python manage.py test
每个测试验证一条行为，改坏代码时能立刻发现。
"""

import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from comments.models import Comment

from .models import BlogSettings, Category, Post, Tag
from .templatetags.blog_extras import sidebar


class PostListTests(TestCase):
    def test_list_shows_only_published(self):
        """首页只显示已发布的文章。"""
        Post.objects.create(title='公开的文章', body='正文', status=Post.STATUS_PUBLISHED)
        Post.objects.create(title='草稿文章', body='正文', status=Post.STATUS_DRAFT)

        response = self.client.get(reverse('blog:list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '公开的文章')
        self.assertNotContains(response, '草稿文章')

    def test_list_orders_newest_first(self):
        """首页按发布时间倒序。"""
        old = Post.objects.create(title='早的文章', body='x')
        new = Post.objects.create(title='晚的文章', body='x')
        # 手动改发布时间，模拟先后
        Post.objects.filter(pk=old.pk).update(
            pub_time=timezone.now() - timezone.timedelta(days=1))

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
        titles = [p.title for p in response.context['posts']]
        self.assertIn('Django 的 MVT', titles)
        self.assertNotIn('饼图画不出来', titles)
        self.assertEqual(response.context['current_category'].pk, self.django.pk)

    def test_filter_ignores_drafts(self):
        """分类筛选同样不能漏出草稿。"""
        Post.objects.create(title='Django 草稿', body='x',
                            category=self.django, status=Post.STATUS_DRAFT)

        response = self.client.get(reverse('blog:list'), {'category': 'Django'})

        titles = [p.title for p in response.context['posts']]
        self.assertNotIn('Django 草稿', titles)

    def test_unknown_category_returns_empty(self):
        """不存在的分类给空列表，而不是把所有文章倒出来。"""
        response = self.client.get(reverse('blog:list'), {'category': '不存在的分类'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_count'], 0)
        self.assertEqual(list(response.context['posts']), [])

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
        titles = [p.title for p in response.context['posts']]
        self.assertIn('饼图踩坑', titles)
        self.assertNotIn('分页', titles)

    def test_search_by_body(self):
        """正文命中也要搜得到。"""
        response = self.client.get(reverse('blog:list'), {'q': 'Paginator'})

        titles = [p.title for p in response.context['posts']]
        self.assertIn('分页', titles)
        self.assertNotIn('饼图踩坑', titles)

    def test_search_is_case_insensitive(self):
        """icontains：大小写不敏感。"""
        response = self.client.get(reverse('blog:list'), {'q': 'paginator'})

        self.assertContains(response, '分页')

    def test_search_hides_drafts(self):
        Post.objects.create(title='饼图草稿', body='x', status=Post.STATUS_DRAFT)

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
        post = Post.objects.create(title='草稿', body='不该看到', status=Post.STATUS_DRAFT)
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
        """正文里混进 <script> 不会被执行，也不会出现在页面源码里。

        只看正文区域：base.html 里有深色模式的防闪烁内联脚本，
        整页断言 <script 会误伤（2026-11-23 加深色模式后调整口径）。
        """
        html = self._detail_html('正常文字 <script>alert("xss")</script> 结束')
        body = html.split('<div class="post-body">')[1].split('</div>')[0]
        self.assertNotIn('<script', body)
        self.assertIn('正常文字', body)

    def test_img_onerror_is_stripped(self):
        html = self._detail_html('<img src="x" onerror="alert(1)">')
        # 只看正文区域（页面 <head> 里的 meta description 是转义后的摘要文本）
        body = html.split('<div class="post-body">')[1].split('</div>')[0]
        self.assertNotIn('onerror', body)

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
        Post.objects.create(title='草稿', body='**秘密**', status=Post.STATUS_DRAFT)
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


class TagFilterTests(TestCase):
    """2026-11-16：标签（多对多）筛选。"""

    def setUp(self):
        self.deploy = Tag.objects.create(name='部署')
        self.post_tagged = Post.objects.create(title='部署踩坑', body='x')
        self.post_tagged.tags.add(self.deploy)
        self.post_plain = Post.objects.create(title='没标签的文章', body='x')

    def test_filter_by_tag(self):
        response = self.client.get(reverse('blog:list'), {'tag': '部署'})

        self.assertEqual(response.status_code, 200)
        titles = [p.title for p in response.context['posts']]
        self.assertIn('部署踩坑', titles)
        self.assertNotIn('没标签的文章', titles)
        self.assertEqual(response.context['current_tag'].pk, self.deploy.pk)

    def test_unknown_tag_returns_empty(self):
        response = self.client.get(reverse('blog:list'), {'tag': '不存在的标签'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_count'], 0)

    def test_tag_shown_on_card_and_detail(self):
        card = self.client.get(reverse('blog:list'))
        self.assertContains(card, 'tag-nav')
        self.assertContains(card, '部署')

        detail = self.client.get(reverse('blog:detail', args=(self.post_tagged.pk,)))
        self.assertContains(detail, 'post-tags')


class CoverImageTests(TestCase):
    """2026-11-16：封面图上传（列表卡片 + 详情页大图）。"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_root = tempfile.mkdtemp(prefix='myblog-test-media-')
        cls.override = override_settings(MEDIA_ROOT=cls.media_root)
        cls.override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.override.disable()
        shutil.rmtree(cls.media_root, ignore_errors=True)
        super().tearDownClass()

    def test_cover_renders_in_list_and_detail(self):
        cover = SimpleUploadedFile('cover.png', b'fake-png-bytes', content_type='image/png')
        post = Post.objects.create(title='有封面的文章', body='x', cover=cover)

        listing = self.client.get(reverse('blog:list'))
        self.assertContains(listing, 'cover.png')
        self.assertContains(listing, 'post-card-cover')

        detail = self.client.get(reverse('blog:detail', args=(post.pk,)))
        self.assertContains(detail, 'cover.png')
        self.assertContains(detail, 'post-cover')

    def test_post_without_cover_has_no_image(self):
        Post.objects.create(title='无封面', body='x')

        response = self.client.get(reverse('blog:list'))
        self.assertNotContains(response, 'post-card-cover')

    def test_wide_cover_is_shrunk_on_save(self):
        """2026-11-23：超过 1600px 的封面自动压缩，避免列表加载 5MB 大图。"""
        from io import BytesIO

        from PIL import Image

        buffer = BytesIO()
        Image.new('RGB', (2400, 1200), (47, 111, 78)).save(buffer, format='JPEG')
        upload = SimpleUploadedFile('wide.jpg', buffer.getvalue(), content_type='image/jpeg')

        post = Post.objects.create(title='大封面', body='x', cover=upload)

        with Image.open(post.cover.path) as saved:
            self.assertEqual(saved.width, 1600)
            self.assertEqual(saved.height, 800)


class ViewsCountTests(TestCase):
    """2026-11-16：阅读量计数。"""

    def test_detail_increments_views(self):
        post = Post.objects.create(title='文章', body='x')
        self.assertEqual(post.views, 0)

        self.client.get(reverse('blog:detail', args=(post.pk,)))
        post.refresh_from_db()
        self.assertEqual(post.views, 1)

        self.client.get(reverse('blog:detail', args=(post.pk,)))
        post.refresh_from_db()
        self.assertEqual(post.views, 2)

    def test_list_does_not_increment(self):
        post = Post.objects.create(title='文章', body='x')

        self.client.get(reverse('blog:list'))

        post.refresh_from_db()
        self.assertEqual(post.views, 0)

    def test_views_shown_on_page(self):
        post = Post.objects.create(title='文章', body='x', views=41)

        response = self.client.get(reverse('blog:detail', args=(post.pk,)))

        self.assertContains(response, '次浏览')


class RelatedPostsTests(TestCase):
    """2026-11-16：相关文章（先按标签，再按分类）。"""

    def test_related_by_tag(self):
        tag = Tag.objects.create(name='Django')
        main = Post.objects.create(title='主文章', body='x')
        main.tags.add(tag)
        related = Post.objects.create(title='同标签文章', body='x')
        related.tags.add(tag)
        unrelated = Post.objects.create(title='无关文章', body='x')

        response = self.client.get(reverse('blog:detail', args=(main.pk,)))

        self.assertContains(response, '相关文章')
        related_titles = [p.title for p in response.context['related_posts']]
        self.assertIn('同标签文章', related_titles)
        self.assertNotIn('无关文章', related_titles)

    def test_related_falls_back_to_category(self):
        category = Category.objects.create(name='Django')
        Post.objects.create(title='同分类文章', body='x', category=category)
        main = Post.objects.create(title='主文章', body='x', category=category)
        Post.objects.create(title='别的分类', body='x')

        response = self.client.get(reverse('blog:detail', args=(main.pk,)))

        related_titles = [p.title for p in response.context['related_posts']]
        self.assertIn('同分类文章', related_titles)
        self.assertNotIn('别的分类', related_titles)


class ArchiveAndAboutTests(TestCase):
    """2026-11-16：归档页、关于页。"""

    def test_archive_page(self):
        Post.objects.create(title='归档里的文章', body='x')

        response = self.client.get(reverse('blog:archive'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '归档')
        self.assertContains(response, timezone.localdate().strftime('%Y'))
        self.assertContains(response, '归档里的文章')

    def test_about_page(self):
        Post.objects.create(title='文章', body='x')

        response = self.client.get(reverse('blog:about'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '关于这个博客')
        self.assertContains(response, '篇文章')


class FeedAndSitemapTests(TestCase):
    """2026-11-16：RSS 订阅和站点地图。"""

    def test_rss_feed(self):
        post = Post.objects.create(title='订阅里的文章', body='x')

        response = self.client.get(reverse('blog:feed'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('application/rss+xml', response['Content-Type'])
        self.assertContains(response, '订阅里的文章')
        self.assertContains(response, reverse('blog:detail', args=(post.pk,)))

    def test_sitemap(self):
        post = Post.objects.create(title='地图里的文章', body='x')

        response = self.client.get(reverse('blog:sitemap'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('application/xml', response['Content-Type'])
        self.assertContains(response, '<urlset')
        self.assertContains(response, reverse('blog:detail', args=(post.pk,)))


class SeoTests(TestCase):
    """2026-11-23：robots.txt / RSS 自动发现 / 分享卡片 / favicon。"""

    def test_robots_txt(self):
        response = self.client.get(reverse('blog:robots'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('text/plain', response['Content-Type'])
        self.assertContains(response, 'Sitemap:')
        self.assertContains(response, '/sitemap.xml')
        self.assertContains(response, 'Disallow: /admin/')

    def test_head_has_rss_favicon_and_og(self):
        response = self.client.get(reverse('blog:list'))
        html = response.content.decode()

        self.assertIn('rel="alternate"', html)
        self.assertIn('application/rss+xml', html)
        self.assertIn('favicon.svg', html)
        self.assertIn('og:title', html)
        self.assertIn('og:url', html)

    def test_detail_has_article_meta(self):
        post = Post.objects.create(title='分享卡片测试', body='x')

        response = self.client.get(reverse('blog:detail', args=(post.pk,)))
        html = response.content.decode()

        self.assertIn('og:type" content="article', html)
        self.assertIn('分享卡片测试', html)
        self.assertIn('article:published_time', html)


class NotFoundSearchTests(TestCase):
    """2026-11-23：404 页也要能搜索。"""

    def test_404_has_search_box(self):
        with override_settings(DEBUG=False, ALLOWED_HOSTS=['testserver']):
            response = self.client.get('/no-such-page/')

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'name="q"', status_code=404)


class CachedRenderingTests(TestCase):
    """2026-11-23：正文/摘要缓存，避免同一页重复渲染 Markdown。"""

    def test_body_html_rendered_once_per_instance(self):
        import blog.markdown_render as renderer

        calls = {'n': 0}
        original = renderer.render_markdown

        def counting(text):
            calls['n'] += 1
            return original(text)

        renderer.render_markdown = counting
        try:
            post = Post.objects.create(title='缓存测试', body='## 标题\n\n**粗体**')
            first = post.body_html
            second = post.body_html
        finally:
            renderer.render_markdown = original

        self.assertEqual(calls['n'], 1)
        self.assertEqual(first, second)

    def test_summary_does_not_render_html(self):
        import blog.markdown_render as renderer

        calls = {'n': 0}
        original = renderer.render_markdown

        def counting(text):
            calls['n'] += 1
            return original(text)

        renderer.render_markdown = counting
        try:
            post = Post.objects.create(title='摘要缓存', body='**粗体**和`代码`')
            post.summary
        finally:
            renderer.render_markdown = original

        self.assertEqual(calls['n'], 0)   # 摘要只去 Markdown 记号，不渲染 HTML


class BackupCommandTests(TestCase):
    """2026-11-23：backup 管理命令能备份媒体文件。"""

    def test_backup_copies_media(self):
        import tempfile
        from io import StringIO
        from pathlib import Path

        from django.core.management import call_command

        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / 'media_src'
            (media / 'covers').mkdir(parents=True)
            (media / 'covers' / 'a.jpg').write_bytes(b'fake-image')
            backup_dir = Path(tmp) / 'backups'

            out = StringIO()
            with override_settings(MEDIA_ROOT=str(media)):
                call_command('backup', dir=str(backup_dir), stdout=out)

            items = list(backup_dir.iterdir())
            self.assertEqual(len(items), 1)
            self.assertTrue((items[0] / 'media' / 'covers' / 'a.jpg').exists())
            self.assertIn('备份完成', out.getvalue())


class LoginRequiredCommentTests(TestCase):
    """2026-11-23：评论必须登录；审核开关、回复、关闭评论。"""

    def setUp(self):
        self.post = Post.objects.create(title='评论测试文章', body='x')
        self.user = User.objects.create_user('reader', password='pass12345')

    def _post_comment(self, body='说两句', parent=None):
        data = {'body': body}
        if parent:
            data['parent'] = parent.pk
        return self.client.post(
            reverse('comments:post_comment', args=[self.post.pk]), data)

    def test_anonymous_cannot_comment(self):
        response = self._post_comment()

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
        self.assertEqual(Comment.objects.count(), 0)

    def test_logged_in_comment_is_pending_when_review_on(self):
        self.client.force_login(self.user)

        response = self._post_comment('第一条评论')

        self.assertEqual(response.status_code, 302)
        comment = Comment.objects.get()
        self.assertEqual(comment.author, self.user)
        self.assertFalse(comment.is_approved)   # 默认站点设置是「需要审核」
        self.assertEqual(comment.post, self.post)

    def test_admin_comment_is_auto_approved(self):
        staff = User.objects.create_user('admin', password='pass12345', is_staff=True)
        self.client.force_login(staff)

        self._post_comment('管理员评论')

        self.assertTrue(Comment.objects.get().is_approved)

    def test_review_off_auto_approves(self):
        site = BlogSettings.load()
        site.comment_need_review = False
        site.save()
        self.client.force_login(self.user)

        self._post_comment('无需审核的评论')

        self.assertTrue(Comment.objects.get().is_approved)

    def test_nested_reply(self):
        parent = Comment.objects.create(
            post=self.post, author=self.user, body='父评论', is_approved=True)
        self.client.force_login(self.user)

        self._post_comment('子回复', parent=parent)

        reply = Comment.objects.exclude(pk=parent.pk).get()
        self.assertEqual(reply.parent, parent)

    def test_closed_comments_are_rejected(self):
        self.post.allow_comments = False
        self.post.save()
        self.client.force_login(self.user)

        self._post_comment('关了还能评论吗')

        self.assertEqual(Comment.objects.count(), 0)

    def test_approved_comment_visible_on_detail(self):
        Comment.objects.create(
            post=self.post, author=self.user, body='已经审核过的评论', is_approved=True)
        Comment.objects.create(
            post=self.post, author=self.user, body='还在审核的评论', is_approved=False)

        response = self.client.get(self.post.get_absolute_url())

        self.assertContains(response, '已经审核过的评论')
        self.assertNotContains(response, '还在审核的评论')

    def test_detail_shows_login_hint_for_anonymous(self):
        response = self.client.get(self.post.get_absolute_url())

        self.assertContains(response, '登录')
        self.assertNotContains(response, '发表评论')

    def test_reply_target_prefills_hint(self):
        parent = Comment.objects.create(
            post=self.post, author=self.user, body='父评论', is_approved=True)
        self.client.force_login(self.user)

        response = self.client.get(self.post.get_absolute_url() + f'?reply={parent.pk}')

        self.assertContains(response, '正在回复')
        self.assertContains(response, f'name="parent" value="{parent.pk}"')


class AccountTests(TestCase):
    """2026-11-23：注册 / 登录 / 退出 / 个人中心。"""

    def test_register_creates_user_and_logs_in(self):
        response = self.client.post(reverse('accounts:register'), {
            'username': 'newbie',
            'email': '',
            'password1': 'test-pass-1234',
            'password2': 'test-pass-1234',
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username='newbie').exists())
        self.assertEqual(response.context['user'].username, 'newbie')
        self.assertContains(response, '注册成功')

    def test_login_page_renders(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)

    def test_login_works(self):
        User.objects.create_user('loginuser', password='pass12345')

        response = self.client.post(reverse('accounts:login'), {
            'username': 'loginuser',
            'password': 'pass12345',
        }, follow=True)

        self.assertEqual(response.context['user'].username, 'loginuser')

    def test_profile_requires_login(self):
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_profile_shows_my_comments(self):
        user = User.objects.create_user('commenter', password='pass12345')
        post = Post.objects.create(title='文章', body='x')
        Comment.objects.create(post=post, author=user, body='我的评论内容', is_approved=True)
        self.client.force_login(user)

        response = self.client.get(reverse('accounts:profile'))

        self.assertContains(response, '我的评论')
        self.assertContains(response, '我的评论内容')

    def test_logout_requires_post(self):
        user = User.objects.create_user('bye', password='pass12345')
        self.client.force_login(user)

        self.assertEqual(self.client.get(reverse('accounts:logout')).status_code, 405)

        response = self.client.post(reverse('accounts:logout'))
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('_auth_user_id', self.client.session)


class PageTests(TestCase):
    """2026-11-23：独立页面（is_page）。"""

    def setUp(self):
        self.page = Post.objects.create(
            title='留言板', body='这里可以留言。', is_page=True,
            status=Post.STATUS_PUBLISHED)
        self.post = Post.objects.create(title='普通文章', body='x')

    def test_page_detail_renders(self):
        response = self.client.get(self.page.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '留言板')
        self.assertContains(response, '这里可以留言。')

    def test_page_not_in_article_list(self):
        response = self.client.get(reverse('blog:list'))
        titles = [p.title for p in response.context['posts']]
        self.assertNotIn('留言板', titles)

    def test_page_not_in_archive_or_feed(self):
        archive = self.client.get(reverse('blog:archive'))
        archive_titles = [
            post.title
            for group in archive.context['groups']
            for post in group['posts']
        ]
        self.assertNotIn('留言板', archive_titles)

        feed = self.client.get(reverse('blog:feed'))
        self.assertNotContains(feed, '留言板')

    def test_page_appears_in_footer_nav(self):
        response = self.client.get(reverse('blog:list'))
        self.assertContains(response, '留言板')

    def test_page_can_have_comments(self):
        user = User.objects.create_user('pageuser', password='pass12345')
        self.client.force_login(user)

        self.client.post(
            reverse('comments:post_comment', args=[self.page.pk]), {'body': '页面评论'})

        self.assertTrue(Comment.objects.filter(post=self.page, body='页面评论').exists())

    def test_draft_page_404(self):
        draft = Post.objects.create(
            title='草稿页面', body='x', is_page=True, status=Post.STATUS_DRAFT)

        response = self.client.get(reverse('blog:page_detail', args=[draft.pk]))

        self.assertEqual(response.status_code, 404)


class SidebarTests(TestCase):
    """2026-11-23：侧边栏模块。"""

    def test_sidebar_has_sections(self):
        tag = Tag.objects.create(name='Django')
        post = Post.objects.create(title='侧边栏文章', body='x')
        post.tags.add(tag)
        user = User.objects.create_user('sideuser', password='pass12345')
        Comment.objects.create(post=post, author=user, body='侧边栏评论', is_approved=True)

        response = self.client.get(reverse('blog:list'))

        self.assertContains(response, '最新文章')
        self.assertContains(response, '最多阅读')
        self.assertContains(response, '标签云')
        self.assertContains(response, '最新评论')
        self.assertContains(response, '侧边栏评论')
        self.assertContains(response, '侧边栏文章')


class SiteSettingsTests(TestCase):
    """2026-11-23：站点设置全站生效。"""

    def test_site_name_appears_in_page(self):
        site = BlogSettings.load()
        site.site_name = '陈城泓的博客'
        site.footer_text = '测试页脚'
        site.save()

        response = self.client.get(reverse('blog:list'))

        self.assertContains(response, '陈城泓的博客')
        self.assertContains(response, '测试页脚')

    def test_beian_and_analytics_render(self):
        site = BlogSettings.load()
        site.beian_code = '粤ICP备00000000号'
        site.analytics_code = '<script>window.__test_analytics__ = 1;</script>'
        site.save()

        response = self.client.get(reverse('blog:list'))

        self.assertContains(response, '粤ICP备00000000号')
        self.assertContains(response, '__test_analytics__')

    def test_comment_need_review_switch(self):
        site = BlogSettings.load()
        self.assertTrue(site.comment_need_review)   # 默认值

        site.comment_need_review = False
        site.save()

        self.assertFalse(BlogSettings.load().comment_need_review)


class VisibleQuerysetTests(TestCase):
    """2026-11-23：统一的「前台可见」查询集（草稿 + 定时发布的核心）。"""

    def test_visible_filters_status_and_time(self):
        published = Post.objects.create(title='可见文章', body='x')
        Post.objects.create(title='草稿', body='x', status=Post.STATUS_DRAFT)
        Post.objects.create(
            title='定时未到', body='x',
            pub_time=timezone.now() + timezone.timedelta(hours=1))
        old = Post.objects.create(title='时间已到', body='x')
        Post.objects.filter(pk=old.pk).update(
            pub_time=timezone.now() - timezone.timedelta(hours=1))

        titles = set(Post.objects.visible().values_list('title', flat=True))

        self.assertEqual(titles, {'可见文章', '时间已到'})
        self.assertIn(published.title, titles)


class DraftAndScheduledPublishTests(TestCase):
    """2026-11-23：草稿 + 定时发布（复现 DjangoBlog 第二批-1）。

    时间模拟统一用 Post.objects.filter(pk=...).update(pub_time=...)，
    不引 freezegun 这类新依赖。
    """

    def setUp(self):
        self.category = Category.objects.create(name='Django')
        self.tag = Tag.objects.create(name='定时发布')
        self.user = User.objects.create_user('draftreader', password='pass12345')

    def _draft(self, title='草稿文章', **kwargs):
        kwargs.setdefault('body', 'x')
        return Post.objects.create(
            title=title, status=Post.STATUS_DRAFT, **kwargs)

    def _scheduled(self, title='定时文章', **kwargs):
        kwargs.setdefault('body', 'x')
        return Post.objects.create(
            title=title,
            pub_time=timezone.now() + timezone.timedelta(days=1),
            **kwargs)

    def _make_due(self, post):
        """把发布时间改到过去，模拟「到点了」。"""
        Post.objects.filter(pk=post.pk).update(
            pub_time=timezone.now() - timezone.timedelta(minutes=1))
        post.refresh_from_db(fields=['pub_time'])

    def _list_titles(self):
        response = self.client.get(reverse('blog:list'))
        return [p.title for p in response.context['posts']]

    # ---------- 草稿：各个前台入口都不能漏 ----------

    def test_draft_not_in_list(self):
        Post.objects.create(title='正常文章', body='x')
        self._draft()

        self.assertEqual(self._list_titles(), ['正常文章'])

    def test_draft_not_in_search(self):
        self._draft(title='饼图草稿')

        response = self.client.get(reverse('blog:list'), {'q': '饼图'})

        self.assertEqual(response.context['total_count'], 0)

    def test_draft_not_in_category_filter(self):
        self._draft(category=self.category)

        response = self.client.get(reverse('blog:list'), {'category': 'Django'})

        self.assertEqual(response.context['total_count'], 0)

    def test_draft_not_in_tag_filter_or_tag_cloud(self):
        draft = self._draft()
        draft.tags.add(self.tag)

        filtered = self.client.get(reverse('blog:list'), {'tag': '定时发布'})
        self.assertEqual(filtered.context['total_count'], 0)

        # 标签云只显示有可见文章的标签：只挂草稿的标签不该出现
        cloud_names = [t.name for t in sidebar()['tags']]
        self.assertNotIn('定时发布', cloud_names)

    def test_draft_not_in_archive(self):
        self._draft(title='归档不该有草稿')

        response = self.client.get(reverse('blog:archive'))

        titles = [p.title for g in response.context['groups'] for p in g['posts']]
        self.assertNotIn('归档不该有草稿', titles)

    def test_draft_not_in_related_posts(self):
        main = Post.objects.create(title='主文章', body='x')
        main.tags.add(self.tag)
        draft = self._draft(title='同标签草稿')
        draft.tags.add(self.tag)

        response = self.client.get(reverse('blog:detail', args=[main.pk]))

        related_titles = [p.title for p in response.context['related_posts']]
        self.assertNotIn('同标签草稿', related_titles)

    def test_draft_not_in_sidebar(self):
        Post.objects.create(title='正常文章', body='x')
        self._draft(title='侧边栏草稿')

        data = sidebar()

        self.assertNotIn('侧边栏草稿', [p.title for p in data['latest_posts']])
        self.assertNotIn('侧边栏草稿', [p.title for p in data['popular_posts']])

    def test_draft_not_in_rss_or_sitemap(self):
        draft = self._draft(title='订阅里的草稿')

        feed = self.client.get(reverse('blog:feed'))
        sitemap = self.client.get(reverse('blog:sitemap'))

        self.assertNotContains(feed, '订阅里的草稿')
        self.assertNotContains(sitemap, reverse('blog:detail', args=[draft.pk]))

    def test_draft_detail_404(self):
        draft = self._draft()

        response = self.client.get(reverse('blog:detail', args=[draft.pk]))

        self.assertEqual(response.status_code, 404)

    def test_cannot_comment_on_draft(self):
        draft = self._draft()
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('comments:post_comment', args=[draft.pk]), {'body': '能评论吗'})

        self.assertEqual(response.status_code, 404)
        self.assertEqual(Comment.objects.count(), 0)

    # ---------- 定时发布：未到点隐藏，到点出现 ----------

    def test_scheduled_not_in_list(self):
        Post.objects.create(title='正常文章', body='x')
        self._scheduled(title='明天才发')

        self.assertEqual(self._list_titles(), ['正常文章'])

    def test_scheduled_detail_404_before_pub_time(self):
        scheduled = self._scheduled()

        response = self.client.get(reverse('blog:detail', args=[scheduled.pk]))

        self.assertEqual(response.status_code, 404)

    def test_scheduled_not_in_rss_or_sitemap(self):
        scheduled = self._scheduled(title='明天的 RSS 文章')

        feed = self.client.get(reverse('blog:feed'))
        sitemap = self.client.get(reverse('blog:sitemap'))

        self.assertNotContains(feed, '明天的 RSS 文章')
        self.assertNotContains(
            sitemap, reverse('blog:detail', args=[scheduled.pk]))

    def test_scheduled_visible_after_pub_time(self):
        scheduled = self._scheduled(title='到点后的文章')
        self.assertEqual(self._list_titles(), [])

        self._make_due(scheduled)

        self.assertIn('到点后的文章', self._list_titles())
        detail = self.client.get(reverse('blog:detail', args=[scheduled.pk]))
        self.assertEqual(detail.status_code, 200)

    def test_pub_time_equal_now_is_visible(self):
        """边界：pub_time <= now 才算可见，恰好等于当前时刻要能看见。"""
        now = timezone.now()
        post = Post.objects.create(title='准点发布', body='x', pub_time=now)

        self.assertIn('准点发布', self._list_titles())
        self.assertEqual(
            self.client.get(reverse('blog:detail', args=[post.pk])).status_code, 200)

    def test_cannot_comment_before_pub_time(self):
        scheduled = self._scheduled()
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('comments:post_comment', args=[scheduled.pk]), {'body': '提前评论'})

        self.assertEqual(response.status_code, 404)
        self.assertEqual(Comment.objects.count(), 0)

    # ---------- 独立页面同样遵守 ----------

    def test_draft_page_404_and_not_in_nav(self):
        draft_page = self._draft(title='草稿页面', is_page=True)

        self.assertEqual(
            self.client.get(reverse('blog:page_detail', args=[draft_page.pk])).status_code,
            404)
        nav_titles = [p.title for p in self.client.get(reverse('blog:list')).context['nav_pages']]
        self.assertNotIn('草稿页面', nav_titles)

    def test_scheduled_page_hidden_until_pub_time(self):
        page = self._scheduled(title='定时页面', is_page=True)

        self.assertEqual(
            self.client.get(reverse('blog:page_detail', args=[page.pk])).status_code, 404)
        nav_titles = [p.title for p in self.client.get(reverse('blog:list')).context['nav_pages']]
        self.assertNotIn('定时页面', nav_titles)

        self._make_due(page)

        self.assertEqual(
            self.client.get(reverse('blog:page_detail', args=[page.pk])).status_code, 200)

    # ---------- 统计口径 / 上下篇 ----------

    def test_home_and_about_counts_exclude_drafts_and_scheduled(self):
        Post.objects.create(title='可见文章', body='x', views=10)
        page = Post.objects.create(title='可见页面', body='x', is_page=True, views=50)
        self._draft(title='草稿', views=100)
        self._scheduled(title='定时文章', views=100)

        home = self.client.get(reverse('blog:list'))
        self.assertEqual(home.context['published_count'], 1)   # 独立页面不算「文章」
        self.assertEqual(home.context['total_views'], 10)

        about = self.client.get(reverse('blog:about'))
        self.assertEqual(about.context['published_count'], 1)
        self.assertIsNotNone(page.pk)

    def test_prev_next_skip_draft_and_scheduled(self):
        first = Post.objects.create(title='第一篇', body='x')
        self._draft(title='中间草稿')
        self._scheduled(title='中间定时')
        last = Post.objects.create(title='最后一篇', body='x')

        detail = self.client.get(reverse('blog:detail', args=[first.pk]))
        self.assertEqual(detail.context['next_post'].pk, last.pk)

        detail = self.client.get(reverse('blog:detail', args=[last.pk]))
        self.assertEqual(detail.context['prev_post'].pk, first.pk)

    # ---------- 后台 ----------

    def test_admin_can_edit_draft_and_action_publishes(self):
        admin_user = User.objects.create_superuser(
            'postadmin', 'postadmin@example.com', 'pass12345')
        self.client.force_login(admin_user)
        draft = self._draft(title='后台草稿')
        changelist = reverse('admin:blog_post_changelist')

        # 管理员能打开草稿的编辑页
        edit_page = self.client.get(
            reverse('admin:blog_post_change', args=[draft.pk]))
        self.assertEqual(edit_page.status_code, 200)
        self.assertContains(edit_page, '发布时间')

        # 后台动作「发布」把草稿改成已发布
        self.client.post(changelist, {
            'action': 'make_published',
            '_selected_action': [str(draft.pk)],
        })
        draft.refresh_from_db()
        self.assertEqual(draft.status, Post.STATUS_PUBLISHED)

