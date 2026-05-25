"""
Creates realistic demo data for VetProject.
Run: python manage.py create_demo_data

Creates:
- 1 admin user
- 4 vets with profiles, availability
- 6 pet owners with pets
- 10 past completed consultations with prescriptions and reviews
- 3 published blog posts
- Site settings with bKash number
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify
from datetime import date, time, timedelta
import random


class Command(BaseCommand):
    help = 'Creates demo data for presentation purposes'

    def handle(self, *args, **options):
        self.stdout.write('Creating demo data...')

        from accounts.models import User, VetProfile
        from consultations.models import (
            Pet, VetAvailability, Appointment,
            Payment, Prescription
        )
        from blog.models import BlogPost, Review
        from core.models import SiteSettings, MeetLink

        # ── Site settings ──────────────────────────────────────────────────────
        settings = SiteSettings.get()
        settings.booking_enabled        = True
        settings.booking_fee            = 50
        settings.cancellation_deduction = 10
        settings.slot_duration_minutes  = 15
        settings.bkash_merchant_number  = '01712345678'
        settings.save()
        self.stdout.write('  ✓ Site settings')

        # ── Meet links ─────────────────────────────────────────────────────────
        meet_urls = [
            'https://meet.google.com/abc-defg-hij',
            'https://meet.google.com/klm-nopq-rst',
            'https://meet.google.com/uvw-xyza-bcd',
            'https://meet.google.com/efg-hijk-lmn',
        ]
        meet_links = []
        for i, url in enumerate(meet_urls):
            link, _ = MeetLink.objects.get_or_create(
                url=url,
                defaults={'notes': f'Link {i+1}', 'is_in_use': False}
            )
            meet_links.append(link)
        self.stdout.write('  ✓ Meet links')

        # ── Admin ──────────────────────────────────────────────────────────────
        admin, _ = User.objects.get_or_create(
            username='admin@vetproject.com',
            defaults={
                'email':      'admin@vetproject.com',
                'first_name': 'Admin',
                'last_name':  'User',
                'role':       User.Role.ADMIN,
                'is_staff':   True,
            }
        )
        admin.set_password('admin1234')
        admin.save()
        self.stdout.write('  ✓ Admin user (admin@vetproject.com / admin1234)')

        # ── Vets ───────────────────────────────────────────────────────────────
        vet_data = [
            {
                'first_name': 'Ayesha',
                'last_name':  'Rahman',
                'email':      'ayesha@vetproject.com',
                'phone':      '01711223344',
                'bio':        'Dr. Ayesha Rahman is a certified veterinarian with over 8 years of experience treating cats and dogs in Dhaka. She specialises in feline internal medicine and dog dermatology.',
                'education':  'DVM, Bangladesh Agricultural University, 2015\nMSc Veterinary Medicine, BAU, 2017',
                'bvc':        'BVC-2015-4821',
                'experience': 8,
                'specs':      'Cats, Dogs, Dermatology, Internal Medicine',
                'fee':        300,
            },
            {
                'first_name': 'Rafiq',
                'last_name':  'Hassan',
                'email':      'rafiq@vetproject.com',
                'phone':      '01822334455',
                'bio':        'Dr. Rafiq Hassan has dedicated his career to small animal care. With a focus on preventive medicine and nutrition, he has helped hundreds of pet owners across Bangladesh keep their animals healthy.',
                'education':  'DVM, Sher-e-Bangla Agricultural University, 2013',
                'bvc':        'BVC-2013-3102',
                'experience': 11,
                'specs':      'Dogs, Nutrition, Preventive Medicine',
                'fee':        250,
            },
            {
                'first_name': 'Nusrat',
                'last_name':  'Jahan',
                'email':      'nusrat@vetproject.com',
                'phone':      '01933445566',
                'bio':        'Dr. Nusrat Jahan is a passionate advocate for animal welfare. She completed her postgraduate training in veterinary surgery and has a special interest in feline behaviour and wellness.',
                'education':  'DVM, Chittagong Veterinary and Animal Sciences University, 2018',
                'bvc':        'BVC-2018-5934',
                'experience': 6,
                'specs':      'Cats, Behaviour, Surgery Consultation',
                'fee':        280,
            },
            {
                'first_name': 'Imran',
                'last_name':  'Chowdhury',
                'email':      'imran@vetproject.com',
                'phone':      '01644556677',
                'bio':        'Dr. Imran Chowdhury brings a wealth of clinical experience from both private practice and university teaching. He is particularly skilled at diagnosing complex cases in dogs.',
                'education':  'DVM, Bangladesh Agricultural University, 2011\nPhD Veterinary Pathology, BAU, 2016',
                'bvc':        'BVC-2011-2241',
                'experience': 14,
                'specs':      'Dogs, Pathology, Complex Diagnostics',
                'fee':        350,
            },
        ]

        vets = []
        for vd in vet_data:
            user, _ = User.objects.get_or_create(
                username=vd['email'],
                defaults={
                    'email':        vd['email'],
                    'first_name':   vd['first_name'],
                    'last_name':    vd['last_name'],
                    'phone_number': vd['phone'],
                    'role':         User.Role.VET,
                }
            )
            user.set_password('vet1234')
            user.save()

            profile, _ = VetProfile.objects.get_or_create(
                user=user,
                defaults={
                    'bio':                    vd['bio'],
                    'education':              vd['education'],
                    'bvc_registration_number': vd['bvc'],
                    'years_of_experience':    vd['experience'],
                    'specializations':        vd['specs'],
                    'consultation_fee':       vd['fee'],
                    'application_status':     VetProfile.ApplicationStatus.APPROVED,
                    'is_active':              True,
                }
            )
            vets.append(profile)

            # Add recurring availability — weekdays 6pm-9pm and weekends 10am-1pm
            for day in [0, 1, 2, 3, 4]:  # Mon-Fri
                VetAvailability.objects.get_or_create(
                    vet=profile,
                    is_recurring=True,
                    day_of_week=day,
                    start_time=time(18, 0),
                    end_time=time(21, 0),
                    defaults={'is_active': True}
                )
            for day in [5, 6]:  # Sat-Sun
                VetAvailability.objects.get_or_create(
                    vet=profile,
                    is_recurring=True,
                    day_of_week=day,
                    start_time=time(10, 0),
                    end_time=time(13, 0),
                    defaults={'is_active': True}
                )

        self.stdout.write(f'  ✓ {len(vets)} vets with availability')

        # ── Pet owners ─────────────────────────────────────────────────────────
        owner_data = [
            {'first': 'Tanvir', 'last': 'Ahmed',    'email': 'tanvir@demo.com',   'phone': '01711000001'},
            {'first': 'Sabrina','last': 'Islam',     'email': 'sabrina@demo.com',  'phone': '01811000002'},
            {'first': 'Farhan', 'last': 'Hossain',   'email': 'farhan@demo.com',   'phone': '01911000003'},
            {'first': 'Mitu',   'last': 'Begum',     'email': 'mitu@demo.com',     'phone': '01611000004'},
            {'first': 'Shakib', 'last': 'Khan',      'email': 'shakib@demo.com',   'phone': '01511000005'},
            {'first': 'Rima',   'last': 'Chowdhury', 'email': 'rima@demo.com',     'phone': '01411000006'},
        ]

        pet_data = [
            {'name': 'Milo',   'species': 'cat', 'breed': 'Persian',         'age_years': 3, 'weight': 4.2},
            {'name': 'Bella',  'species': 'dog', 'breed': 'Labrador',        'age_years': 5, 'weight': 28.0},
            {'name': 'Luna',   'species': 'cat', 'breed': 'Siamese',         'age_years': 2, 'weight': 3.5},
            {'name': 'Bruno',  'species': 'dog', 'breed': 'German Shepherd', 'age_years': 4, 'weight': 32.0},
            {'name': 'Coco',   'species': 'cat', 'breed': 'Mixed',           'age_years': 1, 'weight': 2.8},
            {'name': 'Max',    'species': 'dog', 'breed': 'Golden Retriever','age_years': 6, 'weight': 30.0},
        ]

        owners = []
        pets   = []
        for i, od in enumerate(owner_data):
            owner, _ = User.objects.get_or_create(
                username=od['email'],
                defaults={
                    'email':        od['email'],
                    'first_name':   od['first'],
                    'last_name':    od['last'],
                    'phone_number': od['phone'],
                    'role':         User.Role.USER,
                }
            )
            owner.set_password('user1234')
            owner.save()
            owners.append(owner)

            pd = pet_data[i]
            pet, _ = Pet.objects.get_or_create(
                owner=owner,
                name=pd['name'],
                defaults={
                    'species':    pd['species'],
                    'breed':      pd['breed'],
                    'age_years':  pd['age_years'],
                    'weight_kg':  pd['weight'],
                    'medical_history_notes': f"{pd['name']} has been healthy overall. Vaccinations up to date.",
                }
            )
            pets.append(pet)

        self.stdout.write(f'  ✓ {len(owners)} pet owners with pets')

        # ── Past completed consultations ───────────────────────────────────────
        complaints = [
            Appointment.PrimaryComplaint.DIGESTIVE,
            Appointment.PrimaryComplaint.SKIN,
            Appointment.PrimaryComplaint.EATING,
            Appointment.PrimaryComplaint.VACCINATION,
            Appointment.PrimaryComplaint.GENERAL,
            Appointment.PrimaryComplaint.BEHAVIOURAL,
        ]
        descriptions = [
            "My cat has been vomiting after meals for the past two days. She seems lethargic and is drinking more water than usual.",
            "There are small bald patches appearing on my dog's back. The skin looks red and he keeps scratching the area.",
            "My pet hasn't eaten properly in 3 days. He sniffs the food but walks away without eating.",
            "Due for annual vaccinations. Wanted to confirm the schedule and discuss any side effects.",
            "General health checkup. He seems fine but I wanted a professional opinion before his birthday next week.",
            "My cat has started hiding under the bed and hissing at family members. Very unlike her usual behaviour.",
        ]
        diagnoses = [
            "Mild gastroenteritis likely caused by dietary change. No serious underlying condition detected.",
            "Early stage hot spots, likely triggered by seasonal allergies. Manageable with medication.",
            "Stress-related appetite loss. No medical condition found. Environmental enrichment recommended.",
            "All vaccinations confirmed up to date. Next booster due in 12 months.",
            "Excellent health overall. Weight appropriate. Dental hygiene good.",
            "Territorial anxiety likely triggered by new household member. Behaviour therapy recommended.",
        ]
        medications = [
            ["Metronidazole 250mg", "Probiotic Supplement"],
            ["Hydrocortisone Cream 1%", "Cetirizine 5mg"],
            ["Appetite Stimulant Mirtazapine 1.88mg", "Vitamin B Complex"],
            ["Rabies Vaccine (administered)", "DHPP Booster (administered)"],
            ["No medication required", "Dental chews recommended"],
            ["Feliway Diffuser (pheromone)", "Buspirone 5mg"],
        ]
        dosages = [
            ["1 tablet twice daily for 7 days with food", "1 sachet mixed in food daily for 2 weeks"],
            ["Apply thin layer to affected area twice daily for 5 days", "Half tablet once daily for 10 days"],
            ["0.5ml oral once at night for 4 days", "1 tablet daily with food for 30 days"],
            ["Administered during consultation", "Administered during consultation"],
            ["N/A", "1-2 chews daily"],
            ["Plug in near sleeping area, replace monthly", "1.25mg twice daily for 30 days, review after"],
        ]
        follow_ups = [
            "Return if vomiting persists beyond 5 days or blood appears in stool.",
            "Return in 2 weeks if patches spread. Keep area clean and dry.",
            "Introduce new food variety gradually. Follow-up in 1 week if no improvement.",
            "Next vaccination due in 12 months. Keep vaccination record safe.",
            "Schedule dental cleaning if home care is inconsistent.",
            "Introduce new household member gradually using scent exchange technique first.",
        ]

        today = timezone.localdate()
        created_count = 0

        for i in range(10):
            owner      = owners[i % len(owners)]
            pet        = pets[i % len(pets)]
            vet        = vets[i % len(vets)]
            days_ago   = random.randint(5, 60)
            appt_date  = today - timedelta(days=days_ago)
            start_hour = random.choice([18, 19, 20])
            start      = time(start_hour, 0)
            end        = time(start_hour, 15)
            complaint  = complaints[i % len(complaints)]
            desc       = descriptions[i % len(descriptions)]
            diagnosis  = diagnoses[i % len(diagnoses)]

            appt, created = Appointment.objects.get_or_create(
                pet=pet,
                vet=vet,
                date=appt_date,
                start_time=start,
                defaults={
                    'user':                 owner,
                    'end_time':             end,
                    'status':               Appointment.Status.COMPLETED,
                    'primary_complaint':    complaint,
                    'complaint_description': desc,
                    'diagnosis':            diagnosis,
                    'consultation_notes':   f"Thorough examination conducted via video call. {diagnosis}",
                    'consultation_start_time': timezone.make_aware(
                        timezone.datetime.combine(appt_date, start)
                    ),
                    'consultation_end_time': timezone.make_aware(
                        timezone.datetime.combine(appt_date, end)
                    ),
                    'reminder_sent': True,
                }
            )

            if created:
                # Booking payment
                Payment.objects.create(
                    appointment=appt,
                    payment_type=Payment.PaymentType.BOOKING,
                    amount=50,
                    bkash_number=owner.phone_number,
                    transaction_id=f"DEMO{i:04d}A",
                    status=Payment.Status.VERIFIED,
                    verified_by=admin,
                    verified_at=timezone.now(),
                )
                # Consultation payment
                Payment.objects.create(
                    appointment=appt,
                    payment_type=Payment.PaymentType.CONSULTATION,
                    amount=vet.consultation_fee,
                    bkash_number=owner.phone_number,
                    transaction_id=f"DEMO{i:04d}B",
                    status=Payment.Status.VERIFIED,
                    verified_by=admin,
                    verified_at=timezone.now(),
                )
                # Prescription
                med_idx = i % len(medications)
                Prescription.objects.create(
                    appointment=appt,
                    medications='\n'.join(medications[med_idx]),
                    dosage_instructions='\n'.join(dosages[med_idx]),
                    follow_up_advice=follow_ups[med_idx],
                )
                # Review
                rating = random.choice([4, 4, 5, 5, 5])
                review_comments = [
                    "Very knowledgeable and patient. Milo is doing much better now!",
                    "Excellent consultation. The doctor explained everything clearly.",
                    "So convenient! Saved us a trip to the clinic and Bella got great care.",
                    "Dr. was very thorough. Highly recommend VetProject.",
                    "Fast and professional. Will definitely use again.",
                    "Great experience. The doctor really listened to my concerns.",
                ]
                Review.objects.create(
                    appointment=appt,
                    reviewer=owner,
                    vet=vet,
                    rating=rating,
                    comment=review_comments[i % len(review_comments)],
                    is_visible=True,
                )
                appt.feedback_rating     = rating
                appt.feedback_comment    = review_comments[i % len(review_comments)]
                appt.feedback_submitted_at = timezone.now()
                appt.save()
                created_count += 1

        self.stdout.write(f'  ✓ {created_count} completed consultations with prescriptions and reviews')

        # ── Blog posts ─────────────────────────────────────────────────────────
        blog_data = [
            {
                'title':   'How to Tell If Your Cat Is Sick: 10 Warning Signs',
                'author':  vets[0],
                'content': """Cats are experts at hiding illness — it's an instinct inherited from their wild ancestors who needed to appear strong to survive. This means by the time you notice something is wrong, your cat may have been unwell for some time.

