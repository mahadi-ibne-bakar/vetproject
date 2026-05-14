from django.http import HttpResponse


def blog_list(request):
    return HttpResponse("Coming soon")

def blog_post(request, slug):
    return HttpResponse("Coming soon")

def submit_blog_post(request):
    return HttpResponse("Coming soon")

def my_blog_posts(request):
    return HttpResponse("Coming soon")

def edit_blog_post(request, post_id):
    return HttpResponse("Coming soon")