from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.blog_list, name='blog_list'),

    # Vet blog submission — must come BEFORE the slug pattern
    path('submit/', views.submit_blog_post, name='submit_blog_post'),
    path('my-posts/', views.my_blog_posts, name='my_blog_posts'),
    path('my-posts/<int:post_id>/edit/', views.edit_blog_post, name='edit_blog_post'),

    # Slug pattern last — catches everything else
    path('<slug:slug>/', views.blog_post, name='blog_post'),
]