"""自动化测试。

跑法：python manage.py test
每个测试验证一条行为，改坏代码时能立刻发现。
"""

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Post


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
