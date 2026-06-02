"""
Tests for the booking flow:
- Pet management (add, edit, delete)
- Booking form
- Payment submission
- Rate limiting on payments
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import date, time, timedelta

from accounts.models import User, VetProfile
from consultations.models import (
    Pet, Appointment, Payment,
    VetAvailability,
)
from core.models import SiteSettings


class PetManagementTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='tanvir@test.com',
            email='tanvir@test.com',
            password='pass123!',
            role=User.Role.USER,
        )
        self.client.force_login(self.user)

    def test_my_pets_page_loads(self):
        response = self.client.get(reverse('consultations:my_pets'))
        self.assertEqual(response.status_code, 200)

    def test_add_pet(self):
        response = self.client.post(reverse('consultations:add_pet'), {
            'name':       'Milo',
            'species':    'cat',
            'breed':      'Persian',
            'age_years':  3,
            'age_months': 0,
            'weight_kg':  4.2,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Pet.objects.filter(owner=self.user, name='Milo').exists()
        )

    def test_add_pet_requires_name(self):
        response = self.client.post(reverse('consultations:add_pet'), {
            'species': 'cat',
        })
        self.assertFalse(
            Pet.objects.filter(owner=self.user).exists()
        )

    def test_edit_pet(self):
        pet = Pet.objects.create(
            owner=self.user,
            name='Bella',
            species='dog',
        )
        response = self.client.post(
            reverse('consultations:edit_pet', args=[pet.id]),
            {
                'name':       'Bella Updated',
                'species':    'dog',
                'age_years':  2,
                'age_months': 0,
                'weight_kg':  10.0,
            }
        )
        self.assertEqual(response.status_code, 302)
        pet.refresh_from_db()
        self.assertEqual(pet.name, 'Bella Updated')

    def test_delete_pet(self):
        pet = Pet.objects.create(
            owner=self.user,
            name='Luna',
            species='cat',
        )
        response = self.client.post(
            reverse('consultations:delete_pet', args=[pet.id])
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Pet.objects.filter(id=pet.id).exists())

    def test_cannot_delete_pet_with_upcoming_appointment(self):
        pet = Pet.objects.create(
            owner=self.user,
            name='Max',
            species='dog',
        )
        vet_user = User.objects.create_user(
            username='vet@test.com',
            email='vet@test.com',
            password='pass123!',
            role=User.Role.VET,
        )
        vet = VetProfile.objects.create(
            user=vet_user,
            application_status='approved',
            is_active=True,
            consultation_fee=300,
        )
        Appointment.objects.create(
            pet=pet,
            vet=vet,
            user=self.user,
            date=date.today() + timedelta(days=1),
            start_time=time(18, 0),
            end_time=time(18, 15),
            status='confirmed',
            primary_complaint='general',
            complaint_description='Test',
        )
        response = self.client.post(
            reverse('consultations:delete_pet', args=[pet.id])
        )
        self.assertTrue(Pet.objects.filter(id=pet.id).exists())

    def test_cannot_edit_other_users_pet(self):
        other_user = User.objects.create_user(
            username='other@test.com',
            email='other@test.com',
            password='pass123!',
        )
        pet = Pet.objects.create(
            owner=other_user,
            name='Coco',
            species='cat',
        )
        response = self.client.post(
            reverse('consultations:edit_pet', args=[pet.id]),
            {'name': 'Hacked', 'species': 'cat'}
        )
        pet.refresh_from_db()
        self.assertEqual(pet.name, 'Coco')


class BookingFormTest(TestCase):

    def setUp(self):
        self.client = Client()

        # Create a user with a pet
        self.user = User.objects.create_user(
            username='user@test.com',
            email='user@test.com',
            password='pass123!',
            role=User.Role.USER,
        )
        self.pet = Pet.objects.create(
            owner=self.user,
            name='Milo',
            species='cat',
        )

        # Create an approved vet
        self.vet_user = User.objects.create_user(
            username='vet@test.com',
            email='vet@test.com',
            password='pass123!',
            role=User.Role.VET,
        )
        self.vet = VetProfile.objects.create(
            user=self.vet_user,
            application_status='approved',
            is_active=True,
            consultation_fee=300,
        )

        # Set availability — tomorrow
        self.tomorrow = date.today() + timedelta(days=1)
        VetAvailability.objects.create(
            vet=self.vet,
            is_recurring=True,
            day_of_week=self.tomorrow.weekday(),
            start_time=time(18, 0),
            end_time=time(21, 0),
            is_active=True,
        )

        # Create site settings
        # In BookingFormTest.setUp:
        from core.models import SiteSettings
        settings, _ = SiteSettings.objects.get_or_create(id=1)
        settings.booking_enabled       = True
        settings.booking_fee           = 50
        settings.slot_duration_minutes = 15
        settings.save()

        self.client.force_login(self.user)

    def test_booking_form_loads(self):
        url = (
            reverse('consultations:book_appointment', args=[self.vet.id])
            + f'?date={self.tomorrow}&start=18:00&end=18:15'
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_booking_redirects_unauthenticated(self):
        self.client.logout()
        url = (
            reverse('consultations:book_appointment', args=[self.vet.id])
            + f'?date={self.tomorrow}&start=18:00&end=18:15'
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/', response.url)

    def test_booking_disabled_redirects_home(self):
        settings = SiteSettings.get()
        settings.booking_enabled = False
        settings.save()

        url = (
            reverse('consultations:book_appointment', args=[self.vet.id])
            + f'?date={self.tomorrow}&start=18:00&end=18:15'
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_successful_booking_creates_appointment(self):
        url = (
            reverse('consultations:book_appointment', args=[self.vet.id])
            + f'?date={self.tomorrow}&start=18:00&end=18:15'
        )
        response = self.client.post(url, {
            'pet_id':                self.pet.id,
            'primary_complaint':     'general',
            'complaint_description': 'My cat seems unwell.',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Appointment.objects.filter(
                user=self.user,
                vet=self.vet,
                pet=self.pet,
                status='pending_payment',
            ).exists()
        )

    def test_booking_requires_description(self):
        url = (
            reverse('consultations:book_appointment', args=[self.vet.id])
            + f'?date={self.tomorrow}&start=18:00&end=18:15'
        )
        response = self.client.post(url, {
            'pet_id':            self.pet.id,
            'primary_complaint': 'general',
            # No description
        })
        self.assertFalse(
            Appointment.objects.filter(user=self.user).exists()
        )


class PaymentSubmissionTest(TestCase):

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = Client()

        self.user = User.objects.create_user(
            username='user@test.com',
            email='user@test.com',
            password='pass123!',
            role=User.Role.USER,
        )
        self.pet = Pet.objects.create(
            owner=self.user,
            name='Milo',
            species='cat',
        )
        vet_user = User.objects.create_user(
            username='vet@test.com',
            email='vet@test.com',
            password='pass123!',
            role=User.Role.VET,
        )
        self.vet = VetProfile.objects.create(
            user=vet_user,
            application_status='approved',
            is_active=True,
            consultation_fee=300,
        )
        self.appointment = Appointment.objects.create(
            pet=self.pet,
            vet=self.vet,
            user=self.user,
            date=date.today() + timedelta(days=1),
            start_time=time(18, 0),
            end_time=time(18, 15),
            status='pending_payment',
            primary_complaint='general',
            complaint_description='Test consultation.',
        )

        # In PaymentSubmissionTest.setUp:
        from core.models import SiteSettings
        settings, _ = SiteSettings.objects.get_or_create(id=1)
        settings.booking_enabled       = True
        settings.booking_fee           = 50
        settings.slot_duration_minutes = 15
        settings.save()

        self.client.force_login(self.user)
        self.payment_url = reverse(
            'consultations:submit_payment',
            args=[self.appointment.id]
        )
        
    def tearDown(self):
        from django.core.cache import cache
        cache.clear()

    def test_payment_page_loads(self):
        response = self.client.get(self.payment_url)
        self.assertEqual(response.status_code, 200)

    def test_successful_payment_submission(self):
        response = self.client.post(self.payment_url, {
            'bkash_number':   '01711000001',
            'transaction_id': 'AB12345678',
        })
        # Print debug info
        print(f"\nStatus: {response.status_code}")
        print(f"Redirect URL: {response.get('Location', 'none')}")
        if hasattr(response, 'context') and response.context:
            from django.contrib.messages import get_messages
            msgs = list(get_messages(response.wsgi_request))
            print(f"Messages: {[str(m) for m in msgs]}")
        print(f"Payments exist: {Payment.objects.filter(appointment=self.appointment).count()}")
        print(f"Payments all: {list(Payment.objects.values('transaction_id', 'status', 'payment_type'))}")

        self.assertTrue(
            Payment.objects.filter(
                appointment=self.appointment,
                transaction_id='AB12345678',
                status='pending',
            ).exists()
        )

    def test_invalid_bkash_number_rejected(self):
        response = self.client.post(self.payment_url, {
            'bkash_number':   '12345',  # Invalid
            'transaction_id': 'AB12345678',
        })
        self.assertFalse(
            Payment.objects.filter(appointment=self.appointment).exists()
        )

    def test_invalid_transaction_id_rejected(self):
        response = self.client.post(self.payment_url, {
            'bkash_number':   '01711000001',
            'transaction_id': 'xx',  # Too short
        })
        self.assertFalse(
            Payment.objects.filter(appointment=self.appointment).exists()
        )

    def test_duplicate_transaction_id_rejected(self):
        # Submit the same TrxID twice
        self.client.post(self.payment_url, {
            'bkash_number':   '01711000001',
            'transaction_id': 'AB12345678',
        })
        # Second appointment for the second submission
        appt2 = Appointment.objects.create(
            pet=self.pet,
            vet=self.vet,
            user=self.user,
            date=date.today() + timedelta(days=2),
            start_time=time(18, 0),
            end_time=time(18, 15),
            status='pending_payment',
            primary_complaint='general',
            complaint_description='Second test.',
        )
        response = self.client.post(
            reverse('consultations:submit_payment', args=[appt2.id]),
            {
                'bkash_number':   '01711000001',
                'transaction_id': 'AB12345678',  # Same TrxID
            }
        )
        self.assertEqual(
            Payment.objects.filter(transaction_id='AB12345678').count(),
            1  # Only one payment should exist
        )

    def test_rate_limiting_blocks_after_5_attempts(self):
        for i in range(5):
            self.client.post(self.payment_url, {
                'bkash_number':   'invalid',
                'transaction_id': 'bad',
            })
        # 6th attempt should be blocked
        response = self.client.post(self.payment_url, {
            'bkash_number':   '01711000001',
            'transaction_id': 'AB99999999',
        })
        # Should not create a payment even with valid data
        self.assertFalse(
            Payment.objects.filter(transaction_id='AB99999999').exists()
        )