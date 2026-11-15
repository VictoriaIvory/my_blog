"""后台管理配置。

注册模型后，/admin/ 就自动有增删改查页面，不用写一行前端代码。
"""

from django.contrib import admin

from .models import Category, Post


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'post_count']
    search_fields = ['name']

    def post_count(self, obj):
        """每个分类下有几篇已发布文章。"""
        return obj.posts.filter(is_published=True).count()
    post_count.short_description = '已发布文章数'


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'is_published', 'created_at', 'updated_at']
    list_filter = ['is_published', 'category', 'created_at']
    search_fields = ['title', 'body']
    date_hierarchy = 'created_at'
    # 编辑页里哪些字段只读（时间由系统自动写）
    readonly_fields = ['created_at', 'updated_at']
