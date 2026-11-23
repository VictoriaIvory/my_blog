"""注册 / 登录相关表单。"""
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=False,
        label='邮箱（可选）',
        help_text='不填也能用，填了以后方便找回密码。',
    )

    class Meta:
        model = User
        fields = ['username', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = '用户名'
        self.fields['username'].help_text = '必填。150 个字符以内，可以用字母、数字和 @/./+/-/_。'
        self.fields['password1'].label = '密码'
        self.fields['password2'].label = '再输一次密码'
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-input')

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip()
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('这个邮箱已经被注册过了。')
        return email
