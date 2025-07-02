from django.db import models
from django.contrib.auth.models import AbstractUser


# Create your models here.
class UserProfile(AbstractUser):
    mpassword = models.CharField(verbose_name='密码', blank=True, null=True, default='0', max_length=100)

    def __str__(self):
        return self.username

    class Meta:
        ordering = ['-id']
        verbose_name = '用户管理'
        verbose_name_plural = verbose_name
