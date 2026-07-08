import tkinter as tk
from tkinter import messagebox
import datetime
from db.database import connect_db

C = {
    "side_bg":     "#0d1b2a",
    "side_logo":   "#13293f",
    "side_hover":  "#13293f",
    "side_active_bg": "#173754",
    "side_active":    "#e67e22",
    "side_text":   "#93a8c3",
    "hdr_bg":      "#ffffff",
    "hdr_border":  "#e2e8f0",
    "hdr_text":    "#1e293b",
    "hdr_muted":   "#64748b",
    "bg":          "#f8fafc",
    "card":        "#ffffff",
    "border":      "#e2e8f0",
    "text":        "#1e293b",
    "muted":       "#64748b",
    "indigo":  "#e67e22", "indigo_h":  "#c2660d", "indigo_t":  "#fdf1e2",
    "violet":  "#2c5f9e", "violet_h":  "#1f4677", "violet_t":  "#eaf1fa",
    "emerald": "#10b981", "emerald_h": "#059669", "emerald_t": "#ecfdf5",
    "rose":    "#f43f5e", "rose_h":    "#e11d48", "rose_t":    "#fff1f2",
    "teal":    "#14b8a6", "teal_h":    "#0d9488", "teal_t":    "#f0fdfa",
    "amber":   "#f59e0b", "amber_h":   "#d97706", "amber_t":   "#fffbeb",
}

NAV = [
    ("🏠", "Home",       "home"),
    ("👨‍🎓","Students",  "students"),
    ("🗂", "Batches",    "batches"),
    ("💰", "Billing",    "billing"),
    ("📄", "Reg Form",   "regform"),
]


