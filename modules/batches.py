import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from db.database import connect_db
from modules.students import _btn, _entry_field, _style_tree

C = {
    "bg": "#f8fafc", "card": "#ffffff", "text": "#1e293b",
    "muted": "#64748b", "border": "#e2e8f0",
    "violet": "#2c5f9e", "violet_h": "#1f4677",
    "rose": "#f43f5e", "rose_h": "#e11d48",
    "amber": "#f59e0b", "amber_h": "#d97706",
    "neutral": "#64748b", "neutral_h": "#475569",
    "violet_t": "#eaf1fa",
}


class BatchesPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=C["bg"])
        self.pack(fill="both", expand=True)
        self.selected_id = None
        self._build()
        self._load()

    def _build(self):
        bar = tk.Frame(self, bg=C["bg"], pady=10)
        bar.pack(fill="x", padx=24)
        tk.Label(bar, text="Batches", font=("Segoe UI", 14, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(side="left")
        tk.Label(bar, text=" — Manage class batches and schedules",
                 font=("Segoe UI", 10), bg=C["bg"], fg=C["muted"]).pack(side="left")

        _btn(bar, "+ Add Batch",  self._add,    C["violet"],  C["violet_h"]).pack(side="right", padx=3)
        _btn(bar, "✎ Update",     self._update, C["amber"],   C["amber_h"]).pack(side="right", padx=3)
        _btn(bar, "✕ Delete",     self._delete, C["rose"],    C["rose_h"]).pack(side="right", padx=3)
        _btn(bar, "↺ Clear",      self._clear,  C["neutral"], C["neutral_h"]).pack(side="right", padx=3)

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
        tk.Frame(fc, bg=C["violet"], height=3).pack(fill="x", pady=(0, 14))
        tk.Label(fc, text="Batch Details", font=("Segoe UI", 11, "bold"),
                 bg=C["card"], fg=C["text"]).pack(anchor="w")
        tk.Label(fc, text="Enter batch information below",
                 font=("Segoe UI", 8), bg=C["card"], fg=C["muted"]).pack(anchor="w", pady=(0, 10))

        self.fields = {}
        for label in ["Batch Name *", "Timing *", "Instructor", "Total Seats"]:
            self.fields[label] = _entry_field(fc, label)

        # Table card
        tc = tk.Frame(body, bg=C["card"],
                      highlightbackground=C["border"], highlightthickness=1)
        tc.grid(row=0, column=1, sticky="nsew")
        tk.Frame(tc, bg=C["violet"], height=3).pack(fill="x")
        tk.Label(tc, text="All Batches", font=("Segoe UI", 11, "bold"),
                 bg=C["card"], fg=C["text"]).pack(anchor="w", padx=14, pady=(10, 4))

        _style_tree("Bat", C["violet"])

        cols = ("ID", "Batch Name", "Timing", "Instructor", "Seats", "Students")
        tw = tk.Frame(tc, bg=C["card"])
        tw.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.tree = ttk.Treeview(tw, columns=cols, show="headings",
                                  style="Bat.Treeview", selectmode="browse")
        for col, w in zip(cols, (50, 150, 110, 140, 70, 80)):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="center")

        vsb = ttk.Scrollbar(tw, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        tw.rowconfigure(0, weight=1); tw.columnconfigure(0, weight=1)

        self.tree.tag_configure("odd",  background="#f0f6fc")
        self.tree.tag_configure("even", background=C["card"])
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _clear(self):
        for w in self.fields.values(): w.delete(0, tk.END)
        self.selected_id = None

    def _load(self):
        conn = connect_db()
        rows = conn.execute("""
            SELECT b.id, b.name, b.timing, b.instructor, b.seats,
                   COUNT(s.id) FROM batches b
            LEFT JOIN students s ON s.batch_id=b.id
            GROUP BY b.id ORDER BY b.id DESC
        """).fetchall()
        conn.close()
        for item in self.tree.get_children(): self.tree.delete(item)
        for i, r in enumerate(rows):
            self.tree.insert("", "end", values=tuple(r),
                             tags=("odd" if i%2 else "even",))

    def _add(self):
        name = self.fields["Batch Name *"].get().strip()
        timing = self.fields["Timing *"].get().strip()
        if not name or not timing:
            messagebox.showwarning("Required", "Batch Name and Timing are required."); return
        seats = self.fields["Total Seats"].get().strip() or "30"
        conn = connect_db()
        conn.execute("INSERT INTO batches(name,timing,instructor,seats) VALUES(?,?,?,?)",
                     (name, timing, self.fields["Instructor"].get().strip(), int(seats)))
        conn.commit(); conn.close()
        messagebox.showinfo("Added", f'Batch "{name}" created.')
        self._clear(); self._load()

    def _update(self):
        if not self.selected_id:
            messagebox.showwarning("Select", "Select a batch first."); return
        seats = self.fields["Total Seats"].get().strip() or "30"
        conn = connect_db()
        conn.execute("UPDATE batches SET name=?,timing=?,instructor=?,seats=? WHERE id=?",
                     (self.fields["Batch Name *"].get().strip(),
                      self.fields["Timing *"].get().strip(),
                      self.fields["Instructor"].get().strip(),
                      int(seats), self.selected_id))
        conn.commit(); conn.close()
        messagebox.showinfo("Updated", "Batch updated."); self._clear(); self._load()

    def _delete(self):
        if not self.selected_id:
            messagebox.showwarning("Select", "Select a batch."); return
        if not messagebox.askyesno("Confirm", "Delete this batch?"): return
        conn = connect_db()
        try:
            conn.execute("DELETE FROM batches WHERE id=?", (self.selected_id,))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            messagebox.showwarning(
                "Batch In Use",
                "This batch still has students assigned to it. "
                "Reassign or remove those students before deleting the batch.")
            return
        conn.close()
        self._clear(); self._load()

    def _on_select(self, _e):
        sel = self.tree.selection()
        if not sel: return
        vals = self.tree.item(sel[0], "values")
        self.selected_id = vals[0]
        for key, val in zip(["Batch Name *","Timing *","Instructor","Total Seats"],
                            [vals[1],vals[2],vals[3],vals[4]]):
            self.fields[key].delete(0, tk.END)
            self.fields[key].insert(0, val)
