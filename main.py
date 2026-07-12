import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import tkinter as tk
import hashlib
import datetime

from db.models import create_tables
from db.database import connect_db

from paths import resource_path

LOGO_PATH = resource_path("assets", "logo.jpeg")


def _load_logo(size):
    """Returns a Tk-compatible PhotoImage of the brand logo at `size`,
    or None if Pillow / the asset isn't available (caller falls back to text)."""
    try:
        from PIL import Image, ImageTk
        img = Image.open(LOGO_PATH).convert("RGBA").resize(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


def _fade_in(root, steps=12, delay=15):
    """Gentle window fade-in on open — cheap first-impression polish."""
    try:
        root.attributes("-alpha", 0.0)
    except tk.TclError:
        return  # platform doesn't support window alpha; skip silently
    def step(n):
        try:
            root.attributes("-alpha", min(1.0, n / steps))
        except tk.TclError:
            return
        if n < steps:
            root.after(delay, lambda: step(n + 1))
    step(1)


def _vgradient(canvas, w, h, top, bottom):
    """Paint a top-to-bottom color gradient onto `canvas` (used for subtle
    panel backgrounds — plain Tkinter has no native gradient fill)."""
    tr, tg, tb = int(top[1:3], 16), int(top[3:5], 16), int(top[5:7], 16)
    br, bg_, bb = int(bottom[1:3], 16), int(bottom[3:5], 16), int(bottom[5:7], 16)
    steps = max(1, h)
    for i in range(steps):
        f = i / steps
        r = int(tr + (br - tr) * f)
        g = int(tg + (bg_ - tg) * f)
        b = int(tb + (bb - tb) * f)
        canvas.create_line(0, i, w, i, fill=f"#{r:02x}{g:02x}{b:02x}")


# ── Shake on wrong password ────────────────────────────────────
def _shake(widget, root, times=7, distance=14):
    ox, oy = widget.winfo_x(), widget.winfo_y()
    def step(n):
        if n == 0:
            widget.place(x=ox, y=oy)
            return
        widget.place(x=ox + (distance if n % 2 == 0 else -distance), y=oy)
        root.after(38, lambda: step(n - 1))
    step(times)


def run_login():
    root = tk.Tk()
    root.title("Coding Now | Gurukul of AI — Login")
    root.state("zoomed")            # maximized full screen
    root.configure(bg="#0d1b2a")
    root.resizable(True, True)

    # ═══════════════════════════════════════════════════════════
    # LEFT PANEL  (fills 42 % of screen, no inner card)
    # ═══════════════════════════════════════════════════════════
    left = tk.Canvas(root, bg="#13293f", highlightthickness=0)
    left.place(relx=0, rely=0, relwidth=0.42, relheight=1)
    root.update_idletasks()
    _vgradient(left, left.winfo_width(), left.winfo_height(), "#13293f", "#0d1b2a")

    # ── Top-left logo bar ─────────────────────────────────────
    logo_bar = tk.Frame(left, bg="#0d1b2a", pady=16, padx=20)
    logo_bar.place(relx=0, rely=0, relwidth=1, height=70)

    small_logo_img = _load_logo((44, 44))
    if small_logo_img:
        logo_lbl = tk.Label(logo_bar, image=small_logo_img, bg="#0d1b2a")
        logo_lbl.image = small_logo_img  # keep a reference — Tk drops GC'd images
        logo_lbl.pack(side="left", padx=(0, 10))

    tk.Label(logo_bar, text="CODING NOW",
             font=("Segoe UI", 14, "bold"),
             bg="#0d1b2a", fg="#e67e22").pack(side="left")
    tk.Label(logo_bar, text="  GURUKUL OF AI",
             font=("Segoe UI", 10, "bold"),
             bg="#0d1b2a", fg="#5b8fc7").pack(side="left")

    # ── Big center branding ───────────────────────────────────
    center = tk.Frame(left, bg="#13293f")
    center.place(relx=0.08, rely=0.18, relwidth=0.84, relheight=0.50)

    big_logo_img = _load_logo((150, 150))
    if big_logo_img:
        big_logo_lbl = tk.Label(center, image=big_logo_img, bg="#13293f")
        big_logo_lbl.image = big_logo_img
        big_logo_lbl.pack(anchor="w", pady=(10, 0))
    else:
        tk.Label(center, text="🏫",
                 font=("Segoe UI Emoji", 52),
                 bg="#13293f").pack(anchor="w", pady=(10, 0))
    tk.Label(center, text="Learn the Future,\nthe Right Way.",
             font=("Segoe UI", 22, "bold"),
             bg="#13293f", fg="white",
             justify="left").pack(anchor="w", pady=(12, 6))
    tk.Label(center, text="Manage students, batches, fees\nand generate registration forms.",
             font=("Segoe UI", 11),
             bg="#13293f", fg="#93a8c3",
             justify="left").pack(anchor="w")

    # ── Divider ───────────────────────────────────────────────
    tk.Frame(left, bg="#26496b", height=1).place(
        relx=0.08, rely=0.58, relwidth=0.84)

    # ── Feature list ─────────────────────────────────────────
    features = [
        ("👨‍🎓", "Student Enrollment & Records"),
        ("🗂",  "Batch & Schedule Management"),
        ("💰",  "Fee Tracking & Payment History"),
        ("📄",  "PDF Registration Form Generator"),
    ]
    for i, (icon, text) in enumerate(features):
        row = tk.Frame(left, bg="#13293f")
        row.place(relx=0.08, rely=0.62 + i * 0.082, relwidth=0.84, height=34)

        pill = tk.Frame(row, bg="#173754", padx=8, pady=4)
        pill.pack(side="left", padx=(0, 12))
        pill_icon = tk.Label(pill, text=icon, font=("Segoe UI Emoji", 11),
                              bg="#173754")
        pill_icon.pack()

        txt_lbl = tk.Label(row, text=text, font=("Segoe UI", 10),
                            bg="#13293f", fg="#cbd5e1")
        txt_lbl.pack(side="left")

        # Subtle highlight on hover — small, cheap touch of interactivity
        # instead of these rows being purely static/inert.
        def _f_enter(_e, p=pill, pi=pill_icon, t=txt_lbl):
            p.config(bg="#20456b"); pi.config(bg="#20456b"); t.config(fg="white")
        def _f_leave(_e, p=pill, pi=pill_icon, t=txt_lbl):
            p.config(bg="#173754"); pi.config(bg="#173754"); t.config(fg="#cbd5e1")
        for w in (row, pill, pill_icon, txt_lbl):
            w.bind("<Enter>", _f_enter)
            w.bind("<Leave>", _f_leave)

    # ── Bottom badge ──────────────────────────────────────────
    ver = tk.Frame(left, bg="#0d1b2a", padx=14, pady=8)
    ver.place(relx=0.08, rely=0.95, relwidth=0.84, anchor="w")
    tk.Label(ver, text="v 1.0  ·  Python + Tkinter + SQLite",
             font=("Segoe UI", 8), bg="#0d1b2a", fg="#4a6480").pack(side="left")

    hr = datetime.datetime.now().hour
    gr = "Good Morning" if hr < 12 else ("Good Afternoon" if hr < 17 else "Good Evening")
    tk.Label(ver, text=f"  |  {gr}!",
             font=("Segoe UI", 8), bg="#0d1b2a", fg="#4a6480").pack(side="left")

    # ═══════════════════════════════════════════════════════════
    # RIGHT PANEL  — white login form
    # ═══════════════════════════════════════════════════════════
    right = tk.Frame(root, bg="white")
    right.place(relx=0.42, rely=0, relwidth=0.58, relheight=1)

    # Thin orange brand border between panels
    tk.Frame(right, bg="#e67e22", width=3).pack(side="left", fill="y")

    form_area = tk.Frame(right, bg="white")
    form_area.pack(side="left", fill="both", expand=True)

    # Center the form vertically and horizontally
    form = tk.Frame(form_area, bg="white")
    form.place(relx=0.5, rely=0.5, anchor="center", width=460)

    # ── Welcome ───────────────────────────────────────────────
    tk.Label(form, text="Welcome Back",
             font=("Segoe UI", 30, "bold"),
             bg="white", fg="#0f172a").pack(anchor="w", pady=(6, 0))
    tk.Label(form, text="Sign in to continue to your dashboard",
             font=("Segoe UI", 11),
             bg="white", fg="#94a3b8").pack(anchor="w", pady=(4, 30))

    # ── Email ─────────────────────────────────────────────────
    def _label(text):
        tk.Label(form, text=text, font=("Segoe UI", 10, "bold"),
                 bg="white", fg="#374151").pack(anchor="w")

    def _input_field(show=None):
        outer = tk.Frame(form, bg="#e2e8f0",
                         highlightbackground="#e2e8f0", highlightthickness=2)
        outer.pack(fill="x", pady=(6, 18))
        inner = tk.Frame(outer, bg="white")
        inner.pack(fill="both", padx=2, pady=2)
        e = tk.Entry(inner, font=("Segoe UI", 13), relief="flat",
                     bg="white", fg="#1e293b", insertbackground="#e67e22")
        if show:
            e.config(show=show)
        e.pack(side="left", fill="x", expand=True, ipady=11, padx=12)
        e.bind("<FocusIn>",  lambda _: outer.config(highlightbackground="#e67e22"))
        e.bind("<FocusOut>", lambda _: outer.config(highlightbackground="#e2e8f0"))
        return outer, e, inner

    _label("📧  Email Address")
    email_outer, email_entry, _ = _input_field()
    email_entry.insert(0, "admin@school.com")
    email_entry.focus_set()

    _label("🔒  Password")
    pass_outer = tk.Frame(form, bg="#e2e8f0",
                           highlightbackground="#e2e8f0", highlightthickness=2)
    pass_outer.pack(fill="x", pady=(6, 6))
    pass_inner_f = tk.Frame(pass_outer, bg="white")
    pass_inner_f.pack(fill="both", padx=2, pady=2)
    pass_entry = tk.Entry(pass_inner_f, font=("Segoe UI", 13), relief="flat",
                           bg="white", fg="#1e293b",
                           insertbackground="#e67e22", show="•")
    pass_entry.pack(side="left", fill="x", expand=True, ipady=11, padx=12)
    pass_entry.bind("<FocusIn>",  lambda _: pass_outer.config(highlightbackground="#e67e22"))
    pass_entry.bind("<FocusOut>", lambda _: pass_outer.config(highlightbackground="#e2e8f0"))

    show_var = tk.BooleanVar(value=False)
    def _toggle():
        show_var.set(not show_var.get())
        pass_entry.config(show="" if show_var.get() else "•")
        eye_btn.config(text="🙈" if show_var.get() else "👁")
    eye_btn = tk.Button(pass_inner_f, text="👁", command=_toggle,
                         font=("Segoe UI Emoji", 13), bg="white",
                         relief="flat", bd=0, cursor="hand2", padx=8)
    eye_btn.pack(side="right")
    eye_btn.bind("<Enter>", lambda _: eye_btn.config(bg="#f1f5f9"))
    eye_btn.bind("<Leave>", lambda _: eye_btn.config(bg="white"))

    # ── Error ─────────────────────────────────────────────────
    # A tinted box that only takes up space once there's actually an
    # error to show, instead of a bare label always reserving a line.
    err_box = tk.Frame(form, bg="white")
    err_box.pack(fill="x")
    err_var = tk.StringVar()
    err_lbl = tk.Label(err_box, textvariable=err_var, fg="#b91c1c", bg="#fef2f2",
                        font=("Segoe UI", 9, "bold"), wraplength=420,
                        anchor="w", justify="left", padx=10, pady=7)

    def _set_error(msg):
        err_var.set(msg)
        if msg:
            err_lbl.pack(fill="x", pady=(0, 14))
        else:
            err_lbl.pack_forget()

    # ── Sign In button ────────────────────────────────────────
    sign_btn = tk.Button(form, text="Sign In  →",
                          font=("Segoe UI", 13, "bold"),
                          bg="#e67e22", fg="white", relief="flat",
                          pady=14, cursor="hand2",
                          activebackground="#c2660d", activeforeground="white")
    sign_btn.pack(fill="x", pady=(8, 0))
    sign_btn.bind("<Enter>", lambda _: sign_btn.config(bg="#c2660d")
                  if sign_btn["state"] == "normal" else None)
    sign_btn.bind("<Leave>", lambda _: sign_btn.config(bg="#e67e22")
                  if sign_btn["state"] == "normal" else None)

    # ── Divider ───────────────────────────────────────────────
    tk.Frame(form, bg="#e2e8f0", height=1).pack(fill="x", pady=22)

    # ── Default credentials box ───────────────────────────────
    cred = tk.Frame(form, bg="#f8fafc",
                    highlightbackground="#e2e8f0", highlightthickness=1,
                    padx=18, pady=14)
    cred.pack(fill="x")
    top_c = tk.Frame(cred, bg="#f8fafc")
    top_c.pack(fill="x")
    tk.Label(top_c, text="🔑", font=("Segoe UI Emoji", 11),
             bg="#f8fafc").pack(side="left")
    tk.Label(top_c, text="  Default Credentials",
             font=("Segoe UI", 10, "bold"), bg="#f8fafc",
             fg="#e67e22").pack(side="left")
    tk.Frame(cred, bg="#e2e8f0", height=1).pack(fill="x", pady=8)
    for lbl, val in [("Email", "admin@school.com"), ("Password", "admin123")]:
        r = tk.Frame(cred, bg="#f8fafc"); r.pack(fill="x", pady=2)
        tk.Label(r, text=f"{lbl}:", font=("Segoe UI", 9, "bold"),
                 bg="#f8fafc", fg="#64748b", width=9, anchor="w").pack(side="left")
        tk.Label(r, text=val, font=("Segoe UI", 9),
                 bg="#f8fafc", fg="#1e293b").pack(side="left")

    # ── Login logic ───────────────────────────────────────────
    def do_login(_event=None):
        email    = email_entry.get().strip()
        password = pass_entry.get()
        _set_error("")

        if not email or not password:
            _set_error("⚠  Please fill in both fields.")
            return

        sign_btn.config(text="Signing in…", state="disabled", bg="#94a3b8")
        root.update()

        conn = connect_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, hash_password(password))
        ).fetchone()
        conn.close()

        if user:
            root.destroy()
            from dashboard import open_dashboard
            open_dashboard(user_name=user["name"])
        else:
            sign_btn.config(text="Sign In  →", state="normal", bg="#e67e22")
            _set_error("✗  Invalid email or password. Please try again.")
            pass_entry.delete(0, tk.END)
            _shake(form, root)

    sign_btn.config(command=do_login)
    root.bind("<Return>", do_login)
    _fade_in(root)
    root.mainloop()


if __name__ == "__main__":
    create_tables()
    run_login()
