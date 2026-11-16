"""Markdown 渲染（阶段 3）。

文章正文在后台用 Markdown 写，这里统一转成 HTML：
1. markdown 库转 HTML：表格、围栏代码块（```python）、Pygments 代码高亮
2. bleach 清洗：只保留白名单里的标签和属性
   —— 即使正文里混进 <script>、onerror= 这类东西，输出到页面上也不会执行

为什么只有管理员能写文章还要清洗：
博客以后可能开放评论/投稿，或者从别处复制正文；渲染函数是唯一的出口，
在这里兜底一次，比在模板里到处记得转义可靠。
"""

import re

import bleach
import markdown as md
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe

# 启用的 Markdown 扩展：
#   fenced_code  ``` 围栏代码块
#   codehilite  代码高亮（配合 Pygments）
#   tables      表格
#   sane_lists  嵌套列表
#   nl2br       单个换行也变 <br>（保留旧文章的行间感）
MARKDOWN_EXTENSIONS = ['fenced_code', 'codehilite', 'tables', 'sane_lists', 'nl2br']

MARKDOWN_EXTENSION_CONFIGS = {
    'codehilite': {
        'css_class': 'codehilite',   # 与 static/css/pygments.css 里的选择器对应
        'guess_lang': False,         # 不猜语言，避免高亮错得莫名其妙
    },
}

# bleach 白名单：只放 Markdown 正常会产出的标签
ALLOWED_TAGS = {
    'p', 'br', 'hr',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'strong', 'em', 'del', 'ins', 'mark', 'sup', 'sub',
    'ul', 'ol', 'li',
    'blockquote',
    'code', 'pre', 'span', 'div',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'a', 'img',
}

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'rel'],
    'img': ['src', 'alt', 'title', 'width', 'height'],
    'th': ['align'],
    'td': ['align'],
    # Pygments 输出的高亮用 class 表达（k、s、c1…）
    'div': ['class'],
    'pre': ['class'],
    'code': ['class'],
    'span': ['class'],
    # Markdown 标题生成锚点 id（toc 扩展用得到）
    'h1': ['id'], 'h2': ['id'], 'h3': ['id'],
    'h4': ['id'], 'h5': ['id'], 'h6': ['id'],
}

ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']


def render_markdown(text):
    """把 Markdown 正文转成干净的 HTML（返回 SafeString，模板里直接输出）。"""
    if not text:
        return mark_safe('')

    html = md.markdown(
        text,
        extensions=MARKDOWN_EXTENSIONS,
        extension_configs=MARKDOWN_EXTENSION_CONFIGS,
    )
    clean = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,           # 不在白名单的标签直接删掉（保留里面的文字）
        strip_comments=True,
    )
    return mark_safe(clean)


def make_summary(text, length=80):
    """从 Markdown 正文生成纯文本摘要（列表页用）。

    先渲染再 strip_tags，得到的是「用户实际读到的文字」，
    不会把 **、```、[]() 这些 Markdown 记号混进摘要。
    """
    if not text:
        return ''

    plain = strip_tags(render_markdown(text))
    plain = re.sub(r'\s+', ' ', plain).strip()
    if len(plain) <= length:
        return plain
    return plain[:length] + '…'
