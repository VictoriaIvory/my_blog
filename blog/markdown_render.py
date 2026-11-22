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
from django.utils.safestring import mark_safe

# 启用的 Markdown 扩展：
#   fenced_code  ``` 围栏代码块
#   codehilite  代码高亮（配合 Pygments）
#   tables      表格
#   sane_lists  嵌套列表
#   nl2br       单个换行也变 <br>（保留旧文章的行间感）
#   toc         给标题生成锚点 id（详情页右侧的「本文目录」要用）
MARKDOWN_EXTENSIONS = ['fenced_code', 'codehilite', 'tables', 'sane_lists', 'nl2br', 'toc']


def _slugify_keep_unicode(value, separator='-'):
    """给 toc 扩展生成标题锚点。

    Python-Markdown 默认的 slugify 会把中文全删掉（标题「一、分类」的 id 会变成
    ``slug`` / ``_1``），目录里点过去全错位。这里保留中文、只把标点空格换成连字符。
    """
    if isinstance(value, (list, tuple)):
        value = ''.join(value)
    text = str(value).strip().lower()
    text = re.sub(r'[^\w\u4e00-\u9fff]+', separator, text, flags=re.UNICODE)
    text = re.sub(re.escape(separator) + r'{2,}', separator, text).strip(separator)
    return text or 'section'


MARKDOWN_EXTENSION_CONFIGS = {
    'codehilite': {
        'css_class': 'codehilite',   # 与 static/css/pygments.css 里的选择器对应
        'guess_lang': False,         # 不猜语言，避免高亮错得莫名其妙
    },
    'toc': {
        'slugify': _slugify_keep_unicode,
        'toc_depth': '2-3',          # 只给 h2 / h3 生成锚点
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


_CODE_FENCE_RE = re.compile(r'```[^\n]*\n?(.*?)```', re.S)
_IMAGE_RE = re.compile(r'!\[([^\]]*)\]\([^)]*\)')
_LINK_RE = re.compile(r'\[([^\]]+)\]\([^)]*\)')
_INLINE_MARK_RE = re.compile(r'[#>*_`~]+')


def plain_text(text):
    """把 Markdown 正文变成纯文本（不渲染 HTML，速度快很多）。

    只做「去记号」：保留文字和代码内容，去掉 ```、#、**、[文字](链接) 这类
    结构符号。列表页摘要、字数统计都用它——之前是先渲染再 strip_tags，
    每张卡片都要跑一遍 Markdown + bleach，文章多了会明显变慢。
    """
    if not text:
        return ''

    # 代码围栏只去围栏本身，保留代码内容
    plain = _CODE_FENCE_RE.sub(lambda m: m.group(1), text)
    # 图片 -> alt 文字；链接 -> 链接文字
    plain = _IMAGE_RE.sub(lambda m: m.group(1), plain)
    plain = _LINK_RE.sub(lambda m: m.group(1), plain)
    # 强调/标题/行内代码等记号；表格竖线也当分隔符
    plain = _INLINE_MARK_RE.sub(' ', plain)
    plain = plain.replace('|', ' ')
    return re.sub(r'\s+', ' ', plain).strip()


def make_summary(text, length=80):
    """从 Markdown 正文生成纯文本摘要（列表页用）。

    不渲染 HTML，只去掉 Markdown 记号，保证摘要里不会出现
    **、```、[]() 这些原文符号。
    """
    plain = plain_text(text)
    if len(plain) <= length:
        return plain
    return plain[:length] + '…'


def count_chars(text):
    """正文有效字符数（去掉空白），用来估算阅读时间。"""
    return len(re.sub(r'\s+', '', plain_text(text)))


_HEADING_TAG_RE = re.compile(r'<h([23]) id="([^"]+)">(.*?)</h\1>', re.S)


def extract_toc(html):
    """从渲染后的正文 HTML 里抽出 h2/h3，生成详情页的「本文目录」。

    返回 [{'level': 2, 'anchor': '一-分类', 'text': '一、分类'}, ...]。
    """
    items = []
    for level, anchor, inner in _HEADING_TAG_RE.findall(html or ''):
        text = bleach.clean(inner, tags=set(), strip=True).strip()
        if text:
            items.append({'level': int(level), 'anchor': anchor, 'text': text})
    return items
