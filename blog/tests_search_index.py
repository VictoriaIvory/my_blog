"""全文搜索核心层测试（2026-11-23 第三批：Whoosh + jieba）。

跑法：python manage.py test blog.tests_search_index

每个测试用 `tempfile.mkdtemp()` 指一个临时索引目录（override_settings），
结束后连目录一起删掉，绝不碰工作区里的 search_index/，
也不依赖测试执行顺序。索引文件的生成 / 查询都在本地完成，不需要网络。
"""

import shutil
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from . import search_index
from .models import Post


class SearchIndexTestCase(TestCase):
    """公共准备：每个测试一个临时索引目录 + 几个建文章的快捷方法。"""

    def setUp(self):
        self.index_dir = Path(tempfile.mkdtemp(prefix='myblog-search-'))
        # cleanup 是后进先出：先恢复 settings，再删临时目录
        self.addCleanup(shutil.rmtree, self.index_dir, ignore_errors=True)
        self.settings_override = override_settings(SEARCH_INDEX_DIR=self.index_dir)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)

    # ---------- 小工具 ----------

    def make_post(self, title, body='正文内容', **kwargs):
        """建一篇已发布文章（默认 pub_time=现在，前台可见）。"""
        kwargs.setdefault('status', Post.STATUS_PUBLISHED)
        return Post.objects.create(title=title, body=body, **kwargs)

    @staticmethod
    def titles(hits):
        return [hit['post'].title for hit in hits]

    # ---------- 重建索引 ----------

    def test_rebuild_index_counts_only_articles(self):
        """重建只收「非独立页面」文章；草稿也算（查询时再过滤）。"""
        self.make_post('正常文章')
        self.make_post('草稿文章', status=Post.STATUS_DRAFT)
        self.make_post('留言板', is_page=True)

        self.assertEqual(search_index.rebuild_index(), 2)

    def test_rebuild_index_creates_index_directory(self):
        """rebuild_index 会把索引文件写进 settings 指定的目录。"""
        self.assertFalse(any(self.index_dir.iterdir()))  # 临时目录起初是空的
        self.make_post('文章一')
        count = search_index.rebuild_index()

        self.assertEqual(count, 1)
        self.assertTrue(any(self.index_dir.iterdir()))  # 目录里已经有索引文件

    # ---------- 中文分词 / 标题与正文 ----------

    def test_search_chinese_word_in_body(self):
        """正文里的中文词命中（jieba 分词 + Whoosh 短语检索）。"""
        post = self.make_post('记账本复盘', body='用 SVG 画了一个饼图，遇到问题')
        self.make_post('无关文章', body='今天天气不错')
        search_index.rebuild_index()

        hits, used_index = search_index.search_posts('饼图')

        self.assertTrue(used_index)  # 走的是 Whoosh，不是数据库兜底
        self.assertIn(post, [hit['post'] for hit in hits])
        self.assertNotIn('无关文章', self.titles(hits))
        self.assertGreater(hits[0]['score'], 0)

    def test_search_matches_title_and_body(self):
        """标题命中和正文命中都能搜到。"""
        title_hit = self.make_post('Django 分页技巧', body='正文没有关键词')
        body_hit = self.make_post('随便写写', body='这里讲 Paginator 分页的用法')
        self.make_post('毫无关系', body='别的内容')
        search_index.rebuild_index()

        hits, used_index = search_index.search_posts('分页')
        titles = self.titles(hits)

        self.assertTrue(used_index)
        self.assertIn(title_hit.title, titles)
        self.assertIn(body_hit.title, titles)
        self.assertNotIn('毫无关系', titles)

    def test_search_english_is_case_insensitive(self):
        """英文大小写不敏感（索引和查询都过 LowercaseFilter）。"""
        post = self.make_post('英文文章', body='Paginator 的用法')
        django_post = self.make_post('Django 入门', body='模型和视图')
        search_index.rebuild_index()

        for keyword in ('Paginator', 'paginator', 'PAGINATOR'):
            hits, used_index = search_index.search_posts(keyword)
            self.assertTrue(used_index, keyword)
            self.assertIn(post, [hit['post'] for hit in hits], keyword)

        # 纯英文单词（Django）也仍然命中
        hits, used_index = search_index.search_posts('Django')
        self.assertTrue(used_index)
        self.assertIn(django_post, [hit['post'] for hit in hits])

    # ---------- 查询精度：短语优先，不退回单字 OR ----------

    def test_no_result_for_nonsense_query(self):
        """「zzzz不存在」这种乱串必须 0 结果（不能被「不/存/在」单字带出文章）。"""
        self.make_post('饼图文章', body='用一个饼图展示数据')
        self.make_post('无关文章', body='今天天气很好，适合晒被子')
        search_index.rebuild_index()

        hits, used_index = search_index.search_posts('zzzz不存在')

        self.assertTrue(used_index)  # 走了索引，只是确实没有结果
        self.assertEqual(hits, [])

    def test_phrase_ignores_scattered_single_chars(self):
        """「饼图」只命中真正写了「饼图」的文章；只有「饼」「图」散落的文章不算。"""
        real = self.make_post('饼图教程', body='教程里有一个饼图')
        self.make_post('散落单字', body='只有饼，没有图')
        self.make_post('无关文章', body='今天天气很好，适合晒被子')
        search_index.rebuild_index()

        hits, used_index = search_index.search_posts('饼图')

        self.assertTrue(used_index)
        self.assertEqual(self.titles(hits), [real.title])

    def test_space_separated_query_matches_either(self):
        """空格分隔的多个词是 OR 关系：「饼图 分页」命中两篇。"""
        pie = self.make_post('讲饼图', body='用一个饼图展示数据')
        page = self.make_post('讲分页', body='Paginator 分页的用法')
        self.make_post('无关文章', body='今天天气很好，适合晒被子')
        search_index.rebuild_index()

        hits, used_index = search_index.search_posts('饼图 分页')
        titles = self.titles(hits)

        self.assertTrue(used_index)
        self.assertIn(pie.title, titles)
        self.assertIn(page.title, titles)
        self.assertNotIn('无关文章', titles)

    def test_single_char_query_still_matches(self):
        """单字查询（「图」）只有一个 token，走 Term 仍能命中。"""
        post = self.make_post('饼图文章', body='教程里有一个饼图')
        self.make_post('无关文章', body='今天天气很好，适合晒被子')
        search_index.rebuild_index()

        hits, used_index = search_index.search_posts('图')

        self.assertTrue(used_index)
        self.assertEqual(self.titles(hits), [post.title])

    # ---------- 草稿 / 定时 / 独立页面 ----------

    def test_draft_and_scheduled_hidden_but_indexed(self):
        """草稿、定时文章进了索引，但查询时被 visible() 过滤掉。"""
        published = self.make_post('饼图正式文章', body='饼图怎么画')
        self.make_post('饼图草稿', body='饼图草稿正文', status=Post.STATUS_DRAFT)
        self.make_post(
            '饼图定时', body='饼图定时正文',
            pub_time=timezone.now() + timezone.timedelta(days=1),
        )

        # 三篇都进了索引（改状态 / 到点不用重建索引的前提）
        self.assertEqual(search_index.rebuild_index(), 3)

        hits, used_index = search_index.search_posts('饼图')

        self.assertTrue(used_index)
        self.assertEqual(self.titles(hits), [published.title])

    # ---------- 单篇更新 / 删除 ----------

    def test_index_post_updates_title(self):
        """改标题后重新索引：新词搜得到，旧词搜不到。"""
        post = self.make_post('旧标题', body='正文内容')
        search_index.rebuild_index()
        before, _ = search_index.search_posts('旧标题')
        self.assertEqual(self.titles(before), ['旧标题'])

        post.title = '全新关键词'
        post.save()
        search_index.index_post(post)

        after, used_index = search_index.search_posts('全新关键词')
        self.assertTrue(used_index)
        self.assertEqual(self.titles(after), ['全新关键词'])

        old, _ = search_index.search_posts('旧标题')
        self.assertEqual(old, [])

    def test_index_post_updates_body(self):
        """正文改了重新索引后，新正文里的词也能搜到。"""
        post = self.make_post('文章', body='旧正文内容')
        search_index.rebuild_index()

        post.body = '换成了全新的正文饼图'
        post.save()
        search_index.index_post(post)

        hits, _ = search_index.search_posts('饼图')
        self.assertEqual(self.titles(hits), ['文章'])

    def test_delete_post_removes_from_index(self):
        """删除后搜不到（索引还在、别的文章还能搜）。"""
        post = self.make_post('饼图文章', body='饼图正文')
        self.make_post('另一篇', body='完全不同的内容')
        search_index.rebuild_index()

        search_index.delete_post(post.pk)

        hits, used_index = search_index.search_posts('饼图')
        self.assertTrue(used_index)  # 索引还在（不是退化成数据库兜底）
        self.assertEqual(hits, [])
        other, _ = search_index.search_posts('另一篇')
        self.assertEqual(self.titles(other), ['另一篇'])

    def test_page_not_in_index(self):
        """独立页面不进索引（重建后索引里只有 1 篇）。"""
        from whoosh import index as whoosh_index

        self.make_post('正常文章')
        self.make_post('留言板', is_page=True)
        search_index.rebuild_index()

        ix = whoosh_index.open_dir(str(self.index_dir))
        self.assertEqual(ix.doc_count(), 1)

    # ---------- 索引不可用 → 数据库兜底 ----------

    def test_missing_index_falls_back_to_database(self):
        """索引没建：used_index=False，但数据库兜底仍然能搜到。"""
        post = self.make_post('饼图兜底', body='饼图正文')

        hits, used_index = search_index.search_posts('饼图')

        self.assertFalse(used_index)
        self.assertEqual(self.titles(hits), [post.title])
        self.assertIn('<mark class="search-hit">饼图</mark>', hits[0]['title_html'])

    # ---------- 高亮 / 摘要 ----------

    def test_highlight_escapes_html(self):
        """正文里的 <script> 只会以转义形式出现在 html 里，不会变成真标签。"""
        self.make_post(
            '标题<b>标签</b>',
            body='<script>alert(1)</script> 饼图正文',
        )
        search_index.rebuild_index()

        hits, _ = search_index.search_posts('饼图')
        self.assertEqual(len(hits), 1)
        hit = hits[0]

        self.assertIn('<mark class="search-hit">饼图</mark>', hit['snippet_html'])
        # plain_text() 会把 Markdown 记号里的 > 去掉，所以摘要里可能只剩
        # "&lt;script"；关键是「被转义了、没有裸标签」，而不是原文一字不差。
        self.assertIn('&lt;script', hit['snippet_html'])
        self.assertNotIn('<script', hit['snippet_html'])

        self.assertIn('&lt;b&gt;', hit['title_html'])
        self.assertNotIn('<b>', hit['title_html'])

    def test_snippet_has_keyword_and_ellipsis(self):
        """长正文的摘要围绕命中词截取，两侧有省略号，关键词带 <mark>。"""
        body = '开头的话' * 100 + '饼图' + '结尾的话' * 100
        self.make_post('长文章', body=body)
        search_index.rebuild_index()

        hits, _ = search_index.search_posts('饼图')
        snippet = hits[0]['snippet_html']

        self.assertIn('<mark class="search-hit">饼图</mark>', snippet)
        self.assertIn('…', snippet)
        self.assertLess(len(snippet), len(body))

    # ---------- 边界情况 ----------

    def test_empty_query_returns_empty(self):
        """空查询（含只输空格、None）不碰索引，返回 ([], False)。"""
        self.make_post('文章')
        search_index.rebuild_index()

        self.assertEqual(search_index.search_posts(''), ([], False))
        self.assertEqual(search_index.search_posts('   '), ([], False))
        self.assertEqual(search_index.search_posts(None), ([], False))

    def test_special_characters_query_does_not_crash(self):
        """Whoosh 语法字符不能把搜索搞崩（不用 QueryParser 解析用户输入）。"""
        self.make_post('饼图文章', body='饼图正文')
        search_index.rebuild_index()

        for keyword in ('"a:b AND (', 'NOT 饼图', '饼图*', 'title:饼图', 'a\\b', '((()))'):
            hits, used_index = search_index.search_posts(keyword)
            self.assertIsInstance(hits, list, keyword)
            self.assertIsInstance(used_index, bool, keyword)

    def test_no_hits_for_unrelated_query(self):
        """索引可用但没命中：返回 ([], True)。"""
        self.make_post('饼图文章', body='饼图正文')
        search_index.rebuild_index()

        hits, used_index = search_index.search_posts('完全不相干的词')

        self.assertEqual(hits, [])
        self.assertTrue(used_index)

    # ---------- 管理命令 ----------

    def test_rebuild_search_index_command(self):
        """管理命令能重建索引并打印篇数。"""
        self.make_post('文章一')
        self.make_post('文章二', status=Post.STATUS_DRAFT)
        out = StringIO()

        call_command('rebuild_search_index', stdout=out)

        self.assertIn('索引重建完成：2 篇', out.getvalue())

    def test_rebuild_search_index_command_quiet(self):
        """--quiet：成功时不打印内容。"""
        self.make_post('文章一')
        out = StringIO()

        call_command('rebuild_search_index', '--quiet', stdout=out)

        self.assertEqual(out.getvalue(), '')

    # ---------- 后台保存 / 删除时同步索引 ----------

    @staticmethod
    def _post_admin():
        from django.contrib.admin.sites import AdminSite

        from .admin import PostAdmin

        return PostAdmin(Post, AdminSite())

    def test_admin_save_model_indexes_post(self):
        """后台保存文章后，搜索立刻能搜到（不用手动重建）。"""
        search_index.rebuild_index()  # 先建一个空索引
        post = Post.objects.create(title='后台新建文章', body='后台正文里有饼图')

        self._post_admin().save_model(None, post, None, False)

        hits, used_index = search_index.search_posts('饼图')
        self.assertTrue(used_index)
        self.assertEqual(self.titles(hits), ['后台新建文章'])

    def test_admin_save_model_ignores_missing_index(self):
        """索引没建时后台保存也不能报错（保存成功，只是索引不同步）。"""
        post = Post.objects.create(title='无索引也能保存', body='正文')

        self._post_admin().save_model(None, post, None, False)  # 不应抛异常

        post.refresh_from_db()
        self.assertEqual(post.title, '无索引也能保存')

    def test_admin_delete_model_removes_from_index(self):
        """后台删除文章后，搜索里也不再有它。"""
        post = self.make_post('饼图文章', body='饼图正文')
        self.make_post('保留文章', body='保留正文')
        search_index.rebuild_index()

        self._post_admin().delete_model(None, post)

        hits, used_index = search_index.search_posts('饼图')
        self.assertTrue(used_index)
        self.assertEqual(hits, [])
        kept, _ = search_index.search_posts('保留文章')
        self.assertEqual(self.titles(kept), ['保留文章'])
