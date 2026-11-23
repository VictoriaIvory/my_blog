"""深色模式（第二批 · 复现 DjangoBlog）的自动化测试。

跑法：
    python manage.py test blog.tests_theme
    python manage.py test            # 全量，也会自动发现本文件

这里只测「服务端能保证的东西」：模板里按钮 / 无障碍属性 / 脚本引用 /
防闪烁内联脚本 / 静态资源内容。点按钮切换、跟随系统深浅色、Ctrl+Shift+D
这些真实 JS 交互需要浏览器，本文件不做（也不该做）假测试 ——
留给 Lead 用 Edge headless 在 1440px / 480px 截图人工验收。
"""

import re
from pathlib import Path

from django.contrib.auth.models import User
from django.contrib.staticfiles import finders
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .models import Post


def read_static(relative_path):
    """读取 static/ 下的文件（走 staticfiles finders，不经过网络）。"""
    found = finders.find(relative_path)
    if not found:
        raise AssertionError(f'静态文件不存在：{relative_path}')
    return Path(found).read_text(encoding='utf-8')


class ThemeToggleTemplateTests(TestCase):
    """页面里要有深色模式切换按钮，且带完整的无障碍属性。"""

    def setUp(self):
        self.post = Post.objects.create(title='深色模式测试文章', body='正文')

    def test_home_page_has_toggle_button(self):
        """首页有切换按钮，带 id / aria-label。"""
        response = self.client.get(reverse('blog:list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="theme-toggle"')
        self.assertContains(response, 'aria-label="切换到深色模式"')

    def test_detail_page_has_toggle_button(self):
        """文章详情页同样有切换按钮。"""
        response = self.client.get(self.post.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="theme-toggle"')
        self.assertContains(response, 'aria-label="切换到深色模式"')

    def test_toggle_button_has_accessible_attributes(self):
        """按钮是无障碍可识别的：type=button、aria-pressed、title。"""
        response = self.client.get(reverse('blog:list'))
        html = response.content.decode('utf-8')

        # 截取按钮起始标签，避免把页面别处的 aria-label 误判成按钮的
        match = re.search(r'<button[^>]*id="theme-toggle"[^>]*>', html)
        self.assertIsNotNone(match, '没找到 id="theme-toggle" 的按钮')
        button_tag = match.group(0)

        self.assertIn('type="button"', button_tag)
        self.assertIn('aria-pressed="false"', button_tag)
        self.assertIn('aria-label=', button_tag)
        self.assertIn('title=', button_tag)
        # 两个内联 SVG 图标（太阳 / 月亮），显隐交给 CSS
        self.assertContains(response, 'class="icon-moon"')
        self.assertContains(response, 'class="icon-sun"')

    def test_all_main_pages_render_toggle(self):
        """主要页面都继承 base.html，按钮应该处处都在。"""
        urls = [
            reverse('blog:list'),                 # 首页（列表 / 搜索 / 分页）
            reverse('blog:archive'),              # 归档
            reverse('blog:about'),                # 关于
            reverse('accounts:login'),            # 登录
            reverse('accounts:register'),         # 注册
            self.post.get_absolute_url(),         # 详情（含评论区）
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'id="theme-toggle"')

    def test_logged_in_header_also_has_toggle(self):
        """登录后顶栏多了用户名/退出，按钮不能被挤掉。"""
        user = User.objects.create_user(username='深色测试用户', password='pass-123456')
        self.client.force_login(user)

        response = self.client.get(reverse('blog:list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="theme-toggle"')
        self.assertContains(response, user.username)

    def test_theme_js_loaded_with_defer(self):
        """页面底部引用了 static/js/theme.js，并且是 defer（不阻塞渲染）。"""
        response = self.client.get(reverse('blog:list'))
        html = response.content.decode('utf-8')

        match = re.search(r'<script[^>]*src="[^"]*js/theme\.js"[^>]*>', html)
        self.assertIsNotNone(match, '页面没有引用 js/theme.js')
        self.assertIn('defer', match.group(0))

    def test_anti_flicker_inline_script_present(self):
        """<head> 里的防闪烁脚本要有 localStorage 键、data-theme、系统偏好判断。"""
        response = self.client.get(reverse('blog:list'))
        html = response.content.decode('utf-8')

        self.assertIn('dark-mode-enabled', html)          # localStorage 键名
        self.assertIn('data-theme', html)                 # 给 <html> 设的属性
        self.assertIn('prefers-color-scheme', html)       # 跟随系统
        self.assertIn('localStorage', html)
        # 内联脚本必须出现在样式表之前，否则会闪一下浅色
        self.assertLess(html.find('dark-mode-enabled'),
                        html.find('css/style.css'))

    def test_theme_color_meta_present(self):
        """有 theme-color，深色下浏览器地址栏颜色不会刺眼。"""
        response = self.client.get(reverse('blog:list'))

        self.assertContains(response, 'name="theme-color"')
        self.assertContains(response, 'id="theme-color"')

    def test_url_theme_parameter_supported_in_inline_script(self):
        """内联脚本支持 ?theme=dark / ?theme=light（方便截图、分享）。"""
        response = self.client.get(reverse('blog:list'))
        html = response.content.decode('utf-8')

        self.assertIn('theme=(dark|light)', html)


class ThemeAssetsTests(SimpleTestCase):
    """直接读 static 文件做断言，不经过网络、不需要浏览器。"""

    def test_style_css_has_explicit_dark_theme(self):
        """显式切换：style.css 里有 [data-theme="dark"] 的变量覆盖。"""
        css = read_static('css/style.css')

        self.assertIn('[data-theme="dark"]', css)
        # 深色变量确实被改了：背景变深、文字变浅（不是只写了个空规则）
        dark_block = css[css.index('[data-theme="dark"]'):]
        self.assertIn('--bg: #131715', dark_block)
        self.assertIn('--ink: #e9e5da', dark_block)

    def test_style_css_follows_system_dark(self):
        """跟随系统：有 prefers-color-scheme 媒体查询，并且显式 light 能压过它。"""
        css = read_static('css/style.css')

        self.assertIn('prefers-color-scheme: dark', css)
        self.assertIn(':root:not([data-theme="light"])', css)
        self.assertIn('color-scheme: dark', css)

    def test_style_css_has_toggle_styles(self):
        """切换按钮的样式存在，且用 data-theme 控制太阳/月亮图标。"""
        css = read_static('css/style.css')

        self.assertIn('.theme-toggle', css)
        self.assertIn('.icon-sun', css)
        self.assertIn('.icon-moon', css)

    def test_style_css_overrides_pygments_tokens_for_dark(self):
        """代码高亮：深色下覆盖 Pygments 主要 token（VS Code Dark+ 配色）。"""
        css = read_static('css/style.css')

        self.assertIn('.codehilite', css)
        for color in ('#6a9955', '#ce9178', '#569cd6', '#dcdcaa', '#b5cea8'):
            with self.subTest(color=color):
                self.assertIn(color, css)

        # pygments.css 本身要保持原样（浅色主题），这里不读它的内容，
        # 只确认覆盖规则写在 style.css 里、以 data-theme 作用域出现。
        self.assertRegex(css, r'\[data-theme="dark"\] \.codehilite')

    def test_theme_js_exists_and_uses_local_storage(self):
        """theme.js 存在、用 localStorage 记住选择、键名与内联脚本一致。"""
        js = read_static('js/theme.js')

        self.assertIn('localStorage', js)
        self.assertIn('dark-mode-enabled', js)
        self.assertIn('prefers-color-scheme', js)

    def test_theme_js_handles_toggle_and_aria(self):
        """theme.js 绑定按钮点击、同步 aria 状态、提供调试入口。"""
        js = read_static('js/theme.js')

        self.assertIn('theme-toggle', js)
        self.assertIn('aria-pressed', js)
        self.assertIn('aria-label', js)
        self.assertIn('window.DarkMode', js)
