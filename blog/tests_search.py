"""全文搜索页面（第三批 · 复现 DjangoBlog）的自动化测试。

跑法：
    python manage.py test blog.tests_search
    python manage.py test            # 全量，也会自动发现本文件

大多数测试走「索引不存在 → 数据库兜底」路径（不要求装 Whoosh）：
search_index.search_posts 在没有索引时会退回数据库 icontains，
返回的 used_index=False 就是这条路径。
为了让结果稳定，搜索相关测试用 override_settings 把 SEARCH_INDEX_DIR
指到临时目录——否则本机手动建过索引，测试可能突然走到索引路径上。
最后一个用例（索引路径）依赖核心索引层，未完成/依赖没装时自动跳过。
"""

import atexit
import shutil
import tempfile
from unittest.mock import patch
from urllib.parse import quote

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Category, Post, Tag
from .views import SEARCH_PAGE_SIZE

# 所有「兜底路径」测试共用一个空的临时索引目录：里面永远没有索引，
# search_posts 就会稳定退回数据库。进程退出时自动清理。
SEARCH_INDEX_TEST_DIR = tempfile.mkdtemp(prefix='myblog-search-index-test-')
atexit.register(shutil.rmtree, SEARCH_INDEX_TEST_DIR, ignore_errors=True)


