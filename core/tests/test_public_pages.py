"""
Tests for public-facing pages.
Verifies they load correctly with expected content.
"""

from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User, VetProfile
from blog.models import BlogPost
from core.models import SiteSettings


class PublicPageTest(TestCase):

    def setUp(self):
        from core.models import SiteSettings
        SiteSettings.get()  # Just ensure it exists with defaults
        self.client = Client()
        SiteSettings.objects.get_or_create(
            booking_enabled=True,
            booking_fee=50,
        )

    def test_homepage_loads(self):
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)

    def test_about_page_loads(self):
        response = self.client.get(reverse('core:about'))
        self.assertEqual(response.status_code, 200)

    def test_contact_page_loads(self):
        response = self.client.get(reverse('core:contact'))
        self.assertEqual(response.status_code, 200)

    def test_shop_page_loads(self):
        response = self.client.get(reverse('core:shop'))
        self.assertEqual(response.status_code, 200)

    def test_health_check(self):
        response = self.client.get(reverse('core:health_check'))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {'status': 'ok', 'database': 'ok'}
        )

    def test_vet_list_loads(self):
        response = self.client.get(reverse('consultations:vet_list'))
        self.assertEqual(response.status_code, 200)

    def test_blog_list_loads(self):
        response = self.client.get(reverse('blog:blog_list'))
        self.assertEqual(response.status_code, 200)

    def test_robots_txt(self):
        response = self.client.get('/robots.txt')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain')
        self.assertIn(b'Disallow: /dashboard/', response.content)

    def test_sitemap_xml(self):
        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)


class VetDetailPageTest(TestCase):

    def setUp(self):
        self.client = Client()
        SiteSettings.objects.get_or_create(
            booking_enabled=True,
            booking_fee=50,
        )
        vet_user = User.objects.create_user(
            username='vet@test.com',
            email='vet@test.com',
            password='pass123!',
            first_name='Ayesha',
            last_name='Rahman',
            role=User.Role.VET,
        )
        self.vet = VetProfile.objects.create(
            user=vet_user,
            application_status='approved',
            is_active=True,
            consultation_fee=300,
            bio='Test bio',
        )

    def test_vet_detail_loads(self):
        response = self.client.get(
            reverse('consultations:vet_detail', args=[self.vet.id])
        )
        self.assertEqual(response.status_code, 200)

    def test_unapproved_vet_returns_404(self):
        self.vet.application_status = 'pending'
        self.vet.save()
        response = self.client.get(
            reverse('consultations:vet_detail', args=[self.vet.id])
        )
        self.assertEqual(response.status_code, 404)

    def test_inactive_vet_returns_404(self):
        self.vet.is_active = False
        self.vet.save()
        response = self.client.get(
            reverse('consultations:vet_detail', args=[self.vet.id])
        )
        self.assertEqual(response.status_code, 404)


class BlogPostPageTest(TestCase):

    def setUp(self):
        self.client = Client()
        author = User.objects.create_user(
            username='vet@test.com',
            email='vet@test.com',
            password='pass123!',
            role=User.Role.VET,
        )
        self.post = BlogPost.objects.create(
            title='Test Blog Post',
            slug='test-blog-post',
            content='This is test content for the blog post.',
            author=author,
            status='published',
        )

    def test_blog_post_loads(self):
        response = self.client.get(
            reverse('blog:blog_post', args=[self.post.slug])
        )
        self.assertEqual(response.status_code, 200)

    def test_unpublished_post_returns_404(self):
        self.post.status = 'pending'
        self.post.save()
        response = self.client.get(
            reverse('blog:blog_post', args=[self.post.slug])
        )
        self.assertEqual(response.status_code, 404)

    def test_blog_post_increments_view_count(self):
        initial_count = self.post.view_count
        self.client.get(
            reverse('blog:blog_post', args=[self.post.slug])
        )
        self.post.refresh_from_db()
        self.assertEqual(self.post.view_count, initial_count + 1)


class ContactFormTest(TestCase):

    def setUp(self):
        from core.models import SiteSettings
        SiteSettings.get()  # Just ensure it exists with defaults
        self.client = Client()
        SiteSettings.objects.get_or_create(booking_enabled=True)

    def test_contact_form_submission(self):
        response = self.client.post(reverse('core:contact'), {
            'name':    'Test User',
            'email':   'test@test.com',
            'subject': 'Test Subject',
            'message': 'This is a test message.',
        })
        self.assertEqual(response.status_code, 200)
        # submitted flag should be True
        self.assertTrue(response.context['submitted'])

    def test_contact_form_requires_name_and_email(self):
        response = self.client.post(reverse('core:contact'), {
            'message': 'Just a message without name or email.',
        })
        self.assertFalse(response.context.get('submitted', False))