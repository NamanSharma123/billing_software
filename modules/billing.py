import os
import tkinter as tk
from tkinter import ttk, messagebox
from db.database import connect_db
from modules.students import _btn, _style_tree
from forms.fee_receipt import build_fee_receipt, REPORTLAB_OK
from paths import app_root

C = {
    "bg": "#f8fafc", "card": "#ffffff", "text": "#1e293b",
    "muted": "#64748b", "border": "#e2e8f0",
    "rose": "#f43f5e", "rose_h": "#e11d48", "rose_t": "#fff1f2",
    "emerald": "#10b981", "emerald_h": "#059669", "emerald_t": "#ecfdf5",
    "amber": "#f59e0b", "amber_h": "#d97706", "amber_t": "#fffbeb",
    "indigo": "#e67e22", "indigo_h": "#c2660d",
    "neutral": "#64748b", "neutral_h": "#475569",
    "sky": "#0ea5e9", "sky_h": "#0284c7",
}


class BillingPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=C["bg"])
        self.pack(fill="both", expand=True)
        self.selected_billing_id = None
        self._build()
        self._refresh_students()
        self._load_table()

    def _build(self):
        bar = tk.Frame(self, bg=C["bg"], pady=10)
        bar.pack(fill="x", padx=24)
        tk.Label(bar, text="Billing & Fees", font=("Segoe UI", 14, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(side="left")
        tk.Label(bar, text=" — Track payments and outstanding dues",
                 font=("Segoe UI", 10), bg=C["bg"], fg=C["muted"]).pack(side="left")

        # ── Fee assignment card ────────────────────────────────
        fc = tk.Frame(self, bg=C["card"],
                      highlightbackground=C["border"], highlightthickness=1,
                      padx=22, pady=16)
        fc.pack(fill="x", padx=20, pady=(0, 8))
        tk.Frame(fc, bg=C["rose"], height=3).pack(fill="x", pady=(0, 12))

        row1 = tk.Frame(fc, bg=C["card"])
        row1.pack(fill="x")

        tk.Label(row1, text="Mobile No.:", font=("Segoe UI", 9, "bold"),
                 bg=C["card"], fg=C["muted"]).pack(side="left", padx=(0, 6))
        self.student_cb = ttk.Combobox(row1, state="normal", width=34,
                                        font=("Segoe UI", 10))
        self.student_cb.pack(side="left", padx=(0, 20))
        self.student_cb.bind("<<ComboboxSelected>>", self._on_student)
        self.student_cb.bind("<Return>", self._on_student)
        self.student_cb.bind("<KeyRelease>", self._filter_students)
        self.student_cb.bind("<Down>", self._suggest_focus_list)
        self.student_cb.bind("<FocusOut>", self._suggest_maybe_hide)
        self.student_cb.bind("<Escape>", lambda e: self._suggest_hide())

        # Floating suggestion list — a plain Listbox in a borderless Toplevel,
        # not the ttk.Combobox's native dropdown. The native dropdown steals
        # keyboard focus the instant it opens (see _filter_students below),
        # which is exactly what broke smooth typing before.
        self._suggest_win = None
        self._suggest_list = None
        self._suggest_matches = []

        self.total_var = tk.StringVar()
        self.paid_var  = tk.StringVar(value="0")
        self.total_var.trace("w", self._calc_due)
        self.paid_var.trace("w",  self._calc_due)

        tk.Label(row1, text="Total Fee ₹:", font=("Segoe UI", 9, "bold"),
                 bg=C["card"], fg=C["muted"]).pack(side="left", padx=(0, 4))
        wrap = tk.Frame(row1, bg=C["border"],
                         highlightbackground=C["border"], highlightthickness=1)
        wrap.pack(side="left", padx=(0, 16))
        tk.Entry(wrap, textvariable=self.total_var, font=("Segoe UI", 10),
                  relief="flat", bg=C["card"], width=14).pack(padx=6, pady=5)

        # Amount Paid is read-only — it is always the sum of recorded
        # payments (see _recompute_paid). Editing it here used to let it
        # drift out of sync with the payments ledger and double-count
        # amounts already logged via "Record Payment".
        tk.Label(row1, text="Amount Paid ₹:", font=("Segoe UI", 9, "bold"),
                 bg=C["card"], fg=C["muted"]).pack(side="left", padx=(0, 4))
        wrap2 = tk.Frame(row1, bg=C["border"],
                         highlightbackground=C["border"], highlightthickness=1)
        wrap2.pack(side="left", padx=(0, 16))
        tk.Entry(wrap2, textvariable=self.paid_var, font=("Segoe UI", 10),
                  relief="flat", bg="#f1f5f9", fg=C["muted"], width=14,
                  state="readonly").pack(padx=6, pady=5)

        self.due_lbl = tk.Label(row1, text="Due: ₹ 0",
                                 font=("Segoe UI", 12, "bold"),
                                 bg=C["card"], fg=C["rose"])
        self.due_lbl.pack(side="left", padx=10)

        # ── Selected student's details ─────────────────────────
        details_row = tk.Frame(fc, bg="#f8fafc",
                               highlightbackground=C["border"], highlightthickness=1,
                               padx=14, pady=8)
        details_row.pack(fill="x", pady=(10, 0))
        self._detail_vars = {}
        for label, key in [("Name", "name"), ("Course", "course"),
                            ("Batch", "batch"), ("Email", "email"),
                            ("Next Instalment Due", "next_due")]:
            box = tk.Frame(details_row, bg="#f8fafc")
            box.pack(side="left", expand=True, fill="x", padx=6)
            tk.Label(box, text=label, font=("Segoe UI", 8, "bold"),
                     bg="#f8fafc", fg=C["muted"]).pack(anchor="w")
            var = tk.StringVar(value="—")
            tk.Label(box, textvariable=var, font=("Segoe UI", 10),
                     bg="#f8fafc", fg=C["text"]).pack(anchor="w")
            self._detail_vars[key] = var

        row2 = tk.Frame(fc, bg=C["card"])
        row2.pack(fill="x", pady=(12, 0))
        _btn(row2, "💾 Save Fee",         self._save,    C["rose"],    C["rose_h"]).pack(side="left", padx=(0, 8))
        _btn(row2, "➕ Record Payment",   self._pay,     C["emerald"], C["emerald_h"]).pack(side="left", padx=(0, 8))
        _btn(row2, "📋 Full History",     self._history, C["indigo"],  C["indigo_h"]).pack(side="left")

        # ── Inline recent payment history ──────────────────────
        tk.Label(fc, text="Recent Payments", font=("Segoe UI", 9, "bold"),
                 bg=C["card"], fg=C["muted"]).pack(anchor="w", pady=(14, 4))
        _style_tree("Recent", C["rose"])
        rcols = ("Date", "Amount (₹)", "Mode", "Instalment", "Receipt")
        self.recent_tree = ttk.Treeview(fc, columns=rcols, show="headings",
                                         style="Recent.Treeview", height=4,
                                         selectmode="browse")
        for col, w in zip(rcols, (100, 110, 90, 90, 90)):
            self.recent_tree.heading(col, text=col)
            self.recent_tree.column(col, width=w, anchor="center")
        self.recent_tree.pack(fill="x")
        self.recent_tree.bind("<Double-1>", self._open_recent_receipt)

        # ── Summary stat row ──────────────────────────────────
        stats = tk.Frame(self, bg=C["bg"])
        stats.pack(fill="x", padx=20, pady=6)
        self._stat_labels = {}
        for label, key, color, tint in [
            ("Records",       "count", C["indigo"],  "#fdf1e2"),
            ("Total Fees",    "total", C["text"],    C["card"]),
            ("Collected",     "paid",  C["emerald"], C["emerald_t"]),
            ("Pending Due",   "due",   C["rose"],    C["rose_t"]),
        ]:
            box = tk.Frame(stats, bg=tint,
                            highlightbackground=C["border"], highlightthickness=1,
                            padx=16, pady=10)
            box.pack(side="left", expand=True, fill="x", padx=5)
            tk.Label(box, text=label, font=("Segoe UI", 8), bg=tint,
                     fg=C["muted"]).pack()
            lbl = tk.Label(box, text="—", font=("Segoe UI", 14, "bold"),
                            bg=tint, fg=color)
            lbl.pack()
            self._stat_labels[key] = lbl

        # ── Table ─────────────────────────────────────────────
        tc = tk.Frame(self, bg=C["card"],
                      highlightbackground=C["border"], highlightthickness=1)
        tc.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        tk.Frame(tc, bg=C["rose"], height=3).pack(fill="x")
        tk.Label(tc, text="All Student Fee Records",
                 font=("Segoe UI", 11, "bold"), bg=C["card"],
                 fg=C["text"]).pack(anchor="w", padx=14, pady=(10, 4))

        _style_tree("Bill", C["rose"])
        cols = ("ID", "Student", "Course", "Total Fee", "Paid", "Due", "Status")
        tw = tk.Frame(tc, bg=C["card"])
        tw.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.tree = ttk.Treeview(tw, columns=cols, show="headings",
                                  style="Bill.Treeview", selectmode="browse")
        for col, w in zip(cols, (50, 185, 120, 110, 110, 110, 90)):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="center")

        self.tree.tag_configure("cleared", background="#ecfdf5")
        self.tree.tag_configure("partial",  background="#fffbeb")
        self.tree.tag_configure("pending",  background="#fff1f2")

        vsb = ttk.Scrollbar(tw, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        tw.rowconfigure(0, weight=1); tw.columnconfigure(0, weight=1)

    # ── Helpers ────────────────────────────────────────────────
    def _refresh_students(self):
        conn = connect_db()
        rows = conn.execute(
            "SELECT id, first_name||' '||last_name AS n, phone "
            "FROM students WHERE phone IS NOT NULL AND phone != '' ORDER BY first_name"
        ).fetchall()
        conn.close()
        self._stu = {}
        self._stu_phones = []  # (phone, label) — search matches phone only
        for r in rows:
            label = f"{r['phone']} — {r['n']}"
            self._stu[label] = r["id"]
            self._stu_phones.append((r["phone"], label))
        self._all_student_values = [label for _, label in self._stu_phones]
        self.student_cb["values"] = self._all_student_values

    def _filter_students(self, event):
        if event.keysym in ("Up", "Down", "Left", "Right", "Return", "Escape", "Tab"):
            return
        # Remember the cursor position — reassigning ["values"] below can
        # otherwise reset/select the entry's text and disturb typing.
        cursor_pos = self.student_cb.index(tk.INSERT)
        typed = self.student_cb.get().strip()
        matches = ([(phone, label) for phone, label in self._stu_phones if typed in phone]
                   if typed else [])
        self.student_cb["values"] = ([label for _, label in matches] if typed
                                      else self._all_student_values)
        self.student_cb.icursor(cursor_pos)
        self.student_cb.selection_clear()
        if typed and matches:
            self._suggest_show(matches)
        else:
            self._suggest_hide()

    # ── Floating suggestion popup ───────────────────────────────
    def _suggest_show(self, matches):
        self._suggest_matches = matches
        if self._suggest_win is None:
            self._suggest_win = tk.Toplevel(self)
            self._suggest_win.wm_overrideredirect(True)
            self._suggest_win.attributes("-topmost", True)
            self._suggest_list = tk.Listbox(
                self._suggest_win, font=("Segoe UI", 10), activestyle="none",
                relief="solid", bd=1, highlightthickness=0,
                selectbackground=C["rose"], selectforeground="white")
            self._suggest_list.pack(fill="both", expand=True)
            self._suggest_list.bind("<<ListboxSelect>>", self._suggest_pick)
            self._suggest_list.bind("<Return>", self._suggest_pick)
            self._suggest_list.bind("<Escape>", lambda e: self._suggest_hide())
            self._suggest_list.bind("<FocusOut>", self._suggest_maybe_hide)

        self._suggest_list.delete(0, tk.END)
        for _, label in matches:
            self._suggest_list.insert(tk.END, label)

        x = self.student_cb.winfo_rootx()
        y = self.student_cb.winfo_rooty() + self.student_cb.winfo_height()
        w = self.student_cb.winfo_width()
        h = min(150, 22 * len(matches))
        self._suggest_win.geometry(f"{w}x{h}+{x}+{y}")
        self._suggest_win.deiconify()

    def _suggest_hide(self):
        if self._suggest_win is not None:
            self._suggest_win.withdraw()

    def _suggest_maybe_hide(self, _event=None):
        # Deferred so a click on the listbox registers before we decide to hide it.
        self.after(150, self._suggest_check_focus)

    def _suggest_check_focus(self):
        if self._suggest_win is None:
            return
        focused = self.focus_get()
        if focused not in (self.student_cb, self._suggest_list):
            self._suggest_hide()

    def _suggest_focus_list(self, _event):
        if self._suggest_win is not None and self._suggest_win.winfo_viewable():
            self._suggest_list.focus_set()
            self._suggest_list.selection_set(0)
            self._suggest_list.activate(0)
            return "break"

    def _suggest_pick(self, _event=None):
        sel = self._suggest_list.curselection()
        if not sel:
            return
        label = self._suggest_matches[sel[0]][1]
        self.student_cb.delete(0, tk.END)
        self.student_cb.insert(0, label)
        self._suggest_hide()
        self._on_student(None)

    def _calc_due(self, *_):
        try:
            due = float(self.total_var.get() or 0) - float(self.paid_var.get() or 0)
            self.due_lbl.config(text=f"Due: ₹{due:,.0f}",
                                 fg=C["rose"] if due > 0 else C["emerald"])
        except ValueError:
            pass

    @staticmethod
    def _recompute_paid(conn, billing_id):
        """paid_amount is a cache of SUM(payments.amount) — resync it here
        so any historical drift (e.g. from the old Save-Fee-overwrites-paid
        bug) self-heals the moment this billing record is touched."""
        total_paid = conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM payments WHERE billing_id=?",
            (billing_id,)).fetchone()[0]
        conn.execute("UPDATE billing SET paid_amount=? WHERE id=?", (total_paid, billing_id))
        return total_paid

    @staticmethod
    def _next_instalment_due(enrollment):
        """Earliest instalment date whose paid amount hasn't met its due amount."""
        if not enrollment:
            return None
        candidates = []
        for i in (1, 2, 3):
            date = enrollment[f"inst{i}_date"]
            due  = enrollment[f"inst{i}_due"] or 0
            paid = enrollment[f"inst{i}_paid"] or 0
            if date and paid < due:
                candidates.append((date, i))
        if not candidates:
            return None
        candidates.sort()
        date, i = candidates[0]
        return f"Inst. {i} — {date}"

    def _resolve_student_id(self):
        """Resolve the combobox's current text to a student id.

        Falls back to phone-substring matching (and auto-fills the full
        "phone — name" label) when the text isn't an exact label match —
        e.g. the user typed the raw phone number and hit Enter without
        clicking a suggestion first.
        """
        text = self.student_cb.get().strip()
        sid = self._stu.get(text)
        if sid:
            return sid
        if not text:
            return None
        matches = [label for phone, label in self._stu_phones if text in phone]
        if len(matches) == 1:
            label = matches[0]
            self.student_cb.delete(0, tk.END)
            self.student_cb.insert(0, label)
            return self._stu[label]
        return None

    def _on_student(self, _e):
        sid = self._resolve_student_id()
        if not sid:
            # No, or an ambiguous, match — clear the form instead of
            # silently leaving the previously selected student's figures
            # on screen looking like they belong to this search.
            self.selected_billing_id = None
            self.total_var.set("")
            self.paid_var.set("")
            for var in self._detail_vars.values():
                var.set("—")
            for item in self.recent_tree.get_children():
                self.recent_tree.delete(item)
            self._recent_receipts = {}
            return
        conn = connect_db()
        student = conn.execute("""
            SELECT s.first_name, s.last_name, s.email, s.course, b.name AS batch_name
            FROM students s LEFT JOIN batches b ON s.batch_id = b.id
            WHERE s.id=?
        """, (sid,)).fetchone()
        enrollment = conn.execute(
            "SELECT * FROM enrollment_details WHERE student_id=?", (sid,)).fetchone()
        row = conn.execute("SELECT * FROM billing WHERE student_id=?", (sid,)).fetchone()
        if row:
            self._recompute_paid(conn, row["id"])
            conn.commit()
            row = conn.execute("SELECT * FROM billing WHERE student_id=?", (sid,)).fetchone()
            payments = conn.execute(
                "SELECT * FROM payments WHERE billing_id=? ORDER BY paid_date DESC, id DESC LIMIT 5",
                (row["id"],)).fetchall()
        else:
            payments = []
        conn.close()

        if student:
            self._detail_vars["name"].set(f"{student['first_name']} {student['last_name']}".strip() or "—")
            self._detail_vars["course"].set(student["course"] or "—")
            self._detail_vars["batch"].set(student["batch_name"] or "—")
            self._detail_vars["email"].set(student["email"] or "—")
        self._detail_vars["next_due"].set(self._next_instalment_due(enrollment) or "—")

        for item in self.recent_tree.get_children():
            self.recent_tree.delete(item)
        self._recent_receipts = {}
        for p in payments:
            iid = self.recent_tree.insert("", "end", values=(
                p["paid_date"], f"₹{p['amount']:,.0f}",
                p["mode_of_payment"] or "—", p["instalment_no"] or "—",
                "Open ↗" if p["receipt_path"] else "—",
            ))
            self._recent_receipts[iid] = p["receipt_path"]

        if row:
            self.selected_billing_id = row["id"]
            self.total_var.set(str(row["total_fee"]))
            self.paid_var.set(str(row["paid_amount"]))
        else:
            self.selected_billing_id = None
            self.total_var.set("")
            self.paid_var.set("")

    def _open_recent_receipt(self, _e):
        sel = self.recent_tree.focus()
        path = self._recent_receipts.get(sel)
        if path and os.path.exists(path):
            os.startfile(path)

    # ── DB ─────────────────────────────────────────────────────
    def _load_table(self):
        conn = connect_db()
        # Resync every billing row's paid_amount to its true payments-ledger
        # sum before displaying, so the table/stat cards never show stale
        # or double-counted totals.
        conn.execute("""
            UPDATE billing SET paid_amount = (
                SELECT COALESCE(SUM(amount), 0) FROM payments WHERE payments.billing_id = billing.id
            )
        """)
        conn.commit()
        rows = conn.execute("""
            SELECT b.id, s.first_name||' '||s.last_name, s.course,
                   b.total_fee, b.paid_amount,
                   (b.total_fee-b.paid_amount) AS due
            FROM billing b JOIN students s ON b.student_id=s.id
            ORDER BY due DESC
        """).fetchall()
        agg = conn.execute("""
            SELECT COUNT(*) AS c,
                   COALESCE(SUM(total_fee),0) AS tf,
                   COALESCE(SUM(paid_amount),0) AS pa
            FROM billing
        """).fetchone()
        conn.close()

        for item in self.tree.get_children(): self.tree.delete(item)
        for r in rows:
            due = r["due"]
            if due <= 0:   status, tag = "Cleared", "cleared"
            elif r[4] > 0: status, tag = "Partial", "partial"
            else:           status, tag = "Pending", "pending"
            self.tree.insert("", "end",
                             values=(r[0], r[1], r[2],
                                     f"₹{r[3]:,.0f}", f"₹{r[4]:,.0f}",
                                     f"₹{due:,.0f}", status),
                             tags=(tag,))
        if agg:
            due_t = agg["tf"] - agg["pa"]
            self._stat_labels["count"].config(text=str(agg["c"]))
            self._stat_labels["total"].config(text=f"₹{agg['tf']:,.0f}")
            self._stat_labels["paid"].config(text=f"₹{agg['pa']:,.0f}")
            self._stat_labels["due"].config(text=f"₹{due_t:,.0f}",
                                             fg=C["rose"] if due_t > 0 else C["emerald"])

    def _save(self):
        sid = self._resolve_student_id()
        if not sid: messagebox.showwarning("Select", "Select a student."); return
        try:
            total = float(self.total_var.get())
        except ValueError:
            messagebox.showwarning("Input", "Enter a valid total fee."); return
        conn = connect_db()
        # paid_amount is intentionally NOT set here — it always tracks the
        # sum of the payments ledger (see _recompute_paid) so it can never
        # drift out of sync with "Record Payment" or double-count an amount.
        if conn.execute("SELECT id FROM billing WHERE student_id=?", (sid,)).fetchone():
            conn.execute("UPDATE billing SET total_fee=? WHERE student_id=?", (total, sid))
        else:
            conn.execute("INSERT INTO billing(student_id,total_fee,paid_amount) VALUES(?,?,0)",
                         (sid, total))
        conn.commit(); conn.close()
        messagebox.showinfo("Saved", "Fee record saved.")
        self._on_student(None)
        self._load_table()

    def _pay(self):
        sid = self._resolve_student_id()
        if not sid: messagebox.showwarning("Select", "Select a student."); return
        conn = connect_db()
        row = conn.execute("SELECT * FROM billing WHERE student_id=?", (sid,)).fetchone()
        conn.close()
        if not row: messagebox.showwarning("No Record", "Save a fee record first."); return
        _PaymentDialog(self, sid, row["id"], row["total_fee"],
                       row["paid_amount"], row["total_fee"]-row["paid_amount"],
                       on_close=self._after_payment)

    def _after_payment(self):
        # Refresh both the currently displayed student's totals (Amount
        # Paid / Due update instantly) and the records table below.
        self._on_student(None)
        self._load_table()

    def _history(self):
        sid = self._resolve_student_id()
        if not sid: messagebox.showwarning("Select", "Select a student."); return
        label = self.student_cb.get()
        name = label.split(" — ", 1)[1] if " — " in label else label
        conn = connect_db()
        b = conn.execute("SELECT id FROM billing WHERE student_id=?", (sid,)).fetchone()
        if not b: conn.close(); messagebox.showinfo("Info", "No billing record."); return
        rows = conn.execute(
            "SELECT * FROM payments WHERE billing_id=? ORDER BY paid_date DESC, id DESC",
            (b["id"],)).fetchall()
        conn.close()

        win = tk.Toplevel(self)
        win.title(f"Payment History — {name}")
        win.geometry("640x380")
        win.configure(bg=C["bg"])
        tk.Frame(win, bg=C["rose"], height=4).pack(fill="x")
        tk.Label(win, text=f"Payment History: {name}",
                 font=("Segoe UI", 12, "bold"), bg=C["bg"], fg=C["text"]).pack(pady=12)
        tk.Label(win, text="Double-click a row to open its receipt PDF.",
                 font=("Segoe UI", 8), bg=C["bg"], fg=C["muted"]).pack(pady=(0, 6))
        _style_tree("Hist", C["rose"])
        cols = ("Date", "Amount (₹)", "Mode", "Instalment", "Txn ID", "Note", "Receipt")
        tree = ttk.Treeview(win, columns=cols, show="headings", style="Hist.Treeview")
        for col, w in zip(cols, (90, 90, 80, 80, 100, 120, 70)):
            tree.heading(col, text=col); tree.column(col, width=w, anchor="center")
        receipts = {}
        for r in rows:
            iid = tree.insert("", "end", values=(
                r["paid_date"], f"₹{r['amount']:,.0f}", r["mode_of_payment"] or "—",
                r["instalment_no"] or "—", r["transaction_id"] or "—", r["note"] or "—",
                "Open ↗" if r["receipt_path"] else "—"))
            receipts[iid] = r["receipt_path"]
        tree.pack(fill="both", expand=True, padx=12, pady=6)

        def _open(_e):
            path = receipts.get(tree.focus())
            if path and os.path.exists(path):
                os.startfile(path)
        tree.bind("<Double-1>", _open)


class _PaymentDialog(tk.Toplevel):
    def __init__(self, parent, student_id, billing_id, total, paid, due, on_close):
        super().__init__(parent)
        self.title("Record Payment")
        self.geometry("420x520")
        self.minsize(360, 300)
        self.configure(bg=C["card"])
        self.grab_set()
        self.student_id = student_id
        self.billing_id = billing_id
        self.total      = total
        self.paid       = paid
        self.on_close   = on_close

        tk.Frame(self, bg=C["emerald"], height=4).pack(fill="x", side="top")

        # Confirm button stays pinned to the bottom (outside the scroll
        # area) so it's always reachable without scrolling all the way down.
        _btn(self, "✓  Confirm & Generate Receipt", self._save,
             C["emerald"], C["emerald_h"]).pack(pady=10, side="bottom")

        # ── Scrollable body — so a tall form (or larger Windows display
        # scaling) never forces the user to maximize/resize this dialog
        # just to reach the fields or the button below them.
        canvas = tk.Canvas(self, bg=C["card"], highlightthickness=0)
        vsb = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        body = tk.Frame(canvas, bg=C["card"])
        win_id = canvas.create_window((0, 0), window=body, anchor="nw")

        def _resize(e): canvas.itemconfig(win_id, width=e.width)
        canvas.bind("<Configure>", _resize)
        body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        def _wheel(e):
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
            except tk.TclError:
                pass
        canvas.bind_all("<MouseWheel>", _wheel)
        canvas.bind("<Destroy>", lambda _: canvas.unbind_all("<MouseWheel>"))

        tk.Label(body, text="Record Payment",
                 font=("Segoe UI", 14, "bold"), bg=C["card"], fg=C["text"]).pack(pady=14)

        info = tk.Frame(body, bg="#f8fafc",
                        highlightbackground=C["border"], highlightthickness=1,
                        padx=18, pady=10)
        info.pack(fill="x", padx=22)
        for lbl, val, fg in [("Total Fee", f"₹{total:,.0f}", C["text"]),
                              ("Paid So Far", f"₹{paid:,.0f}", C["emerald"]),
                              ("Remaining Due", f"₹{due:,.0f}", C["rose"])]:
            row = tk.Frame(info, bg="#f8fafc"); row.pack(fill="x", pady=2)
            tk.Label(row, text=lbl+":", font=("Segoe UI", 9), bg="#f8fafc",
                     fg=C["muted"], width=15, anchor="w").pack(side="left")
            tk.Label(row, text=val, font=("Segoe UI", 10, "bold"),
                     bg="#f8fafc", fg=fg).pack(side="left")

        f = tk.Frame(body, bg=C["card"]); f.pack(padx=22, pady=10, fill="x")
        tk.Label(f, text="Payment Amount (₹):", font=("Segoe UI", 9, "bold"),
                 bg=C["card"], fg=C["muted"]).pack(anchor="w")
        self.amount_var = tk.StringVar()
        wrap = tk.Frame(f, bg=C["border"]); wrap.pack(fill="x", pady=(3, 8))
        tk.Entry(wrap, textvariable=self.amount_var, font=("Segoe UI", 11),
                  relief="flat", bg=C["card"]).pack(fill="x", padx=8, pady=6)

        tk.Label(f, text="Mode of Payment:", font=("Segoe UI", 9, "bold"),
                 bg=C["card"], fg=C["muted"]).pack(anchor="w")
        self.mode_var = tk.StringVar(value="Cash")
        ttk.Combobox(f, textvariable=self.mode_var, state="readonly",
                     values=["Cash", "UPI", "Card", "Bank Transfer", "Cheque"],
                     font=("Segoe UI", 10)).pack(fill="x", pady=(3, 8))

        tk.Label(f, text="Transaction ID (optional):", font=("Segoe UI", 9, "bold"),
                 bg=C["card"], fg=C["muted"]).pack(anchor="w")
        self.txn_var = tk.StringVar()
        wrap3 = tk.Frame(f, bg=C["border"]); wrap3.pack(fill="x", pady=(3, 8))
        tk.Entry(wrap3, textvariable=self.txn_var, font=("Segoe UI", 10),
                  relief="flat", bg=C["card"]).pack(fill="x", padx=8, pady=5)

        tk.Label(f, text="Instalment No. (optional):", font=("Segoe UI", 9, "bold"),
                 bg=C["card"], fg=C["muted"]).pack(anchor="w")
        self.inst_var = tk.StringVar()
        wrap4 = tk.Frame(f, bg=C["border"]); wrap4.pack(fill="x", pady=(3, 8))
        tk.Entry(wrap4, textvariable=self.inst_var, font=("Segoe UI", 10),
                  relief="flat", bg=C["card"]).pack(fill="x", padx=8, pady=5)

        tk.Label(f, text="Note (optional):", font=("Segoe UI", 9, "bold"),
                 bg=C["card"], fg=C["muted"]).pack(anchor="w")
        self.note_var = tk.StringVar()
        wrap2 = tk.Frame(f, bg=C["border"]); wrap2.pack(fill="x", pady=3)
        tk.Entry(wrap2, textvariable=self.note_var, font=("Segoe UI", 10),
                  relief="flat", bg=C["card"]).pack(fill="x", padx=8, pady=5)

    def _save(self):
        try: amount = float(self.amount_var.get())
        except ValueError:
            messagebox.showwarning("Input", "Enter a valid amount.", parent=self); return

        mode = self.mode_var.get().strip()
        txn  = self.txn_var.get().strip()
        inst = self.inst_var.get().strip()
        note = self.note_var.get().strip()

        conn = connect_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO payments(billing_id,amount,note,mode_of_payment,transaction_id,instalment_no) "
            "VALUES(?,?,?,?,?,?)",
            (self.billing_id, amount, note, mode, txn, inst))
        payment_id = cur.lastrowid
        # Recompute from the payments ledger rather than incrementing —
        # keeps paid_amount from ever drifting out of sync (see _recompute_paid).
        new_paid = BillingPanel._recompute_paid(conn, self.billing_id)
        conn.commit()

        payment_row = conn.execute(
            "SELECT paid_date FROM payments WHERE id=?", (payment_id,)).fetchone()
        student = conn.execute("""
            SELECT s.first_name, s.last_name, s.phone, s.email, s.course,
                   b.name AS batch_name, e.gst
            FROM students s
            LEFT JOIN batches b ON s.batch_id = b.id
            LEFT JOIN enrollment_details e ON e.student_id = s.id
            WHERE s.id=?
        """, (self.student_id,)).fetchone()
        conn.close()

        messagebox.showinfo("Recorded", f"₹{amount:,.0f} payment recorded.", parent=self)
        self._generate_receipt(payment_id, payment_row, student, amount, new_paid)
        self.on_close(); self.destroy()

    def _generate_receipt(self, payment_id, payment_row, student, amount, new_paid):
        if not REPORTLAB_OK:
            messagebox.showerror("Missing", "Install reportlab:\n  pip install reportlab", parent=self)
            return
        data = {
            "reg_no": f"STU-{self.student_id:04d}",
            "name": f"{student['first_name']} {student['last_name']}".strip(),
            "phone": student["phone"], "email": student["email"],
            "course": student["course"], "batch_name": student["batch_name"],
            "receipt_no": f"RCPT-{payment_id:04d}",
            "date": payment_row["paid_date"],
            "mode_of_payment": self.mode_var.get().strip(),
            "gst": student["gst"],
            "total_fee": self.total,
            "amount_paid": amount,
            "amount_due": self.total - new_paid,
            "transaction_id": self.txn_var.get().strip(),
            "instalment_no": self.inst_var.get().strip(),
        }
        out_dir = os.path.join(app_root(), "forms_output")
        os.makedirs(out_dir, exist_ok=True)
        fname = f"receipt_{data['name'].replace(' ', '_')}_STU{self.student_id:04d}_{payment_id}.pdf"
        path = os.path.join(out_dir, fname)
        build_fee_receipt(data, path)

        conn = connect_db()
        conn.execute("UPDATE payments SET receipt_path=? WHERE id=?", (path, payment_id))
        conn.commit(); conn.close()

        messagebox.showinfo("Receipt Generated", f"Fee receipt saved:\n{path}", parent=self)
