"""评论相关的小工具：取可见评论、组装成树。"""
from .models import Comment


def visible_comments(post):
    """这篇下面所有已通过审核的评论（新版在前面的排序交给调用方）。"""
    return (
        Comment.objects
        .filter(post=post, is_approved=True)
        .select_related('author')
        .order_by('created_at')
    )


def build_comment_tree(post, max_depth=5):
    """把评论组装成嵌套结构，模板里递归渲染。

    返回 [{'comment': c, 'depth': 1, 'children': [...]}, ...]。
    只显示审核通过的评论；父评论没通过时，子评论也一并隐藏。
    """
    comments = list(visible_comments(post))
    nodes = {c.pk: {'comment': c, 'depth': 1, 'children': []} for c in comments}

    roots = []
    for comment in comments:
        node = nodes[comment.pk]
        parent = nodes.get(comment.parent_id)
        if parent is None:
            roots.append(node)
        else:
            node['depth'] = parent['depth'] + 1
            parent['children'].append(node)

    def trim(node):
        if node['depth'] >= max_depth:
            node['children'] = []
            return
        for child in node['children']:
            trim(child)

    for root in roots:
        trim(root)
    return roots


def reply_target(post, comment_id):
    """回复某条评论时，确认目标属于这篇文章且已通过审核。"""
    if not comment_id:
        return None
    return Comment.objects.filter(
        pk=comment_id, post=post, is_approved=True
    ).select_related('author').first()
