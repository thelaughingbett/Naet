import io
from pyhanko_certvalidator import ValidationContext
from pyhanko.sign.fields import SigFieldSpec
from pyhanko.sign import signers, fields
from django.http import HttpResponse
from django.template.loader import render_to_string
from playwright.sync_api import sync_playwright
import tempfile
import os


def html_to_pdf_bytes(html_string: str) -> bytes:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html_string, wait_until="networkidle")
        pdf_bytes = page.pdf(format="A4", print_background=True)
        browser.close()
        return pdf_bytes


def transcript_pdf(request, student_id):
    student = Student.objects.get(id=student_id)

    html_string = render_to_string("transcripts/transcript_pdf.html", {
        "student": student,
        "courses": student.courses.all(),
    })

    pdf_bytes = html_to_pdf_bytes(html_string)

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="transcript_{student.id}.pdf"'
    return response


def sign_transcript(pdf_bytes: bytes, student_id: str) -> bytes:
    signer = signers.SimpleSigner.load(
        key_file="certs/institution_private_key.pem",
        cert_file="certs/institution_cert.pem",
        ca_chain_files=("certs/intermediate_ca.pem",),
        key_passphrase=settings.SIGNING_KEY_PASSPHRASE.encode(),
    )

    input_buf = io.BytesIO(pdf_bytes)
    output_buf = io.BytesIO()

    signers.sign_pdf(
        input_buf,
        signers.PdfSignatureMetadata(
            field_name="TranscriptSignature",
            reason=f"Official transcript verification - Student {student_id}",
            location="Registrar's Office",
        ),
        signer=signer,
        output=output_buf,
    )

    return output_buf.getvalue()
