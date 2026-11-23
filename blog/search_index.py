"""全文搜索：Whoosh 索引 + jieba 中文分词 + 数据库兜底。

2026-11-23 第三批复现 DjangoBlog：全文搜索 + 关键词高亮。
参考项目用 `django-haystack + Whoosh + jieba.analyse.ChineseAnalyzer`；
本项目不引 haystack，直接用 Whoosh + jieba 写一层薄索引（少一层抽象、少一个依赖）。

设计约定（views / 模板只依赖这里的接口，不要直接 import whoosh）：
- 索引里放所有「非独立页面」文章（草稿、定时也放；命中后再用
  `Post.objects.visible()` 过滤，这样改状态 / 到点不用重建索引）；
- 索引不存在 / 依赖没装 / 查询出错时，自动退回数据库 `icontains`，
  站点永远不会因为没建索引而搜索报错；返回值里的 `used_index` 说明走了哪条路；
- 高亮不用 Whoosh 自带的 formatter（它直接拼 HTML，容易漏转义），
  自己按关键词切段、先 `escape` 再包 `<mark class="search-hit">`，XSS 安全；
- whoosh / jieba 都是「延迟导入」（放在函数里），`manage.py` 启动不会被拖慢；
- 索引目录每次从 `settings.SEARCH_INDEX_DIR` 现读，测试里可以用
  `override_settings` 指到临时目录。

对外接口：
    search_posts(query, limit=200) -> (hits, used_index)
        hits: [{'post': Post, 'title_html': str, 'snippet_html': str, 'score': float}, ...]
    rebuild_index() -> int
    index_post(post) -> None
    delete_post(post_id) -> None
"""

import logging
import re
import shutil
from pathlib import Path

from django.db.models import Q
from django.utils.html import escape

from .markdown_render import plain_text
from .models import Post

logger = logging.getLogger(__name__)

MARK_CLASS = 'search-hit'
SNIPPET_WIDTH = 160
DEFAULT_LIMIT = 200

# 用一个模块级缓存持有 jieba 分析器：第一次用到时才创建（延迟导入、不拖慢启动），
# 之后复用，避免每次搜索都重新组装一遍 Whoosh 分析器管道。
_ANALYZER = None


class SearchIndexUnavailable(Exception):
    """索引不可用（没建 / 依赖缺失 / 目录损坏）——由调用方决定是否退回数据库。"""


def _clean_query(query):
    return (query or '').strip()


def _query_terms(query):
    """把查询拆成用于高亮的词：原文 + 按空白/标点切出来的片段。"""
    query = _clean_query(query)
    if not query:
        return []

    parts = [query] + [p for p in re.split(r'[\s,，。;；:：]+', query) if p]
    seen, terms = set(), []
    for part in parts:
        key = part.casefold()
        if key and key not in seen:
            seen.add(key)
            terms.append(part)
    return terms


def _analyzer():
    """jieba 中文分析器（whoosh 的 TEXT 字段和查询共用同一套切词规则）。

    jieba.analyse.ChineseAnalyzer 是 `ChineseTokenizer | LowercaseFilter |
    StopFilter | StemFilter` 的管道：索引和查询都过一遍，
    英文大小写、词干（Paginator → pagin）才能对上。
    """
    global _ANALYZER
    if _ANALYZER is None:
        from jieba.analyse import ChineseAnalyzer

        _ANALYZER = ChineseAnalyzer()
    return _ANALYZER


def _analyzer_terms(text):
    """用索引同款分析器切词，返回去重后的查询词（已小写 / 去停用词 / 去标点）。

    为什么不用 jieba.lcut：索引里的词经过了 Whoosh 的 LowercaseFilter 和
    StemFilter，直接拿 jieba 原词去 Term 查询会漏掉英文（Paginator 存的是
    pagin）。过一遍同一个分析器，查询词和索引词才能一一对应。
    """
    terms, seen = [], set()
    for token in _analyzer()(text or ''):
        term = (token.text or '').strip()
        if not term or term in seen:
            continue
        seen.add(term)
        terms.append(term)
    return terms


def _index_path():
    """现读搜索索引目录（测试用 override_settings 覆盖）。"""
    from django.conf import settings

    return Path(settings.SEARCH_INDEX_DIR)


def _schema():
    """Whoosh 索引结构：只放检索需要的字段。

    - id：帖子主键的字符串（unique，更新同一篇文章时按它覆盖）；
    - title：标题，field_boost=2.0 —— 标题命中应当排在正文命中前面；
    - body：正文纯文本（Markdown 记号先去掉，搜索时不会搜到 ``` / ## 这类符号）。

    分析和查询都用 ChineseAnalyzer，中文按 jieba 切词。
    """
    from whoosh.fields import ID, TEXT, Schema

    analyzer = _analyzer()
    return Schema(
        id=ID(stored=True, unique=True),
        title=TEXT(stored=True, analyzer=analyzer, field_boost=2.0),
        body=TEXT(stored=True, analyzer=analyzer),
    )


