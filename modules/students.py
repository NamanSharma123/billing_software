import tkinter as tk
from tkinter import ttk, messagebox
from db.database import connect_db

C = {
    "bg": "#f8fafc", "card": "#ffffff", "text": "#1e293b",
    "muted": "#64748b", "border": "#e2e8f0",
    "indigo": "#e67e22", "indigo_h": "#c2660d",
    "rose": "#f43f5e", "rose_h": "#e11d48",
    "amber": "#f59e0b", "amber_h": "#d97706",
    "neutral": "#64748b", "neutral_h": "#475569",
    "emerald": "#10b981", "emerald_h": "#059669",
    "indigo_t": "#fdf1e2",
}


def _btn(p, text, cmd, bg, hover):
    b = tk.Button(p, text=text, command=cmd, bg=bg, fg="white",
                  font=("Segoe UI", 9, "bold"), relief="flat",
                  padx=14, pady=7, cursor="hand2",
                  activebackground=hover, activeforeground="white", bd=0)
    b.bind("<Enter>", lambda _: b.config(bg=hover))
    b.bind("<Leave>", lambda _: b.config(bg=bg))
    return b


def _entry_field(parent, label, kind=None):
    lf = tk.Frame(parent, bg=C["card"])
    lf.pack(fill="x", pady=4)
    tk.Label(lf, text=label, font=("Segoe UI", 8, "bold"),
             bg=C["card"], fg=C["muted"]).pack(anchor="w")
    if kind == "combo":
        w = ttk.Combobox(lf, state="readonly", font=("Segoe UI", 10), width=24)
        w.pack(fill="x", pady=(2, 0))
    else:
        wrap = tk.Frame(lf, bg=C["border"],
                        highlightbackground=C["border"], highlightthickness=1)
        wrap.pack(fill="x", pady=(2, 0))
        w = tk.Entry(wrap, font=("Segoe UI", 10), relief="flat",
                     bg=C["card"], fg=C["text"])
        w.pack(fill="x", padx=8, pady=6)
        w.bind("<FocusIn>",  lambda _: wrap.config(bg=C["indigo"]))
        w.bind("<FocusOut>", lambda _: wrap.config(bg=C["border"]))
    return w


class StudentsPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=C["bg"])
        self.pack(fill="both", expand=True)
        self.selected_id = None
        self._build()
        self._load()

    def _build(self):
        # ── Toolbar ───────────────────────────────────────────
        bar = tk.Frame(self, bg=C["bg"], pady=10)
        bar.pack(fill="x", padx=24)

        tk.Label(bar, text="Students", font=("Segoe UI", 14, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(side="left")
        tk.Label(bar, text=" — Add, edit and manage student records",
                 font=("Segoe UI", 10), bg=C["bg"], fg=C["muted"]).pack(side="left")

        _btn(bar, "+ Add Student",  self._add,    C["indigo"],  C["indigo_h"]).pack(side="right", padx=3)
        _btn(bar, "✎ Update",       self._update, C["amber"],   C["amber_h"]).pack(side="right", padx=3)
        _btn(bar, "✕ Delete",       self._delete, C["rose"],    C["rose_h"]).pack(side="right", padx=3)
        _btn(bar, "↺ Clear Form",   self._clear,  C["neutral"], C["neutral_h"]).pack(side="right", padx=3)

        # ── Body: form left | table right ─────────────────────
        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        # Form card
        fc = tk.Frame(body, bg=C["card"],
                      highlightbackground=C["border"], highlightthickness=1,
                      padx=20, pady=18)
        fc.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Indigo top bar
        tk.Frame(fc, bg=C["indigo"], height=3).pack(fill="x", pady=(0, 14))
        tk.Label(fc, text="Student Details", font=("Segoe UI", 11, "bold"),
                 bg=C["card"], fg=C["text"]).pack(anchor="w")
        tk.Label(fc, text="Fill in the information below",
                 font=("Segoe UI", 8), bg=C["card"], fg=C["muted"]).pack(anchor="w", pady=(0, 10))

        self.fields = {}
        for label in ["First Name *", "Last Name *", "Phone", "Email", "Course", "Address"]:
            self.fields[label] = _entry_field(fc, label)
        self.fields["Batch"] = _entry_field(fc, "Batch", kind="combo")
        self.fields["Batch"]["values"] = self._get_batches()

        # Search bar (above table)
        sb_row = tk.Frame(body, bg=C["bg"])
        sb_row.grid(row=0, column=1, sticky="nsew")

        search_bar = tk.Frame(sb_row, bg=C["bg"])
        search_bar.pack(fill="x", pady=(0, 8))
        tk.Label(search_bar, text="🔍", font=("Segoe UI Emoji", 11),
                 bg=C["bg"], fg=C["muted"]).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *_: self._load())
        sw = tk.Frame(search_bar, bg=C["border"],
                      highlightbackground=C["border"], highlightthickness=1)
        sw.pack(side="left", fill="x", expand=True, padx=6)
        tk.Entry(sw, textvariable=self.search_var, font=("Segoe UI", 10),
                  relief="flat", bg=C["card"]).pack(fill="x", padx=8, pady=5)

        # Table card
        tc = tk.Frame(sb_row, bg=C["card"],
                      highlightbackground=C["border"], highlightthickness=1)
        tc.pack(fill="both", expand=True)

        tk.Frame(tc, bg=C["indigo"], height=3).pack(fill="x")
        tk.Label(tc, text="All Students", font=("Segoe UI", 11, "bold"),
                 bg=C["card"], fg=C["text"]).pack(anchor="w", padx=14, pady=(10, 4))

        _style_tree("Stu", C["indigo"])

        cols = ("ID", "First Name", "Last Name", "Phone", "Email", "Course", "Batch")
        tree_wrap = tk.Frame(tc, bg=C["card"])
        tree_wrap.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.tree = ttk.Treeview(tree_wrap, columns=cols, show="headings",
                                  style="Stu.Treeview", selectmode="browse")
        for col, w in zip(cols, (45, 110, 110, 100, 160, 120, 95)):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="center")

        vsb = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        tree_wrap.rowconfigure(0, weight=1)
        tree_wrap.columnconfigure(0, weight=1)

        self.tree.tag_configure("odd",  background="#f8fafc")
        self.tree.tag_configure("even", background=C["card"])
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    # ── Helpers ───────────────────────────────────────────────
    def _get_batches(self):
        conn = connect_db()
        rows = conn.execute("SELECT name FROM batches ORDER BY name").fetchall()
        conn.close()
        return [r["name"] for r in rows]

    def _get(self, k):
        w = self.fields[k]
        return w.get().strip()

    def _clear(self):
        for k, w in self.fields.items():
            if isinstance(w, ttk.Combobox): w.set("")
            else: w.delete(0, tk.END)
        self.selected_id = None

    def _load(self):
        q = self.search_var.get().strip()
        conn = connect_db()
        sql = """SELECT s.id, s.first_name, s.last_name, s.phone, s.email,
                        s.course, b.name AS batch
                 FROM students s LEFT JOIN batches b ON s.batch_id=b.id"""
        rows = conn.execute(
            sql + (" WHERE s.first_name LIKE ? OR s.last_name LIKE ?"
                   " OR s.phone LIKE ? OR s.course LIKE ? ORDER BY s.id DESC"
                   if q else " ORDER BY s.id DESC"),
            [f"%{q}%"]*4 if q else []
        ).fetchall()
        conn.close()
        for item in self.tree.get_children(): self.tree.delete(item)
        for i, r in enumerate(rows):
            self.tree.insert("", "end", values=tuple(r),
                             tags=("odd" if i%2 else "even",))

    def _add(self):
        fn, ln = self._get("First Name *"), self._get("Last Name *")
        if not fn or not ln:
            messagebox.showwarning("Required", "First Name and Last Name are required.")
            return
        bid = self._bid(self._get("Batch"))
        conn = connect_db()
        conn.execute("INSERT INTO students(first_name,last_name,phone,email,course,batch_id,address)"
                     " VALUES(?,?,?,?,?,?,?)",
                     (fn, ln, self._get("Phone"), self._get("Email"),
                      self._get("Course"), bid, self._get("Address")))
        conn.commit(); conn.close()
        messagebox.showinfo("Added", f"Student {fn} {ln} added.")
        self._clear(); self._load()

    def _update(self):
        if not self.selected_id:
            messagebox.showwarning("Select", "Select a student row first."); return
        bid = self._bid(self._get("Batch"))
        conn = connect_db()
        conn.execute("UPDATE students SET first_name=?,last_name=?,phone=?,email=?,"
                     "course=?,batch_id=?,address=? WHERE id=?",
                     (self._get("First Name *"), self._get("Last Name *"),
                      self._get("Phone"), self._get("Email"),
                      self._get("Course"), bid, self._get("Address"),
                      self.selected_id))
        conn.commit(); conn.close()
        messagebox.showinfo("Updated", "Record updated."); self._clear(); self._load()

    def _delete(self):
        if not self.selected_id:
            messagebox.showwarning("Select", "Select a student first."); return
        if not messagebox.askyesno("Delete", "Delete this student and all billing records?"): return
        conn = connect_db()
        conn.execute("DELETE FROM students WHERE id=?", (self.selected_id,))
        conn.commit(); conn.close()
        self._clear(); self._load()

    def _bid(self, name):
        if not name: return None
        conn = connect_db()
        row = conn.execute("SELECT id FROM batches WHERE name=?", (name,)).fetchone()
        conn.close()
        return row["id"] if row else None

    def _on_select(self, _e):
        sel = self.tree.selection()
        if not sel: return
        vals = self.tree.item(sel[0], "values")
        self.selected_id = vals[0]
        for key, val in zip(["First Name *","Last Name *","Phone","Email","Course","Batch"],
                            [vals[1],vals[2],vals[3],vals[4],vals[5],vals[6] or ""]):
            w = self.fields[key]
            if isinstance(w, ttk.Combobox):
                w["values"] = self._get_batches(); w.set(val)
            else:
                w.delete(0, tk.END); w.insert(0, val)


def _style_tree(name, header_color):
    s = ttk.Style()
    s.theme_use("default")
    s.configure(f"{name}.Treeview.Heading",
                background=header_color, foreground="white",
                font=("Segoe UI", 9, "bold"), relief="flat")
    s.configure(f"{name}.Treeview",
                rowheight=30, font=("Segoe UI", 9),
                fieldbackground=C["card"], borderwidth=0)
    s.map(f"{name}.Treeview",
          background=[("selected", header_color)],
          foreground=[("selected", "white")])
