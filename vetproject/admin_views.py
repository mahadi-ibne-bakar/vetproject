from django.http import HttpResponse


def dashboard_home(request):
    return HttpResponse("Coming soon")

def vet_list(request):
    return HttpResponse("Coming soon")

def vet_detail(request, vet_id):
    return HttpResponse("Coming soon")

def approve_vet(request, vet_id):
    return HttpResponse("Coming soon")

def reject_vet(request, vet_id):
    return HttpResponse("Coming soon")

def toggle_vet(request, vet_id):
    return HttpResponse("Coming soon")

def user_list(request):
    return HttpResponse("Coming soon")

def ban_user(request, user_id):
    return HttpResponse("Coming soon")

def unban_user(request, user_id):
    return HttpResponse("Coming soon")

def consultation_list(request):
    return HttpResponse("Coming soon")

def consultation_detail(request, appointment_id):
    return HttpResponse("Coming soon")

def cancel_consultation(request, appointment_id):
    return HttpResponse("Coming soon")

def payment_list(request):
    return HttpResponse("Coming soon")

def verify_payment(request):
    return HttpResponse("Coming soon")

def refund_list(request):
    return HttpResponse("Coming soon")

def mark_refunded(request, payment_id):
    return HttpResponse("Coming soon")

def meet_links(request):
    return HttpResponse("Coming soon")

def add_meet_link(request):
    return HttpResponse("Coming soon")

def delete_meet_link(request, link_id):
    return HttpResponse("Coming soon")

def blog_list(request):
    return HttpResponse("Coming soon")

def blog_detail(request, post_id):
    return HttpResponse("Coming soon")

def approve_blog(request, post_id):
    return HttpResponse("Coming soon")

def reject_blog(request, post_id):
    return HttpResponse("Coming soon")

def create_blog(request):
    return HttpResponse("Coming soon")

def delete_blog(request, post_id):
    return HttpResponse("Coming soon")

def review_list(request):
    return HttpResponse("Coming soon")

def toggle_review(request, review_id):
    return HttpResponse("Coming soon")

def delete_review(request, review_id):
    return HttpResponse("Coming soon")

def site_settings(request):
    return HttpResponse("Coming soon")

def analytics(request):
    return HttpResponse("Coming soon")

def admin_list(request):
    return HttpResponse("Coming soon")

def add_admin(request):
    return HttpResponse("Coming soon")

def remove_admin(request, user_id):
    return HttpResponse("Coming soon")