def _document(post):
    """一篇文章 → 一个 Whoosh 文档。"""
    return {
        'id': str(post.pk),
        'title': post.title or '',
        'body': plain_text(post.body),
    }


def _open_index():
    """打开已存在的索引；不存在 / 为空 / 损坏都抛 SearchIndexUnavailable。"""
    from whoosh import index as whoosh_index

    path = _index_path()
    if not path.exists() or not whoosh_index.exists_in(str(path)):
        raise SearchIndexUnavailable(f'全文索引不存在：{path}')

    try:
        return whoosh_index.open_dir(str(path))
    except Exception as exc:  # 空目录 / 坏 TOC / 文件锁 —— 一律按「不可用」处理
        raise SearchIndexUnavailable(f'全文索引无法打开：{exc}') from exc


def highlight_html(text, terms):
    """把 text 里的关键词包上 <mark>，其余内容全部 HTML 转义。

    先按关键词切原文、再对每一段单独 escape，最后拼 `<mark>`；
    这样正文里的 `<script>`、`&`、引号都只会以转义后的文字出现。
    """
    text = text or ''
    terms = [t for t in (terms or []) if t]
    if not terms:
        return escape(text)

    pattern = re.compile(
        '|'.join(re.escape(t) for t in sorted(terms, key=len, reverse=True)),
        re.IGNORECASE,
    )
    pieces, last = [], 0
    for match in pattern.finditer(text):
        pieces.append(escape(text[last:match.start()]))
        pieces.append(f'<mark class="{MARK_CLASS}">{escape(match.group(0))}</mark>')
        last = match.end()
    pieces.append(escape(text[last:]))
    return ''.join(pieces)


