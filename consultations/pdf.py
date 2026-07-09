"""
PDF Prescription Generator
==========================
Uses ReportLab to generate a professional prescription PDF.
Called after vet submits prescription and second payment is verified.
"""

from io import BytesIO
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import (
    HexColor, black, white
)
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT


# ── Brand colours ─────────────────────────────────────────────────────────────
PRIMARY       = HexColor('#2D6A4F')
PRIMARY_LIGHT = HexColor('#B7E4C7')
SECONDARY     = HexColor('#C75E3A')
GRAY          = HexColor('#4A4741')
LIGHT_GRAY    = HexColor('#F4F0E8')
DARK          = HexColor('#1C1B19')


def generate_prescription_pdf(appointment) -> bytes:
    """
    Generates a prescription PDF for the given appointment.
    Returns the PDF as bytes.
    """
    buffer = BytesIO()
    prescription = appointment.prescription

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm,
    )

    # ── Styles ─────────────────────────────────────────────────────────────────
    styles = getSampleStyleSheet()

    brand_title = ParagraphStyle(
        'BrandTitle',
        fontName='Helvetica-Bold',
        fontSize=22,
        textColor=PRIMARY,
        spaceAfter=0,
        spaceBefore=0,
        leading=26,
    )
    brand_sub = ParagraphStyle(
        'BrandSub',
        fontName='Helvetica',
        fontSize=9,
        textColor=GRAY,
        spaceAfter=0,
        spaceBefore=0,
        leading=12,
    )
    section_heading = ParagraphStyle(
        'SectionHeading',
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=PRIMARY,
        spaceBefore=10,
        spaceAfter=4,
        borderPad=0,
    )
    body_text = ParagraphStyle(
        'BodyText',
        fontName='Helvetica',
        fontSize=10,
        textColor=DARK,
        spaceAfter=4,
        leading=14,
    )
    body_bold = ParagraphStyle(
        'BodyBold',
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=DARK,
        spaceAfter=2,
    )
    small_gray = ParagraphStyle(
        'SmallGray',
        fontName='Helvetica',
        fontSize=8,
        textColor=GRAY,
        spaceAfter=2,
    )
    disclaimer = ParagraphStyle(
        'Disclaimer',
        fontName='Helvetica-Oblique',
        fontSize=8,
        textColor=GRAY,
        leading=11,
        alignment=TA_CENTER,
    )

    # ── Build content ──────────────────────────────────────────────────────────
    story = []
    vet   = appointment.vet
    pet   = appointment.pet
    owner = appointment.user

    # Parse medication and dosage lines
    med_lines  = [m.strip() for m in prescription.medications.splitlines() if m.strip()]
    dose_lines = [d.strip() for d in prescription.dosage_instructions.splitlines() if d.strip()]

    # Pad shorter list so zip works cleanly
    max_len    = max(len(med_lines), len(dose_lines))
    med_lines  += [''] * (max_len - len(med_lines))
    dose_lines += [''] * (max_len - len(dose_lines))
    med_pairs  = list(zip(med_lines, dose_lines))

    # ── Header ─────────────────────────────────────────────────────────────────
    header_data = [[
        Paragraph('Amarvet', brand_title),
        Paragraph(
            f"Date: <b>{appointment.date.strftime('%B %d, %Y')}</b>",
            ParagraphStyle(
                'Right', fontName='Helvetica', fontSize=10,
                textColor=GRAY, alignment=TA_RIGHT
            )
        ),
    ]]
    header_table = Table(header_data, colWidths=[120*mm, 50*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',  (1, 0), (1, 0),  'RIGHT'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        'Online Veterinary Consultation Service · Bangladesh',
        brand_sub
    ))
    story.append(Spacer(1, 6*mm))
    story.append(HRFlowable(
        width='100%', thickness=2, color=PRIMARY, spaceAfter=6
    ))

    # ── Vet info ───────────────────────────────────────────────────────────────
    vet_name = f"Dr. {vet.user.get_full_name()}"
    vet_data = [[
        Paragraph(vet_name, body_bold),
        Paragraph(
            f"BVC Reg. No: {vet.bvc_registration_number or '—'}",
            small_gray
        ),
    ]]
    if vet.specializations:
        vet_data.append([
            Paragraph(vet.specializations, small_gray),
            Paragraph(
                f"Experience: {vet.years_of_experience} years",
                small_gray
            ),
        ])
    vet_table = Table(vet_data, colWidths=[90*mm, 80*mm])
    vet_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN',  (1, 0), (1, -1), 'RIGHT'),
    ]))
    story.append(vet_table)
    story.append(Spacer(1, 3*mm))
    story.append(HRFlowable(
        width='100%', thickness=0.5, color=HexColor('#CCC8BF'), spaceAfter=6
    ))

    # ── Patient info ───────────────────────────────────────────────────────────
    story.append(Paragraph('PATIENT', section_heading))

    patient_data = [
        ['Pet Name', pet.name, 'Owner', owner.get_full_name() or owner.username],
        [
            'Species',
            pet.get_species_display(),
            'Phone',
            owner.phone_number or '—',
        ],
        [
            'Breed',
            pet.breed or '—',
            'Consultation',
            f"{appointment.start_time.strftime('%I:%M %p')} – "
            f"{appointment.end_time.strftime('%I:%M %p')}",
        ],
        [
            'Age',
            f"{pet.age_years}yr {pet.age_months}mo".strip(),
            'Weight',
            f"{pet.weight_kg}kg" if pet.weight_kg else '—',
        ],
    ]

    pt_table = Table(
        patient_data,
        colWidths=[22*mm, 53*mm, 22*mm, 53*mm]
    )
    pt_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), LIGHT_GRAY),
        ('BACKGROUND', (2, 0), (2, -1), LIGHT_GRAY),
        ('FONTNAME',   (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME',   (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE',   (0, 0), (-1, -1), 9),
        ('TEXTCOLOR',  (0, 0), (-1, -1), DARK),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [white, LIGHT_GRAY]),
        ('GRID',       (0, 0), (-1, -1), 0.3, HexColor('#CCC8BF')),
        ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING',   (0, 0), (-1, -1), 5),
    ]))
    story.append(pt_table)
    story.append(Spacer(1, 3*mm))

    # ── Complaint ──────────────────────────────────────────────────────────────
    story.append(HRFlowable(
        width='100%', thickness=0.5, color=HexColor('#CCC8BF'), spaceAfter=4
    ))
    story.append(Paragraph('COMPLAINT', section_heading))
    story.append(Paragraph(
        f"<b>{appointment.get_primary_complaint_display()}</b>",
        body_text
    ))
    story.append(Paragraph(appointment.complaint_description, body_text))

    if appointment.diagnosis:
        story.append(Paragraph(
            f"<b>Diagnosis:</b> {appointment.diagnosis}", body_text
        ))

    story.append(Spacer(1, 3*mm))

    # ── Prescription ───────────────────────────────────────────────────────────
    story.append(HRFlowable(
        width='100%', thickness=0.5, color=HexColor('#CCC8BF'), spaceAfter=4
    ))
    story.append(Paragraph('PRESCRIPTION', section_heading))

    rx_data = [['#', 'Medication', 'Dosage & Instructions']]
    for i, (med, dose) in enumerate(med_pairs, 1):
        rx_data.append([
            str(i),
            Paragraph(med, body_bold),
            Paragraph(dose, body_text),
        ])

    rx_table = Table(rx_data, colWidths=[8*mm, 60*mm, 102*mm])
    rx_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND',    (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR',     (0, 0), (-1, 0), white),
        ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, 0), 9),
        ('ALIGN',         (0, 0), (-1, 0), 'CENTER'),
        # Data rows
        ('FONTSIZE',      (0, 1), (-1, -1), 9),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [white, LIGHT_GRAY]),
        ('GRID',          (0, 0), (-1, -1), 0.3, HexColor('#CCC8BF')),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 5),
        ('ALIGN',         (0, 0), (0, -1), 'CENTER'),
    ]))
    story.append(rx_table)
    story.append(Spacer(1, 4*mm))

    # ── Follow-up ──────────────────────────────────────────────────────────────
    if prescription.follow_up_advice:
        story.append(HRFlowable(
            width='100%', thickness=0.5,
            color=HexColor('#CCC8BF'), spaceAfter=4
        ))
        story.append(Paragraph('FOLLOW-UP ADVICE', section_heading))
        story.append(Paragraph(prescription.follow_up_advice, body_text))
        story.append(Spacer(1, 3*mm))

    # ── Additional notes ───────────────────────────────────────────────────────
    if prescription.additional_notes:
        story.append(Paragraph('ADDITIONAL NOTES', section_heading))
        story.append(Paragraph(prescription.additional_notes, body_text))
        story.append(Spacer(1, 3*mm))

    # ── Vet signature area ─────────────────────────────────────────────────────
    story.append(Spacer(1, 10*mm))
    story.append(HRFlowable(
        width='100%', thickness=0.5,
        color=HexColor('#CCC8BF'), spaceAfter=4
    ))

    sig_data = [[
        Paragraph(
            f"<b>{vet_name}</b><br/>"
            f"{vet.specializations or ''}<br/>"
            f"BVC Reg. No: {vet.bvc_registration_number or '—'}",
            ParagraphStyle(
                'SigLeft', fontName='Helvetica', fontSize=9,
                textColor=DARK, leading=13
            )
        ),
        Paragraph(
            f"<b>Amarvet</b><br/>"
            f"Online Veterinary Consultation<br/>"
            f"Bangladesh",
            ParagraphStyle(
                'SigRight', fontName='Helvetica', fontSize=9,
                textColor=GRAY, leading=13, alignment=TA_RIGHT
            )
        ),
    ]]
    sig_table = Table(sig_data, colWidths=[85*mm, 85*mm])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN',  (1, 0), (1, 0), 'RIGHT'),
    ]))
    story.append(sig_table)

    # ── Footer disclaimer ──────────────────────────────────────────────────────
    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(
        width='100%', thickness=1, color=PRIMARY, spaceAfter=4
    ))
    story.append(Paragraph(
        'This prescription was issued following an online veterinary consultation via Amarvet. '
        'It is valid for use at any registered veterinary pharmacy in Bangladesh. '
        'For emergencies or if symptoms worsen, please visit a physical veterinary clinic immediately. '
        'Amarvet does not replace in-person veterinary care.',
        disclaimer
    ))

    # ── Build PDF ──────────────────────────────────────────────────────────────
    doc.build(story)
    return buffer.getvalue()