class SearchPageTests(TestCase):
    """搜索页本身：路由、模板、表单、导航/页脚入口、空查询。"""

    def test_search_page_renders(self):
        """GET /search/ 能渲染，用的是搜索页模板。"""
        response = self.client.get(reverse('blog:search'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'blog/search.html')
        self.assertContains(response, '全文搜索')

    def test_search_form_present(self):
        """搜索表单：GET 提交到搜索页，输入框 name="q"。"""
        response = self.client.get(reverse('blog:search'))

        self.assertContains(response, 'method="get"')
        self.assertContains(response, 'name="q"')
        self.assertContains(response, 'action="/search/"')

    def test_nav_has_search_entry(self):
        """顶栏有搜索入口（放大镜图标 + aria-label / title）。"""
        response = self.client.get(reverse('blog:list'))

        self.assertContains(response, 'href="/search/"')
        self.assertContains(response, 'aria-label="全文搜索"')
        self.assertContains(response, 'title="全文搜索"')

    def test_search_nav_marked_active_on_search_page(self):
        """在搜索页时，顶栏搜索入口有 active 选中态。"""
        response = self.client.get(reverse('blog:search'))

        self.assertIn('class="nav-search active"', response.content.decode('utf-8'))

    def test_template_comment_not_rendered(self):
        """模板注释 {# #} 不能跨行：跨行不会被当注释，会原样输出到页面（踩过的坑）。

        第三批加导航入口时踩过：两行的 {# ... #} 被当成普通文本渲染，
        顶栏布局直接坏掉。这里守住「页面里不能出现裸的 {#」。
        """
        response = self.client.get(reverse('blog:search'))
        html = response.content.decode('utf-8')

        self.assertNotIn('{#', html)

    def test_footer_has_search_link(self):
        """页脚也有一个「搜索」文字链接。"""
        response = self.client.get(reverse('blog:list'))

        self.assertContains(response, '>搜索</a>')

    def test_empty_query_renders_guide(self):
        """没输入关键词：显示引导文案，不调用索引层。"""
        with patch('blog.views.search_posts') as mocked:
            response = self.client.get(reverse('blog:search'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['q'], '')
        self.assertEqual(response.context['total_count'], 0)
        self.assertEqual(list(response.context['hits']), [])
        self.assertIsNone(response.context['used_index'])
        self.assertContains(response, '输入关键词')
        mocked.assert_not_called()

    def test_whitespace_query_treated_as_empty(self):
        """只有空格的关键词等于没输入（去空格后为空）。"""
        response = self.client.get(reverse('blog:search'), {'q': '   '})

        self.assertEqual(response.context['q'], '')
        self.assertEqual(response.context['total_count'], 0)
        self.assertEqual(list(response.context['hits']), [])


@override_settings(SEARCH_INDEX_DIR=SEARCH_INDEX_TEST_DIR)
class SearchResultTests(TestCase):
    """结果展示：标题/正文高亮、可见性过滤、详情链接、无结果、XSS。"""

    def setUp(self):
        self.category = Category.objects.create(name='踩坑记录')
        self.tag = Tag.objects.create(name='SVG')
        # 标题命中（正文不含关键词）
        self.title_post = Post.objects.create(
            title='饼图踩坑记录',
            body='SVG 角度计算的一段正文。',
            category=self.category,
        )
        self.title_post.tags.add(self.tag)
        # 正文命中（标题不含关键词）
        self.body_post = Post.objects.create(
            title='SVG 画图踩坑',
            body='画环形图的时候把起始角度算错了。',
        )
        # 另一个无关文章
        self.other_post = Post.objects.create(title='分页与搜索', body='Paginator 的用法。')

    def search(self, q, **extra):
        params = {'q': q}
        params.update(extra)
        return self.client.get(reverse('blog:search'), params)

    def test_title_hit_highlighted(self):
        """标题命中：title_html 里有关键词高亮，且只返回这一篇。"""
        response = self.search('饼图')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_count'], 1)
        hit = response.context['hits'][0]
        self.assertEqual(hit['post'].pk, self.title_post.pk)
        self.assertIn('<mark class="search-hit">饼图</mark>', hit['title_html'])
        self.assertContains(response, '<mark class="search-hit">饼图</mark>')

    def test_body_hit_highlighted(self):
        """正文命中：摘要里有关键词高亮，标题不被误标。"""
        response = self.search('环形图')

        self.assertEqual(response.context['total_count'], 1)
        hit = response.context['hits'][0]
        self.assertEqual(hit['post'].pk, self.body_post.pk)
        self.assertIn('<mark class="search-hit">环形图</mark>', hit['snippet_html'])
        self.assertNotIn('<mark class="search-hit">', hit['title_html'])
        self.assertContains(response, '<mark class="search-hit">环形图</mark>')

    def test_draft_and_scheduled_posts_hidden(self):
        """草稿 / 还没到发布时间的定时文章不能出现在搜索结果里。"""
        Post.objects.create(
            title='饼图草稿', body='饼图正文', status=Post.STATUS_DRAFT)
        Post.objects.create(
            title='饼图定时', body='饼图正文',
            status=Post.STATUS_PUBLISHED,
            pub_time=timezone.now() + timezone.timedelta(days=1),
        )

        response = self.search('饼图')
        titles = [hit['post'].title for hit in response.context['hits']]

        self.assertEqual(response.context['total_count'], 1)
        self.assertIn('饼图踩坑记录', titles)
        self.assertNotIn('饼图草稿', titles)
        self.assertNotIn('饼图定时', titles)

    def test_result_links_to_post_detail(self):
        """结果标题链接指向文章详情页。"""
        response = self.search('饼图')

        self.assertContains(response, f'href="{self.title_post.get_absolute_url()}"')

    def test_no_results_message(self):
        """有关键词但没命中：给「没有找到」提示。

        查询词故意用 ASCII 乱串：中文词里的「不」「在」这类单字
        在改精确的索引查询里可能被切出来误命中，测试会不稳定。
        """
        response = self.search('zzzz-not-exist')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_count'], 0)
        self.assertContains(response, '没有找到')

    def test_fallback_hint_when_index_missing(self):
        """索引没建（数据库兜底）时，提示可以运行重建命令。"""
        response = self.search('饼图')

        self.assertIs(response.context['used_index'], False)
        self.assertContains(response, 'rebuild_search_index')
        self.assertContains(response, '数据库快速搜索')

    def test_query_whitespace_stripped(self):
        """关键词两端空格会被去掉，不影响命中。"""
        response = self.search('  饼图  ')

        self.assertEqual(response.context['q'], '饼图')
        self.assertEqual(response.context['total_count'], 1)

    def test_script_in_body_escaped(self):
        """正文里的 <script> 只以转义文本出现，不会变成可执行标签。"""
        Post.objects.create(
            title='脚本注入测试',
            body='脚本 <script>alert(1)</script> 结尾',
        )

        response = self.search('脚本')

        self.assertEqual(response.context['total_count'], 1)
        # plain_text 会先去掉 Markdown/HTML 里的尖括号记号，但不管怎样
        # 页面里绝不能出现可执行的 <script>alert(1)</script>
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertNotContains(response, '<script>alert')
        self.assertContains(response, '&lt;script')

    def test_script_in_title_escaped(self):
        """标题里的 <script> 同样被转义（标题高亮也要安全）。"""
        Post.objects.create(
            title='标题 <script>alert(2)</script> 饼图',
            body='正文',
        )

        response = self.search('标题')

        self.assertEqual(response.context['total_count'], 1)
        self.assertNotContains(response, '<script>alert(2)</script>')
        self.assertNotContains(response, '<script>alert')
        self.assertContains(response, '&lt;script&gt;alert(2)&lt;/script&gt;')


@override_settings(SEARCH_INDEX_DIR=SEARCH_INDEX_TEST_DIR)
class SearchPaginationTests(TestCase):
    """搜索结果分页（每页 SEARCH_PAGE_SIZE 条，翻页保留 q）。"""

    def setUp(self):
        # 造 12 篇都含「饼图」的文章 → 10 + 2 两页
        for index in range(12):
            Post.objects.create(
                title=f'饼图系列 {index:02d}',
                body=f'第 {index} 篇饼图文章。',
            )

    def test_first_page_has_page_size_results(self):
        response = self.client.get(reverse('blog:search'), {'q': '饼图'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_count'], 12)
        self.assertEqual(len(response.context['hits']), SEARCH_PAGE_SIZE)
        self.assertEqual(response.context['page_obj'].number, 1)

    def test_second_page_renders_with_results(self):
        """?page=2 返回第二页，结果 2 条，页码条也渲染出来。"""
        response = self.client.get(reverse('blog:search'), {'q': '饼图', 'page': 2})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].number, 2)
        self.assertEqual(len(response.context['hits']), 2)
        self.assertEqual(response.context['total_count'], 12)
        self.assertContains(response, 'pager-pages')

    def test_pager_keeps_query_string(self):
        """翻页链接保留关键词 q（不含 page 本身）。"""
        response = self.client.get(reverse('blog:search'), {'q': '饼图', 'page': 2})

        self.assertEqual(response.context['querystring'], f'q={quote("饼图")}')
        html = response.content.decode('utf-8')
        self.assertIn(f'q={quote("饼图")}', html)
        self.assertIn('page=1', html)


class SearchIndexPathTests(TestCase):
    """可选：索引建好后走 Whoosh 索引路径。

    依赖核心索引层（feature-search-core）与 whoosh/jieba 依赖；
    如果此刻还没实现或依赖没装，跳过而不是失败。
    """

    def test_used_index_after_rebuild(self):
        from .search_index import rebuild_index

        Post.objects.create(title='饼图索引测试', body='Whoosh 全文搜索的一段正文。')
        index_dir = tempfile.mkdtemp(prefix='myblog-search-index-path-')
        self.addCleanup(shutil.rmtree, index_dir, ignore_errors=True)

        try:
            with override_settings(SEARCH_INDEX_DIR=index_dir):
                rebuild_index()
        except NotImplementedError:
            self.skipTest('全文索引层尚未实现（feature-search-core 负责）')
        except ImportError as exc:
            self.skipTest(f'索引依赖未安装：{exc}')

        with override_settings(SEARCH_INDEX_DIR=index_dir):
            response = self.client.get(reverse('blog:search'), {'q': '饼图'})

        self.assertTrue(response.context['used_index'])
        self.assertEqual(response.context['total_count'], 1)
        self.assertContains(response, '<mark class="search-hit">饼图</mark>')
