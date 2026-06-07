from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.utils.text import slugify

from accounts.decorators import login_required_vet, login_required_user
from .models import BlogPost, Review

from django import forms as django_forms
from core.widgets import ImageUploadWidget

class BlogSubmitForm(django_forms.Form):
    title   = django_forms.CharField(
        max_length=200,
        widget=django_forms.TextInput(attrs={'placeholder': ' '})
    )
    content = django_forms.CharField(
        widget=django_forms.Textarea(attrs={'placeholder': ' ', 'rows': 18})
    )
    featured_image = django_forms.ImageField(
        required=False,
        widget=ImageUploadWidget(),
    )

class BlogEditForm(django_forms.Form):
    title   = django_forms.CharField(
        max_length=200,
        widget=django_forms.TextInput(attrs={'placeholder': ' '})
    )
    content = django_forms.CharField(
        widget=django_forms.Textarea(attrs={'placeholder': ' ', 'rows': 18})
    )
    featured_image = django_forms.ImageField(
        required=False,
        widget=ImageUploadWidget(),
    )


# ── Public views ───────────────────────────────────────────────────────────────

def blog_list(request):
    from blog.models import BlogPost

    search   = request.GET.get('search', '').strip()
    category = request.GET.get('category', '')

    posts = BlogPost.objects.filter(
        status='published'
    ).select_related('author').order_by('-published_at')

    if search:
        from django.db.models import Q
        posts = posts.filter(
            Q(title__icontains=search)   |
            Q(content__icontains=search) |
            Q(author__first_name__icontains=search) |
            Q(author__last_name__icontains=search)
        )

    if category:
        posts = posts.filter(category=category)

    ctx = {
        'posts':            posts,
        'search':           search,
        'selected_category': category,
        'categories':       BlogPost.Category.choices,
        'total_count':      posts.count(),
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
        form = BlogSubmitForm(request.POST, request.FILES)
        if form.is_valid():
            title   = form.cleaned_data['title']
            content = form.cleaned_data['content']
            category = request.POST.get('category', 'general_health')

            slug = slugify(title)
            base_slug = slug
            counter = 1
            while BlogPost.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            post = BlogPost.objects.create(
                title=title,
                category = category
                slug=slug,
                content=content,
                author=request.user,
                status=BlogPost.Status.PENDING,
            )

            if form.cleaned_data.get('featured_image'):
                from core.image_utils import compress_if_image, rename_image
                new_name = rename_image(
                    request.FILES['featured_image'],
                    prefix='blog',
                    identifier=title,
                )
                post.featured_image = compress_if_image(
                    request.FILES['featured_image'],
                    image_type='blog',
                    new_name=new_name,
                )
                
                post.save()

            messages.success(
                request,
                "Your post has been submitted for review."
            )
            return redirect('blog:my_blog_posts')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = BlogSubmitForm()

    return render(request, 'vet/submit_blog.html', {'form': form})


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
        BlogPost, id=post_id, author=request.user
    )

    if post.status not in ['draft', 'rejected']:
        messages.error(
            request,
            "You can only edit draft or rejected posts."
        )
        return redirect('blog:my_blog_posts')

    if request.method == 'POST':
        form = BlogEditForm(request.POST, request.FILES)
        if form.is_valid():
            post.title   = form.cleaned_data['title']
            post.content = form.cleaned_data['content']
            post.status  = BlogPost.Status.PENDING

            if form.cleaned_data.get('featured_image'):
                from core.image_utils import compress_if_image, rename_image
                from core.storage_utils import delete_file
                if post.featured_image:
                    delete_file(post.featured_image)
                new_name = rename_image(
                    request.FILES['featured_image'],
                    prefix='blog',
                    identifier=post.title,
                )
                post.featured_image = compress_if_image(
                    request.FILES['featured_image'],
                    image_type='blog',
                    new_name=new_name,
                )

            post.save()
            messages.success(request, "Post updated and resubmitted for review.")
            return redirect('blog:my_blog_posts')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = BlogEditForm(initial={
            'title':   post.title,
            'content': post.content,
        })

    return render(request, 'vet/edit_blog.html', {
        'form': form,
        'post': post,
    })