Here are 10 warning signs every cat owner should know:

1. Changes in eating or drinking habits
A sudden decrease or increase in food or water intake can signal anything from dental pain to kidney disease. Monitor your cat's bowl daily.

2. Lethargy and reduced activity
If your normally playful cat is sleeping more than usual and showing no interest in activities they previously enjoyed, it deserves attention.

3. Changes in litter box behaviour
Straining to urinate, blood in urine, or avoiding the litter box are serious signs — particularly in male cats, urinary blockages can be life-threatening.

4. Vomiting or diarrhoea
Occasional vomiting can be normal, but frequent episodes, especially with blood, warrant immediate attention.

5. Sudden weight loss or gain
Weight changes that aren't explained by diet changes should always be investigated.

6. Discharge from eyes or nose
Clear discharge may indicate allergies, while coloured discharge often signals infection.

7. Changes in coat condition
A healthy cat has a shiny, well-groomed coat. Dullness, excessive shedding, or matting can indicate nutritional deficiency or illness.

8. Hiding behaviour
Cats instinctively hide when they feel vulnerable. If your cat is suddenly spending a lot of time hidden away, take note.

9. Changes in vocalisation
Both increased meowing and unusual silence can be signs of distress or pain.

10. Difficulty breathing
Any laboured breathing, wheezing, or open-mouth breathing is an emergency.

