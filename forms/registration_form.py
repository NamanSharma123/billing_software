import os
from datetime import date
import tkinter as tk
from tkinter import ttk, messagebox
from db.database import connect_db

C = {
    "bg": "#f8fafc", "card": "white", "text": "#1e293b",
    "muted": "#64748b", "border": "#e2e8f0",
    "teal": "#14b8a6", "teal_h": "#0d9488",
    "indigo": "#e67e22", "indigo_h": "#c2660d",
    "green": "#10b981", "green_h": "#059669",
}

try:
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib import colors
    from reportlab.lib.units import cm, inch
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                    Paragraph, Spacer, KeepTogether, Image,
                                    HRFlowable)
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False

LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "logo.jpeg")
WATERMARK_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "watermark.png")


def _btn(parent, text, cmd, bg, hover):
    from modules.students import _btn as _make_btn
    return _make_btn(parent, text, cmd, bg, hover)


ENROLL_FIELDS = [
    "date_of_birth", "education", "university", "professional_exp",
    "company_name", "guardian_name", "guardian_phone", "valid_id", "ref",
    "mode_of_payment", "gst", "transaction_id", "course_fee", "remarks",
    "receipt_no", "receipt_date",
    "inst1_date", "inst1_due", "inst1_paid",
    "inst2_date", "inst2_due", "inst2_paid",
    "inst3_date", "inst3_due", "inst3_paid",
]


