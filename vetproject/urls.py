from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from core.sitemaps import StaticViewSitemap, BlogPostSitemap, VetProfileSitemap

sitemaps = {
    'static': StaticViewSitemap,
    'blog':   BlogPostSitemap,
    'vets':   VetProfileSitemap,
}

urlpatterns = [
    # Django's built-in admin (keep for database emergencies)
    path('django-admin/', admin.site.urls),

    # App URLs
    path('', include('core.urls', namespace='core')),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('consultations/', include('consultations.urls', namespace='consultations')),
    path('blog/', include('blog.urls', namespace='blog')),

    # Custom admin dashboard
    path('dashboard/', include('vetproject.admin_urls', namespace='dashboard')),

    path('sitemap.xml', sitemap, {'sitemaps': sitemaps},
         name='django.contrib.sitemaps.views.sitemap'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)