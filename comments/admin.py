"""评论后台：审核、批量通过/取消。"""
from django.contrib import admin

from .models import Comment


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['short_body', 'post', 'author', 'is_reply', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'created_at']
    search_fields = ['body', 'author__username', 'post__title']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']
    actions = ['approve_comments', 'unapprove_comments']

    @admin.display(description='内容')
    def short_body(self, obj):
        return obj.body[:40] + ('…' if len(obj.body) > 40 else '')

    @admin.action(description='通过选中的评论')
    def approve_comments(self, request, queryset):
        count = queryset.update(is_approved=True)
        self.message_user(request, f'已通过 {count} 条评论')

    @admin.action(description='取消通过选中的评论')
    def unapprove_comments(self, request, queryset):
        count = queryset.update(is_approved=False)
        self.message_user(request, f'已取消 {count} 条评论')