def _get_enrollment(student_id):
    conn = connect_db()
    row = conn.execute(
        "SELECT * FROM enrollment_details WHERE student_id=?", (student_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else {}


def _save_enrollment(student_id, values):
    conn = connect_db()
    cols = ", ".join(ENROLL_FIELDS)
    qs   = ", ".join("?" * len(ENROLL_FIELDS))
    updates = ", ".join(f"{c}=excluded.{c}" for c in ENROLL_FIELDS)
    conn.execute(
        f"""INSERT INTO enrollment_details (student_id, {cols}) VALUES (?, {qs})
            ON CONFLICT(student_id) DO UPDATE SET {updates}""",
        [student_id] + [values.get(c) or None for c in ENROLL_FIELDS]
    )
    conn.commit()
    conn.close()


# ══════════════════════════════════════════════════════════════
# UI PANEL
# ══════════════════════════════════════════════════════════════
ENROLL_LABELS = [
    ("date_of_birth",    "Date of Birth"),
    ("education",        "Education"),
    ("university",       "University / College"),
    ("professional_exp", "Professional Exp."),
    ("company_name",     "Company Name"),
    ("guardian_name",    "Father's / Guardian"),
    ("guardian_phone",   "Guardian Phone"),
    ("valid_id",         "Valid ID (Aadhar/Voter/DL)"),
    ("ref",               "Ref"),
    ("mode_of_payment",  "Mode of Payment"),
    ("gst",              "GST"),
    ("transaction_id",   "Transaction ID"),
    ("course_fee",       "Course Fee"),
    ("remarks",          "Batch / Remarks"),
    ("receipt_no",       "Receipt No."),
    ("receipt_date",     "Receipt Date"),
]


class RegistrationPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=C["bg"])
        self.pack(fill="both", expand=True)
        self._current = None
        self._current_bill = None
        self._enroll_entries = {}
        self._build()

    def _build(self):
        canvas = tk.Canvas(self, bg=C["bg"], highlightthickness=0)
        vsb = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        sf = tk.Frame(canvas, bg=C["bg"])
        win_id = canvas.create_window((0, 0), window=sf, anchor="nw")

        def _resize(e): canvas.itemconfig(win_id, width=e.width)
        canvas.bind("<Configure>", _resize)
        sf.bind("<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        def _wheel(e):
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
            except tk.TclError:
                pass
        canvas.bind_all("<MouseWheel>", _wheel)
        canvas.bind("<Destroy>", lambda _: canvas.unbind_all("<MouseWheel>"))

        # ── Selector card ──────────────────────────────────────
        sel = tk.Frame(sf, bg=C["card"],
                       highlightbackground=C["border"], highlightthickness=1,
                       padx=22, pady=18)
        sel.pack(fill="x", padx=20, pady=(14, 8))

        tk.Frame(sel, bg=C["teal"], height=3).pack(fill="x", pady=(0, 12))
        tk.Label(sel, text="Registration Form Generator",
                 font=("Segoe UI", 13, "bold"), bg=C["card"], fg=C["text"]).pack(anchor="w")
        tk.Label(sel, text="Select a student to generate a PDF form exactly matching the institute's physical form.",
                 font=("Segoe UI", 9), bg=C["card"], fg=C["muted"]).pack(anchor="w", pady=(2, 14))

        row = tk.Frame(sel, bg=C["card"])
        row.pack(fill="x")
        tk.Label(row, text="Select Student:", font=("Segoe UI", 10, "bold"),
                 bg=C["card"], fg=C["text"]).pack(side="left", padx=(0, 10))
        self.student_cb = ttk.Combobox(row, state="readonly", width=36,
                                        font=("Segoe UI", 10))
        self.student_cb.pack(side="left")
        self.student_cb.bind("<<ComboboxSelected>>", self._fill_preview)
        self._refresh_students()

        btn_row = tk.Frame(sel, bg=C["card"])
        btn_row.pack(anchor="w", pady=(14, 0))
        _btn(btn_row, "📄  Generate PDF Form", self._generate,
             C["teal"],   C["teal_h"]).pack(side="left", padx=(0, 10))
        _btn(btn_row, "📂  Open Output Folder", self._open_folder,
             C["indigo"], C["indigo_h"]).pack(side="left")

        if not REPORTLAB_OK:
            tk.Label(sel, text="⚠  reportlab not installed — run: pip install reportlab",
                     font=("Segoe UI", 9), bg=C["card"], fg="#f59e0b").pack(anchor="w", pady=(8, 0))

        # ── Preview card ───────────────────────────────────────
        prev = tk.Frame(sf, bg=C["card"],
                        highlightbackground=C["border"], highlightthickness=1,
                        padx=22, pady=16)
        prev.pack(fill="x", padx=20, pady=(0, 8))
        tk.Frame(prev, bg=C["indigo"], height=3).pack(fill="x", pady=(0, 12))
        tk.Label(prev, text="Preview",
                 font=("Segoe UI", 11, "bold"), bg=C["card"], fg=C["text"]).pack(anchor="w")

        grid = tk.Frame(prev, bg=C["card"])
        grid.pack(fill="x", pady=(8, 0))
        self.prev_vars = {}
        fields = [
            ("Full Name", 0, 0), ("Reg No",      0, 2),
            ("Course",    1, 0), ("Batch",        1, 2),
            ("Phone",     2, 0), ("Email",        2, 2),
            ("Joined",    3, 0), ("Address",      3, 2),
        ]
        for label, r, c in fields:
            tk.Label(grid, text=label + ":", font=("Segoe UI", 9, "bold"),
                     bg=C["card"], fg=C["muted"]).grid(
                         row=r*2, column=c, sticky="w",
                         padx=(0 if c == 0 else 40, 8), pady=(4, 0))
            var = tk.StringVar(value="—")
            tk.Label(grid, textvariable=var, font=("Segoe UI", 10),
                     bg=C["card"], fg=C["text"]).grid(
                         row=r*2+1, column=c, sticky="w",
                         padx=(0 if c == 0 else 40, 8))
            self.prev_vars[label] = var

        # Fee strip
        fee_strip = tk.Frame(sf, bg=C["bg"])
        fee_strip.pack(fill="x", padx=20, pady=(0, 6))
        self.fee_labels = {}
        for label, key in [("Total Fee", "total"), ("Paid", "paid"), ("Balance Due", "due")]:
            box = tk.Frame(fee_strip, bg=C["card"],
                           highlightbackground=C["border"], highlightthickness=1,
                           padx=18, pady=10)
            box.pack(side="left", expand=True, fill="x", padx=4)
            tk.Label(box, text=label, font=("Segoe UI", 8),
                     bg=C["card"], fg=C["muted"]).pack()
            lbl = tk.Label(box, text="—", font=("Segoe UI", 13, "bold"),
                            bg=C["card"], fg=C["text"])
            lbl.pack()
            self.fee_labels[key] = lbl

        # ── Additional Enrollment Details card ──────────────────
        extra = tk.Frame(sf, bg=C["card"],
                         highlightbackground=C["border"], highlightthickness=1,
                         padx=22, pady=16)
        extra.pack(fill="x", padx=20, pady=(0, 8))
        tk.Frame(extra, bg=C["indigo"], height=3).pack(fill="x", pady=(0, 12))
        tk.Label(extra, text="Additional Enrollment Details",
                 font=("Segoe UI", 11, "bold"), bg=C["card"], fg=C["text"]).pack(anchor="w")
        tk.Label(extra, text="Fields printed on the physical Course Enrollment Form — fill in and Save before generating the PDF.",
                 font=("Segoe UI", 8), bg=C["card"], fg=C["muted"]).pack(anchor="w", pady=(2, 12))

        eg = tk.Frame(extra, bg=C["card"])
        eg.pack(fill="x")
        for c in range(3):
            eg.columnconfigure(c, weight=1, uniform="ecol")
        for i, (key, label) in enumerate(ENROLL_LABELS):
            r, c = divmod(i, 3)
            self._enroll_entries[key] = self._mini_field(eg, r, c, label)

        # ── Installments card ───────────────────────────────────
        inst = tk.Frame(sf, bg=C["card"],
                        highlightbackground=C["border"], highlightthickness=1,
                        padx=22, pady=16)
        inst.pack(fill="x", padx=20, pady=(0, 8))
        tk.Frame(inst, bg=C["indigo"], height=3).pack(fill="x", pady=(0, 12))
        tk.Label(inst, text="Installments",
                 font=("Segoe UI", 11, "bold"), bg=C["card"], fg=C["text"]).pack(anchor="w", pady=(0, 10))

        ig = tk.Frame(inst, bg=C["card"])
        ig.pack(fill="x")
        for c in range(4):
            ig.columnconfigure(c, weight=1 if c else 0, uniform="icol" if c else "")
        for c, h in enumerate(["", "Date", "Amount Due (₹)", "Amount Paid (₹)"]):
            tk.Label(ig, text=h, font=("Segoe UI", 8, "bold"),
                     bg=C["card"], fg=C["muted"]).grid(row=0, column=c, sticky="w", padx=6, pady=(0, 4))
        for i in range(1, 4):
            tk.Label(ig, text=f"Installment {i}", font=("Segoe UI", 9, "bold"),
                     bg=C["card"], fg=C["text"]).grid(row=i, column=0, sticky="w", padx=(0, 10), pady=4)
            for c, part in enumerate(["date", "due", "paid"], start=1):
                wrap = tk.Frame(ig, bg=C["border"], highlightbackground=C["border"], highlightthickness=1)
                wrap.grid(row=i, column=c, sticky="ew", padx=6, pady=4)
                e = tk.Entry(wrap, font=("Segoe UI", 9), relief="flat", bg=C["card"])
                e.pack(fill="x", padx=6, pady=5)
                self._enroll_entries[f"inst{i}_{part}"] = e

        save_bar = tk.Frame(sf, bg=C["bg"])
        save_bar.pack(fill="x", padx=20, pady=(0, 8))
        _btn(save_bar, "💾  Save Enrollment Details", self._save_details,
             C["green"], C["green_h"]).pack(side="left")

    def _mini_field(self, parent, r, c, label):
        f = tk.Frame(parent, bg=C["card"])
        f.grid(row=r, column=c, sticky="ew", padx=6, pady=5)
        tk.Label(f, text=label, font=("Segoe UI", 8, "bold"),
                 bg=C["card"], fg=C["muted"]).pack(anchor="w")
        wrap = tk.Frame(f, bg=C["border"], highlightbackground=C["border"], highlightthickness=1)
        wrap.pack(fill="x", pady=(2, 0))
        e = tk.Entry(wrap, font=("Segoe UI", 9), relief="flat", bg=C["card"])
        e.pack(fill="x", padx=6, pady=5)
        return e

    def _save_details(self, silent=False):
        sid = self._stu_map.get(self.student_cb.get())
        if not sid:
            if not silent:
                messagebox.showwarning("Select", "Please select a student first.")
            return
        values = {k: e.get().strip() for k, e in self._enroll_entries.items()}
        _save_enrollment(sid, values)
        if not silent:
            messagebox.showinfo("Saved", "Enrollment details saved.")

    def _load_enrollment(self, sid):
        data = _get_enrollment(sid)
        for key, entry in self._enroll_entries.items():
            entry.delete(0, tk.END)
            if data.get(key) not in (None, ""):
                entry.insert(0, str(data[key]))

    def _refresh_students(self):
        conn = connect_db()
        rows = conn.execute(
            "SELECT id, first_name||' '||last_name AS n FROM students ORDER BY first_name"
        ).fetchall()
        conn.close()
        self._stu_map = {r["n"]: r["id"] for r in rows}
        self.student_cb["values"] = list(self._stu_map.keys())

    def _fill_preview(self, *_):
        name = self.student_cb.get()
        sid  = self._stu_map.get(name)
        if not sid:
            return
        conn = connect_db()
        row  = conn.execute("""
            SELECT s.*, b.name AS batch_name, b.timing
            FROM students s LEFT JOIN batches b ON s.batch_id=b.id
            WHERE s.id=?
        """, (sid,)).fetchone()
        bill = conn.execute(
            "SELECT total_fee, paid_amount FROM billing WHERE student_id=?", (sid,)
        ).fetchone()
        conn.close()
        if not row:
            return
        self._current      = dict(row)
        self._current_bill = dict(bill) if bill else None

        self.prev_vars["Full Name"].set(f"{row['first_name']} {row['last_name']}")
        self.prev_vars["Reg No"].set(f"STU-{row['id']:04d}")
        self.prev_vars["Course"].set(row["course"] or "—")
        self.prev_vars["Batch"].set(row["batch_name"] or "—")
        self.prev_vars["Phone"].set(row["phone"] or "—")
        self.prev_vars["Email"].set(row["email"] or "—")
        self.prev_vars["Joined"].set(row["joined_date"] or "—")
        self.prev_vars["Address"].set(row["address"] or "—")

        self._load_enrollment(sid)

        if bill:
            total = bill["total_fee"]
            paid  = bill["paid_amount"]
            due   = total - paid
            self.fee_labels["total"].config(text=f"₹{total:,.0f}", fg=C["text"])
            self.fee_labels["paid"].config(text=f"₹{paid:,.0f}",  fg=C["green"])
            self.fee_labels["due"].config(text=f"₹{due:,.0f}",
                                           fg=C["muted"] if due <= 0 else "#ef4444")
        else:
            for k in self.fee_labels:
                self.fee_labels[k].config(text="Not set", fg=C["muted"])

    def _generate(self):
        if not REPORTLAB_OK:
            messagebox.showerror("Missing", "Install reportlab:\n  pip install reportlab")
            return
        if not self._current:
            messagebox.showwarning("Select", "Please select a student first.")
            return
        receipt_date_entry = self._enroll_entries.get("receipt_date")
        if receipt_date_entry is not None and not receipt_date_entry.get().strip():
            receipt_date_entry.insert(0, date.today().isoformat())
        self._save_details(silent=True)
        enrollment = _get_enrollment(self._current["id"])
        out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "forms_output")
        os.makedirs(out_dir, exist_ok=True)
        r = self._current
        fname = f"reg_form_{r['first_name']}_{r['last_name']}_STU{r['id']:04d}.pdf"
        path  = os.path.join(out_dir, fname)
        _build_pdf(r, self._current_bill, enrollment, path)
        messagebox.showinfo("Done", f"PDF saved:\n{path}")

    def _open_folder(self):
        out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "forms_output")
        os.makedirs(out_dir, exist_ok=True)
        os.startfile(out_dir)


