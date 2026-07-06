import tkinter as tk
from tkinter import ttk, messagebox
from db.database import connect_db
from modules.students import _btn, _style_tree

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

        tk.Label(row1, text="Student:", font=("Segoe UI", 9, "bold"),
                 bg=C["card"], fg=C["muted"]).pack(side="left", padx=(0, 6))
        self.student_cb = ttk.Combobox(row1, state="readonly", width=30,
                                        font=("Segoe UI", 10))
        self.student_cb.pack(side="left", padx=(0, 20))
        self.student_cb.bind("<<ComboboxSelected>>", self._on_student)

        self.total_var = tk.StringVar()
        self.paid_var  = tk.StringVar()
        self.total_var.trace("w", self._calc_due)
        self.paid_var.trace("w",  self._calc_due)

        for label, var in [("Total Fee ₹:", self.total_var),
                            ("Amount Paid ₹:", self.paid_var)]:
            tk.Label(row1, text=label, font=("Segoe UI", 9, "bold"),
                     bg=C["card"], fg=C["muted"]).pack(side="left", padx=(0, 4))
            wrap = tk.Frame(row1, bg=C["border"],
                             highlightbackground=C["border"], highlightthickness=1)
            wrap.pack(side="left", padx=(0, 16))
            tk.Entry(wrap, textvariable=var, font=("Segoe UI", 10),
                      relief="flat", bg=C["card"], width=14).pack(padx=6, pady=5)

        self.due_lbl = tk.Label(row1, text="Due: ₹ 0",
                                 font=("Segoe UI", 12, "bold"),
                                 bg=C["card"], fg=C["rose"])
        self.due_lbl.pack(side="left", padx=10)

        row2 = tk.Frame(fc, bg=C["card"])
        row2.pack(fill="x", pady=(12, 0))
        _btn(row2, "💾 Save Fee",         self._save,    C["rose"],    C["rose_h"]).pack(side="left", padx=(0, 8))
        _btn(row2, "➕ Record Payment",   self._pay,     C["emerald"], C["emerald_h"]).pack(side="left", padx=(0, 8))
        _btn(row2, "📋 Payment History",  self._history, C["indigo"],  C["indigo_h"]).pack(side="left")

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
            "SELECT id, first_name||' '||last_name AS n FROM students ORDER BY first_name"
        ).fetchall()
        conn.close()
        self._stu = {r["n"]: r["id"] for r in rows}
        self.student_cb["values"] = list(self._stu.keys())

    def _calc_due(self, *_):
        try:
            due = float(self.total_var.get() or 0) - float(self.paid_var.get() or 0)
            self.due_lbl.config(text=f"Due: ₹{due:,.0f}",
                                 fg=C["rose"] if due > 0 else C["emerald"])
        except ValueError:
            pass

    def _on_student(self, _e):
        sid = self._stu.get(self.student_cb.get())
        if not sid: return
        conn = connect_db()
        row = conn.execute("SELECT * FROM billing WHERE student_id=?", (sid,)).fetchone()
        conn.close()
        if row:
            self.selected_billing_id = row["id"]
            self.total_var.set(str(row["total_fee"]))
            self.paid_var.set(str(row["paid_amount"]))
        else:
            self.selected_billing_id = None
            self.total_var.set("")
            self.paid_var.set("")

    # ── DB ─────────────────────────────────────────────────────
    def _load_table(self):
        conn = connect_db()
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
        sid = self._stu.get(self.student_cb.get())
        if not sid: messagebox.showwarning("Select", "Select a student."); return
        try:
            total = float(self.total_var.get())
            paid  = float(self.paid_var.get())
        except ValueError:
            messagebox.showwarning("Input", "Enter valid amounts."); return
        conn = connect_db()
        if conn.execute("SELECT id FROM billing WHERE student_id=?", (sid,)).fetchone():
            conn.execute("UPDATE billing SET total_fee=?,paid_amount=? WHERE student_id=?",
                         (total, paid, sid))
        else:
            conn.execute("INSERT INTO billing(student_id,total_fee,paid_amount) VALUES(?,?,?)",
                         (sid, total, paid))
        conn.commit(); conn.close()
        messagebox.showinfo("Saved", "Fee record saved.")
        self._load_table()

    def _pay(self):
        sid = self._stu.get(self.student_cb.get())
        if not sid: messagebox.showwarning("Select", "Select a student."); return
        conn = connect_db()
        row = conn.execute("SELECT * FROM billing WHERE student_id=?", (sid,)).fetchone()
        conn.close()
        if not row: messagebox.showwarning("No Record", "Save a fee record first."); return
        _PaymentDialog(self, row["id"], row["total_fee"],
                       row["paid_amount"], row["total_fee"]-row["paid_amount"],
                       on_close=self._load_table)

    def _history(self):
        name = self.student_cb.get()
        sid  = self._stu.get(name)
        if not sid: messagebox.showwarning("Select", "Select a student."); return
        conn = connect_db()
        b = conn.execute("SELECT id FROM billing WHERE student_id=?", (sid,)).fetchone()
        if not b: conn.close(); messagebox.showinfo("Info", "No billing record."); return
        rows = conn.execute(
            "SELECT amount,note,paid_date FROM payments WHERE billing_id=? ORDER BY paid_date DESC",
            (b["id"],)).fetchall()
        conn.close()

        win = tk.Toplevel(self)
        win.title(f"Payment History — {name}")
        win.geometry("500x380")
        win.configure(bg=C["bg"])
        tk.Frame(win, bg=C["rose"], height=4).pack(fill="x")
        tk.Label(win, text=f"Payment History: {name}",
                 font=("Segoe UI", 12, "bold"), bg=C["bg"], fg=C["text"]).pack(pady=12)
        _style_tree("Hist", C["rose"])
        cols = ("Date", "Amount (₹)", "Note")
        tree = ttk.Treeview(win, columns=cols, show="headings", style="Hist.Treeview")
        for col, w in zip(cols, (130, 130, 210)):
            tree.heading(col, text=col); tree.column(col, width=w, anchor="center")
        for r in rows:
            tree.insert("", "end", values=(r["paid_date"], f"₹{r['amount']:,.0f}", r["note"] or "—"))
        tree.pack(fill="both", expand=True, padx=12, pady=6)


