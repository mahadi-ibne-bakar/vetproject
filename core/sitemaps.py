from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from blog.models import BlogPost
from accounts.models import VetProfile


class StaticViewSitemap(Sitemap):
    """
    Static pages — homepage, vets listing, blog listing, about, contact.
    """
    priority    = 0.8
    changefreq  = 'weekly'
    protocol    = 'https'

    def items(self):
        return [
            'core:home',
            'consultations:vet_list',
            'blog:blog_list',
            'core:about',
            'core:contact',
        ]

    def location(self, item):
        return reverse(item)


class BlogPostSitemap(Sitemap):
    """
    All published blog posts.
    """
    priority   = 0.7
    changefreq = 'monthly'
    protocol   = 'https'

    def items(self):
        return BlogPost.objects.filter(
            status='published'
        ).order_by('-published_at')

    def lastmod(self, obj):
        return obj.published_at

    def location(self, obj):
        return reverse('blog:blog_post', args=[obj.slug])


class VetProfileSitemap(Sitemap):
    """
    All approved active vet profiles.
    """
    priority   = 0.8
    changefreq = 'weekly'
    protocol   = 'https'

    def items(self):
        return VetProfile.objects.filter(
            application_status='approved',
            is_active=True,
        ).select_related('user').order_by('id')

    def lastmod(self, obj):
        return obj.updated_at if hasattr(obj, 'updated_at') else None

    def location(self, obj):
        return reverse('consultations:vet_detail', args=[obj.id])