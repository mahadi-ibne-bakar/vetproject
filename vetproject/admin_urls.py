from django.urls import path
from . import admin_views

app_name = 'dashboard'

urlpatterns = [
    path('', admin_views.dashboard_home, name='home'),

    # Vet management
    path('vets/', admin_views.vet_list, name='vet_list'),
    path('vets/<int:vet_id>/', admin_views.vet_detail, name='vet_detail'),
    path('vets/<int:vet_id>/approve/', admin_views.approve_vet, name='approve_vet'),
    path('vets/<int:vet_id>/reject/', admin_views.reject_vet, name='reject_vet'),
    path('vets/<int:vet_id>/toggle/', admin_views.toggle_vet, name='toggle_vet'),

    # User management
    path('users/', admin_views.user_list, name='user_list'),
    path('users/<int:user_id>/ban/', admin_views.ban_user, name='ban_user'),
    path('users/<int:user_id>/unban/', admin_views.unban_user, name='unban_user'),

    # Consultation management
    path('consultations/', admin_views.consultation_list, name='consultation_list'),
    path('consultations/<int:appointment_id>/', admin_views.consultation_detail, name='consultation_detail'),
    path('consultations/<int:appointment_id>/cancel/', admin_views.cancel_consultation, name='cancel_consultation'),

    # Payment management
    path('payments/', admin_views.payment_list, name='payment_list'),
    path('payments/verify/', admin_views.verify_payment, name='verify_payment'),
    path('payments/refunds/', admin_views.refund_list, name='refund_list'),
    path('payments/<int:payment_id>/mark-refunded/', admin_views.mark_refunded, name='mark_refunded'),
    path('payments/<int:payment_id>/quick-verify/', admin_views.quick_verify_payment, name='quick_verify_payment'),

    # Meet links
    path('meet-links/', admin_views.meet_links, name='meet_links'),
    path('meet-links/add/', admin_views.add_meet_link, name='add_meet_link'),
    path('meet-links/<int:link_id>/delete/', admin_views.delete_meet_link, name='delete_meet_link'),

    # Blog
    path('blog/', admin_views.blog_list, name='blog_list'),
    path('blog/<int:post_id>/', admin_views.blog_detail, name='blog_detail'),
    path('blog/<int:post_id>/approve/', admin_views.approve_blog, name='approve_blog'),
    path('blog/<int:post_id>/reject/', admin_views.reject_blog, name='reject_blog'),
    path('blog/new/', admin_views.create_blog, name='create_blog'),
    path('blog/<int:post_id>/delete/', admin_views.delete_blog, name='delete_blog'),

    # Reviews
    path('reviews/', admin_views.review_list, name='review_list'),
    path('reviews/<int:review_id>/toggle/', admin_views.toggle_review, name='toggle_review'),
    path('reviews/<int:review_id>/delete/', admin_views.delete_review, name='delete_review'),

    # Site settings
    path('settings/', admin_views.site_settings, name='site_settings'),

    # Analytics
    path('analytics/', admin_views.analytics, name='analytics'),

    # Admin management
    path('admins/', admin_views.admin_list, name='admin_list'),
    path('admins/add/', admin_views.add_admin, name='add_admin'),
    path('admins/<int:user_id>/remove/', admin_views.remove_admin, name='remove_admin'),

    # Vet availability admin overrides
    path('vets/<int:vet_id>/availability/add/', admin_views.admin_add_availability, name='admin_add_availability'),
    path('vets/<int:vet_id>/availability/<int:window_id>/delete/', admin_views.admin_delete_availability, name='admin_delete_availability'),
    path('vets/<int:vet_id>/blocked/<int:blocked_id>/delete/', admin_views.admin_delete_blocked, name='admin_delete_blocked'),

    # Coupons
    path('coupons/', admin_views.coupon_list, name='coupon_list'),
    path('coupons/create/', admin_views.coupon_create, name='coupon_create'),
    path('coupons/<int:coupon_id>/edit/', admin_views.coupon_edit, name='coupon_edit'),
    path('coupons/<int:coupon_id>/toggle/', admin_views.coupon_toggle, name='coupon_toggle'),
    path('coupons/<int:coupon_id>/delete/', admin_views.coupon_delete, name='coupon_delete'),
    path('coupons/<int:coupon_id>/usages/', admin_views.coupon_usages, name='coupon_usages'),

]