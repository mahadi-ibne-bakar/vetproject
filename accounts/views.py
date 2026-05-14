from django.http import HttpResponse


def register(request):
    return HttpResponse("Coming soon")


def user_login(request):
    return HttpResponse("Coming soon")


def user_logout(request):
    return HttpResponse("Coming soon")


def profile(request):
    return HttpResponse("Coming soon")


def password_reset_request(request):
    return HttpResponse("Coming soon")


def password_reset_done(request):
    return HttpResponse("Coming soon")


def password_reset_confirm(request, uidb64, token):
    return HttpResponse("Coming soon")


def password_reset_complete(request):
    return HttpResponse("Coming soon")


def vet_apply(request):
    return HttpResponse("Coming soon")


def vet_login(request):
    return HttpResponse("Coming soon")


def vet_application_pending(request):
    return HttpResponse("Coming soon")