class _PaymentDialog(tk.Toplevel):
    def __init__(self, parent, billing_id, total, paid, due, on_close):
        super().__init__(parent)
        self.title("Record Payment")
        self.geometry("400x300")
        self.configure(bg=C["card"])
        self.grab_set()
        self.billing_id = billing_id
        self.on_close   = on_close

        tk.Frame(self, bg=C["emerald"], height=4).pack(fill="x")
        tk.Label(self, text="Record Payment",
                 font=("Segoe UI", 14, "bold"), bg=C["card"], fg=C["text"]).pack(pady=14)

        info = tk.Frame(self, bg="#f8fafc",
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

        f = tk.Frame(self, bg=C["card"]); f.pack(padx=22, pady=10, fill="x")
        tk.Label(f, text="Payment Amount (₹):", font=("Segoe UI", 9, "bold"),
                 bg=C["card"], fg=C["muted"]).pack(anchor="w")
        self.amount_var = tk.StringVar()
        wrap = tk.Frame(f, bg=C["border"]); wrap.pack(fill="x", pady=(3, 8))
        tk.Entry(wrap, textvariable=self.amount_var, font=("Segoe UI", 11),
                  relief="flat", bg=C["card"]).pack(fill="x", padx=8, pady=6)

        tk.Label(f, text="Note (optional):", font=("Segoe UI", 9, "bold"),
                 bg=C["card"], fg=C["muted"]).pack(anchor="w")
        self.note_var = tk.StringVar()
        wrap2 = tk.Frame(f, bg=C["border"]); wrap2.pack(fill="x", pady=3)
        tk.Entry(wrap2, textvariable=self.note_var, font=("Segoe UI", 10),
                  relief="flat", bg=C["card"]).pack(fill="x", padx=8, pady=5)

        _btn(self, "✓  Confirm Payment", self._save,
             C["emerald"], C["emerald_h"]).pack(pady=10)

    def _save(self):
        try: amount = float(self.amount_var.get())
        except ValueError:
            messagebox.showwarning("Input", "Enter a valid amount.", parent=self); return
        conn = connect_db()
        conn.execute("INSERT INTO payments(billing_id,amount,note) VALUES(?,?,?)",
                     (self.billing_id, amount, self.note_var.get().strip()))
        conn.execute("UPDATE billing SET paid_amount=paid_amount+? WHERE id=?",
                     (amount, self.billing_id))
        conn.commit(); conn.close()
        messagebox.showinfo("Recorded", f"₹{amount:,.0f} payment recorded.", parent=self)
        self.on_close(); self.destroy()
