"""后台管理配置。

注册模型后，/admin/ 就自动有增删改查页面，不用写一行前端代码。
2026-11-16：加标签、封面图、阅读量后同步更新。
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Post, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'post_count']
    search_fields = ['name']

    def post_count(self, obj):
        """每个分类下有几篇已发布文章。"""
        return obj.posts.filter(is_published=True).count()
    post_count.short_description = '已发布文章数'


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'post_count']
    search_fields = ['name']

    def post_count(self, obj):
        return obj.posts.filter(is_published=True).count()
    post_count.short_description = '已发布文章数'


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'views', 'is_published', 'created_at', 'updated_at']
    list_filter = ['is_published', 'category', 'tags', 'created_at']
    search_fields = ['title', 'body']
    date_hierarchy = 'created_at'
    # 编辑页里哪些字段只读（时间、阅读量由系统自动写）
    readonly_fields = ['created_at', 'updated_at', 'views', 'cover_preview']
    filter_horizontal = ['tags']

    fieldsets = [
        ('内容', {'fields': ['title', 'body', 'cover', 'cover_preview']}),
        ('归类', {'fields': ['category', 'tags', 'is_published']}),
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