def open_dashboard(user_name="Admin"):
    from main import _load_logo, _fade_in  # lazy import avoids a circular import at module load

    root = tk.Tk()
    root.title("Coding Now | Gurukul of AI — Billing System")
    root.state("zoomed")
    root.minsize(960, 600)
    root.configure(bg=C["side_bg"])

    # ── SIDEBAR ───────────────────────────────────────────────
    sidebar = tk.Frame(root, bg=C["side_bg"], width=220)
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    # Logo
    logo_block = tk.Frame(sidebar, bg=C["side_logo"], pady=18)
    logo_block.pack(fill="x")
    logo_img = _load_logo((52, 52))
    if logo_img:
        logo_img_lbl = tk.Label(logo_block, image=logo_img, bg=C["side_logo"])
        logo_img_lbl.image = logo_img  # keep a reference — Tk drops GC'd images
        logo_img_lbl.pack(pady=(0, 6))
    tk.Label(logo_block, text="CODING NOW", font=("Segoe UI", 15, "bold"),
             bg=C["side_logo"], fg=C["indigo"]).pack()
    tk.Label(logo_block, text="GURUKUL OF AI", font=("Segoe UI", 9, "bold"),
             bg=C["side_logo"], fg=C["violet"]).pack(pady=(1, 4))
    tk.Label(logo_block, text="Billing System",
             font=("Segoe UI", 8), bg=C["side_logo"],
             fg=C["side_text"], justify="center").pack()

    # User row
    u_row = tk.Frame(sidebar, bg=C["side_bg"], pady=10, padx=14)
    u_row.pack(fill="x")
    dot = tk.Canvas(u_row, width=8, height=8, bg=C["side_bg"], highlightthickness=0)
    dot.create_oval(0, 0, 8, 8, fill=C["emerald"], outline="")
    dot.pack(side="left", padx=(0, 6))
    tk.Label(u_row, text=user_name, font=("Segoe UI", 9),
             bg=C["side_bg"], fg=C["side_text"]).pack(side="left")

    tk.Frame(sidebar, bg="#1e293b", height=1).pack(fill="x")

    tk.Label(sidebar, text="  NAVIGATION", font=("Segoe UI", 7, "bold"),
             bg=C["side_bg"], fg="#334155").pack(anchor="w", padx=14, pady=(10, 4))

    active_key    = tk.StringVar(value="home")
    nav_refs      = {}
    current_frame = [None]
    _toast_id     = [None]

    # ── Nav builder ───────────────────────────────────────────
    def _activate(key):
        active_key.set(key)
        for k, (btn_f, bar_f, icon_l, lbl_l, inner_f) in nav_refs.items():
            if k == key:
                btn_f.config(bg=C["side_active_bg"])
                inner_f.config(bg=C["side_active_bg"])
                bar_f.config(bg=C["side_active"])
                icon_l.config(bg=C["side_active_bg"], fg=C["side_active"])
                lbl_l.config(bg=C["side_active_bg"], fg="white",
                              font=("Segoe UI", 11))
            else:
                btn_f.config(bg=C["side_bg"])
                inner_f.config(bg=C["side_bg"])
                bar_f.config(bg=C["side_bg"])
                icon_l.config(bg=C["side_bg"], fg=C["side_text"])
                lbl_l.config(bg=C["side_bg"], fg=C["side_text"],
                              font=("Segoe UI", 11))

    def _nav(key):
        _activate(key)
        _load(key)

    for emoji, label, key in NAV:
        btn_f  = tk.Frame(sidebar, bg=C["side_bg"], cursor="hand2")
        btn_f.pack(fill="x")
        bar_f  = tk.Frame(btn_f, bg=C["side_bg"], width=4)
        bar_f.pack(side="left", fill="y")
        inner_f = tk.Frame(btn_f, bg=C["side_bg"], pady=12, padx=10)
        inner_f.pack(side="left", fill="both", expand=True)
        icon_l  = tk.Label(inner_f, text=emoji, font=("Segoe UI Emoji", 13),
                            bg=C["side_bg"], fg=C["side_text"], width=3)
        icon_l.pack(side="left")
        lbl_l   = tk.Label(inner_f, text=label, font=("Segoe UI", 11),
                            bg=C["side_bg"], fg=C["side_text"], anchor="w")
        lbl_l.pack(side="left", padx=4)

        nav_refs[key] = (btn_f, bar_f, icon_l, lbl_l, inner_f)

        def _click(_e, k=key): _nav(k)
        def _enter(_e, bf=btn_f, inf=inner_f, il=icon_l, ll=lbl_l, brf=bar_f, k=key):
            if active_key.get() != k:
                for w in [bf, inf, il, ll]: w.config(bg=C["side_hover"])
        def _leave(_e, bf=btn_f, inf=inner_f, il=icon_l, ll=lbl_l, brf=bar_f, k=key):
            if active_key.get() != k:
                for w in [bf, inf, il, ll]: w.config(bg=C["side_bg"])

        for w in [btn_f, inner_f, icon_l, lbl_l, bar_f]:
            w.bind("<Button-1>", _click)
            w.bind("<Enter>",    _enter)
            w.bind("<Leave>",    _leave)

    tk.Frame(sidebar, bg=C["side_bg"]).pack(fill="both", expand=True)
    tk.Frame(sidebar, bg="#1e293b", height=1).pack(fill="x")

    def _logout():
        if messagebox.askyesno("Sign Out", "Sign out of the system?", parent=root):
            root.destroy()
            import main; main.run_login()

    lo_btn = tk.Frame(sidebar, bg="#1e293b", cursor="hand2", pady=14)
    lo_btn.pack(fill="x")
    lo_lbl = tk.Label(lo_btn, text="⎋  Sign Out",
                       font=("Segoe UI", 11, "bold"), bg="#1e293b", fg=C["rose"])
    lo_lbl.pack()
    for w in [lo_btn, lo_lbl]:
        w.bind("<Button-1>", lambda _: _logout())
        w.bind("<Enter>", lambda _: [lo_btn.config(bg="#2d1219"),
                                      lo_lbl.config(bg="#2d1219")])
        w.bind("<Leave>", lambda _: [lo_btn.config(bg="#1e293b"),
                                      lo_lbl.config(bg="#1e293b")])

    # ── RIGHT AREA ────────────────────────────────────────────
    right = tk.Frame(root, bg=C["bg"])
    right.pack(side="left", fill="both", expand=True)

    # White top header
    hdr = tk.Frame(right, bg=C["hdr_bg"],
                   highlightbackground=C["hdr_border"], highlightthickness=1,
                   height=58)
    hdr.pack(fill="x")
    hdr.pack_propagate(False)

    page_title = tk.Label(hdr, text="Dashboard — Overview",
                           font=("Segoe UI", 15, "bold"),
                           bg=C["hdr_bg"], fg=C["hdr_text"])
    page_title.pack(side="left", padx=22, pady=12)

    clock_lbl = tk.Label(hdr, font=("Segoe UI", 10), bg=C["hdr_bg"], fg=C["hdr_muted"])
    clock_lbl.pack(side="right", padx=18)

    def _tick():
        clock_lbl.config(text=datetime.datetime.now().strftime("%d %b %Y   %I:%M:%S %p"))
        root.after(1000, _tick)
    _tick()

    # Toast bar (bottom of right area)
    toast_bar = tk.Frame(right, bg=C["bg"], height=0)
    toast_bar.pack(side="bottom", fill="x")
    toast_lbl = tk.Label(toast_bar, text="", font=("Segoe UI", 9, "bold"),
                          bg=C["bg"], fg=C["bg"], pady=0)
    toast_lbl.pack()

    def show_toast(msg, color=C["emerald"]):
        if _toast_id[0]:
            root.after_cancel(_toast_id[0])
        toast_bar.config(bg=color, height=32)
        toast_lbl.config(text=f"  ✓  {msg}", bg=color, fg="white", pady=7)
        _toast_id[0] = root.after(3000, _hide_toast)

    def _hide_toast():
        toast_bar.config(bg=C["bg"], height=0)
        toast_lbl.config(text="", bg=C["bg"], fg=C["bg"], pady=0)

    content_outer = tk.Frame(right, bg=C["bg"])
    content_outer.pack(fill="both", expand=True)

    # ── Module loader ─────────────────────────────────────────
    def _load(key):
        titles = {
            "home":     "Dashboard — Overview",
            "students": "👨‍🎓  Students Management",
            "batches":  "🗂  Batch Management",
            "billing":  "💰  Billing & Fees",
            "regform":  "📄  Registration Form",
        }
        page_title.config(text=titles.get(key, key.title()))

        if current_frame[0]:
            current_frame[0].destroy()

        frame = tk.Frame(content_outer, bg=C["bg"])
        frame.pack(fill="both", expand=True)
        current_frame[0] = frame

        if key == "home":
            _build_home(frame)
        elif key == "students":
            from modules.students import StudentsPanel
            StudentsPanel(frame)
        elif key == "batches":
            from modules.batches import BatchesPanel
            BatchesPanel(frame)
        elif key == "billing":
            from modules.billing import BillingPanel
            BillingPanel(frame)
        elif key == "regform":
            from forms.registration_form import RegistrationPanel
            RegistrationPanel(frame)

    # ── HOME PANEL ────────────────────────────────────────────
    def _build_home(parent):
        canvas = tk.Canvas(parent, bg=C["bg"], highlightthickness=0)
        vsb = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        sf = tk.Frame(canvas, bg=C["bg"])
        win_id = canvas.create_window((0, 0), window=sf, anchor="nw")

        def _resize(e): canvas.itemconfig(win_id, width=e.width)
        canvas.bind("<Configure>", _resize)
        sf.bind("<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # ── SCROLL: fix — unbind when canvas destroyed ─────────
        def _wheel(e):
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
            except tk.TclError:
                pass

        canvas.bind_all("<MouseWheel>", _wheel)
        canvas.bind("<Destroy>", lambda _: canvas.unbind_all("<MouseWheel>"))

        # ── Greeting ──────────────────────────────────────────
        g_row = tk.Frame(sf, bg=C["bg"])
        g_row.pack(fill="x", padx=28, pady=(22, 4))
        hr = datetime.datetime.now().hour
        gr = "Good Morning" if hr < 12 else ("Good Afternoon" if hr < 17 else "Good Evening")
        tk.Label(g_row, text=f"{gr}, {user_name}! 👋",
                 font=("Segoe UI", 20, "bold"), bg=C["bg"], fg=C["text"]).pack(side="left")
        tk.Label(g_row, text=datetime.datetime.now().strftime("%A, %d %B %Y"),
                 font=("Segoe UI", 10), bg=C["bg"], fg=C["muted"]).pack(side="left", padx=14)

        def _refresh_home():
            parent.destroy()
            _nav("home")
            show_toast("Dashboard refreshed")

        _pill_btn(g_row, "⟳  Refresh", _refresh_home,
                  C["indigo"], C["indigo_h"]).pack(side="right")

        # ── STAT CARDS ────────────────────────────────────────
        conn = connect_db()
        n_stu = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        n_bat = conn.execute("SELECT COUNT(*) FROM batches").fetchone()[0]
        paid  = conn.execute("SELECT COALESCE(SUM(paid_amount),0) FROM billing").fetchone()[0]
        total = conn.execute("SELECT COALESCE(SUM(total_fee),0) FROM billing").fetchone()[0]
        conn.close()
        due = total - paid

        stat_row = tk.Frame(sf, bg=C["bg"])
        stat_row.pack(fill="x", padx=22, pady=(14, 6))

        for label, value, color, tint, emoji in [
            ("Total Students", str(n_stu),          C["indigo"],  C["indigo_t"],  "👨‍🎓"),
            ("Active Batches", str(n_bat),           C["violet"],  C["violet_t"],  "🗂"),
            ("Fees Collected", f"₹{paid:,.0f}",     C["emerald"], C["emerald_t"], "✅"),
            ("Balance Due",    f"₹{due:,.0f}",      C["rose"],    C["rose_t"],    "⚠️"),
        ]:
            _stat_card(stat_row, label, value, color, tint, emoji)

        # ── QUICK ACCESS ──────────────────────────────────────
        sec_row = tk.Frame(sf, bg=C["bg"])
        sec_row.pack(fill="x", padx=28, pady=(20, 8))
        tk.Label(sec_row, text="Modules", font=("Segoe UI", 14, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(side="left")
        tk.Label(sec_row, text=" — click any card to open",
                 font=("Segoe UI", 10), bg=C["bg"], fg=C["muted"]).pack(side="left")

        grid = tk.Frame(sf, bg=C["bg"])
        grid.pack(fill="x", padx=20, pady=(0, 16))
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        mods = [
            ("students", "👨‍🎓", "Students",
             "Enroll, edit and search student records.\nAssign batches and track enrollment.",
             C["indigo"], C["indigo_t"], C["indigo_h"]),
            ("batches", "🗂", "Batches",
             "Create class batches with timing.\nManage instructors and seat capacity.",
             C["violet"], C["violet_t"], C["violet_h"]),
            ("billing", "💰", "Billing & Fees",
             "Assign fees, record payments,\ntrack dues and view payment history.",
             C["rose"], C["rose_t"], C["rose_h"]),
            ("regform", "📄", "Registration Form",
             "Generate a printable PDF form\nfor any enrolled student.",
             C["teal"], C["teal_t"], C["teal_h"]),
        ]
        for i, (key, emoji, title, desc, color, tint, hover) in enumerate(mods):
            r, c = divmod(i, 2)
            grid.rowconfigure(r, weight=1)
            _module_card(grid, r, c, emoji, title, desc,
                          color, tint, hover, lambda k=key: _nav(k))

        # ── Info tip ──────────────────────────────────────────
        tip = tk.Frame(sf, bg=C["violet_t"],
                        highlightbackground="#bcd3ec", highlightthickness=1,
                        padx=18, pady=12)
        tip.pack(fill="x", padx=24, pady=(4, 28))
        tk.Label(tip, text="💡  Tip:", font=("Segoe UI", 10, "bold"),
                 bg=C["violet_t"], fg=C["violet"]).pack(side="left", padx=(0, 8))
        tk.Label(tip, text="Start by adding Batches → then enroll Students → then assign Billing.",
                 font=("Segoe UI", 10), bg=C["violet_t"], fg=C["violet_h"]).pack(side="left")

    _activate("home")
    _load("home")
    _fade_in(root)
    root.mainloop()


# ══════════════════════════════════════════════════════════════
# WIDGET FACTORIES
# ══════════════════════════════════════════════════════════════
def _pill_btn(parent, text, cmd, bg, hover):
    b = tk.Button(parent, text=text, command=cmd, bg=bg, fg="white",
                  font=("Segoe UI", 9, "bold"), relief="flat",
                  padx=16, pady=7, cursor="hand2",
                  activebackground=hover, activeforeground="white", bd=0)
    b.bind("<Enter>", lambda _: b.config(bg=hover))
    b.bind("<Leave>", lambda _: b.config(bg=bg))
    return b


def _stat_card(parent, label, value, color, tint, emoji):
    """White card, 4 px colored top bar, big colored number, tinted icon."""
    outer = tk.Frame(parent, bg=color)          # top bar = 4px gap
    outer.pack(side="left", expand=True, fill="x", padx=7)

    card = tk.Frame(outer, bg=C["card"],
                    highlightbackground=C["border"], highlightthickness=1)
    card.pack(fill="both", expand=True, pady=(4, 0))

    body = tk.Frame(card, bg=C["card"], padx=18, pady=16)
    body.pack(fill="both")

    # Icon tinted box top-right
    icon_frame = tk.Frame(body, bg=tint, padx=8, pady=6)
    icon_frame.pack(side="right", anchor="n")
    tk.Label(icon_frame, text=emoji, font=("Segoe UI Emoji", 18),
             bg=tint).pack()

    tk.Label(body, text=value, font=("Segoe UI", 26, "bold"),
             bg=C["card"], fg=color).pack(anchor="w")
    tk.Label(body, text=label, font=("Segoe UI", 9),
             bg=C["card"], fg=C["muted"]).pack(anchor="w", pady=(2, 0))

    # Subtle "lift" on hover — border picks up the card's accent color,
    # matching the interactivity feel of the module cards below.
    def _enter(_e):
        card.config(highlightbackground=color, highlightthickness=2)
    def _leave(_e):
        card.config(highlightbackground=C["border"], highlightthickness=1)
    for w in (card, body, icon_frame):
        w.bind("<Enter>", _enter)
        w.bind("<Leave>", _leave)


def _module_card(grid, row, col, emoji, title, desc, color, tint, hover_color, cmd):
    """Card with colored top strip, icon circle, description, open button."""
    outer = tk.Frame(grid, bg=color)           # 5px colored strip
    outer.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

    card = tk.Frame(outer, bg=C["card"], cursor="hand2",
                    highlightbackground=C["border"], highlightthickness=1)
    card.pack(fill="both", expand=True, pady=(5, 0))

    body = tk.Frame(card, bg=C["card"], padx=24, pady=20)
    body.pack(fill="both", expand=True)

    # Icon circle (tinted bg)
    circle = tk.Frame(body, bg=tint, padx=10, pady=8)
    circle.pack(anchor="w")
    tk.Label(circle, text=emoji, font=("Segoe UI Emoji", 24),
             bg=tint, fg=color).pack()

    tk.Label(body, text=title, font=("Segoe UI", 14, "bold"),
             bg=C["card"], fg=C["text"]).pack(anchor="w", pady=(12, 3))

    tk.Label(body, text=desc, font=("Segoe UI", 9),
             bg=C["card"], fg=C["muted"],
             wraplength=260, justify="left").pack(anchor="w")

    # Open button
    open_frame = tk.Frame(body, bg=color, pady=0)
    open_frame.pack(anchor="w", pady=(14, 2))
    open_lbl = tk.Label(open_frame, text=f"  Open {title}  →  ",
                         font=("Segoe UI", 9, "bold"),
                         bg=color, fg="white", padx=4, pady=5, cursor="hand2")
    open_lbl.pack()

    # ── Hover: tint the card ─────────────────────────────────
    all_inner = _all_desc(body) + [body]

    def _press(_e):
        # Brief darken on click = press feedback
        card.config(bg=tint)
        body.config(bg=tint)
        card.after(120, lambda: [card.config(bg=C["card"]), body.config(bg=C["card"]),
                                  cmd()])

    def _enter(_e):
        card.config(bg=tint)
        body.config(bg=tint)
        for w in all_inner:
            if w is circle or w is open_frame or w is open_lbl: continue
            try: w.config(bg=tint)
            except Exception: pass

    def _leave(_e):
        card.config(bg=C["card"])
        body.config(bg=C["card"])
        for w in all_inner:
            if w is circle or w is open_frame or w is open_lbl: continue
            try: w.config(bg=C["card"])
            except Exception: pass

    for w in [card, body, outer] + all_inner:
        w.bind("<Button-1>", _press)
        w.bind("<Enter>",    _enter)
        w.bind("<Leave>",    _leave)

    # Open-button hover darkens further
    open_lbl.bind("<Enter>", lambda _: open_lbl.config(bg=hover_color))
    open_lbl.bind("<Leave>", lambda _: open_lbl.config(bg=color))
    open_lbl.bind("<Button-1>", lambda _: cmd())
    open_frame.bind("<Button-1>", lambda _: cmd())


def _all_desc(widget):
    ch = list(widget.winfo_children())
    for c in widget.winfo_children():
        ch.extend(_all_desc(c))
    return ch