# ══════════════════════════════════════════════════════════════
# PDF BUILDER  — matches the "CodingNow_Enrollment_Form.docx" reference
# ══════════════════════════════════════════════════════════════
def _build_pdf(student, bill, enrollment, path):
    enrollment = enrollment or {}
    W_PAGE, H_PAGE = LETTER                     # 612 x 792 pts
    LM = RM = TM = BM = 0.5 * inch
    W = W_PAGE - LM - RM                        # usable width ≈ 7.5in

    doc = SimpleDocTemplate(path, pagesize=LETTER,
                            leftMargin=LM, rightMargin=RM,
                            topMargin=TM, bottomMargin=BM)

    def _watermark(canvas_obj, _doc):
        """Faint centered logo behind the page content."""
        if not os.path.exists(WATERMARK_PATH):
            return
        size = 4.5 * inch
        canvas_obj.saveState()
        canvas_obj.drawImage(
            WATERMARK_PATH,
            (W_PAGE - size) / 2, (H_PAGE - size) / 2,
            width=size, height=size,
            mask="auto", preserveAspectRatio=True,
        )
        canvas_obj.restoreState()

    # ── Shared styles (sampled from the reference document) ───
    BLK    = colors.black
    NAVY   = colors.HexColor("#001F5F")         # brand "CODING NOW" text
    SEC_BG = colors.HexColor("#1A1A2D")         # dark-navy section banners
    ORANGE = colors.HexColor("#EC7C30")         # brand orange + note text
    LBL_BG = colors.HexColor("#D9E1F3")         # pale lavender label-cell tint

    def _ps(name, font="Helvetica", size=8, leading=10, align=TA_LEFT, color=colors.black):
        return ParagraphStyle(name, fontName=font, fontSize=size,
                              leading=leading, alignment=align, textColor=color)

    normal  = _ps("n")
    small   = _ps("sm", size=8, leading=11)
    bold8   = _ps("b8",  font="Helvetica-Bold", size=8,  leading=11)
    bold9w  = _ps("b9w", font="Helvetica-Bold", size=9,  leading=12,
                  align=TA_CENTER, color=colors.white)
    title16 = _ps("t16", font="Helvetica-Bold", size=16, leading=19,
                  align=TA_CENTER, color=SEC_BG)
    orange_bold9 = _ps("ob9", font="Helvetica-Bold", size=9, leading=12, color=ORANGE)
    bold10  = _ps("b10", font="Helvetica-Bold", size=10, leading=13)

    def p(text, style=normal):
        return Paragraph(text or " ", style)

    # ── Column-width helper: normalizes a set of relative cm values
    # so every multi-column table sums to exactly W.
    def _cols(*cm_values, total=None):
        total = W if total is None else total
        pts = [v * cm for v in cm_values]
        s = sum(pts)
        return [v * total / s for v in pts]

    # Shared label-column width — used for every label cell in every
    # section so the vertical grid lines up all the way down the page.
    LABEL_COL = 1.85 * inch
    VAL_COL = (W - 2 * LABEL_COL) / 2

    def _lbl(text):
        return p(f"<b>{text}</b>", bold8)

    def _val(text):
        return p(text if text not in (None, "") else " ", normal)

    def _money(v):
        if v in (None, ""):
            return " "
        try:
            return f"Rs. {float(v):,.0f}"
        except (TypeError, ValueError):
            return str(v)

    def _sec_hdr(title):
        """Centered white-on-navy section banner spanning full width."""
        t = Table([[p(f"<b>{title}</b>", bold9w)]], colWidths=[W])
        t.setStyle(TableStyle([
            ("BOX",           (0, 0), (-1, -1), 0.8, BLK),
            ("BACKGROUND",    (0, 0), (-1, -1), SEC_BG),
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        return t

    def _row_table(rows, span_single=True, white_rows=()):
        """Build a 4-col [label, value, label, value] section table.

        `rows` is a list of either:
          - (lbl1, val1, lbl2, val2)  -> a normal 2-pair row
          - (lbl1, val1)              -> a single row; value cell spans
            the rest of the row width (label/value colon omitted callers
            can include their own punctuation)
        `white_rows` holds row indexes that should NOT get the lavender
        label background (matches the reference's Valid ID/Ref row).
        """
        data, spans, lbl_bg_cmds = [], [], []
        for i, row in enumerate(rows):
            if len(row) == 4:
                lbl1, val1, lbl2, val2 = row
                data.append([_lbl(lbl1), _val(val1), _lbl(lbl2), _val(val2)])
                if i not in white_rows:
                    lbl_bg_cmds.append(("BACKGROUND", (0, i), (0, i), LBL_BG))
                    lbl_bg_cmds.append(("BACKGROUND", (2, i), (2, i), LBL_BG))
            else:
                lbl1, val1 = row
                data.append([_lbl(lbl1), _val(val1), "", ""])
                if span_single:
                    spans.append(("SPAN", (1, i), (3, i)))
                if i not in white_rows:
                    lbl_bg_cmds.append(("BACKGROUND", (0, i), (0, i), LBL_BG))
        t = Table(data, colWidths=[LABEL_COL, VAL_COL, LABEL_COL, VAL_COL])
        t.setStyle(TableStyle([
            ("GRID",          (0, 0), (-1, -1), 0.6, BLK),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
            *spans,
            *lbl_bg_cmds,
        ]))
        return t

    story = []

    # ══════════════════════════════════════════════════════════
    # HEADER — logo + institute info, centered title below
    # ══════════════════════════════════════════════════════════
    logo_w = 0.8 * inch
    logo = Image(LOGO_PATH, width=logo_w, height=logo_w) if os.path.exists(LOGO_PATH) else p(" ")

    inst_lines = [
        [p('<font color="#001F5F"><b>CODING NOW</b></font> '
           '<font color="#EC7C30"><b>GURUKUL OF AI</b></font>',
           _ps("brand", font="Helvetica-Bold", size=16, leading=19))],
        [p('<b>Address:</b> 2nd Floor, opp. Metro Pillar No.354, Kapil Vihar, Pitampura, New Delhi, 110034', small)],
        [p('<b>Contact :</b> +91667708830 / +919899508745', small)],
        [p('<b>Email</b>&nbsp;&nbsp;&nbsp;&nbsp;: info@codingnowai.in / <b>website :</b> www.codingnowai.in', small)],
    ]
    inst_t = Table(inst_lines, colWidths=[W - logo_w - 10])
    inst_t.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))

    hdr_t = Table([[logo, inst_t]], colWidths=[logo_w + 10, W - logo_w - 10])
    hdr_t.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(hdr_t)
    story.append(Spacer(1, 0.08 * inch))
    story.append(HRFlowable(width="100%", thickness=1.6, color=BLK))
    story.append(Spacer(1, 0.08 * inch))

    story.append(p("COURSE ENROLLMENT FORM", title16))
    story.append(Spacer(1, 0.08 * inch))

    # ══════════════════════════════════════════════════════════
    # Registration No / Date of Joining
    # ══════════════════════════════════════════════════════════
    reg_no = f"STU-{student['id']:04d}"
    story.append(_row_table([
        ("Registration No :", reg_no, "Date of Joining :", student.get("joined_date")),
    ]))
    story.append(Spacer(1, 0.05 * inch))

    # ══════════════════════════════════════════════════════════
    # PERSONAL DETAILS
    # ══════════════════════════════════════════════════════════
    story.append(_sec_hdr("PERSONAL DETAILS"))

    full_name = f"{student.get('first_name', '')} {student.get('last_name', '')}".strip()
    story.append(_row_table([
        ("Name :", full_name, "Email :", student.get("email")),
        ("Phone :", student.get("phone"), "Date of Birth :", enrollment.get("date_of_birth")),
        ("Education :", enrollment.get("education"), "University / College :", enrollment.get("university")),
        ("Professional Exp. :", enrollment.get("professional_exp"), "Company Name :", enrollment.get("company_name")),
        ("Father's / Guardian :", enrollment.get("guardian_name"), "Guardian Phone :", enrollment.get("guardian_phone")),
        ("Correspondence Address", student.get("address")),
        ("Valid ID (Aadhar/Voter/DL) :", enrollment.get("valid_id"), "Ref :", enrollment.get("ref")),
    ], white_rows={6}))
    story.append(Spacer(1, 0.05 * inch))

    # ══════════════════════════════════════════════════════════
    # COURSE DETAILS
    # ══════════════════════════════════════════════════════════
    story.append(_sec_hdr("COURSE DETAILS"))

    total_fee = bill["total_fee"]   if bill else 0
    paid_amt  = bill["paid_amount"] if bill else 0
    due_amt   = total_fee - paid_amt
    batch_remarks = " / ".join(
        v for v in (student.get("batch_name"), enrollment.get("remarks")) if v
    )

    story.append(_row_table([
        ("Course Name :", student.get("course"), "Mode of Payment :", enrollment.get("mode_of_payment")),
        ("Course Fee :", _money(enrollment.get("course_fee")), "GST :", enrollment.get("gst")),
        ("Total Course Fee :", _money(total_fee) if total_fee else " ", "Transaction ID :", enrollment.get("transaction_id")),
        ("Batch / Remarks :", batch_remarks),
    ]))
    story.append(Spacer(1, 0.05 * inch))

    # ══════════════════════════════════════════════════════════
    # REGISTRATION DETAILS  (receipt)
    # ══════════════════════════════════════════════════════════
    rd_data = [
        [p("<b>Receipt No.</b>", bold8), p("<b>Date</b>", bold8),
         p("<b>Amount Paid</b>", bold8), p("<b>Amount Due</b>", bold8)],
        [_val(enrollment.get("receipt_no")), _val(enrollment.get("receipt_date")),
         _val(_money(paid_amt) if paid_amt else " "),
         _val(_money(due_amt) if total_fee else " ")],
    ]
    rd_t = Table(rd_data, colWidths=_cols(1, 1, 1, 1))
    rd_t.setStyle(TableStyle([
        ("GRID",          (0, 0), (-1, -1), 0.6, BLK),
        ("BACKGROUND",    (0, 0), (-1, 0), LBL_BG),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(KeepTogether([_sec_hdr("REGISTRATION DETAILS"), rd_t]))
    story.append(Spacer(1, 0.05 * inch))

    # ══════════════════════════════════════════════════════════
    # INSTALLMENTS
    # ══════════════════════════════════════════════════════════
    inst_data = [[
        p("<b>Installments Dates</b>", bold8),
        p("<b>Amount Due</b>", bold8), p("<b>Amount Paid</b>", bold8),
    ]]
    for i in (1, 2, 3):
        inst_data.append([
            p(f"<b>Installments {i} :</b>", bold8),
            _val(_money(enrollment.get(f"inst{i}_due"))),
            _val(_money(enrollment.get(f"inst{i}_paid"))),
        ])
    inst_t = Table(inst_data, colWidths=[LABEL_COL, (W - LABEL_COL) / 2, (W - LABEL_COL) / 2])
    inst_t.setStyle(TableStyle([
        ("GRID",          (0, 0), (-1, -1), 0.6, BLK),
        ("BACKGROUND",    (0, 0), (-1, 0), LBL_BG),
        ("BACKGROUND",    (0, 1), (0, -1), LBL_BG),
        ("ALIGN",         (1, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(KeepTogether([_sec_hdr("INSTALLMENTS"), inst_t]))
    story.append(Spacer(1, 0.08 * inch))

    # ══════════════════════════════════════════════════════════
    # NOTE + TERMS & CONDITIONS + SIGNATURES
    # ══════════════════════════════════════════════════════════
    footer = [
        Paragraph(
            "Note: If the fee is not paid on the stipulated date, Rs. 100/- per day "
            "will be charged as fine, which will increase to Rs. 500/- on the 5th consecutive day.",
            orange_bold9),
        Spacer(1, 0.1 * inch),
        Paragraph("Terms &amp; Conditions:", bold10),
        Spacer(1, 0.05 * inch),
    ]
    for i, term in enumerate([
        'Cheque to be made in favour of "CODING NOW GURUKUL OF AI", payable at Delhi.',
        "Course Fee is Non-refundable / Non-adjustable / Non-transferable.",
        "Any disputes are under the Jurisdiction of Delhi.",
        "Registration / Student ID is valid for 1 Year.",
    ], start=1):
        footer.append(Paragraph(f"{i}. {term}", _ps("term", size=9, leading=13)))
    footer.append(Spacer(1, 0.15 * inch))

    half = W / 2
    sig_t = Table(
        [[HRFlowable(width="90%", thickness=0.8, color=BLK), "",
          HRFlowable(width="90%", thickness=0.8, color=BLK), ""],
         [p("Counsellor's Signature", normal), "",
          p("Applicant's Signature", normal), ""]],
        colWidths=[half - 10, 10, half - 10, 10])
    sig_t.setStyle(TableStyle([
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",   (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 2),
    ]))
    footer.append(KeepTogether(sig_t))

    story.extend(footer)

    doc.build(story, onFirstPage=_watermark, onLaterPages=_watermark)
