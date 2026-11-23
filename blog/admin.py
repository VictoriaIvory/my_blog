"""后台管理配置。

注册模型后，/admin/ 就自动有增删改查页面，不用写一行前端代码。
2026-11-16：加标签、封面图、阅读量。
2026-11-23：加站点设置、独立页面开关、评论审核入口。
2026-11-23：用「状态 + 发布时间」替代「已发布」开关（草稿 / 定时发布）。
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    STATUS_DRAFT,
    STATUS_PUBLISHED,
    BlogSettings,
    Category,
    Post,
    Tag,
    visible_condition,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'post_count']
    search_fields = ['name']

    def post_count(self, obj):
        """每个分类下有几篇前台可见的文章（不含独立页面）。"""
        return obj.posts.filter(visible_condition(), is_page=False).count()
    post_count.short_description = '已发布文章数'


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'post_count']
    search_fields = ['name']

    def post_count(self, obj):
        return obj.posts.filter(visible_condition(), is_page=False).count()
    post_count.short_description = '已发布文章数'


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'pub_time', 'is_page', 'category', 'views', 'created_at']
    list_filter = ['status', 'is_page', 'category', 'tags', 'pub_time']
    search_fields = ['title', 'body']
    date_hierarchy = 'created_at'
    # 编辑页里哪些字段只读（时间、阅读量由系统自动写）
    readonly_fields = ['created_at', 'updated_at', 'views', 'cover_preview']
    filter_horizontal = ['tags']
    actions = ['make_published', 'make_draft']

    fieldsets = [
        ('内容', {'fields': ['title', 'body', 'cover', 'cover_preview']}),
        ('归类', {'fields': ['category', 'tags', 'is_page']}),
        ('发布', {
            'fields': ['status', 'pub_time'],
            'description': (
                '「草稿」不会出现在前台；「已发布」还要等「发布时间」到了才可见。'
                '把发布时间填成将来，就是定时发布。'
            ),
        }),
        ('互动', {'fields': ['allow_comments']}),
        ('统计', {'fields': ['views', 'created_at', 'updated_at']}),
    ]

    @admin.display(description='封面预览')
    def cover_preview(self, obj):
        if obj.cover:
            return format_html(
                '<img src="{}" style="max-height:120px;border-radius:8px">',
                obj.cover.url,
            )
        return '（未上传封面图）'

    @admin.action(description='发布选中的文章（改为「已发布」）')
    def make_published(self, request, queryset):
        """只改状态，不动发布时间；想立刻可见就顺手把发布时间改成过去。"""
        queryset.update(status=STATUS_PUBLISHED)

    @admin.action(description='把选中的文章转为「草稿」')
    def make_draft(self, request, queryset):
        queryset.update(status=STATUS_DRAFT)


@admin.register(BlogSettings)
class BlogSettingsAdmin(admin.ModelAdmin):
    """站点设置是单例：只允许一行，且不允许在后台新增第二行。"""

    fieldsets = [
        ('基本信息', {
            'fields': ['site_name', 'site_description', 'site_keywords'],
        }),
        ('页脚 / 备案', {
            'fields': ['footer_text', 'beian_code'],
        }),
        ('统计代码', {
            'fields': ['analytics_code'],
            'description': '原样插入页面底部，只粘贴可信的统计脚本（如百度统计）。',
        }),
        ('互动', {
            'fields': ['allow_site_comments', 'comment_need_review'],
        }),
        ('侧边栏', {
            'fields': ['sidebar_article_count', 'sidebar_comment_count'],
        }),
    ]
    readonly_fields = ['updated_at']

    def has_add_permission(self, request):
        # 已经有那一行就不让再加
        return not BlogSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
