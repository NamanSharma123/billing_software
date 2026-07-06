import os
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
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                    Paragraph, Spacer, KeepTogether)
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False


def _btn(parent, text, cmd, bg, hover):
    from modules.students import _btn as _make_btn
    return _make_btn(parent, text, cmd, bg, hover)


ENROLL_FIELDS = [
    "date_of_birth", "education", "university", "professional_exp",
    "company_name", "guardian_name", "guardian_phone", "valid_id",
    "mode_of_payment", "gst", "transaction_id", "receipt_no", "receipt_date",
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
    ("mode_of_payment",  "Mode of Payment"),
    ("gst",              "GST"),
    ("transaction_id",   "Transaction ID"),
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
# PDF BUILDER  — matches the physical form exactly
# ══════════════════════════════════════════════════════════════
def _build_pdf(student, bill, enrollment, path):
    enrollment = enrollment or {}
    W_PAGE, H_PAGE = A4                          # 595, 841 pts
    LM = RM = 1.2 * cm
    TM = BM = 1.0 * cm
    W = W_PAGE - LM - RM                        # usable width ≈ 18.6 cm

    doc = SimpleDocTemplate(path, pagesize=A4,
                            leftMargin=LM, rightMargin=RM,
                            topMargin=TM, bottomMargin=BM)

    # ── Shared styles ─────────────────────────────────────────
    BLK    = colors.black
    ORANGE = colors.HexColor("#e67e22")         # Coding Now brand orange
    BLUE   = colors.HexColor("#2c5f9e")         # Gurukul of AI brand blue
    LBL_BG = colors.HexColor("#eaf1fa")         # pale brand-blue tint for label cells
    SEC_BG = BLUE                               # solid brand-blue section banners

    def _ps(name, font="Helvetica", size=8, leading=10, align=TA_LEFT, color=colors.black):
        return ParagraphStyle(name, fontName=font, fontSize=size,
                              leading=leading, alignment=align, textColor=color)

    normal   = _ps("n")
    small    = _ps("sm", size=7, leading=9)
    bold7    = _ps("b7",  font="Helvetica-Bold", size=7,  leading=9)
    bold8    = _ps("b8",  font="Helvetica-Bold", size=8,  leading=10)
    bold9    = _ps("b9",  font="Helvetica-Bold", size=9,  leading=11, color=colors.white)
    bold11   = _ps("b11", font="Helvetica-Bold", size=11, leading=13)
    bold16   = _ps("b16", font="Helvetica-Bold", size=14, leading=16,
                   align=TA_CENTER, color=BLUE)
    center8  = _ps("c8",  size=8, align=TA_CENTER)
    right8   = _ps("r8",  size=8, align=TA_RIGHT)
    orange_bold9 = _ps("ob9", font="Helvetica-Bold", size=9, color=ORANGE)

    def p(text, style=normal):
        return Paragraph(text or " ", style)

    # ── Column-width helper: normalizes a set of relative cm values
    # so every multi-column table sums to exactly W, keeping every
    # section's grid lines aligned down the page.
    def _cols(*cm_values, total=None):
        total = W if total is None else total
        pts = [v * cm for v in cm_values]
        s = sum(pts)
        return [v * total / s for v in pts]

    # ── Shared table style helpers ────────────────────────────
    def _ts(*cmds):
        base = [
            ("GRID",          (0, 0), (-1, -1), 0.6, BLK),
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING",   (0, 0), (-1, -1), 4),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]
        base.extend(cmds)
        return TableStyle(base)

    def _sec_hdr(title):
        """Bold brand-blue section header bar spanning full width."""
        t = Table([[p(f"<b>{title}</b>", bold9)]], colWidths=[W])
        t.setStyle(TableStyle([
            ("BOX",           (0, 0), (-1, -1), 0.8, BLK),
            ("BACKGROUND",    (0, 0), (-1, -1), SEC_BG),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ]))
        return t

    def _lbl(text):
        return p(f"<b>{text}</b>", bold7)

    def _val(text):
        return p(text or " ", normal)

    story = []

    # ══════════════════════════════════════════════════════════
    # HEADER
    # ══════════════════════════════════════════════════════════
    reg_no = f"STU-{student['id']:04d}"

    # Institute info paragraphs
    inst_lines = [
        [p('<b><font color="#e67e22">CODING NOW</font> '
           '<font color="#2c5f9e">GURUKUL OF AI</font></b>',
           _ps("brand", font="Helvetica-Bold", size=13, leading=15))],
        [p("Address: 2nd Floor, opp. Metro Pillar No.354, Kapil Vihar,", small)],
        [p("            Pitampura, New Delhi, 110034", small)],
        [p("Contact : +91667708830 / +919899508745", small)],
        [p("Email   : info@codingnowai.in  /  website : www.codingnowai.in", small)],
    ]
    inst_w, title_w, reg_w = _cols(8.0, 4.6, 6.0)

    inst_t = Table(inst_lines, colWidths=[inst_w])
    inst_t.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
    ]))

    # Reg No + DIRECT STUDENT box (right column)
    right_box_data = [
        [p("<b>Reg No.</b>", bold8),    p(reg_no, bold8)],
        [p("<b>DIRECT STUDENT</b>", bold7), p("✓", bold8)],
        [p("Ref :", small),             p(" ", normal)],
    ]
    right_box = Table(right_box_data, colWidths=_cols(3, 2.5, total=reg_w))
    right_box.setStyle(_ts(
        ("BOX", (0, 0), (-1, -1), 1.0, BLK),
        ("BACKGROUND", (0, 0), (0, -1), LBL_BG),
    ))

    # Assemble header row
    hdr_data = [[inst_t, p("<b>REGISTRATION<br/>FORM</b>", bold16), right_box]]
    hdr_t = Table(hdr_data, colWidths=[inst_w, title_w, reg_w])
    hdr_t.setStyle(TableStyle([
        ("VALIGN",  (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",   (1, 0), (1, 0),   "CENTER"),
        ("BOX",     (0, 0), (-1, -1), 1.0, BLK),
        ("LINEAFTER", (0, 0), (0, 0), 0.6, BLK),
        ("LINEAFTER", (1, 0), (1, 0), 0.6, BLK),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
    ]))
    story.append(hdr_t)
    story.append(Spacer(1, 0.15 * cm))

    # ── REGISTRATION DATE ─────────────────────────────────────
    reg_date_data = [[
        p("<b>REGISTRATION DATE</b>", bold8),
        p(student.get("joined_date") or " ", normal),
    ]]
    reg_date_t = Table(reg_date_data, colWidths=[4 * cm, W - 4 * cm])
    reg_date_t.setStyle(_ts(
        ("BOX",        (0, 0), (-1, -1), 0.8, BLK),
        ("BACKGROUND", (0, 0), (0,  0),  LBL_BG),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ))
    story.append(reg_date_t)
    story.append(Spacer(1, 0.15 * cm))

    # ══════════════════════════════════════════════════════════
    # COURSE REGISTRATION
    # ══════════════════════════════════════════════════════════
    story.append(_sec_hdr("COURSE REGISTRATION"))

    course_fee = f"Rs. {bill['total_fee']:,.0f}" if bill else " "
    cr_data = [[
        _lbl("Course :"), _val(student.get("course")),
        _lbl("Date :"),   _val(student.get("joined_date")),
        _lbl("Registration Fee :"), _val(course_fee),
    ]]
    cr_t = Table(cr_data, colWidths=_cols(1.8, 5.5, 1.5, 3, 2.5, 3.7))
    cr_t.setStyle(_ts(
        ("BACKGROUND", (0, 0), (0, 0), LBL_BG),
        ("BACKGROUND", (2, 0), (2, 0), LBL_BG),
        ("BACKGROUND", (4, 0), (4, 0), LBL_BG),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ))
    story.append(cr_t)
    story.append(Spacer(1, 0.15 * cm))

    # ══════════════════════════════════════════════════════════
    # STUDENT INFORMATION
    # ══════════════════════════════════════════════════════════
    story.append(_sec_hdr("STUDENT INFORMATION"))

    col6 = _cols(2.65, 3.0, 2.75, 3.0, 2.65, 4.6)   # wide enough labels never wrap

    def _row6(pairs):
        row = []
        for lbl_txt, val_txt in pairs:
            row.append(_lbl(lbl_txt))
            row.append(_val(val_txt))
        return row

    si_rows = [
        [("First Name :", student.get("first_name")),
         ("Mid. Name :", ""),
         ("Last Name :", student.get("last_name"))],
        [("Date Of Birth :", enrollment.get("date_of_birth")),
         ("Education :",     enrollment.get("education")),
         ("Email :",         student.get("email"))],
        [("Student Contact :",     student.get("phone")),
         ("University/College :",  enrollment.get("university")),
         ("Batch :",               student.get("batch_name"))],
        [("Father's/Guardian :", enrollment.get("guardian_name")),
         ("Guardian Phone :",    enrollment.get("guardian_phone")),
         ("Professional Exp. :", enrollment.get("professional_exp"))],
    ]
    si_data = [_row6(r) for r in si_rows]
    si_t = Table(si_data, colWidths=col6)
    si_t.setStyle(_ts(
        ("BACKGROUND", (0, 0), (0, -1), LBL_BG),
        ("BACKGROUND", (2, 0), (2, -1), LBL_BG),
        ("BACKGROUND", (4, 0), (4, -1), LBL_BG),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ))
    story.append(si_t)

    # Company Name + Valid ID (wide labels get their own row)
    id_cols = _cols(2.35, 4.85, 3.6, 7.8)
    id_data = [[
        _lbl("Company Name :"),               _val(enrollment.get("company_name")),
        _lbl("Valid ID (Aadhar/Voter/DL) :"),  _val(enrollment.get("valid_id")),
    ]]
    id_t = Table(id_data, colWidths=id_cols)
    id_t.setStyle(_ts(
        ("BACKGROUND", (0, 0), (0, 0), LBL_BG),
        ("BACKGROUND", (2, 0), (2, 0), LBL_BG),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ))
    story.append(id_t)
    story.append(Spacer(1, 0.15 * cm))

    # ══════════════════════════════════════════════════════════
    # ADDRESS
    # ══════════════════════════════════════════════════════════
    story.append(_sec_hdr("ADDRESS"))

    addr_cols = _cols(3.1, 7.2, 1.5, 2.7, 1.8, 2.7)   # 3.1 fits "Permanent Address :" on one line
    addr_data = [
        [_lbl("Current Address :"),   _val(student.get("address")),
         _lbl("City :"), _val(""),    _lbl("Pin Code :"), _val("")],
        [_lbl("Permanent Address :"), _val(""),
         _lbl("City :"), _val(""),    _lbl("Pin Code :"), _val("")],
    ]
    addr_t = Table(addr_data, colWidths=addr_cols)
    addr_t.setStyle(_ts(
        ("BACKGROUND", (0, 0), (0, -1), LBL_BG),
        ("BACKGROUND", (2, 0), (2, -1), LBL_BG),
        ("BACKGROUND", (4, 0), (4, -1), LBL_BG),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
    ))
    story.append(addr_t)
    story.append(Spacer(1, 0.15 * cm))

    # ══════════════════════════════════════════════════════════
    # PAYMENT DETAILS
    # ══════════════════════════════════════════════════════════
    story.append(_sec_hdr("PAYMENT DETAILS"))

    pay_cols = _cols(2.7, 4.1, 1.1, 2.4, 2.4, 5.5)
    pay_data = [[
        _lbl("Mode of Payment :"), _val(enrollment.get("mode_of_payment")),
        _lbl("GST :"),             _val(enrollment.get("gst")),
        _lbl("Transaction ID :"),  _val(enrollment.get("transaction_id")),
    ]]
    pay_t = Table(pay_data, colWidths=pay_cols)
    pay_t.setStyle(_ts(
        ("BACKGROUND", (0, 0), (0, -1), LBL_BG),
        ("BACKGROUND", (2, 0), (2, -1), LBL_BG),
        ("BACKGROUND", (4, 0), (4, -1), LBL_BG),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ))
    story.append(pay_t)
    story.append(Spacer(1, 0.15 * cm))

    # ══════════════════════════════════════════════════════════
    # ADMISSION FEES DETAIL
    # ══════════════════════════════════════════════════════════
    story.append(_sec_hdr("ADMISSION FEES DETAIL"))

    total_fee  = bill["total_fee"]   if bill else 0
    paid_amt   = bill["paid_amount"] if bill else 0
    due_amt    = total_fee - paid_amt

    half = W / 2

    fees_left = [
        [_lbl("Course Detail :"), _val(student.get("course"))],
        [_lbl("Total Fee :"),     _val(f"Rs. {total_fee:,.0f}" if total_fee else " ")],
        [_lbl("First Instalment :"), _val(f"Rs. {paid_amt:,.0f}" if paid_amt else " ")],
        [_lbl("DATE :"),          _val(" ")],
    ]
    fees_right = [
        [_lbl("Second Instalment :"), _val(" ")],
        [_lbl("DATE :"),              _val(" ")],
        [_lbl("Balance Due :"),
         p(f"Rs. {due_amt:,.0f}" if total_fee else " ", orange_bold9)],
        [p(" ", normal),              p(" ", normal)],
    ]

    fl_t = Table(fees_left,  colWidths=[3*cm, half - 3*cm])
    fr_t = Table(fees_right, colWidths=[3.5*cm, half - 3.5*cm])

    for tbl in [fl_t, fr_t]:
        tbl.setStyle(_ts(
            ("BACKGROUND", (0, 0), (0, -1), LBL_BG),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ))

    fees_wrap = Table([[fl_t, fr_t]], colWidths=[half, half])
    fees_wrap.setStyle(TableStyle([
        ("BOX",       (0, 0), (-1, -1), 0.8, BLK),
        ("LINEAFTER", (0, 0), (0, -1), 0.6, BLK),
        ("VALIGN",    (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(fees_wrap)
    story.append(Spacer(1, 0.15 * cm))

    # ══════════════════════════════════════════════════════════
    # REGISTRATION DETAILS  (receipt)
    # ══════════════════════════════════════════════════════════
    def _money(v):
        if v in (None, ""):
            return " "
        try:
            return f"Rs. {float(v):,.0f}"
        except (TypeError, ValueError):
            return str(v)

    rd_cols = _cols(1, 1, 1, 1)
    rd_data = [
        [p("<b>Receipt No.</b>", bold8), p("<b>Date</b>", bold8),
         p("<b>Amount Paid</b>", bold8), p("<b>Amount Due</b>", bold8)],
        [_val(enrollment.get("receipt_no")), _val(enrollment.get("receipt_date")),
         _val(_money(paid_amt) if paid_amt else " "),
         _val(_money(due_amt) if total_fee else " ")],
    ]
    rd_t = Table(rd_data, colWidths=rd_cols)
    rd_t.setStyle(_ts(
        ("BACKGROUND", (0, 0), (-1, 0), LBL_BG),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ))
    story.append(KeepTogether([_sec_hdr("REGISTRATION DETAILS"), rd_t]))
    story.append(Spacer(1, 0.15 * cm))

    # ══════════════════════════════════════════════════════════
    # INSTALLMENTS
    # ══════════════════════════════════════════════════════════
    inst_cols = _cols(2.6, 1.7, 2.05, 2.05)
    inst_data = [[
        p("<b>Installment</b>", bold8), p("<b>Date</b>", bold8),
        p("<b>Amount Due</b>", bold8),  p("<b>Amount Paid</b>", bold8),
    ]]
    for i in (1, 2, 3):
        inst_data.append([
            p(f"<b>Installment {i}</b>", bold8),
            _val(enrollment.get(f"inst{i}_date")),
            _val(_money(enrollment.get(f"inst{i}_due"))),
            _val(_money(enrollment.get(f"inst{i}_paid"))),
        ])
    inst_t = Table(inst_data, colWidths=inst_cols)
    inst_t.setStyle(_ts(
        ("BACKGROUND", (0, 0), (-1, 0), LBL_BG),
        ("BACKGROUND", (0, 1), (0, -1), LBL_BG),
        ("ALIGN",      (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ))
    story.append(KeepTogether([_sec_hdr("INSTALLMENTS"), inst_t]))
    story.append(Spacer(1, 0.15 * cm))

    # ══════════════════════════════════════════════════════════
    # NON-REFUNDABLE FEES
    # ══════════════════════════════════════════════════════════
    nrf_data = [
        [p("<b>Registration Fee Is Required Upon Registration.</b>", bold8),
         p(" ", normal)],
        [_lbl("Registration Fee :"),
         _val("Rs. 2,000.00")],
        [p("Instalment Fee (if required) Will Be Added to Balance.", small),
         _val(" ")],
        [_lbl("Instalment Fee :"),
         p("<b>Rs. 2000.00/-</b>",
           _ps("amt", font="Helvetica-Bold", size=9, align=TA_RIGHT, color=ORANGE))],
    ]
    nrf_t = Table(nrf_data, colWidths=[W * 0.55, W * 0.45])
    nrf_t.setStyle(_ts(
        ("SPAN",       (0, 0), (1, 0)),
        ("SPAN",       (0, 2), (1, 2)),
        ("BACKGROUND", (0, 1), (0, 1), LBL_BG),
        ("BACKGROUND", (0, 3), (0, 3), LBL_BG),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ))
    story.append(KeepTogether([_sec_hdr("NON-REFUNDABLE FEES"), nrf_t]))
    story.append(Spacer(1, 0.3 * cm))

    # ══════════════════════════════════════════════════════════
    # NOTE + TERMS & CONDITIONS + SIGNATURES
    # ══════════════════════════════════════════════════════════
    bold9_blk = _ps("b9k", font="Helvetica-Bold", size=9, leading=12)

    sig_data = [[
        p("<b>Counsellor's Signature:</b>", bold8),
        p(" ", normal),
        p("<b>Applicant's Signature:</b>", bold8),
        p(" ", normal),
    ]]
    sig_t = Table(sig_data, colWidths=[3.9*cm, W/2 - 3.9*cm, 3.9*cm, W/2 - 3.9*cm])
    sig_t.setStyle(TableStyle([
        ("GRID",          (0, 0), (-1, -1), 0.6, BLK),
        ("BACKGROUND",    (0, 0), (0, 0), LBL_BG),
        ("BACKGROUND",    (2, 0), (2, 0), LBL_BG),
        ("TOPPADDING",    (0, 0), (-1, -1), 28),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
    ]))

    footer = [
        Paragraph(
            "<b>Note:</b> If the fee is not paid on the stipulated date, Rs. 100/- per day "
            "will be charged as fine, which will increase to Rs. 500/- on the 5th consecutive day.",
            _ps("note", font="Helvetica-Bold", size=8, leading=11, color=ORANGE)),
        Spacer(1, 0.2 * cm),
        Paragraph("Terms &amp; Conditions:", bold9_blk),
        Spacer(1, 0.05 * cm),
    ]
    for i, term in enumerate([
        'Cheque to be made in favour of "CODING NOW GURUKUL OF AI", payable at Delhi.',
        "Course Fee is Non-refundable / Non-adjustable / Non-transferable.",
        "Any disputes are under the Jurisdiction of Delhi.",
        "Registration / Student ID is valid for 1 Year.",
    ], start=1):
        footer.append(Paragraph(f"{i}. {term}", _ps("term", size=8, leading=11)))
    footer.append(Spacer(1, 0.35 * cm))
    footer.append(sig_t)

    story.append(KeepTogether(footer))

    doc.build(story)