def make_snippet(text, terms, width=SNIPPET_WIDTH):
    """从 Markdown 正文里截一段带高亮的摘要（围绕第一个命中词）。"""
    plain = plain_text(text)
    if not plain:
        return ''

    lower = plain.casefold()
    positions = [lower.find(t.casefold()) for t in terms if t]
    positions = [pos for pos in positions if pos >= 0]

    if not positions:
        head = plain[:width]
        return highlight_html(head, terms) + ('…' if len(plain) > width else '')

    # 让命中词大致出现在片段前 1/3 处，读起来更自然
    start = max(0, min(positions) - width // 3)
    end = min(len(plain), start + width)
    snippet = plain[start:end]
    prefix = '…' if start > 0 else ''
    suffix = '…' if end < len(plain) else ''
    return prefix + highlight_html(snippet, terms) + suffix


def _fallback_hits(query, limit):
    """数据库兜底：SQL icontains 搜标题/正文（索引没建时也能用）。"""
    q = _clean_query(query)
    if not q:
        return []

    terms = _query_terms(q)
    posts = (
        Post.objects.visible()
        .filter(is_page=False)
        .filter(Q(title__icontains=q) | Q(body__icontains=q))
        .select_related('category')
        .prefetch_related('tags')[:limit]
    )
    return [
        {
            'post': post,
            'title_html': highlight_html(post.title, terms),
            'snippet_html': make_snippet(post.body, terms),
            'score': 0.0,
        }
        for post in posts
    ]


def _strict_query(query):
    """第一轮查询：按空白切段，每段尽量做成「短语」。

    为什么要短语而不是逐字 OR：jieba 对未登录词会切成单字（「饼图」→ 饼/图），
    纯 OR 会让「zzzz不存在」里的「不/存/在」命中几乎所有中文文章，
    「无结果」状态永远出不来。短语查询要求这些字在原文里**连着出现**，
    「饼图」只命中真正写了「饼图」的文章；单个词的段落直接走 Term。

    返回 None 表示查询里没有任何可检索的词（纯标点 / 全是停用词）。
    """
    from whoosh.query import Or, Phrase, Term

    clauses = []
    for segment in _clean_query(query).split():
        tokens = _analyzer_terms(segment)
        if not tokens:
            continue
        if len(tokens) == 1:
            # 单字 / 单词：Term 就够，别把「图」这类单字查询也卡死
            clauses.extend([Term('title', tokens[0]), Term('body', tokens[0])])
        else:
            clauses.extend([
                Phrase('title', tokens),
                Phrase('body', tokens),
            ])
    return Or(clauses) if clauses else None


def _loose_query(query):
    """第二轮（兜底）查询：短语 0 结果时，用「够长的词」做 OR 再搜一次。

    只保留长度 >= 2 的中文词和纯 ASCII 词 —— 单个汉字不再参与，
    所以「zzzz不存在」不会因为「不」字命中一堆文章；
    而「ALLOWED_HOSTS」这类被 jieba 拆开、短语对不上的词还能救回来。
    仍然搜不到就返回 None（调用方直接给空结果，不再退回单字匹配）。
    """
    from whoosh.query import Or, Term

    terms = []
    for segment in _clean_query(query).split():
        for token in _analyzer_terms(segment):
            if (len(token) >= 2 or token.isascii()) and token not in terms:
                terms.append(token)
    if not terms:
        return None
    return Or(
        [Term('title', term) for term in terms]
        + [Term('body', term) for term in terms]
    )


def _search_candidates(searcher, query_obj, limit):
    """在打开的 searcher 上跑一次查询，返回 [(id 字符串, 分数), ...]。"""
    if query_obj is None:
        return []
    # 多取一些候选（limit*3），留出「命中但前台不可见」被过滤掉的余量。
    results = searcher.search(query_obj, limit=limit * 3)
    return [(hit['id'], float(hit.score or 0.0)) for hit in results]


def _whoosh_hits(query, limit):
    """Whoosh 索引查询：短语优先 → 宽松兜底 → 数据库可见性过滤 → 组装结果。"""
    q = _clean_query(query)
    if not _analyzer_terms(q):
        # 查询里没有可检索的词（纯标点 / 全是停用词），别去碰索引
        return []

    limit = limit if isinstance(limit, int) and limit > 0 else DEFAULT_LIMIT
    ix = _open_index()
    searcher = ix.searcher()
    try:
        if searcher.doc_count() == 0:
            raise SearchIndexUnavailable('全文索引为空')

        candidates = _search_candidates(searcher, _strict_query(q), limit)
        if not candidates:
            # 短语太严（词被 jieba 拆开、原文写法不同）时才放宽一次；
            # 放宽后仍为空就收工，绝不退回「按单字匹配」的老路。
            candidates = _search_candidates(searcher, _loose_query(q), limit)
            if not candidates:
                return []
    finally:
        searcher.close()

    # 索引里草稿/定时文章也在，这里统一用 visible() 过滤；分数顺序保持不变。
    ids = [int(pk) for pk, _ in candidates if str(pk).isdigit()]
    posts = (
        Post.objects.visible()
        .filter(is_page=False, pk__in=ids)
        .select_related('category')
        .prefetch_related('tags')
    )
    posts_by_id = {post.pk: post for post in posts}

    highlight_terms = _query_terms(q)
    hits = []
    for pk, score in candidates:
        try:
            post = posts_by_id.get(int(pk))
        except (TypeError, ValueError):
            continue
        if post is None:
            continue
        hits.append({
            'post': post,
            'title_html': highlight_html(post.title, highlight_terms),
            'snippet_html': make_snippet(post.body, highlight_terms),
            'score': score,
        })
        if len(hits) >= limit:
            break
    return hits


def search_posts(query, limit=DEFAULT_LIMIT):
    """搜索前台可见的文章，返回 (hits, used_index)。"""
    q = _clean_query(query)
    if not q:
        return [], False

    try:
        return _whoosh_hits(q, limit), True
    except SearchIndexUnavailable:
        return _fallback_hits(q, limit), False
    except Exception:  # 索引损坏、whoosh 导入失败等，都退回数据库
        logger.warning('全文搜索失败，退回数据库搜索', exc_info=True)
        return _fallback_hits(q, limit), False


def rebuild_index():
    """重建全文索引（清空旧目录、遍历所有非独立页面文章），返回入库篇数。"""
    from whoosh import index as whoosh_index

    path = _index_path()
    try:
        if path.exists():
            shutil.rmtree(path)
    except OSError as exc:
        raise SearchIndexUnavailable(f'无法清空旧索引目录：{exc}') from exc
    path.mkdir(parents=True, exist_ok=True)

    ix = whoosh_index.create_in(str(path), _schema())
    writer = ix.writer()
    count = 0
    try:
        # 草稿 / 定时也入库：查询时再用 visible() 过滤，改状态不用重建索引。
        # 只取入库需要的三列，并分批迭代（文章多的时候不一次性读进内存）。
        posts = Post.objects.filter(is_page=False).values_list(
            'pk', 'title', 'body')
        for pk, title, body in posts.iterator(chunk_size=200):
            writer.add_document(id=str(pk), title=title or '', body=plain_text(body))
            count += 1
        writer.commit()
    except Exception:
        writer.cancel()
        raise
    return count


def index_post(post):
    """新增 / 更新一篇文章的索引（独立页面则从索引里删掉）。"""
    if post is None or post.pk is None:
        return
    if post.is_page:
        delete_post(post.pk)
        return

    ix = _open_index()
    writer = ix.writer()
    try:
        writer.update_document(**_document(post))
        writer.commit()
    except Exception:
        writer.cancel()
        raise


def delete_post(post_id):
    """从索引里删除一篇文章（索引不存在则抛 SearchIndexUnavailable）。"""
    ix = _open_index()
    writer = ix.writer()
    try:
        writer.delete_by_term('id', str(post_id))
        writer.commit()
    except Exception:
        writer.cancel()
        raise
