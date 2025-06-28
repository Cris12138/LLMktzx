from django.urls import path, include
from django.contrib import admin
from myneo4j.views import health_assessment
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include(('accounts.urls', 'accounts'), namespace='accounts')),
    path('', include(('myneo4j.urls', 'myneo4j'), namespace='myneo4j')),  # 所有 myneo4j 的路由通过这里统一管理
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # 添加媒体文件路由