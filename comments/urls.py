from django.urls import path

from . import views

app_name = 'comments'

urlpatterns = [
    # 发表评论：POST /comment/<post_id>/post
    path('comment/<int:post_id>/post', views.post_comment, name='post_comment'),
]
