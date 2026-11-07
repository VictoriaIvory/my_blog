"""后台管理配置。

注册模型后，/admin/ 就自动有增删改查页面，不用写一行前端代码。
"""

from django.contrib import admin

from .models import Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['title', 'is_published', 'created_at', 'updated_at']
    list_filter = ['is_published', 'created_at']
    search_fields = ['title', 'body']
    date_hierarchy = 'created_at'
    # 编辑页里哪些字段只读（时间由系统自动写）
    readonly_fields = ['created_at', 'updated_at']
