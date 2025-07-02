from django.db import models
from accounts.models import UserProfile
from django.utils import timezone
# Create your models here.


class MyNode(models.Model):
    name = models.CharField(verbose_name='node的name', blank=True, null=True, default='', max_length=100)
    leixing = models.CharField(verbose_name='类型的中文', blank=True, null=True, default='', max_length=100)

    def __str__(self):
        return str(self.name)

    class Meta:
        ordering = ['-id']
        verbose_name = '节点信息'
        verbose_name_plural = verbose_name


class MyWenda(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    question = models.CharField(verbose_name='问题', blank=True, null=True, default='', max_length=1000)
    anster = models.CharField(verbose_name='答案', blank=True, null=True, default='', max_length=1000)

    def __str__(self):
        return str(self.question)

    class Meta:
        ordering = ['-id']
        verbose_name = '问答信息'
        verbose_name_plural = verbose_name





class ForumPost(models.Model):
    title = models.CharField("帖子标题", max_length=200)
    content = models.TextField("帖子内容")
    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name="作者")
    created_at = models.DateTimeField("创建时间", default=timezone.now)
    updated_at = models.DateTimeField("更新时间", auto_now=True)
    views = models.PositiveIntegerField("浏览数", default=0)

    class Meta:
        verbose_name = "论坛帖子"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def likes_count(self):
        """获取点赞数"""
        return self.likes.count()


class PostLike(models.Model):
    """点赞记录表"""
    post = models.ForeignKey(ForumPost, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name="点赞用户")
    created_at = models.DateTimeField("点赞时间", default=timezone.now)

    class Meta:
        verbose_name = "帖子点赞"
        verbose_name_plural = verbose_name
        unique_together = ('post', 'user')  # 确保用户不能重复点赞

class PostReply(models.Model):
    post = models.ForeignKey(ForumPost, on_delete=models.CASCADE, related_name='replies')
    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name="作者")
    content = models.TextField("回复内容")
    created_at = models.DateTimeField("创建时间", default=timezone.now)

    class Meta:
        verbose_name = "帖子回复"
        verbose_name_plural = verbose_name
        ordering = ['created_at']

    def __str__(self):
        return f"回复: {self.post.title}"