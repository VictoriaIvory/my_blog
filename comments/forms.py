"""评论表单。"""
from django import forms

from .models import Comment


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['body']
        widgets = {
            'body': forms.Textarea(attrs={
                'rows': 4,
                'maxlength': 1000,
                'placeholder': '写下你的想法…（支持换行）',
            }),
        }
        labels = {'body': ''}

    def clean_body(self):
        body = self.cleaned_data.get('body', '').strip()
        if not body:
            raise forms.ValidationError('评论内容不能为空。')
        return body
