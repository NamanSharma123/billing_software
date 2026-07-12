import os

from paths import resource_path

try:
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                    Paragraph, Spacer, KeepTogether, Image,
                                    HRFlowable)
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False

LOGO_PATH = resource_path("assets", "logo.jpeg")
WATERMARK_PATH = resource_path("assets", "watermark.png")


# ══════════════════════════════════════════════════════════════
# Number → Indian-currency words  (e.g. 40000 -> "Forty Thousand Rupees Only")
# ══════════════════════════════════════════════════════════════
_ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
         "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
         "Seventeen", "Eighteen", "Nineteen"]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _two_digits(n):
    if n < 20:
        return _ONES[n]
    return _TENS[n // 10] + (f" {_ONES[n % 10]}" if n % 10 else "")


def _three_digits(n):
    if n >= 100:
        rest = _two_digits(n % 100)
        return f"{_ONES[n // 100]} Hundred" + (f" {rest}" if rest else "")
    return _two_digits(n)


def amount_to_words(amount):
    n = int(round(amount or 0))
    if n == 0:
        return "Zero Rupees Only"
    crore, n = divmod(n, 10 ** 7)
    lakh, n = divmod(n, 10 ** 5)
    thousand, n = divmod(n, 1000)
    hundred = n
    parts = []
    if crore:
        parts.append(f"{_three_digits(crore)} Crore")
    if lakh:
        parts.append(f"{_three_digits(lakh)} Lakh")
    if thousand:
        parts.append(f"{_three_digits(thousand)} Thousand")
    if hundred:
        parts.append(_three_digits(hundred))
    return " ".join(parts) + " Rupees Only"


# ══════════════════════════════════════════════════════════════
# PDF BUILDER — matches "DEVENDAR CodingNow_Fee_Receipt.pdf" reference
# ══════════════════════════════════════════════════════════════
def build_fee_receipt(data, path):
    """`data` keys: reg_no, name, phone, email, course, batch_name,
    receipt_no, date, mode_of_payment, gst, total_fee, amount_paid,
    amount_due, transaction_id, instalment_no.
    """
    W_PAGE, H_PAGE = LETTER
    LM = RM = TM = BM = 0.5 * inch
    W = W_PAGE - LM - RM

    doc = SimpleDocTemplate(path, pagesize=LETTER,
                            leftMargin=LM, rightMargin=RM,
                            topMargin=TM, bottomMargin=BM)

    BLK    = colors.black
    NAVY   = colors.HexColor("#0B1F3A")
    SEC_BG = colors.HexColor("#0B1F3A")
    ORANGE = colors.HexColor("#EC7C30")
    LBL_BG = colors.HexColor("#D9E1F3")

    def _ps(name, font="Times-Roman", size=9, leading=12, align=TA_LEFT, color=colors.black):
        return ParagraphStyle(name, fontName=font, fontSize=size,
                              leading=leading, alignment=align, textColor=color)

    normal  = _ps("n")
    small   = _ps("sm", size=9, leading=12)
    bold9   = _ps("b9", font="Times-Bold", size=9, leading=12)
    bold9w  = _ps("b9w", font="Times-Bold", size=10, leading=13, align=TA_CENTER, color=colors.white)
    title18 = _ps("t18", font="Times-Bold", size=20, leading=24, align=TA_CENTER, color=NAVY)
    note_i  = _ps("note", font="Times-Italic", size=9, leading=13, color=ORANGE)
    terms_h = _ps("th", font="Times-Bold", size=10, leading=13)
    term_t  = _ps("tt", font="Times-Roman", size=9, leading=13)

    def p(text, style=normal):
        return Paragraph(text if text not in (None, "") else " ", style)

    LABEL_COL = 1.9 * inch
    VAL_COL = (W - 2 * LABEL_COL) / 2

    def _lbl(text):
        return p(f"<b>{text}</b>", bold9)

    def _val(text):
        return p(text if text not in (None, "") else " ", normal)

    def _sec_hdr(title):
        t = Table([[p(f"<b>{title}</b>", bold9w)]], colWidths=[W])
        t.setStyle(TableStyle([
            ("BOX",           (0, 0), (-1, -1), 0.8, BLK),
            ("BACKGROUND",    (0, 0), (-1, -1), SEC_BG),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        return t

    def _row_table(rows, white_rows=()):
        data_, spans, lbl_bg_cmds = [], [], []
        for i, row in enumerate(rows):
            if len(row) == 4:
                l1, v1, l2, v2 = row
                data_.append([_lbl(l1), _val(v1), _lbl(l2), _val(v2)])
                if i not in white_rows:
                    lbl_bg_cmds += [("BACKGROUND", (0, i), (0, i), LBL_BG),
                                    ("BACKGROUND", (2, i), (2, i), LBL_BG)]
            else:
                l1, v1 = row
                data_.append([_lbl(l1), _val(v1), "", ""])
                spans.append(("SPAN", (1, i), (3, i)))
                if i not in white_rows:
                    lbl_bg_cmds.append(("BACKGROUND", (0, i), (0, i), LBL_BG))
        t = Table(data_, colWidths=[LABEL_COL, VAL_COL, LABEL_COL, VAL_COL])
        t.setStyle(TableStyle([
            ("GRID",          (0, 0), (-1, -1), 0.6, BLK),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
            *spans, *lbl_bg_cmds,
        ]))
        return t

    def _money(v):
        if v in (None, ""):
            return " "
        try:
            return f"Rs. {float(v):,.2f}"
        except (TypeError, ValueError):
            return str(v)

    def _watermark(canvas_obj, _doc):
        if not os.path.exists(WATERMARK_PATH):
            return
        size = 4.5 * inch
        canvas_obj.saveState()
        canvas_obj.drawImage(WATERMARK_PATH, (W_PAGE - size) / 2, (H_PAGE - size) / 2,
                             width=size, height=size, mask="auto", preserveAspectRatio=True)
        canvas_obj.restoreState()

    story = []

    # ── HEADER ──────────────────────────────────────────────────
    logo_w = 0.8 * inch
    logo = Image(LOGO_PATH, width=logo_w, height=logo_w) if os.path.exists(LOGO_PATH) else p(" ")

    inst_lines = [
        [p('<font color="#001F5F"><b>CODING NOW</b></font> '
           '<font color="#EC7C30"><b>GURUKUL OF AI</b></font>',
           _ps("brand", font="Times-Bold", size=17, leading=20))],
        [p('<b>Address:</b> 2nd Floor, opp. Metro Pillar No.354, Kapil Vihar, Pitampura, New Delhi, 110034', small)],
        [p('<b>Contact:</b> +91 6677088300 / +91 9899508745', small)],
        [p('<b>Email:</b> info@codingnowai.in&nbsp;&nbsp;|&nbsp;&nbsp;Website: www.codingnowai.in', small)],
    ]
    inst_t = Table(inst_lines, colWidths=[W - logo_w - 10])
    inst_t.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    hdr_t = Table([[logo, inst_t]], colWidths=[logo_w + 10, W - logo_w - 10])
    hdr_t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(hdr_t)
    story.append(Spacer(1, 0.1 * inch))
    story.append(HRFlowable(width="100%", thickness=1.6, color=BLK))
    story.append(Spacer(1, 0.2 * inch))

    story.append(p("FEE RECEIPT", title18))
    story.append(Spacer(1, 0.2 * inch))

    # ── Receipt No. / Date ───────────────────────────────────────
    story.append(_row_table([
        ("Receipt No.:", data.get("receipt_no"), "Date:", data.get("date")),
    ]))
    story.append(Spacer(1, 0.22 * inch))

    # ── STUDENT DETAILS ──────────────────────────────────────────
    story.append(_sec_hdr("STUDENT DETAILS"))
    story.append(_row_table([
        ("Registration No.:", data.get("reg_no"), "Name:", data.get("name")),
        ("Phone:", data.get("phone"), "Email:", data.get("email")),
        ("Course Name:", data.get("course")),
        ("Batch:", data.get("batch_name"), "Mode of Payment:", data.get("mode_of_payment")),
    ]))
    story.append(Spacer(1, 0.22 * inch))

    # ── PAYMENT DETAILS ──────────────────────────────────────────
    story.append(_sec_hdr("PAYMENT DETAILS"))
    story.append(_row_table([
        ("Total Course Fee:", _money(data.get("total_fee")), "GST:", data.get("gst")),
        ("Amount Paid:", _money(data.get("amount_paid")), "Amount Due:", _money(data.get("amount_due"))),
        ("Transaction ID:", data.get("transaction_id"), "Instalment No.:", data.get("instalment_no")),
        ("Amount in Words:", amount_to_words(data.get("amount_paid"))),
    ]))
    story.append(Spacer(1, 0.4 * inch))

    # ── NOTE + TERMS + SIGNATURES ────────────────────────────────
    footer = [
        Paragraph(
            "Note: If the fee is not paid on the stipulated date, Rs. 100/- per day "
            "will be charged as fine, which will increase to Rs. 500/- on the 5th consecutive day.",
            note_i),
        Spacer(1, 0.18 * inch),
        Paragraph("Terms &amp; Conditions:", terms_h),
        Spacer(1, 0.06 * inch),
    ]
    for i, term in enumerate([
        'Cheque to be made in favour of "CODING NOW GURUKUL OF AI", payable at Delhi.',
        "Course Fee is Non-refundable / Non-adjustable / Non-transferable.",
        "Any disputes are under the jurisdiction of Delhi.",
        "Registration / Student ID is valid for 1 year.",
    ], start=1):
        footer.append(Paragraph(f"{i}. {term}", term_t))
    footer.append(Spacer(1, 0.7 * inch))

    half = W / 2
    sig_t = Table(
        [[HRFlowable(width="90%", thickness=0.8, color=BLK), "",
          HRFlowable(width="90%", thickness=0.8, color=BLK), ""],
         [p("Cashier / Counsellor's Signature", normal), "",
          p("Student's Signature", normal), ""]],
        colWidths=[half - 10, 10, half - 10, 10])
    sig_t.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    footer.append(KeepTogether(sig_t))
    story.extend(footer)

    doc.build(story, onFirstPage=_watermark, onLaterPages=_watermark)
