from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.utils.text import slugify

from accounts.decorators import login_required_vet, login_required_user
from .models import BlogPost, Review


# ── Public views ───────────────────────────────────────────────────────────────

def blog_list(request):
    posts = BlogPost.objects.filter(
        status='published'
    ).select_related('author').order_by('-published_at')

    ctx = {
        'posts': posts,
        'post_count': posts.count(),
    }
    return render(request, 'public/blog_list.html', ctx)


def blog_post(request, slug):
    post = get_object_or_404(
        BlogPost,
        slug=slug,
        status='published',
    )

    # Increment view count — use F() to avoid race conditions
    from django.db.models import F
    BlogPost.objects.filter(pk=post.pk).update(view_count=F('view_count') + 1)
    post.refresh_from_db()

    other_posts = BlogPost.objects.filter(
        status='published',
    ).exclude(id=post.id).order_by('-published_at')[:4]

    return render(request, 'public/blog_post.html', {
        'post': post,
        'other_posts': other_posts,
    })

# ── Vet blog views ─────────────────────────────────────────────────────────────

@login_required_vet
def submit_blog_post(request):
    if request.method == 'POST':
        title   = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()

        if not title or not content:
            messages.error(request, "Title and content are required.")
            return render(request, 'vet/submit_blog.html', {
                'title': title,
                'content': content,
            })

        # Generate unique slug
        slug = slugify(title)
        base_slug = slug
        counter = 1
        while BlogPost.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        BlogPost.objects.create(
            title=title,
            slug=slug,
            content=content,
            author=request.user,
            status=BlogPost.Status.PENDING,
        )
        messages.success(
            request,
            "Your post has been submitted for review. "
            "We'll publish it once approved."
        )
        return redirect('blog:my_blog_posts')

    return render(request, 'vet/submit_blog.html', {})


@login_required_vet
def my_blog_posts(request):
    posts = BlogPost.objects.filter(
        author=request.user,
    ).order_by('-created_at')

    ctx = {'posts': posts}
    return render(request, 'vet/my_blog_posts.html', ctx)


@login_required_vet
def edit_blog_post(request, post_id):
    post = get_object_or_404(
        BlogPost,
        id=post_id,
        author=request.user,
    )

    # Can only edit drafts or rejected posts
    if post.status not in ['draft', 'rejected']:
        messages.error(
            request,
            "You can only edit draft or rejected posts. "
            "Published and pending posts cannot be edited."
        )
        return redirect('blog:my_blog_posts')

    if request.method == 'POST':
        title   = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()

        if not title or not content:
            messages.error(request, "Title and content are required.")
            return render(request, 'vet/edit_blog.html', {
                'post': post,
            })

        post.title   = title
        post.content = content
        post.status  = BlogPost.Status.PENDING
        post.save()

        messages.success(
            request,
            "Post updated and resubmitted for review."
        )
        return redirect('blog:my_blog_posts')

    return render(request, 'vet/edit_blog.html', {'post': post})