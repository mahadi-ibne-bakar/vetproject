from django.contrib import admin
from .models import BlogPost, Review

@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'status', 'published_at', 'created_at']
    prepopulated_fields = {'slug': ('title',)}

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['reviewer', 'vet', 'rating', 'is_visible', 'created_at']