If you notice any of these signs, don't wait. An online consultation can help you assess whether your cat needs urgent in-person care or whether the situation can be managed at home.""",
            },
            {
                'title':   'The Complete Guide to Vaccinating Your Dog in Bangladesh',
                'author':  vets[1],
                'content': """Vaccination is one of the most important things you can do to protect your dog's health. Yet many dog owners in Bangladesh are unsure about what vaccines are needed, when to give them, and where to find reliable veterinary care.

This guide answers all your questions.

Why vaccination matters
Vaccines protect your dog from serious and potentially fatal diseases including rabies, distemper, parvovirus, and leptospirosis. Some of these diseases can also be transmitted to humans, making vaccination a public health issue as well.

The core vaccines for dogs in Bangladesh

Rabies: Required by law and critically important given the prevalence of rabies in Bangladesh. First dose at 12 weeks, booster annually.

DHPP (Distemper, Hepatitis, Parvovirus, Parainfluenza): This combination vaccine protects against four serious diseases. First dose at 6-8 weeks, boosters every 3-4 weeks until 16 weeks old, then annually.

Leptospirosis: Common in Bangladesh due to flooding and contact with contaminated water. Two doses 2-4 weeks apart, then annually.

The vaccination schedule
Week 6-8: First DHPP
Week 10-12: Second DHPP, First Leptospirosis
Week 14-16: Third DHPP, Second Leptospirosis, Rabies
12 months: Annual boosters for all vaccines

What to expect after vaccination
Mild lethargy and reduced appetite for 24-48 hours is normal. More serious reactions are rare but include facial swelling, difficulty breathing, or collapse — seek immediate care if these occur.

Keeping records
Always maintain a vaccination booklet for your dog. This is required for travel, boarding, and in case of a bite incident.

If you're unsure about your dog's vaccination status or schedule, an online consultation with one of our vets can help you create a personalised plan.""",
            },
            {
                'title':   'Understanding Your Cat\'s Behaviour: What They\'re Trying to Tell You',
                'author':  vets[2],
                'content': """Cats communicate constantly — through vocalisations, body language, and behaviour. Learning to read these signals strengthens your bond with your cat and helps you identify when something is wrong.

The tail tells the story
A high, upright tail signals confidence and happiness. A puffed tail means fear or aggression. A tail tucked between the legs indicates anxiety. A slowly swishing tail often means your cat is focused or mildly annoyed — not content like a dog.

What different meows mean
Cats rarely meow at other cats — it's a language developed specifically for communicating with humans. Short, chirpy meows are greetings. Long, drawn-out meows are demands. Low, rumbling meows indicate dissatisfaction. Repeated meowing can signal pain or distress.

Kneading — the comfort behaviour
When cats push their paws in and out against a soft surface, they're expressing contentment. It's a behaviour from kittenhood associated with nursing. Consider it a compliment.

Slow blinking
If your cat looks at you and slowly blinks, they're showing trust and affection. You can slow-blink back — it's the closest thing to a cat kiss.

Bringing you gifts
Cats that bring you dead animals are not being morbid — they're sharing food with a member of their social group. It's an honour, even if an unwelcome one.

Hiding and avoiding
While cats naturally value alone time, excessive hiding is a warning sign. Cats in pain or distress often isolate themselves. If your cat's hiding habits change suddenly, it warrants attention.

Scratching
Scratching is normal and necessary — it maintains claw health and marks territory. Provide appropriate scratching posts and your furniture will thank you.

Understanding your cat's normal behaviour patterns makes it much easier to notice when something is off. If you've observed behavioural changes in your cat that concern you, our vets are available for online consultations any day of the week.""",
            },
        ]

        for bd in blog_data:
            slug = slugify(bd['title'])
            if not BlogPost.objects.filter(slug=slug).exists():
                BlogPost.objects.create(
                    title=bd['title'],
                    slug=slug,
                    content=bd['content'],
                    author=bd['author'].user,
                    status=BlogPost.Status.PUBLISHED,
                    published_at=timezone.now() - timedelta(
                        days=random.randint(1, 30)
                    ),
                    view_count=random.randint(15, 120),
                )

        self.stdout.write(f'  ✓ {len(blog_data)} blog posts')

        # ── Summary ────────────────────────────────────────────────────────────
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Demo data created successfully!'))
        self.stdout.write('')
        self.stdout.write('Login credentials:')
        self.stdout.write('  Admin:    admin@vetproject.com / admin1234')
        self.stdout.write('  Vets:     ayesha@vetproject.com / vet1234')
        self.stdout.write('            rafiq@vetproject.com / vet1234')
        self.stdout.write('            nusrat@vetproject.com / vet1234')
        self.stdout.write('            imran@vetproject.com / vet1234')
        self.stdout.write('  Users:    tanvir@demo.com / user1234')
        self.stdout.write('            sabrina@demo.com / user1234')
        self.stdout.write('            (and 4 more with password user1234)')
        self.stdout.write('')
        self.stdout.write('Note: No profile photos are added.')
        self.stdout.write('Upload photos manually via each profile for best presentation.')