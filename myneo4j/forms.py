from django import forms
from .models import ForumPost

class PostForm(forms.ModelForm):
    class Meta:
        model = ForumPost
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入标题'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': '请输入内容'
            })
        }