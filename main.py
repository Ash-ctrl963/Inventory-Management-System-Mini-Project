"""
Inventory Management System — Desktop App
Framework : CustomTkinter (dark mode)
Backend   : MySQL
"""

import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import date, datetime, timedelta
import db_config
import threading
import urllib.parse
import webbrowser
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import defaultdict

# ── Global theme ──────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Palette ───────────────────────────────────────────────────
C_BG        = "#1a1d2e"      # main background
C_SIDEBAR   = "#16192a"      # sidebar
C_CARD      = "#1e2235"      # card / panel
C_CARD2     = "#252840"      # slightly lighter card
C_ACCENT    = "#4f8ef7"      # blue accent
C_GREEN     = "#2ecc71"
C_RED       = "#e74c3c"
C_ORANGE    = "#e67e22"
C_PURPLE    = "#9b59b6"
C_YELLOW    = "#f1c40f"
C_TEXT      = "#e8eaf6"
C_MUTED     = "#6c7293"
C_BORDER    = "#2d3154"

# row tag colours for ttk.Treeview
TAG_EXPIRED  = "#3d1515"
TAG_EXPIRING = "#3d2e0a"
TAG_LOW      = "#2e2e0a"
TAG_OUT      = "#2a1a1a"
TAG_OK       = C_CARD


# ══════════════════════════════════════════════════════════════
#  UTILITIES
# ══════════════════════════════════════════════════════════════
def days_until(exp):
    if not exp:
        return None
    if isinstance(exp, str):
        exp = datetime.strptime(exp, "%Y-%m-%d").date()
    return (exp - date.today()).days


def expiry_str(exp):
    if not exp:
        return "—"
    d = days_until(exp)
    if d < 0:   return f"EXPIRED ({abs(d)}d ago)"
    if d == 0:  return "Expires TODAY"
    if d <= 30: return f"In {d} days"
    return str(exp)[:10]


def dark_treeview_style(name="Dark.Treeview"):
    """Create and return a dark-themed ttk.Style for Treeview."""
    import tkinter.font as tkfont
    style = ttk.Style()
    style.theme_use("default")
    style.configure(name,
        background=C_CARD, fieldbackground=C_CARD,
        foreground=C_TEXT, rowheight=32,
        font=("Helvetica", 10),
        borderwidth=0, relief="flat")
    style.configure(f"{name}.Heading",
        background=C_CARD2, foreground=C_ACCENT,
        font=("Helvetica", 10, "bold"),
        relief="flat", borderwidth=0)
    style.map(name,
        background=[("selected", C_ACCENT)],
        foreground=[("selected", "#ffffff")])
    style.map(f"{name}.Heading",
        background=[("active", C_CARD2)])
    return style


def make_table(parent, cols, widths, anchors=None, height=None):
    dark_treeview_style()
    frame = ctk.CTkFrame(parent, fg_color=C_CARD, corner_radius=10)
    vsb = ttk.Scrollbar(frame, orient="vertical")
    hsb = ttk.Scrollbar(frame, orient="horizontal")
    kw = {"height": height} if height else {}
    tree = ttk.Treeview(frame, columns=cols, show="headings",
                        style="Dark.Treeview",
                        yscrollcommand=vsb.set,
                        xscrollcommand=hsb.set, **kw)
    vsb.configure(command=tree.yview)
    hsb.configure(command=tree.xview)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    frame.grid_rowconfigure(0, weight=1)
    frame.grid_columnconfigure(0, weight=1)
    for i, (c, w) in enumerate(zip(cols, widths)):
        anc = anchors[i] if anchors else "center"
        tree.heading(c, text=c)
        tree.column(c, width=w, anchor=anc, minwidth=30)
    # tag colours
    tree.tag_configure("expired",  background=TAG_EXPIRED,  foreground="#ff8080")
    tree.tag_configure("expiring", background=TAG_EXPIRING, foreground="#ffcc55")
    tree.tag_configure("low",      background=TAG_LOW,      foreground="#ffe066")
    tree.tag_configure("out",      background=TAG_OUT,      foreground="#ff6b6b")
    tree.tag_configure("alt",      background=C_CARD2)
    return frame, tree


def sidebar_btn(parent, text, cmd, icon=""):
    full = f"{icon}  {text}" if icon else text
    b = ctk.CTkButton(parent, text=full, anchor="w",
                      fg_color="transparent", hover_color=C_CARD2,
                      text_color=C_TEXT, font=ctk.CTkFont(size=13),
                      corner_radius=8, height=42, command=cmd)
    return b


def section_label(parent, text):
    return ctk.CTkLabel(parent, text=text,
                        font=ctk.CTkFont(size=19, weight="bold"),
                        text_color=C_TEXT)


def muted_label(parent, text):
    return ctk.CTkLabel(parent, text=text,
                        font=ctk.CTkFont(size=11),
                        text_color=C_MUTED)


def accent_btn(parent, text, cmd, color=None, width=120, height=36, icon=""):
    full = f"{icon} {text}" if icon else text
    return ctk.CTkButton(parent, text=full, command=cmd,
                         fg_color=color or C_ACCENT,
                         hover_color=_darken(color or C_ACCENT),
                         font=ctk.CTkFont(size=12, weight="bold"),
                         corner_radius=8, width=width, height=height)


def _darken(hex_color):
    """Return a slightly darker shade."""
    darken_map = {C_ACCENT:"#3a75e0", C_GREEN:"#27ae60",
                  C_RED:"#c0392b", C_ORANGE:"#ca6f1e", C_PURPLE:"#7d3c98"}
    return darken_map.get(hex_color, "#333355")


def card_frame(parent, **kw):
    return ctk.CTkFrame(parent, fg_color=C_CARD, corner_radius=12, **kw)


def stat_card(parent, icon, value, label, color):
    f = ctk.CTkFrame(parent, fg_color=C_CARD, corner_radius=14,
                     border_width=1, border_color=C_BORDER)
    ctk.CTkFrame(f, fg_color=color, height=4, corner_radius=2).pack(fill="x")
    ctk.CTkLabel(f, text=icon, font=ctk.CTkFont(size=28)).pack(pady=(12, 2))
    ctk.CTkLabel(f, text=str(value),
                 font=ctk.CTkFont(size=28, weight="bold"),
                 text_color=C_TEXT).pack()
    ctk.CTkLabel(f, text=label,
                 font=ctk.CTkFont(size=11),
                 text_color=C_MUTED).pack(pady=(2, 14))
    return f


def form_entry(parent, label, row, var, placeholder="", width=320, show=""):
    ctk.CTkLabel(parent, text=label, font=ctk.CTkFont(size=12),
                 text_color=C_MUTED, anchor="w").grid(
        row=row*2, column=0, columnspan=2, sticky="w", padx=4, pady=(10, 1))
    e = ctk.CTkEntry(parent, textvariable=var, width=width,
                     placeholder_text=placeholder,
                     fg_color=C_CARD2, border_color=C_BORDER,
                     text_color=C_TEXT, show=show,
                     font=ctk.CTkFont(size=12))
    e.grid(row=row*2+1, column=0, columnspan=2, sticky="ew", padx=4, pady=(0, 2))
    return e


# ══════════════════════════════════════════════════════════════
#  LOGIN
# ══════════════════════════════════════════════════════════════
class LoginApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Inventory Manager")
        self.geometry("460x560")
        self.resizable(False, False)
        self.configure(fg_color=C_BG)
        self._center()
        self._build()

    def _center(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - 460) // 2
        y = (self.winfo_screenheight() - 560) // 2
        self.geometry(f"+{x}+{y}")

    def _build(self):
        # Logo area
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(pady=(50, 30))
        ctk.CTkLabel(top, text="\ud83d\udce6",
                     font=ctk.CTkFont(size=60)).pack()
        ctk.CTkLabel(top, text="Inventory Manager",
                     font=ctk.CTkFont(size=24, weight="bold"),
                     text_color=C_TEXT).pack(pady=(6, 2))
        ctk.CTkLabel(top, text="Sign in to your account",
                     font=ctk.CTkFont(size=12),
                     text_color=C_MUTED).pack()

        # Card
        card = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=16,
                             border_width=1, border_color=C_BORDER)
        card.pack(fill="x", padx=50)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=30, pady=30)

        ctk.CTkLabel(inner, text="Username",
                     font=ctk.CTkFont(size=12), text_color=C_MUTED,
                     anchor="w").pack(fill="x")
        self.user_var = ctk.StringVar()
        ctk.CTkEntry(inner, textvariable=self.user_var,
                     placeholder_text="Enter username",
                     fg_color=C_CARD2, border_color=C_BORDER,
                     text_color=C_TEXT, height=42,
                     font=ctk.CTkFont(size=13)).pack(fill="x", pady=(4, 14))

        ctk.CTkLabel(inner, text="Password",
                     font=ctk.CTkFont(size=12), text_color=C_MUTED,
                     anchor="w").pack(fill="x")
        self.pass_var = ctk.StringVar()
        self.pass_entry = ctk.CTkEntry(inner, textvariable=self.pass_var,
                     placeholder_text="Enter password",
                     fg_color=C_CARD2, border_color=C_BORDER,
                     text_color=C_TEXT, height=42, show="●",
                     font=ctk.CTkFont(size=13))
        self.pass_entry.pack(fill="x", pady=(4, 20))

        ctk.CTkButton(inner, text="LOGIN", command=self._login,
                      fg_color=C_ACCENT, hover_color="#3a75e0",
                      font=ctk.CTkFont(size=14, weight="bold"),
                      height=46, corner_radius=10).pack(fill="x")

        self.msg_lbl = ctk.CTkLabel(inner, text="",
                                     font=ctk.CTkFont(size=11),
                                     text_color=C_RED)
        self.msg_lbl.pack(pady=(10, 0))

        ctk.CTkLabel(self, text="Default: admin / admin123",
                     font=ctk.CTkFont(size=10),
                     text_color=C_MUTED).pack(pady=14)

        self.bind("<Return>", lambda _: self._login())

    def _login(self):
        u = self.user_var.get().strip()
        p = self.pass_var.get().strip()
        if not u or not p:
            self.msg_lbl.configure(text="Please enter username and password.")
            return
        try:
            user = db_config.execute_query(
                "SELECT * FROM users WHERE username=%s AND password=%s AND is_active=1",
                (u, p), fetch="one")
        except Exception as e:
            messagebox.showerror("DB Error", str(e))
            return
        if user:
            self.withdraw()
            main = MainApp(user)
            main.protocol("WM_DELETE_WINDOW", lambda: (main.destroy(), self.destroy()))
            main.mainloop()
        else:
            self.msg_lbl.configure(text="Invalid credentials. Try again.")
            self.pass_var.set("")


# ══════════════════════════════════════════════════════════════
#  MAIN APP WINDOW
# ══════════════════════════════════════════════════════════════
class MainApp(ctk.CTk):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.title(f"Inventory Manager  ·  {self.user['full_name'] or self.user['username']}")
        self.geometry("1340x800")
        self.minsize(1100, 680)
        self.configure(fg_color=C_BG)
        self._build_layout()
        self._startup_alerts()
        self._navigate("dashboard")

    def _build_layout(self):
        # ── Sidebar ──────────────────────────────────────────
        self.sidebar = ctk.CTkFrame(self, fg_color=C_SIDEBAR,
                                    corner_radius=0, width=230)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Logo
        logo_f = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_f.pack(fill="x", padx=18, pady=(24, 8))
        ctk.CTkLabel(logo_f, text="\ud83d\udce6", font=ctk.CTkFont(size=28)).pack(side="left")
        ctk.CTkLabel(logo_f, text=" InvManager",
                     font=ctk.CTkFont(size=17, weight="bold"),
                     text_color=C_TEXT).pack(side="left")

        ctk.CTkFrame(self.sidebar, fg_color=C_BORDER, height=1,
                     corner_radius=0).pack(fill="x", padx=16, pady=8)

        # User chip
        uc = ctk.CTkFrame(self.sidebar, fg_color=C_CARD2, corner_radius=10)
        uc.pack(fill="x", padx=14, pady=(0, 16))
        ctk.CTkLabel(uc, text=f"\ud83d\udc64  {self.user['full_name'] or self.user['username']}",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=C_TEXT).pack(anchor="w", padx=12, pady=(8, 2))
        role_colors = {"admin": C_PURPLE, "manager": C_ACCENT, "staff": C_GREEN}
        role_c = role_colors.get(self.user["role"], C_MUTED)
        ctk.CTkLabel(uc, text=f"● {self.user['role'].capitalize()}",
                     font=ctk.CTkFont(size=11),
                     text_color=role_c).pack(anchor="w", padx=12, pady=(0, 8))

        # Nav items
        self.nav_btns = {}
        nav = [
            ("\ud83c\udfe0", "Dashboard",        "dashboard"),
            ("\ud83d\udce6", "Products",          "products"),
            ("\ud83d\uded2", "Point of Sale",     "pos"),
            ("\ud83d\udccb", "Purchase Orders",   "purchase_orders"),
            ("\ud83d\udcca", "Sales History",     "sales_history"),
            ("\ud83d\udcc8", "Sales Analytics",   "analytics"),
            ("⚠️", "Alerts",            "alerts"),
            ("\ud83e\udd16", "AI Companion",      "ai_companion"),
            ("\ud83d\udc65", "Users",             "users"),
        ]
        for icon, label, key in nav:
            b = sidebar_btn(self.sidebar, label, lambda k=key: self._navigate(k), icon=icon)
            b.pack(fill="x", padx=10, pady=2)
            self.nav_btns[key] = b

        # Spacer + logout
        ctk.CTkFrame(self.sidebar, fg_color="transparent").pack(fill="y", expand=True)
        ctk.CTkFrame(self.sidebar, fg_color=C_BORDER, height=1,
                     corner_radius=0).pack(fill="x", padx=16, pady=8)
        ctk.CTkButton(self.sidebar, text="\ud83d\udeaa  Logout",
                      anchor="w", fg_color="transparent",
                      hover_color="#3d0f0f",
                      text_color=C_RED,
                      font=ctk.CTkFont(size=13),
                      corner_radius=8, height=42,
                      command=self._logout).pack(fill="x", padx=10, pady=(0, 16))

        # ── Content ──────────────────────────────────────────
        self.content = ctk.CTkFrame(self, fg_color=C_BG, corner_radius=0)
        self.content.pack(side="left", fill="both", expand=True)

    def _navigate(self, key):
        # Highlight active nav
        for k, b in self.nav_btns.items():
            b.configure(fg_color=C_ACCENT if k == key else "transparent",
                        text_color="#ffffff" if k == key else C_TEXT)
        # Clear content
        for w in self.content.winfo_children():
            w.destroy()
        pages = {
            "dashboard":       DashboardPage,
            "products":        ProductsPage,
            "pos":             POSPage,
            "purchase_orders": PurchaseOrdersPage,
            "sales_history":   SalesHistoryPage,
            "analytics":       SalesAnalyticsPage,
            "alerts":          AlertsPage,
            "ai_companion":    AICompanionPage,
            "users":           UsersPage,
        }
        pages[key](self.content, self.user, self).pack(fill="both", expand=True)

    def _startup_alerts(self):
        try:
            exp = db_config.execute_query(
                "SELECT COUNT(*) c FROM products WHERE expiry_date < CURDATE()", fetch="one")["c"]
            low = db_config.execute_query(
                "SELECT COUNT(*) c FROM products WHERE quantity < 5", fetch="one")["c"]
        except: return
        msgs = []
        if exp: msgs.append(f"\ud83d\udea8 {exp} product(s) have EXPIRED")
        if low: msgs.append(f"⚠️ {low} product(s) are LOW on stock (< 5)")
        if msgs:
            messagebox.showwarning("Inventory Alerts",
                "\n".join(msgs) + "\n\nCheck the Alerts page for details.")
        badge = " \ud83d\udd34" if (exp + low) > 0 else ""
        self.nav_btns["alerts"].configure(text=f"⚠️  Alerts{badge}")

    def refresh_alerts(self):
        self._startup_alerts()

    def _logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            self.destroy()
            app = LoginApp()
            app.mainloop()


# ══════════════════════════════════════════════════════════════
#  PAGE HEADER
# ══════════════════════════════════════════════════════════════
def page_header(parent, title, subtitle=""):
    hdr = ctk.CTkFrame(parent, fg_color="transparent")
    hdr.pack(fill="x", padx=28, pady=(24, 12))
    ctk.CTkLabel(hdr, text=title,
                 font=ctk.CTkFont(size=22, weight="bold"),
                 text_color=C_TEXT).pack(anchor="w")
    if subtitle:
        ctk.CTkLabel(hdr, text=subtitle,
                     font=ctk.CTkFont(size=12),
                     text_color=C_MUTED).pack(anchor="w")
    ctk.CTkFrame(parent, fg_color=C_BORDER, height=1,
                 corner_radius=0).pack(fill="x", padx=28)


# ══════════════════════════════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════════════════════════════
class DashboardPage(ctk.CTkFrame):
    def __init__(self, parent, user, app):
        super().__init__(parent, fg_color="transparent")
        self.user = user
        page_header(self, "Dashboard",
                    f"Welcome back, {self.user['full_name'] or self.user['username']}!  ·  "
                    f"{date.today().strftime('%A, %d %B %Y')}")
        self._stats()
        self._alerts_table()

    def _stats(self):
        try:
            tp  = db_config.execute_query("SELECT COUNT(*) c FROM products", fetch="one")["c"]
            low = db_config.execute_query("SELECT COUNT(*) c FROM products WHERE quantity < 5", fetch="one")["c"]
            exp = db_config.execute_query("SELECT COUNT(*) c FROM products WHERE expiry_date < CURDATE()", fetch="one")["c"]
            soon= db_config.execute_query(
                "SELECT COUNT(*) c FROM products WHERE expiry_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(),INTERVAL 30 DAY)",
                fetch="one")["c"]
            rev = db_config.execute_query(
                "SELECT COALESCE(SUM(total_amount),0) c FROM sales_orders WHERE DATE(order_date)=CURDATE()",
                fetch="one")["c"]
        except Exception as e:
            messagebox.showerror("DB", str(e)); return

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=28, pady=18)
        data = [
            ("\ud83d\udce6", tp,              "Total Products",     C_ACCENT),
            ("⚠️", low,             "Low Stock  (< 5)",   C_ORANGE),
            ("\ud83d\udea8", exp,             "Expired",            C_RED),
            ("⏳", soon,            "Expiring ≤ 30 days", C_YELLOW),
            ("\ud83d\udcb0", f"₹{rev:,.0f}", "Sales Today",        C_GREEN),
        ]
        for icon, val, lbl, clr in data:
            c = stat_card(row, icon, val, lbl, clr)
            c.pack(side="left", fill="x", expand=True, padx=6)

    def _alerts_table(self):
        ctk.CTkLabel(self, text="\ud83d\udea8  Active Alerts",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=C_TEXT).pack(anchor="w", padx=28, pady=(6, 6))

        cols = ("Alert Type", "Product", "SKU", "Stock", "Expiry", "Details")
        frm, tree = make_table(self, cols,
                               [140, 210, 110, 70, 140, 200],
                               anchors=["c","w","c","c","c","w"])
        frm.pack(fill="both", expand=True, padx=28, pady=(0, 24))

        try:
            rows = db_config.execute_query(
                """SELECT name, sku, quantity, expiry_date FROM products
                   WHERE quantity < 5
                      OR (expiry_date IS NOT NULL AND expiry_date <= DATE_ADD(CURDATE(),INTERVAL 30 DAY))
                   ORDER BY expiry_date IS NULL, expiry_date""", fetch="all")
            for r in rows:
                d   = days_until(r["expiry_date"])
                tag = ""
                if d is not None and d < 0:
                    atype = "\ud83d\udea8 EXPIRED";  detail = f"Expired {abs(d)} days ago"; tag = "expired"
                elif d is not None and d == 0:
                    atype = "⏳ TODAY";    detail = "Expires today!";             tag = "expiring"
                elif d is not None and d <= 30:
                    atype = "⏳ EXPIRING"; detail = f"Expires in {d} days";       tag = "expiring"
                else:
                    atype = ""; detail = ""
                if r["quantity"] < 5:
                    if atype: atype += " + LOW"
                    else:     atype = "⚠️ LOW STOCK"
                    detail = (detail + "  " if detail else "") + f"Only {r['quantity']} left"
                    if not tag: tag = "low"
                tree.insert("", "end",
                            values=(atype, r["name"], r["sku"],
                                    r["quantity"], expiry_str(r["expiry_date"]), detail),
                            tags=(tag,))
        except Exception as e:
            messagebox.showerror("DB", str(e))


# ══════════════════════════════════════════════════════════════
#  ALERTS PAGE
# ══════════════════════════════════════════════════════════════
class AlertsPage(ctk.CTkFrame):
    def __init__(self, parent, user, app):
        super().__init__(parent, fg_color="transparent")
        page_header(self, "⚠️  Alerts", "Products requiring immediate attention")
        self._build()

    def _build(self):
        tabs = ctk.CTkTabview(self, fg_color=C_CARD,
                               segmented_button_fg_color=C_CARD2,
                               segmented_button_selected_color=C_ACCENT,
                               segmented_button_unselected_color=C_CARD2,
                               segmented_button_selected_hover_color="#3a75e0")
        tabs.pack(fill="both", expand=True, padx=28, pady=18)

        for title in ["\ud83d\udea8 Expired", "⏳ Expiring Soon", "\ud83d\udcc9 Low Stock", "\ud83d\udced Out of Stock"]:
            tabs.add(title)

        self._expired_tab(tabs.tab("\ud83d\udea8 Expired"))
        self._expiring_tab(tabs.tab("⏳ Expiring Soon"))
        self._lowstock_tab(tabs.tab("\ud83d\udcc9 Low Stock"))
        self._outstock_tab(tabs.tab("\ud83d\udced Out of Stock"))

    def _base_table(self, parent, query, extra_cols=(), val_fn=None, tag=None, banner="", banner_color=C_RED):
        if banner:
            ctk.CTkLabel(parent, text=banner, font=ctk.CTkFont(size=12),
                         text_color=banner_color).pack(anchor="w", padx=8, pady=8)
        cols   = ("ID", "Product", "SKU", "Category", "Stock") + extra_cols
        widths = [50, 220, 110, 130, 70] + [140]*len(extra_cols)
        frm, tree = make_table(parent, cols, widths,
                               anchors=["c","w","c","c","c"]+["c"]*len(extra_cols))
        frm.pack(fill="both", expand=True, padx=6, pady=(0,10))
        try:
            rows = db_config.execute_query(query, fetch="all")
            for i, r in enumerate(rows):
                extras = val_fn(r) if val_fn else ()
                t = tag or ("alt" if i%2 else "")
                tree.insert("","end",values=(r["id"],r["name"],r["sku"],
                                             r.get("cat","—"),r["quantity"])+extras,tags=(t,))
        except Exception as e:
            messagebox.showerror("DB", str(e))
        return tree

    def _expired_tab(self, parent):
        self._base_table(parent,
            """SELECT p.id,p.name,p.sku,p.quantity,p.expiry_date,COALESCE(c.name,'—') cat
               FROM products p LEFT JOIN categories c ON p.category_id=c.id
               WHERE expiry_date < CURDATE() ORDER BY expiry_date""",
            ("Expiry Date","Days Overdue"),
            lambda r: (str(r["expiry_date"]), abs(days_until(r["expiry_date"]))),
            tag="expired",
            banner="These products are past their expiry date. Remove from sale immediately.",
            banner_color=C_RED)

    def _expiring_tab(self, parent):
        self._base_table(parent,
            """SELECT p.id,p.name,p.sku,p.quantity,p.expiry_date,COALESCE(c.name,'—') cat
               FROM products p LEFT JOIN categories c ON p.category_id=c.id
               WHERE expiry_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(),INTERVAL 30 DAY)
               ORDER BY expiry_date""",
            ("Expiry Date","Days Left"),
            lambda r: (str(r["expiry_date"]), days_until(r["expiry_date"])),
            tag="expiring",
            banner="Products expiring within 30 days — consider discounting or reordering.",
            banner_color=C_ORANGE)

    def _lowstock_tab(self, parent):
        self._base_table(parent,
            """SELECT p.id,p.name,p.sku,p.quantity,COALESCE(c.name,'—') cat,
                      COALESCE(s.name,'—') supplier
               FROM products p LEFT JOIN categories c ON p.category_id=c.id
                               LEFT JOIN suppliers  s ON p.supplier_id=s.id
               WHERE p.quantity > 0 AND p.quantity < 5 ORDER BY p.quantity""",
            ("Supplier",), lambda r: (r["supplier"],),
            tag="low",
            banner="Stock below 5 units — reorder soon.",
            banner_color=C_ORANGE)

    def _outstock_tab(self, parent):
        self._base_table(parent,
            """SELECT p.id,p.name,p.sku,p.quantity,COALESCE(c.name,'—') cat
               FROM products p LEFT JOIN categories c ON p.category_id=c.id
               WHERE p.quantity = 0 ORDER BY p.name""",
            tag="out",
            banner="Completely out of stock — no sales possible for these items.",
            banner_color=C_RED)


# ══════════════════════════════════════════════════════════════
#  PRODUCTS
# ══════════════════════════════════════════════════════════════
class ProductsPage(ctk.CTkFrame):
    def __init__(self, parent, user, app):
        super().__init__(parent, fg_color="transparent")
        self.user = user
        page_header(self, "Products", "Full product catalogue management")
        self._toolbar()
        self._table()
        self._load()

    def _toolbar(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(fill="x", padx=28, pady=10)
        accent_btn(f, "Add Product", self._add, C_GREEN, icon="＋").pack(side="left")
        accent_btn(f, "Refresh", self._load, C_ACCENT, icon="↻").pack(side="left", padx=8)

        self.search_var = ctk.StringVar()
        self.search_var.trace("w", lambda *_: self._load())
        ctk.CTkEntry(f, textvariable=self.search_var, width=260,
                     placeholder_text="\ud83d\udd0d  Search by name or SKU…",
                     fg_color=C_CARD, border_color=C_BORDER,
                     text_color=C_TEXT).pack(side="left", padx=12)

    def _table(self):
        cols = ("ID","Name","SKU","Category","Supplier","Stock","Cost ₹","Price ₹","Expiry","Status")
        frm, self.tree = make_table(self, cols,
            [50,180,100,110,140,65,90,90,130,130],
            anchors=["c","w","c","c","c","c","c","c","c","c"])
        frm.pack(fill="both", expand=True, padx=28, pady=(0,6))

        ab = ctk.CTkFrame(self, fg_color="transparent")
        ab.pack(fill="x", padx=28, pady=(0, 20))
        for txt, clr, cmd, icon in [
            ("Edit",      C_ACCENT,  self._edit,      "✏"),
            ("Delete",    C_RED,     self._delete,    "\ud83d\uddd1"),
            ("Stock In",  C_GREEN,   self._stock_in,  "＋"),
            ("Stock Out", C_ORANGE,  self._stock_out, "－"),
        ]:
            accent_btn(ab, txt, cmd, clr, icon=icon).pack(side="left", padx=(0, 8))

    def _load(self):
        self.tree.delete(*self.tree.get_children())
        q = self.search_var.get().strip()
        try:
            rows = db_config.execute_query(
                """SELECT p.id,p.name,p.sku,
                          COALESCE(c.name,'—') cat,COALESCE(s.name,'—') sup,
                          p.quantity,p.unit_price,p.selling_price,p.expiry_date
                   FROM products p
                   LEFT JOIN categories c ON p.category_id=c.id
                   LEFT JOIN suppliers  s ON p.supplier_id=s.id
                   WHERE p.name LIKE %s OR p.sku LIKE %s ORDER BY p.id""",
                (f"%{q}%",f"%{q}%"), fetch="all")
        except Exception as e:
            messagebox.showerror("DB", str(e)); return

        for i, r in enumerate(rows):
            d = days_until(r["expiry_date"])
            if d is not None and d < 0:
                status, tag = "\ud83d\udea8 EXPIRED",    "expired"
            elif d is not None and d == 0:
                status, tag = "⏳ Expires TODAY","expiring"
            elif d is not None and d <= 30:
                status, tag = f"⏳ Exp {d}d",   "expiring"
            elif r["quantity"] == 0:
                status, tag = "\ud83d\udced Out of Stock","out"
            elif r["quantity"] < 5:
                status, tag = "⚠️ Low Stock",  "low"
            else:
                status, tag = "✅ OK",          ("alt" if i%2 else "")
            self.tree.insert("","end", values=(
                r["id"], r["name"], r["sku"], r["cat"], r["sup"],
                r["quantity"], f"{r['unit_price']:.2f}",
                f"{r['selling_price']:.2f}",
                expiry_str(r["expiry_date"]), status), tags=(tag,))

    def _sel_id(self):
        s = self.tree.selection()
        if not s: messagebox.showwarning("Select","Select a product first."); return None
        return self.tree.item(s[0])["values"][0]

    def _add(self):     ProductDialog(self, self.user, cb=self._load)
    def _edit(self):
        p = self._sel_id()
        if p: ProductDialog(self, self.user, pid=p, cb=self._load)
    def _delete(self):
        p = self._sel_id()
        if not p: return
        if messagebox.askyesno("Delete","Delete this product permanently?"):
            try: db_config.execute_query("DELETE FROM products WHERE id=%s",(p,)); self._load()
            except Exception as e: messagebox.showerror("Error",str(e))
    def _stock_in(self):
        p = self._sel_id()
        if p: StockDialog(self, p, "purchase", self.user["id"], cb=self._load)
    def _stock_out(self):
        p = self._sel_id()
        if p: StockDialog(self, p, "adjustment", self.user["id"], cb=self._load)


# ── Product Dialog ────────────────────────────────────────────
class ProductDialog(ctk.CTkToplevel):
    def __init__(self, parent, user, pid=None, cb=None):
        super().__init__(parent)
        self.pid, self.cb = pid, cb
        self.title("Edit Product" if pid else "Add Product")
        self.geometry("520x680")
        self.resizable(False, False)
        self.configure(fg_color=C_BG)
        self.grab_set()
        self.cats = db_config.execute_query("SELECT id,name FROM categories ORDER BY name", fetch="all") or []
        self.sups = db_config.execute_query("SELECT id,name FROM suppliers  ORDER BY name", fetch="all") or []
        self._build()
        if pid: self._populate()

    def _build(self):
        # Scrollable area
        scroll = ctk.CTkScrollableFrame(self, fg_color=C_CARD, corner_radius=12,
                                         scrollbar_button_color=C_BORDER)
        scroll.pack(fill="both", expand=True, padx=20, pady=16)
        scroll.columnconfigure(1, weight=1)

        self.v = {}
        fields = [
            ("name",           "Product Name *",             "e.g. Paracetamol 500mg"),
            ("sku",            "SKU / Code *",               "e.g. MED-001"),
            ("barcode",        "Barcode",                    "optional"),
            ("quantity",       "Initial Quantity",           "0"),
            ("unit_price",     "Cost Price (₹) *",           "0.00"),
            ("selling_price",  "Selling Price (₹) *",        "0.00"),
            ("low_stock_alert","Low Stock Alert threshold",  "5"),
            ("expiry_date",    "Expiry Date (YYYY-MM-DD)",   "leave blank if N/A"),
        ]
        for i, (key, lbl, ph) in enumerate(fields):
            ctk.CTkLabel(scroll, text=lbl, font=ctk.CTkFont(size=12),
                         text_color=C_MUTED, anchor="w").grid(
                row=i*2, column=0, columnspan=2, sticky="w", padx=8, pady=(10,1))
            v = ctk.StringVar()
            ctk.CTkEntry(scroll, textvariable=v, placeholder_text=ph,
                         fg_color=C_CARD2, border_color=C_BORDER,
                         text_color=C_TEXT, font=ctk.CTkFont(size=12)).grid(
                row=i*2+1, column=0, columnspan=2, sticky="ew", padx=8, pady=(0,2))
            self.v[key] = v

        r = len(fields)*2
        ctk.CTkLabel(scroll, text="Category", font=ctk.CTkFont(size=12),
                     text_color=C_MUTED, anchor="w").grid(row=r, column=0, columnspan=2, sticky="w", padx=8, pady=(10,1))
        self.v["category"] = ctk.StringVar()
        ctk.CTkOptionMenu(scroll, variable=self.v["category"],
                          values=[c["name"] for c in self.cats] or ["—"],
                          fg_color=C_CARD2, button_color=C_ACCENT,
                          text_color=C_TEXT).grid(row=r+1, column=0, columnspan=2, sticky="ew", padx=8, pady=(0,2))

        ctk.CTkLabel(scroll, text="Supplier", font=ctk.CTkFont(size=12),
                     text_color=C_MUTED, anchor="w").grid(row=r+2, column=0, columnspan=2, sticky="w", padx=8, pady=(10,1))
        self.v["supplier"] = ctk.StringVar()
        ctk.CTkOptionMenu(scroll, variable=self.v["supplier"],
                          values=[s["name"] for s in self.sups] or ["—"],
                          fg_color=C_CARD2, button_color=C_ACCENT,
                          text_color=C_TEXT).grid(row=r+3, column=0, columnspan=2, sticky="ew", padx=8, pady=(0,2))

        ctk.CTkLabel(scroll, text="Description", font=ctk.CTkFont(size=12),
                     text_color=C_MUTED, anchor="w").grid(row=r+4, column=0, columnspan=2, sticky="w", padx=8, pady=(10,1))
        self.desc = ctk.CTkTextbox(scroll, height=70, fg_color=C_CARD2,
                                    border_color=C_BORDER, text_color=C_TEXT,
                                    font=ctk.CTkFont(size=12))
        self.desc.grid(row=r+5, column=0, columnspan=2, sticky="ew", padx=8, pady=(0,10))

        # Buttons
        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(fill="x", padx=20, pady=(0, 16))
        accent_btn(bf, "Cancel", self.destroy, C_RED).pack(side="right", padx=(8,0))
        accent_btn(bf, "Save Product", self._save, C_GREEN, icon="\ud83d\udcbe").pack(side="right")

    def _populate(self):
        p = db_config.execute_query(
            """SELECT p.*,c.name cat_name,s.name sup_name FROM products p
               LEFT JOIN categories c ON p.category_id=c.id
               LEFT JOIN suppliers  s ON p.supplier_id=s.id
               WHERE p.id=%s""", (self.pid,), fetch="one")
        if not p: return
        for k in ("name","sku","barcode","quantity","unit_price","selling_price","low_stock_alert"):
            self.v[k].set(str(p.get(k,"") or ""))
        if p.get("expiry_date"): self.v["expiry_date"].set(str(p["expiry_date"])[:10])
        if p.get("cat_name"):    self.v["category"].set(p["cat_name"])
        if p.get("sup_name"):    self.v["supplier"].set(p["sup_name"])
        if p.get("description"): self.desc.insert("1.0", p["description"])

    def _save(self):
        name = self.v["name"].get().strip()
        sku  = self.v["sku"].get().strip()
        up   = self.v["unit_price"].get().strip()
        sp   = self.v["selling_price"].get().strip()
        if not all([name, sku, up, sp]):
            messagebox.showwarning("Required", "Name, SKU, Cost Price and Selling Price are required.", parent=self)
            return
        try:
            up, sp  = float(up), float(sp)
            qty     = int(self.v["quantity"].get() or 0)
            alert   = int(self.v["low_stock_alert"].get() or 5)
        except ValueError:
            messagebox.showwarning("Format", "Prices and quantity must be numbers.", parent=self); return
        exp = self.v["expiry_date"].get().strip() or None
        if exp:
            try: datetime.strptime(exp, "%Y-%m-%d")
            except: messagebox.showwarning("Date","Use YYYY-MM-DD format.",parent=self); return
        cat_id  = next((c["id"] for c in self.cats if c["name"]==self.v["category"].get()), None)
        sup_id  = next((s["id"] for s in self.sups if s["name"]==self.v["supplier"].get()), None)
        barcode = self.v["barcode"].get().strip() or None
        desc    = self.desc.get("1.0","end-1c").strip()
        try:
            if self.pid:
                db_config.execute_query(
                    """UPDATE products SET name=%s,sku=%s,barcode=%s,category_id=%s,supplier_id=%s,
                       quantity=%s,unit_price=%s,selling_price=%s,low_stock_alert=%s,
                       expiry_date=%s,description=%s WHERE id=%s""",
                    (name,sku,barcode,cat_id,sup_id,qty,up,sp,alert,exp,desc,self.pid))
            else:
                db_config.execute_query(
                    """INSERT INTO products(name,sku,barcode,category_id,supplier_id,quantity,
                       unit_price,selling_price,low_stock_alert,expiry_date,description)
                       VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (name,sku,barcode,cat_id,sup_id,qty,up,sp,alert,exp,desc))
        except Exception as e:
            messagebox.showerror("DB Error", str(e), parent=self); return
        if self.cb: self.cb()
        self.destroy()


# ── Stock Dialog ──────────────────────────────────────────────
class StockDialog(ctk.CTkToplevel):
    def __init__(self, parent, pid, txn_type, uid, cb=None):
        super().__init__(parent)
        self.pid, self.txn_type, self.uid, self.cb = pid, txn_type, uid, cb
        self.title("Stock In" if txn_type=="purchase" else "Adjust Stock")
        self.geometry("380x310")
        self.resizable(False, False)
        self.configure(fg_color=C_BG)
        self.grab_set()
        self._build()

    def _build(self):
        p = db_config.execute_query("SELECT name,quantity FROM products WHERE id=%s",(self.pid,),fetch="one")
        card = card_frame(self)
        card.pack(fill="both", expand=True, padx=20, pady=20)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=24, pady=20)

        ctk.CTkLabel(inner, text=p["name"], font=ctk.CTkFont(size=14,weight="bold"),
                     text_color=C_TEXT).pack(anchor="w")
        ctk.CTkLabel(inner, text=f"Current stock: {p['quantity']}",
                     font=ctk.CTkFont(size=11), text_color=C_MUTED).pack(anchor="w", pady=(2,16))

        self.qty_v   = ctk.StringVar()
        self.price_v = ctk.StringVar()
        self.notes_v = ctk.StringVar()
        for lbl, var, ph in [("Quantity *", self.qty_v, "e.g. 10"),
                              ("Unit Price ₹", self.price_v, "optional"),
                              ("Notes", self.notes_v, "optional")]:
            ctk.CTkLabel(inner, text=lbl, font=ctk.CTkFont(size=12),
                         text_color=C_MUTED, anchor="w").pack(fill="x")
            ctk.CTkEntry(inner, textvariable=var, placeholder_text=ph,
                         fg_color=C_CARD2, border_color=C_BORDER,
                         text_color=C_TEXT).pack(fill="x", pady=(2,10))

        bf = ctk.CTkFrame(inner, fg_color="transparent")
        bf.pack(fill="x", pady=(4,0))
        accent_btn(bf, "Cancel",  self.destroy, C_RED).pack(side="right", padx=(8,0))
        accent_btn(bf, "Confirm", self._save,   C_GREEN, icon="✔").pack(side="right")

    def _save(self):
        try:
            qty = int(self.qty_v.get()); assert qty > 0
        except: messagebox.showwarning("Qty","Enter valid positive quantity.",parent=self); return
        price = None
        if self.price_v.get().strip():
            try: price = float(self.price_v.get())
            except: messagebox.showwarning("Price","Enter valid price.",parent=self); return
        delta = qty if self.txn_type=="purchase" else -qty
        try:
            cur = db_config.execute_query("SELECT quantity FROM products WHERE id=%s",(self.pid,),fetch="one")
            new_q = cur["quantity"] + delta
            if new_q < 0: messagebox.showwarning("Stock","Not enough stock!",parent=self); return
            db_config.execute_query("UPDATE products SET quantity=%s WHERE id=%s",(new_q,self.pid))
            db_config.execute_query(
                """INSERT INTO stock_transactions(product_id,transaction_type,quantity,unit_price,notes,created_by)
                   VALUES(%s,%s,%s,%s,%s,%s)""",
                (self.pid,self.txn_type,qty,price,self.notes_v.get().strip(),self.uid))
        except Exception as e: messagebox.showerror("Error",str(e),parent=self); return
        if self.cb: self.cb()
        self.destroy()


# ══════════════════════════════════════════════════════════════
#  POINT OF SALE
# ══════════════════════════════════════════════════════════════
class POSPage(ctk.CTkFrame):
    def __init__(self, parent, user, app):
        super().__init__(parent, fg_color="transparent")
        self.user = user
        self.app  = app
        self.cart = []
        page_header(self, "\ud83d\uded2  Point of Sale", "Real-time sales processing")
        self._build()

    def _build(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=24, pady=12)
        main.columnconfigure(0, weight=3)
        main.columnconfigure(1, weight=2)
        main.rowconfigure(0, weight=1)

        # ── LEFT ──────────────────────────────────────────────
        left = card_frame(main)
        left.grid(row=0, column=0, sticky="nsew", padx=(0,12))

        # Search bar
        sf = ctk.CTkFrame(left, fg_color="transparent")
        sf.pack(fill="x", padx=16, pady=12)
        ctk.CTkLabel(sf, text="Product:", font=ctk.CTkFont(size=12),
                     text_color=C_MUTED).pack(side="left")
        self.pos_search = ctk.StringVar()
        self.pos_search.trace("w", lambda *_: self._search())
        ctk.CTkEntry(sf, textvariable=self.pos_search, width=240,
                     placeholder_text="Search by name or SKU…",
                     fg_color=C_CARD2, border_color=C_BORDER,
                     text_color=C_TEXT).pack(side="left", padx=8)
        ctk.CTkLabel(sf, text="Qty:", font=ctk.CTkFont(size=12), text_color=C_MUTED).pack(side="left",padx=(10,4))
        self.pos_qty = ctk.StringVar(value="1")
        ctk.CTkEntry(sf, textvariable=self.pos_qty, width=55,
                     fg_color=C_CARD2, border_color=C_BORDER, text_color=C_TEXT).pack(side="left")
        accent_btn(sf, "Add", self._add_to_cart, C_GREEN, width=80, icon="＋").pack(side="left", padx=10)

        # Search results
        ctk.CTkLabel(left, text="Search Results",
                     font=ctk.CTkFont(size=11,weight="bold"),
                     text_color=C_MUTED).pack(anchor="w", padx=16, pady=(0,4))
        p_cols = ("ID","Product","SKU","Stock","Price ₹","Expiry")
        pf, self.prod_tree = make_table(left, p_cols, [50,210,100,60,90,120],
                                        anchors=["c","w","c","c","c","c"], height=6)
        pf.pack(fill="x", padx=16, pady=(0,10))
        self.prod_tree.bind("<Double-1>", lambda _: self._add_to_cart())

        # Cart header
        ctk.CTkLabel(left, text="\ud83d\uded2  Cart",
                     font=ctk.CTkFont(size=14,weight="bold"),
                     text_color=C_TEXT).pack(anchor="w", padx=16, pady=(6,4))
        c_cols = ("Product","Qty","Unit Price","Subtotal")
        cf, self.cart_tree = make_table(left, c_cols, [260,60,100,100],
                                        anchors=["w","c","c","c"])
        cf.pack(fill="both", expand=True, padx=16, pady=(0,8))

        cr = ctk.CTkFrame(left, fg_color="transparent")
        cr.pack(fill="x", padx=16, pady=(0,14))
        accent_btn(cr, "Remove Selected", self._remove_item, C_RED, icon="✖").pack(side="left")
        accent_btn(cr, "Clear Cart",      self._clear_cart,  C_ORANGE, icon="\ud83d\uddd1").pack(side="left", padx=8)

        # ── RIGHT ─────────────────────────────────────────────
        right = card_frame(main)
        right.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(right, text="Order Summary",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=C_TEXT).pack(pady=(20,8))
        ctk.CTkFrame(right, fg_color=C_BORDER, height=1, corner_radius=0).pack(fill="x", padx=20)

        inf = ctk.CTkFrame(right, fg_color="transparent")
        inf.pack(fill="x", padx=20, pady=16)

        ctk.CTkLabel(inf, text="Customer Name", font=ctk.CTkFont(size=12), text_color=C_MUTED, anchor="w").pack(fill="x")
        self.cust_var = ctk.StringVar()
        ctk.CTkEntry(inf, textvariable=self.cust_var, placeholder_text="Walk-in Customer",
                     fg_color=C_CARD2, border_color=C_BORDER, text_color=C_TEXT).pack(fill="x", pady=(4,8))

        ctk.CTkLabel(inf, text="📱 WhatsApp Number (optional)", font=ctk.CTkFont(size=12), text_color=C_MUTED, anchor="w").pack(fill="x")
        self.phone_entry = ctk.CTkEntry(inf, placeholder_text="e.g. 919876543210 (with country code)",
                     fg_color=C_CARD2, border_color=C_BORDER, text_color=C_TEXT)
        self.phone_entry.pack(fill="x", pady=(4,12))

        ctk.CTkLabel(inf, text="Discount (₹)", font=ctk.CTkFont(size=12), text_color=C_MUTED, anchor="w").pack(fill="x")
        self.disc_var = ctk.StringVar(value="0")
        self.disc_var.trace("w", lambda *_: self._update_totals())
        ctk.CTkEntry(inf, textvariable=self.disc_var,
                     fg_color=C_CARD2, border_color=C_BORDER, text_color=C_TEXT).pack(fill="x", pady=(4,16))

        ctk.CTkFrame(inf, fg_color=C_BORDER, height=1, corner_radius=0).pack(fill="x", pady=4)

        for lbl, attr, clr, size in [
            ("Subtotal",  "sub_lbl", C_MUTED, 13),
            ("Discount",  "dis_lbl", C_ORANGE, 13),
            ("TOTAL",     "tot_lbl", C_GREEN,  22),
        ]:
            rf = ctk.CTkFrame(inf, fg_color="transparent")
            rf.pack(fill="x", pady=3)
            ctk.CTkLabel(rf, text=lbl+":", font=ctk.CTkFont(size=12), text_color=C_MUTED).pack(side="left")
            lv = ctk.CTkLabel(rf, text="₹0.00",
                              font=ctk.CTkFont(size=size, weight="bold"),
                              text_color=clr)
            lv.pack(side="right")
            setattr(self, attr, lv)

        ctk.CTkFrame(inf, fg_color=C_BORDER, height=1, corner_radius=0).pack(fill="x", pady=12)

        accent_btn(right, "\ud83d\udcb0  PROCESS SALE", self._process_sale,
                   C_GREEN, width=260, height=50).pack(padx=20, pady=(0,10))
        btn_row = ctk.CTkFrame(right, fg_color="transparent")
        btn_row.pack(padx=20, pady=(0,10))
        accent_btn(btn_row, "\ud83d\udda8 Receipt", self._print_receipt,
                   C_ACCENT, width=124, height=38).pack(side="left", padx=(0,4))
        accent_btn(btn_row, "\ud83d\udcf2 WhatsApp", self._send_whatsapp,
                   C_GREEN, width=124, height=38).pack(side="left")

        self._search()

    def _search(self):
        self.prod_tree.delete(*self.prod_tree.get_children())
        q = self.pos_search.get().strip()
        try:
            rows = db_config.execute_query(
                """SELECT id,name,sku,quantity,selling_price,expiry_date FROM products
                   WHERE (name LIKE %s OR sku LIKE %s) AND quantity > 0
                   ORDER BY name LIMIT 60""",
                (f"%{q}%",f"%{q}%"), fetch="all")
        except: return
        for r in rows:
            d = days_until(r["expiry_date"])
            tag = "expired" if (d is not None and d < 0) else ""
            self.prod_tree.insert("","end",values=(
                r["id"],r["name"],r["sku"],r["quantity"],
                f"{r['selling_price']:.2f}",expiry_str(r["expiry_date"])),tags=(tag,))

    def _add_to_cart(self):
        sel = self.prod_tree.selection()
        if not sel: messagebox.showwarning("Select","Pick a product.",parent=self); return
        v = self.prod_tree.item(sel[0])["values"]
        pid, name, sku, stock, price = v[0], v[1], v[2], v[3], float(v[4])
        try: qty = int(self.pos_qty.get()); assert qty > 0
        except: messagebox.showwarning("Qty","Valid qty required.",parent=self); return

        pd = db_config.execute_query("SELECT expiry_date FROM products WHERE id=%s",(pid,),fetch="one")
        d  = days_until(pd["expiry_date"])
        if d is not None and d < 0:
            if not messagebox.askyesno("Expired",f"'{name}' is EXPIRED!\nAdd anyway?",parent=self): return

        total_cart = sum(i["qty"] for i in self.cart if i["pid"]==pid)
        if total_cart + qty > stock:
            messagebox.showwarning("Stock",f"Only {stock} in stock.",parent=self); return

        for item in self.cart:
            if item["pid"]==pid: item["qty"]+=qty; self._refresh_cart(); return
        self.cart.append({"pid":pid,"name":name,"qty":qty,"price":price})
        self._refresh_cart()

    def _refresh_cart(self):
        self.cart_tree.delete(*self.cart_tree.get_children())
        for i, item in enumerate(self.cart):
            sub = item["qty"]*item["price"]
            self.cart_tree.insert("","end",
                values=(item["name"],item["qty"],f"₹{item['price']:.2f}",f"₹{sub:.2f}"),
                tags=("alt" if i%2 else ""))
        self._update_totals()

    def _update_totals(self):
        sub = sum(i["qty"]*i["price"] for i in self.cart)
        try:    disc = float(self.disc_var.get() or 0)
        except: disc = 0
        total = max(0, sub - disc)
        self.sub_lbl.configure(text=f"₹{sub:.2f}")
        self.dis_lbl.configure(text=f"₹{disc:.2f}")
        self.tot_lbl.configure(text=f"₹{total:.2f}")

    def _remove_item(self):
        sel = self.cart_tree.selection()
        if sel:
            del self.cart[self.cart_tree.index(sel[0])]
            self._refresh_cart()

    def _clear_cart(self):
        if self.cart and messagebox.askyesno("Clear","Clear entire cart?",parent=self):
            self.cart.clear(); self._refresh_cart()

    def _process_sale(self):
        if not self.cart: messagebox.showwarning("Empty","Cart is empty.",parent=self); return
        try:    disc = float(self.disc_var.get() or 0)
        except: disc = 0
        sub   = sum(i["qty"]*i["price"] for i in self.cart)
        total = max(0, sub - disc)
        cust  = self.cust_var.get().strip() or "Walk-in Customer"
        if not messagebox.askyesno("Confirm",
            f"Customer: {cust}\nItems: {len(self.cart)}\nTotal: ₹{total:.2f}\n\nProcess sale?",parent=self): return
        try:
            oid = db_config.execute_query(
                "INSERT INTO sales_orders(customer_name,total_amount,discount,created_by) VALUES(%s,%s,%s,%s)",
                (cust,total,disc,self.user["id"]))
            for item in self.cart:
                db_config.execute_query(
                    "INSERT INTO sales_order_items(sales_order_id,product_id,product_name,quantity,unit_price) VALUES(%s,%s,%s,%s,%s)",
                    (oid,item["pid"],item["name"],item["qty"],item["price"]))
                db_config.execute_query(
                    "UPDATE products SET quantity=quantity-%s WHERE id=%s",
                    (item["qty"],item["pid"]))
                db_config.execute_query(
                    "INSERT INTO stock_transactions(product_id,transaction_type,quantity,unit_price,reference_id,created_by) VALUES(%s,'sale',%s,%s,%s,%s)",
                    (item["pid"],item["qty"],item["price"],oid,self.user["id"]))
        except Exception as e: messagebox.showerror("Error",str(e),parent=self); return
        messagebox.showinfo("✅ Sale Complete",f"Order #{oid}\nTotal: ₹{total:.2f}\n\nSuccess!",parent=self)
        self.cart.clear(); self._refresh_cart()
        self.cust_var.set(""); self.phone_entry.delete(0, "end"); self.disc_var.set("0"); self.pos_search.set("")
        self.app.refresh_alerts()

    def _send_whatsapp(self):
        # ── Guard: cart must not be empty ─────────────────────────
        if not self.cart:
            messagebox.showwarning("Empty", "Cart is empty.", parent=self)
            return

        # ── Get & clean phone number ──────────────────────────────
        try:
            raw = self.phone_entry.get()
        except Exception as err:
            messagebox.showwarning("Error", f"Could not read phone field: {err}", parent=self)
            return

        phone = raw.strip().replace(" ", "").replace("-", "").replace("+", "").replace("(", "").replace(")", "")

        # DEBUG: show what was read — remove this line after confirming it works
        # messagebox.showinfo("DEBUG", f"Raw input: '{raw}'\nCleaned: '{phone}'\nLength: {len(phone)}", parent=self)

        if not phone:
            # Fallback: ask via popup dialog if entry field failed to capture
            from tkinter import simpledialog
            fallback = simpledialog.askstring(
                "WhatsApp Number",
                "Enter WhatsApp number (with country code):\n"
                "Example: 919876543210",
                parent=self)
            if not fallback:
                return
            phone = fallback.strip().replace(" ","").replace("-","").replace("+","").replace("(","").replace(")","")
            if not phone:
                messagebox.showwarning("No Number", "No number entered.", parent=self)
                return

        if not phone.isdigit():
            messagebox.showwarning("Invalid Number",
                f"'{phone}' contains non-numeric characters.\nUse digits only (e.g. 919876543210).",
                parent=self)
            return

        # Auto-fix: if 10 digits and starts with valid Indian prefix, add 91
        if len(phone) == 10 and phone[0] in "6789":
            phone = "91" + phone

        # Final length check
        if len(phone) < 10 or len(phone) > 15:
            messagebox.showwarning("Invalid Number",
                f"Number must be 10–15 digits.\nYou entered {len(phone)} digits: {phone}\n\n"
                "Include country code. Example: 919876543210",
                parent=self)
            return

        # ── Build receipt text ────────────────────────────────────
        try:
            disc = float(self.disc_var.get() or 0)
        except Exception:
            disc = 0

        sub   = sum(i["qty"] * i["price"] for i in self.cart)
        total = max(0, sub - disc)
        cust  = self.cust_var.get().strip() or "Customer"
        now   = datetime.now().strftime("%Y-%m-%d %H:%M")

        lines = [
            "🛒 *INVENTORY MANAGER*",
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            "📋 *Receipt*",
            f"👤 Customer: {cust}",
            f"📅 Date: {now}",
            "━━━━━━━━━━━━━━━━━━━━━━━━",
        ]
        for item in self.cart:
            sub_item = item["qty"] * item["price"]
            lines.append(f"• {item['name']} x{item['qty']} = ₹{sub_item:.2f}")
        lines += [
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            f"Subtotal : ₹{sub:.2f}",
        ]
        if disc > 0:
            lines.append(f"Discount : -₹{disc:.2f}")
        lines += [
            f"*TOTAL   : ₹{total:.2f}*",
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            "Thank you for shopping! 🙏",
        ]

        message = "\n".join(lines)

        # ── Open WhatsApp ─────────────────────────────────────────
        try:
            encoded = urllib.parse.quote(message)
            url = f"https://wa.me/{phone}?text={encoded}"
            webbrowser.open(url)
            messagebox.showinfo(
                "✅ WhatsApp Opened",
                f"WhatsApp opened for +{phone}\n\n"
                "The receipt is pre-filled — just press SEND in WhatsApp.",
                parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open WhatsApp:\n{e}", parent=self)

    def _print_receipt(self):
        if not self.cart: messagebox.showwarning("Empty","Cart is empty.",parent=self); return
        try:    disc = float(self.disc_var.get() or 0)
        except: disc = 0
        sub = sum(i["qty"]*i["price"] for i in self.cart)
        lines = ["="*38," INVENTORY MANAGER"," Receipt","="*38,
                 f" Customer: {self.cust_var.get() or 'Walk-in Customer'}",
                 f" Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}","-"*38]
        for i in self.cart:
            lines += [f" {i['name'][:24]:<24} x{i['qty']}",
                      f"   @ ₹{i['price']:.2f} = ₹{i['qty']*i['price']:.2f}"]
        lines += ["-"*38, f" Subtotal:  ₹{sub:.2f}"]
        if disc: lines.append(f" Discount: -₹{disc:.2f}")
        lines += [f" TOTAL:     ₹{max(0,sub-disc):.2f}", "="*38, "  Thank you! \ud83d\ude4f"]
        rw = ctk.CTkToplevel(self)
        rw.title("Receipt Preview"); rw.geometry("360x480"); rw.configure(fg_color=C_BG); rw.grab_set()
        tb = ctk.CTkTextbox(rw, font=ctk.CTkFont(family="Courier", size=11),
                            fg_color=C_CARD, text_color=C_TEXT)
        tb.pack(fill="both", expand=True, padx=16, pady=16)
        tb.insert("1.0", "\n".join(lines)); tb.configure(state="disabled")
        accent_btn(rw, "Close", rw.destroy, C_ACCENT).pack(pady=8)


# ══════════════════════════════════════════════════════════════
#  PURCHASE ORDERS
# ══════════════════════════════════════════════════════════════
class PurchaseOrdersPage(ctk.CTkFrame):
    def __init__(self, parent, user, app):
        super().__init__(parent, fg_color="transparent")
        self.user = user
        page_header(self, "Purchase Orders", "Manage supplier purchase orders")
        self._toolbar()
        self._table()
        self._load()

    def _toolbar(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(fill="x", padx=28, pady=10)
        accent_btn(f, "New Order",       self._new_po,        C_GREEN,  icon="＋").pack(side="left")
        accent_btn(f, "Mark Received",   self._mark_received, C_ACCENT, icon="✅").pack(side="left", padx=8)
        accent_btn(f, "View Items",      self._view_items,    C_PURPLE, icon="\ud83d\udccb").pack(side="left")

    def _table(self):
        cols = ("ID","Date","Supplier","Items","Total ₹","Status","Created By")
        frm, self.tree = make_table(self, cols, [60,120,170,70,110,110,130])
        frm.pack(fill="both", expand=True, padx=28, pady=(0,20))

    def _load(self):
        self.tree.delete(*self.tree.get_children())
        color_map = {"pending":"expiring","received":"","cancelled":"expired"}
        try:
            rows = db_config.execute_query(
                """SELECT po.id,po.order_date,COALESCE(s.name,'—') sup,
                          COUNT(poi.id) items,po.total_amount,po.status,
                          COALESCE(u.username,'—') usr
                   FROM purchase_orders po
                   LEFT JOIN suppliers s ON po.supplier_id=s.id
                   LEFT JOIN purchase_order_items poi ON poi.purchase_order_id=po.id
                   LEFT JOIN users u ON po.created_by=u.id
                   GROUP BY po.id ORDER BY po.id DESC""", fetch="all")
            for i, r in enumerate(rows):
                tag = color_map.get(r["status"], "") or ("alt" if i%2 else "")
                self.tree.insert("","end",values=(
                    r["id"],r["order_date"],r["sup"],r["items"],
                    f"{r['total_amount']:.2f}",r["status"].capitalize(),r["usr"]),tags=(tag,))
        except Exception as e: messagebox.showerror("DB",str(e))

    def _sel_id(self):
        s = self.tree.selection()
        if not s: messagebox.showwarning("Select","Select a PO."); return None
        return self.tree.item(s[0])["values"][0]

    def _new_po(self):   PurchaseOrderDialog(self, self.user, cb=self._load)
    def _view_items(self):
        oid = self._sel_id()
        if not oid: return
        dlg = ctk.CTkToplevel(self); dlg.title(f"PO #{oid} Items")
        dlg.geometry("580x380"); dlg.configure(fg_color=C_BG); dlg.grab_set()
        cols = ("Product","SKU","Qty","Unit Price ₹","Subtotal ₹")
        frm, tree = make_table(dlg, cols, [210,110,70,120,120])
        frm.pack(fill="both", expand=True, padx=16, pady=16)
        try:
            for r in db_config.execute_query(
                """SELECT p.name,p.sku,poi.quantity,poi.unit_price FROM purchase_order_items poi
                   JOIN products p ON poi.product_id=p.id WHERE poi.purchase_order_id=%s""",(oid,),fetch="all"):
                tree.insert("","end",values=(r["name"],r["sku"],r["quantity"],
                    f"₹{r['unit_price']:.2f}",f"₹{r['quantity']*r['unit_price']:.2f}"))
        except Exception as e: messagebox.showerror("DB",str(e))
        accent_btn(dlg,"Close",dlg.destroy,C_ACCENT).pack(pady=8)

    def _mark_received(self):
        oid = self._sel_id()
        if not oid: return
        po = db_config.execute_query("SELECT status FROM purchase_orders WHERE id=%s",(oid,),fetch="one")
        if po["status"]!="pending": messagebox.showinfo("Info","Only pending orders can be received."); return
        if messagebox.askyesno("Confirm",f"Mark PO #{oid} received and update stock?"):
            try:
                items = db_config.execute_query("SELECT * FROM purchase_order_items WHERE purchase_order_id=%s",(oid,),fetch="all")
                for it in items:
                    db_config.execute_query("UPDATE products SET quantity=quantity+%s WHERE id=%s",(it["quantity"],it["product_id"]))
                    db_config.execute_query(
                        "INSERT INTO stock_transactions(product_id,transaction_type,quantity,unit_price,reference_id,created_by) VALUES(%s,'purchase',%s,%s,%s,%s)",
                        (it["product_id"],it["quantity"],it["unit_price"],oid,self.user["id"]))
                db_config.execute_query("UPDATE purchase_orders SET status='received' WHERE id=%s",(oid,))
            except Exception as e: messagebox.showerror("Error",str(e)); return
            messagebox.showinfo("✅","Stock updated!"); self._load()


class PurchaseOrderDialog(ctk.CTkToplevel):
    def __init__(self, parent, user, cb=None):
        super().__init__(parent)
        self.user, self.cb, self.items = user, cb, []
        self.title("New Purchase Order"); self.geometry("720x620")
        self.configure(fg_color=C_BG); self.grab_set()
        self.sups  = db_config.execute_query("SELECT id,name FROM suppliers ORDER BY name",fetch="all") or []
        self.prods = db_config.execute_query("SELECT id,name,sku,unit_price FROM products ORDER BY name",fetch="all") or []
        self._build()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=14)
        ctk.CTkLabel(top, text="Supplier:", font=ctk.CTkFont(size=12), text_color=C_MUTED).pack(side="left")
        self.sup_var = ctk.StringVar()
        ctk.CTkOptionMenu(top, variable=self.sup_var,
                          values=[s["name"] for s in self.sups] or ["—"],
                          fg_color=C_CARD2, button_color=C_ACCENT,
                          text_color=C_TEXT, width=200).pack(side="left", padx=8)
        ctk.CTkLabel(top, text="Date:", font=ctk.CTkFont(size=12), text_color=C_MUTED).pack(side="left", padx=(10,4))
        self.date_var = ctk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        ctk.CTkEntry(top, textvariable=self.date_var, width=130,
                     fg_color=C_CARD2, border_color=C_BORDER, text_color=C_TEXT).pack(side="left")

        af = ctk.CTkFrame(self, fg_color="transparent")
        af.pack(fill="x", padx=20, pady=6)
        ctk.CTkLabel(af, text="Product:", font=ctk.CTkFont(size=12), text_color=C_MUTED).pack(side="left")
        self.item_prod = ctk.StringVar()
        ctk.CTkComboBox(af, variable=self.item_prod,
                        values=[f"{p['name']} ({p['sku']})" for p in self.prods],
                        fg_color=C_CARD2, border_color=C_BORDER, text_color=C_TEXT,
                        width=260).pack(side="left", padx=8)
        ctk.CTkLabel(af, text="Qty:", font=ctk.CTkFont(size=12), text_color=C_MUTED).pack(side="left",padx=(8,4))
        self.item_qty   = ctk.StringVar(value="1")
        ctk.CTkEntry(af, textvariable=self.item_qty, width=60,
                     fg_color=C_CARD2, border_color=C_BORDER, text_color=C_TEXT).pack(side="left")
        ctk.CTkLabel(af, text="Price:", font=ctk.CTkFont(size=12), text_color=C_MUTED).pack(side="left",padx=(8,4))
        self.item_price = ctk.StringVar()
        ctk.CTkEntry(af, textvariable=self.item_price, width=90,
                     fg_color=C_CARD2, border_color=C_BORDER, text_color=C_TEXT).pack(side="left")
        accent_btn(af, "Add", self._add_item, C_GREEN, width=70, icon="＋").pack(side="left", padx=10)

        cols = ("Product","Qty","Unit Price ₹","Subtotal ₹")
        frm, self.itree = make_table(self, cols, [280,70,120,120])
        frm.pack(fill="both", expand=True, padx=20, pady=8)

        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(fill="x", padx=20, pady=(0,12))
        accent_btn(bf, "Remove", self._remove_item, C_RED, icon="✖").pack(side="left")
        self.tot_lbl = ctk.CTkLabel(bf, text="Total: ₹0.00",
                                     font=ctk.CTkFont(size=14,weight="bold"), text_color=C_GREEN)
        self.tot_lbl.pack(side="right")

        bf2 = ctk.CTkFrame(self, fg_color="transparent")
        bf2.pack(fill="x", padx=20, pady=(0,16))
        ctk.CTkLabel(bf2, text="Notes:", font=ctk.CTkFont(size=12), text_color=C_MUTED).pack(side="left")
        self.notes_v = ctk.StringVar()
        ctk.CTkEntry(bf2, textvariable=self.notes_v, width=300,
                     fg_color=C_CARD2, border_color=C_BORDER, text_color=C_TEXT).pack(side="left", padx=8)
        accent_btn(bf2, "Cancel", self.destroy, C_RED).pack(side="right", padx=(8,0))
        accent_btn(bf2, "Save Order", self._save, C_GREEN, icon="\ud83d\udcbe").pack(side="right")

    def _add_item(self):
        pname = self.item_prod.get().strip()
        prod  = next((p for p in self.prods if f"{p['name']} ({p['sku']})"==pname), None)
        if not prod: return
        try:
            qty   = int(self.item_qty.get()); assert qty > 0
            price = float(self.item_price.get() or prod["unit_price"])
        except: messagebox.showwarning("Input","Valid qty/price required.",parent=self); return
        self.items.append({"pid":prod["id"],"name":prod["name"],"qty":qty,"price":price})
        self._refresh()

    def _remove_item(self):
        sel = self.itree.selection()
        if sel: del self.items[self.itree.index(sel[0])]; self._refresh()

    def _refresh(self):
        self.itree.delete(*self.itree.get_children())
        total = 0
        for i, it in enumerate(self.items):
            sub = it["qty"]*it["price"]; total += sub
            self.itree.insert("","end",values=(it["name"],it["qty"],f"₹{it['price']:.2f}",f"₹{sub:.2f}"),
                              tags=("alt" if i%2 else ""))
        self.tot_lbl.configure(text=f"Total: ₹{total:.2f}")

    def _save(self):
        if not self.items: messagebox.showwarning("Empty","Add items.",parent=self); return
        sup_id = next((s["id"] for s in self.sups if s["name"]==self.sup_var.get()), None)
        total  = sum(i["qty"]*i["price"] for i in self.items)
        try:
            oid = db_config.execute_query(
                "INSERT INTO purchase_orders(supplier_id,order_date,total_amount,notes,created_by) VALUES(%s,%s,%s,%s,%s)",
                (sup_id,self.date_var.get(),total,self.notes_v.get().strip(),self.user["id"]))
            for it in self.items:
                db_config.execute_query(
                    "INSERT INTO purchase_order_items(purchase_order_id,product_id,quantity,unit_price) VALUES(%s,%s,%s,%s)",
                    (oid,it["pid"],it["qty"],it["price"]))
        except Exception as e: messagebox.showerror("Error",str(e),parent=self); return
        messagebox.showinfo("✅",f"Purchase Order #{oid} created!",parent=self)
        if self.cb: self.cb()
        self.destroy()


# ══════════════════════════════════════════════════════════════
#  SALES HISTORY
# ══════════════════════════════════════════════════════════════
class SalesHistoryPage(ctk.CTkFrame):
    def __init__(self, parent, user, app):
        super().__init__(parent, fg_color="transparent")
        self.user = user
        page_header(self, "Sales History", "All completed transactions")
        self._build()

    def _build(self):
        ff = ctk.CTkFrame(self, fg_color="transparent")
        ff.pack(fill="x", padx=28, pady=10)
        ctk.CTkLabel(ff, text="Period:", font=ctk.CTkFont(size=12), text_color=C_MUTED).pack(side="left")
        self.period = ctk.StringVar(value="today")
        for lbl, val in [("Today","today"),("Week","week"),("Month","month"),("All","all")]:
            ctk.CTkRadioButton(ff, text=lbl, variable=self.period, value=val,
                               command=self._load,
                               fg_color=C_ACCENT, hover_color=C_ACCENT).pack(side="left", padx=8)

        cols = ("ID","Date","Customer","Items","Subtotal ₹","Disc ₹","Total ₹","By")
        frm, self.tree = make_table(self, cols, [60,145,170,60,100,80,100,110])
        self.tree.bind("<Double-1>", self._view_items)
        frm.pack(fill="both", expand=True, padx=28, pady=(0,6))

        sf = ctk.CTkFrame(self, fg_color="transparent")
        sf.pack(fill="x", padx=28, pady=(0,18))
        accent_btn(sf, "View Items (double-click)", self._view_items, C_ACCENT, icon="\ud83d\udccb").pack(side="left")
        self.rev_lbl = ctk.CTkLabel(sf, text="",
                                     font=ctk.CTkFont(size=14, weight="bold"),
                                     text_color=C_GREEN)
        self.rev_lbl.pack(side="right")
        self._load()

    def _load(self):
        self.tree.delete(*self.tree.get_children())
        where = {"today":"WHERE DATE(so.order_date)=CURDATE()",
                 "week": "WHERE so.order_date>=DATE_SUB(CURDATE(),INTERVAL 7 DAY)",
                 "month":"WHERE so.order_date>=DATE_SUB(CURDATE(),INTERVAL 30 DAY)",
                 "all":  ""}[self.period.get()]
        try:
            rows = db_config.execute_query(
                f"""SELECT so.id,so.order_date,so.customer_name,
                           COUNT(soi.id) items,
                           so.total_amount+so.discount sub,
                           so.discount,so.total_amount,
                           COALESCE(u.username,'—') usr
                    FROM sales_orders so
                    LEFT JOIN sales_order_items soi ON soi.sales_order_id=so.id
                    LEFT JOIN users u ON so.created_by=u.id
                    {where} GROUP BY so.id ORDER BY so.id DESC""", fetch="all")
            total_rev = 0
            for i, r in enumerate(rows):
                self.tree.insert("","end",values=(
                    r["id"],str(r["order_date"])[:16],r["customer_name"] or "—",
                    r["items"],f"{r['sub']:.2f}",f"{r['discount']:.2f}",
                    f"{r['total_amount']:.2f}",r["usr"]),tags=("alt" if i%2 else ""))
                total_rev += float(r["total_amount"])
            self.rev_lbl.configure(text=f"Revenue: ₹{total_rev:,.2f}")
        except Exception as e: messagebox.showerror("DB",str(e))

    def _view_items(self, event=None):
        sel = self.tree.selection()
        if not sel: return
        oid = self.tree.item(sel[0])["values"][0]
        dlg = ctk.CTkToplevel(self); dlg.title(f"Order #{oid}")
        dlg.geometry("520x360"); dlg.configure(fg_color=C_BG); dlg.grab_set()
        cols = ("Product","Qty","Unit Price ₹","Subtotal ₹")
        frm, tree = make_table(dlg, cols, [230,70,120,120])
        frm.pack(fill="both", expand=True, padx=16, pady=16)
        try:
            for r in db_config.execute_query(
                "SELECT * FROM sales_order_items WHERE sales_order_id=%s",(oid,),fetch="all"):
                tree.insert("","end",values=(r["product_name"],r["quantity"],
                    f"₹{r['unit_price']:.2f}",f"₹{r['quantity']*r['unit_price']:.2f}"))
        except Exception as e: messagebox.showerror("DB",str(e))
        accent_btn(dlg,"Close",dlg.destroy,C_ACCENT).pack(pady=8)


# ══════════════════════════════════════════════════════════════
#  USERS PAGE
# ══════════════════════════════════════════════════════════════
class UsersPage(ctk.CTkFrame):
    def __init__(self, parent, user, app):
        super().__init__(parent, fg_color="transparent")
        self.user = user
        page_header(self, "Users & Access", "Manage system users")
        if user["role"] != "admin":
            ctk.CTkLabel(self, text="\ud83d\udd12  Admin access required.",
                         font=ctk.CTkFont(size=16),
                         text_color=C_RED).pack(pady=80)
            return
        self._toolbar(); self._table(); self._load()

    def _toolbar(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(fill="x", padx=28, pady=10)
        accent_btn(f, "Add User", self._add, C_GREEN, icon="＋").pack(side="left")

    def _table(self):
        cols = ("ID","Username","Full Name","Role","Active","Created")
        frm, self.tree = make_table(self, cols, [50,130,170,100,70,140])
        frm.pack(fill="both", expand=True, padx=28, pady=(0,6))
        ab = ctk.CTkFrame(self, fg_color="transparent")
        ab.pack(fill="x", padx=28, pady=(0,20))
        accent_btn(ab, "Edit",   self._edit,   C_ACCENT, icon="✏").pack(side="left", padx=(0,8))
        accent_btn(ab, "Delete", self._delete, C_RED,    icon="\ud83d\uddd1").pack(side="left")

    def _load(self):
        self.tree.delete(*self.tree.get_children())
        try:
            for i, r in enumerate(db_config.execute_query("SELECT * FROM users ORDER BY id",fetch="all")):
                self.tree.insert("","end",values=(
                    r["id"],r["username"],r.get("full_name",""),r["role"],
                    "Yes" if r["is_active"] else "No",str(r["created_at"])[:10]),
                    tags=("alt" if i%2 else ""))
        except Exception as e: messagebox.showerror("DB",str(e))

    def _sel_id(self):
        s = self.tree.selection()
        if not s: messagebox.showwarning("Select","Select a user."); return None
        return self.tree.item(s[0])["values"][0]

    def _add(self):  UserDialog(self, cb=self._load)
    def _edit(self):
        uid = self._sel_id()
        if uid: UserDialog(self, uid=uid, cb=self._load)
    def _delete(self):
        uid = self._sel_id()
        if not uid: return
        if uid == self.user["id"]: messagebox.showwarning("Nope","Can't delete your own account."); return
        if messagebox.askyesno("Confirm","Delete this user?"):
            try: db_config.execute_query("DELETE FROM users WHERE id=%s",(uid,)); self._load()
            except Exception as e: messagebox.showerror("Error",str(e))


class UserDialog(ctk.CTkToplevel):
    def __init__(self, parent, uid=None, cb=None):
        super().__init__(parent)
        self.uid, self.cb = uid, cb
        self.title("Edit User" if uid else "Add User")
        self.geometry("420x400"); self.resizable(False,False)
        self.configure(fg_color=C_BG); self.grab_set()
        self._build()
        if uid: self._populate()

    def _build(self):
        card = card_frame(self)
        card.pack(fill="both", expand=True, padx=20, pady=20)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=24, pady=20)

        self.v = {}
        for lbl, key, ph, show in [
            ("Username *",  "username",  "e.g. john_doe", ""),
            ("Full Name",   "full_name", "e.g. John Doe", ""),
            ("Password *",  "password",  "min 6 chars",   "●"),
        ]:
            ctk.CTkLabel(inner, text=lbl, font=ctk.CTkFont(size=12), text_color=C_MUTED, anchor="w").pack(fill="x")
            v = ctk.StringVar()
            ctk.CTkEntry(inner, textvariable=v, placeholder_text=ph,
                         fg_color=C_CARD2, border_color=C_BORDER, text_color=C_TEXT,
                         show=show if show else "").pack(fill="x", pady=(2,10))
            self.v[key] = v

        ctk.CTkLabel(inner, text="Role", font=ctk.CTkFont(size=12), text_color=C_MUTED, anchor="w").pack(fill="x")
        self.v["role"] = ctk.StringVar(value="staff")
        ctk.CTkOptionMenu(inner, variable=self.v["role"],
                          values=["admin","manager","staff"],
                          fg_color=C_CARD2, button_color=C_ACCENT, text_color=C_TEXT).pack(fill="x", pady=(2,10))

        self.active_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(inner, text="Active", variable=self.active_var,
                        fg_color=C_ACCENT, hover_color=C_ACCENT).pack(anchor="w", pady=(4,0))

        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(fill="x", padx=20, pady=(0,16))
        accent_btn(bf, "Cancel", self.destroy, C_RED).pack(side="right", padx=(8,0))
        accent_btn(bf, "Save",   self._save,   C_GREEN, icon="\ud83d\udcbe").pack(side="right")

    def _populate(self):
        u = db_config.execute_query("SELECT * FROM users WHERE id=%s",(self.uid,),fetch="one")
        if not u: return
        self.v["username"].set(u["username"])
        self.v["full_name"].set(u.get("full_name","") or "")
        self.v["password"].set(u["password"])
        self.v["role"].set(u["role"])
        self.active_var.set(bool(u["is_active"]))

    def _save(self):
        uname = self.v["username"].get().strip()
        pwd   = self.v["password"].get().strip()
        if not uname or not pwd:
            messagebox.showwarning("Required","Username and Password required.",parent=self); return
        try:
            if self.uid:
                db_config.execute_query(
                    "UPDATE users SET username=%s,full_name=%s,password=%s,role=%s,is_active=%s WHERE id=%s",
                    (uname,self.v["full_name"].get().strip(),pwd,self.v["role"].get(),int(self.active_var.get()),self.uid))
            else:
                db_config.execute_query(
                    "INSERT INTO users(username,full_name,password,role,is_active) VALUES(%s,%s,%s,%s,%s)",
                    (uname,self.v["full_name"].get().strip(),pwd,self.v["role"].get(),int(self.active_var.get())))
        except Exception as e: messagebox.showerror("Error",str(e),parent=self); return
        if self.cb: self.cb()
        self.destroy()


# ══════════════════════════════════════════════════════════════
#  SALES ANALYTICS PAGE
# ══════════════════════════════════════════════════════════════
class SalesAnalyticsPage(ctk.CTkFrame):
    def __init__(self, parent, user, app):
        super().__init__(parent, fg_color="transparent")
        self.user = user
        page_header(self, "📈  Sales Analytics", "Visual sales breakdown per product")
        self._build()

    def _build(self):
        # ── Controls bar ──────────────────────────────────────────
        ctrl = ctk.CTkFrame(self, fg_color="transparent")
        ctrl.pack(fill="x", padx=28, pady=(10, 0))

        ctk.CTkLabel(ctrl, text="Period:", font=ctk.CTkFont(size=12), text_color=C_MUTED).pack(side="left")
        self.period_var = ctk.StringVar(value="30")
        for lbl, val in [("7 Days","7"),("30 Days","30"),("60 Days","60"),("90 Days","90")]:
            ctk.CTkRadioButton(ctrl, text=lbl, variable=self.period_var, value=val,
                               command=self._refresh, fg_color=C_ACCENT,
                               hover_color=C_ACCENT).pack(side="left", padx=8)

        ctk.CTkLabel(ctrl, text="  Chart:", font=ctk.CTkFont(size=12), text_color=C_MUTED).pack(side="left", padx=(16,0))
        self.chart_var = ctk.StringVar(value="bar")
        for lbl, val in [("Bar","bar"),("Line","line"),("Pie","pie")]:
            ctk.CTkRadioButton(ctrl, text=lbl, variable=self.chart_var, value=val,
                               command=self._refresh, fg_color=C_PURPLE,
                               hover_color=C_PURPLE).pack(side="left", padx=6)

        accent_btn(ctrl, "Refresh", self._refresh, C_ACCENT, width=90, icon="↻").pack(side="right")

        # ── Tab view ──────────────────────────────────────────────
        tabs = ctk.CTkTabview(self, fg_color=C_CARD,
                               segmented_button_fg_color=C_CARD2,
                               segmented_button_selected_color=C_ACCENT,
                               segmented_button_unselected_color=C_CARD2,
                               segmented_button_selected_hover_color="#3a75e0")
        tabs.pack(fill="both", expand=True, padx=28, pady=12)
        tabs.add("📊 Revenue by Product")
        tabs.add("📦 Units Sold")
        tabs.add("📅 Daily Trend")
        tabs.add("🏆 Top 5 Products")
        self.tabs = tabs
        self._refresh()

    def _get_days(self):
        return int(self.period_var.get())

    def _refresh(self):
        for tab_name in ["📊 Revenue by Product", "📦 Units Sold", "📅 Daily Trend", "🏆 Top 5 Products"]:
            tab = self.tabs.tab(tab_name)
            for w in tab.winfo_children():
                w.destroy()
        days = self._get_days()
        chart = self.chart_var.get()
        self._chart_revenue(self.tabs.tab("📊 Revenue by Product"), days, chart)
        self._chart_units(self.tabs.tab("📦 Units Sold"), days, chart)
        self._chart_daily(self.tabs.tab("📅 Daily Trend"), days)
        self._chart_top5(self.tabs.tab("🏆 Top 5 Products"), days)

    def _embed_fig(self, fig, parent):
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)
        plt.close(fig)

    def _style_fig(self, fig, ax):
        fig.patch.set_facecolor("#1e2235")
        ax.set_facecolor("#1e2235")
        ax.tick_params(colors="#e8eaf6", labelsize=8)
        ax.xaxis.label.set_color("#6c7293")
        ax.yaxis.label.set_color("#6c7293")
        ax.title.set_color("#e8eaf6")
        for spine in ax.spines.values():
            spine.set_edgecolor("#2d3154")

    def _chart_revenue(self, parent, days, chart_type):
        try:
            rows = db_config.execute_query(
                """SELECT soi.product_name, SUM(soi.quantity * soi.unit_price) revenue
                   FROM sales_order_items soi
                   JOIN sales_orders so ON soi.sales_order_id = so.id
                   WHERE so.order_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                   GROUP BY soi.product_name ORDER BY revenue DESC LIMIT 15""",
                (days,), fetch="all")
        except Exception as e:
            ctk.CTkLabel(parent, text=f"DB Error: {e}", text_color=C_RED).pack(pady=20); return
        if not rows:
            ctk.CTkLabel(parent, text="No sales data in this period", text_color=C_MUTED,
                         font=ctk.CTkFont(size=14)).pack(pady=60); return
        names = [r["product_name"][:18] for r in rows]
        vals  = [float(r["revenue"]) for r in rows]
        colors = plt.cm.Blues([0.4 + 0.6*i/max(len(vals)-1,1) for i in range(len(vals))])
        fig, ax = plt.subplots(figsize=(9, 4.5), dpi=90)
        self._style_fig(fig, ax)
        if chart_type == "bar":
            bars = ax.bar(names, vals, color=colors, edgecolor="#1e2235", linewidth=0.5)
            for bar, v in zip(bars, vals):
                ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+max(vals)*0.01,
                        f"₹{v:,.0f}", ha="center", va="bottom", color="#e8eaf6", fontsize=7)
            plt.xticks(rotation=30, ha="right")
        elif chart_type == "line":
            ax.plot(names, vals, color="#4f8ef7", marker="o", linewidth=2, markersize=5)
            ax.fill_between(range(len(names)), vals, alpha=0.15, color="#4f8ef7")
            plt.xticks(rotation=30, ha="right")
        elif chart_type == "pie":
            wedges, texts, autotexts = ax.pie(vals, labels=names, autopct="%1.1f%%",
                                               colors=plt.cm.Blues([0.3+0.7*i/max(len(vals)-1,1) for i in range(len(vals))]),
                                               textprops={"color":"#e8eaf6","fontsize":7})
        ax.set_title(f"Revenue by Product (Last {days} days)", pad=10, fontsize=11)
        if chart_type != "pie":
            ax.set_ylabel("Revenue (₹)")
        fig.tight_layout()
        self._embed_fig(fig, parent)

    def _chart_units(self, parent, days, chart_type):
        try:
            rows = db_config.execute_query(
                """SELECT soi.product_name, SUM(soi.quantity) units
                   FROM sales_order_items soi
                   JOIN sales_orders so ON soi.sales_order_id = so.id
                   WHERE so.order_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                   GROUP BY soi.product_name ORDER BY units DESC LIMIT 15""",
                (days,), fetch="all")
        except Exception as e:
            ctk.CTkLabel(parent, text=f"DB Error: {e}", text_color=C_RED).pack(pady=20); return
        if not rows:
            ctk.CTkLabel(parent, text="No sales data in this period", text_color=C_MUTED,
                         font=ctk.CTkFont(size=14)).pack(pady=60); return
        names = [r["product_name"][:18] for r in rows]
        vals  = [int(r["units"]) for r in rows]
        fig, ax = plt.subplots(figsize=(9, 4.5), dpi=90)
        self._style_fig(fig, ax)
        if chart_type == "bar":
            colors = ["#2ecc71" if v == max(vals) else "#4f8ef7" for v in vals]
            bars = ax.bar(names, vals, color=colors, edgecolor="#1e2235")
            for bar, v in zip(bars, vals):
                ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.1,
                        str(v), ha="center", va="bottom", color="#e8eaf6", fontsize=8)
            plt.xticks(rotation=30, ha="right")
        elif chart_type == "line":
            ax.plot(names, vals, color="#2ecc71", marker="s", linewidth=2, markersize=6)
            ax.fill_between(range(len(names)), vals, alpha=0.15, color="#2ecc71")
            plt.xticks(rotation=30, ha="right")
        elif chart_type == "pie":
            ax.pie(vals, labels=names, autopct="%1.1f%%",
                   colors=plt.cm.Greens([0.3+0.7*i/max(len(vals)-1,1) for i in range(len(vals))]),
                   textprops={"color":"#e8eaf6","fontsize":7})
        ax.set_title(f"Units Sold by Product (Last {days} days)", pad=10, fontsize=11)
        if chart_type != "pie":
            ax.set_ylabel("Units Sold")
        fig.tight_layout()
        self._embed_fig(fig, parent)

    def _chart_daily(self, parent, days):
        try:
            rows = db_config.execute_query(
                """SELECT DATE(order_date) day, SUM(total_amount) total
                   FROM sales_orders
                   WHERE order_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                   GROUP BY DATE(order_date) ORDER BY day""",
                (days,), fetch="all")
        except Exception as e:
            ctk.CTkLabel(parent, text=f"DB Error: {e}", text_color=C_RED).pack(pady=20); return
        if not rows:
            ctk.CTkLabel(parent, text="No sales data in this period", text_color=C_MUTED,
                         font=ctk.CTkFont(size=14)).pack(pady=60); return
        dates = [r["day"] for r in rows]
        vals  = [float(r["total"]) for r in rows]
        fig, ax = plt.subplots(figsize=(9, 4.5), dpi=90)
        self._style_fig(fig, ax)
        ax.plot(dates, vals, color="#4f8ef7", linewidth=2, marker="o", markersize=4)
        ax.fill_between(dates, vals, alpha=0.12, color="#4f8ef7")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.xticks(rotation=30, ha="right")
        # Annotate max
        if vals:
            max_idx = vals.index(max(vals))
            ax.annotate(f"₹{max(vals):,.0f}", xy=(dates[max_idx], max(vals)),
                        xytext=(0, 10), textcoords="offset points",
                        ha="center", color="#f1c40f", fontsize=8)
        ax.set_title(f"Daily Revenue Trend (Last {days} days)", pad=10, fontsize=11)
        ax.set_ylabel("Revenue (₹)")
        ax.set_xlabel("Date")
        fig.tight_layout()
        self._embed_fig(fig, parent)

    def _chart_top5(self, parent, days):
        try:
            rows = db_config.execute_query(
                """SELECT soi.product_name,
                          SUM(soi.quantity) units,
                          SUM(soi.quantity * soi.unit_price) revenue,
                          COUNT(DISTINCT soi.sales_order_id) orders
                   FROM sales_order_items soi
                   JOIN sales_orders so ON soi.sales_order_id = so.id
                   WHERE so.order_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                   GROUP BY soi.product_name ORDER BY revenue DESC LIMIT 5""",
                (days,), fetch="all")
        except Exception as e:
            ctk.CTkLabel(parent, text=f"DB Error: {e}", text_color=C_RED).pack(pady=20); return
        if not rows:
            ctk.CTkLabel(parent, text="No sales data in this period", text_color=C_MUTED,
                         font=ctk.CTkFont(size=14)).pack(pady=60); return
        # Side by side: chart + table
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=3)
        frame.columnconfigure(1, weight=2)
        frame.rowconfigure(0, weight=1)
        # Left: chart
        chart_frame = ctk.CTkFrame(frame, fg_color="transparent")
        chart_frame.grid(row=0, column=0, sticky="nsew")
        names = [r["product_name"][:16] for r in rows]
        revs  = [float(r["revenue"]) for r in rows]
        palette = ["#4f8ef7","#2ecc71","#e67e22","#9b59b6","#f1c40f"]
        fig, ax = plt.subplots(figsize=(5.5, 4), dpi=90)
        self._style_fig(fig, ax)
        bars = ax.barh(names[::-1], revs[::-1], color=palette[::-1], edgecolor="#1e2235")
        for bar, v in zip(bars, revs[::-1]):
            ax.text(bar.get_width()+max(revs)*0.01, bar.get_y()+bar.get_height()/2,
                    f"₹{v:,.0f}", va="center", color="#e8eaf6", fontsize=8)
        ax.set_title(f"Top 5 by Revenue", pad=8, fontsize=10)
        ax.set_xlabel("Revenue (₹)")
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=8)
        plt.close(fig)
        # Right: table
        tbl_frame = ctk.CTkFrame(frame, fg_color=C_CARD, corner_radius=12)
        tbl_frame.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        ctk.CTkLabel(tbl_frame, text="🏆 Top Products Summary",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=C_TEXT).pack(pady=(14,8))
        for i, r in enumerate(rows):
            medal = ["🥇","🥈","🥉","4️⃣","5️⃣"][i]
            card = ctk.CTkFrame(tbl_frame, fg_color=C_CARD2, corner_radius=8)
            card.pack(fill="x", padx=12, pady=4)
            ctk.CTkLabel(card, text=f"{medal}  {r['product_name'][:20]}",
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=C_TEXT, anchor="w").pack(anchor="w", padx=10, pady=(6,2))
            info = ctk.CTkFrame(card, fg_color="transparent")
            info.pack(fill="x", padx=10, pady=(0,6))
            ctk.CTkLabel(info, text=f"₹{float(r['revenue']):,.0f}",
                         font=ctk.CTkFont(size=11), text_color=C_GREEN).pack(side="left")
            ctk.CTkLabel(info, text=f"  {r['units']} units  |  {r['orders']} orders",
                         font=ctk.CTkFont(size=10), text_color=C_MUTED).pack(side="left")


# ══════════════════════════════════════════════════════════════
#  AI COMPANION PAGE
# ══════════════════════════════════════════════════════════════
class AICompanionPage(ctk.CTkFrame):
    def __init__(self, parent, user, app):
        super().__init__(parent, fg_color="transparent")
        self.user = user
        page_header(self, "🤖  AI Companion", "Smart restocking predictions based on sales history")
        self._build()

    def _build(self):
        # ── Controls ──────────────────────────────────────────────
        ctrl = ctk.CTkFrame(self, fg_color="transparent")
        ctrl.pack(fill="x", padx=28, pady=(10,0))

        ctk.CTkLabel(ctrl, text="Analyse last:", font=ctk.CTkFont(size=12), text_color=C_MUTED).pack(side="left")
        self.days_var = ctk.StringVar(value="30")
        for lbl, val in [("30 Days","30"),("45 Days","45"),("60 Days","60")]:
            ctk.CTkRadioButton(ctrl, text=lbl, variable=self.days_var, value=val,
                               fg_color=C_ACCENT, hover_color=C_ACCENT).pack(side="left", padx=8)

        ctk.CTkLabel(ctrl, text="   Forecast next:", font=ctk.CTkFont(size=12), text_color=C_MUTED).pack(side="left")
        self.forecast_var = ctk.StringVar(value="30")
        for lbl, val in [("7 Days","7"),("14 Days","14"),("30 Days","30")]:
            ctk.CTkRadioButton(ctrl, text=lbl, variable=self.forecast_var, value=val,
                               fg_color=C_PURPLE, hover_color=C_PURPLE).pack(side="left", padx=6)

        accent_btn(ctrl, "🤖 Run Analysis", self._analyse, C_ACCENT, width=130).pack(side="right")

        # ── Summary banner ────────────────────────────────────────
        self.banner = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=10)
        self.banner.pack(fill="x", padx=28, pady=(10,0))
        self.banner_lbl = ctk.CTkLabel(self.banner,
            text="👆  Select a time range above and click  🤖 Run Analysis",
            font=ctk.CTkFont(size=13), text_color=C_MUTED)
        self.banner_lbl.pack(pady=14)

        # ── Results table ─────────────────────────────────────────
        cols = ("Product", "Sold/Day", "Current Stock", "Days Left", "Suggested Order", "Quantity Range", "Priority")
        frm, self.tree = make_table(self, cols,
            [170, 80, 110, 80, 130, 130, 90],
            anchors=["w","c","c","c","c","c","c"])
        frm.pack(fill="both", expand=True, padx=28, pady=(10,0))

        # ── Insight panel ─────────────────────────────────────────
        self.insight_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.insight_frame.pack(fill="x", padx=28, pady=(8,16))

    def _analyse(self):
        days     = int(self.days_var.get())
        forecast = int(self.forecast_var.get())
        self.tree.delete(*self.tree.get_children())
        for w in self.insight_frame.winfo_children():
            w.destroy()

        self.banner_lbl.configure(text="⏳  Analysing sales data...", text_color=C_YELLOW)
        self.update()

        try:
            # Get sales velocity per product
            rows = db_config.execute_query(
                """SELECT soi.product_name, p.id pid, p.quantity current_stock,
                          p.expiry_date, p.low_stock_alert,
                          SUM(soi.quantity) total_sold,
                          COUNT(DISTINCT DATE(so.order_date)) active_days
                   FROM sales_order_items soi
                   JOIN sales_orders so ON soi.sales_order_id = so.id
                   JOIN products p ON soi.product_id = p.id
                   WHERE so.order_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                   GROUP BY soi.product_id, soi.product_name, p.quantity, p.expiry_date, p.low_stock_alert
                   ORDER BY total_sold DESC""",
                (days,), fetch="all")

            if not rows:
                self.banner_lbl.configure(
                    text=f"⚠️  No sales data found in the last {days} days. Make some sales first!",
                    text_color=C_ORANGE)
                return

            urgent = 0
            warning = 0
            ok_count = 0
            results = []

            for r in rows:
                total_sold    = int(r["total_sold"])
                active_days   = max(int(r["active_days"]), 1)
                current_stock = int(r["current_stock"])
                exp_date      = r["expiry_date"]

                # Daily velocity = total sold / number of days in range
                daily_velocity = total_sold / days

                # Days of stock left
                if daily_velocity > 0:
                    days_of_stock = current_stock / daily_velocity
                else:
                    days_of_stock = 999

                # How much will be needed in forecast window
                base_needed = daily_velocity * forecast

                # Add 20% safety buffer
                safe_needed = base_needed * 1.2

                # Expiry adjustment: don't order more than can be sold before expiry
                if exp_date:
                    if isinstance(exp_date, str):
                        exp_date = datetime.strptime(exp_date, "%Y-%m-%d").date()
                    days_to_expiry = (exp_date - date.today()).days
                    if days_to_expiry <= 0:
                        # Already expired — don't order
                        safe_needed = 0
                    elif days_to_expiry < forecast:
                        # Will expire before forecast window ends — cap order
                        safe_needed = min(safe_needed, daily_velocity * days_to_expiry * 0.9)

                # Quantity range: -15% to +25%
                qty_low  = max(0, math.floor(safe_needed * 0.85))
                qty_high = math.ceil(safe_needed * 1.25)
                suggested = math.ceil(safe_needed)

                # Priority logic
                if days_of_stock <= forecast * 0.5:
                    priority = "🔴 URGENT"
                    tag = "expired"
                    urgent += 1
                elif days_of_stock <= forecast:
                    priority = "🟡 ORDER SOON"
                    tag = "expiring"
                    warning += 1
                else:
                    priority = "🟢 OK"
                    tag = ""
                    ok_count += 1

                results.append({
                    "name": r["product_name"],
                    "daily": daily_velocity,
                    "stock": current_stock,
                    "days_left": days_of_stock,
                    "suggested": suggested,
                    "low": qty_low,
                    "high": qty_high,
                    "priority": priority,
                    "tag": tag,
                })

                self.tree.insert("", "end", values=(
                    r["product_name"][:28],
                    f"{daily_velocity:.2f}",
                    current_stock,
                    f"{days_of_stock:.0f}" if days_of_stock < 999 else "∞",
                    f"{suggested} units",
                    f"{qty_low} – {qty_high}",
                    priority,
                ), tags=(tag,))

            # Banner summary
            self.banner_lbl.configure(
                text=f"✅  Analysis complete for {len(results)} products  |  "
                     f"🔴 {urgent} Urgent  |  🟡 {warning} Order Soon  |  🟢 {ok_count} OK  "
                     f"  (Based on last {days} days → forecasting next {forecast} days)",
                text_color=C_GREEN)

            # Insight cards
            self._draw_insights(results, forecast)

        except Exception as e:
            self.banner_lbl.configure(text=f"❌ Error: {e}", text_color=C_RED)

    def _draw_insights(self, results, forecast):
        urgent_items   = [r for r in results if "URGENT" in r["priority"]]
        ok_items       = [r for r in results if "OK" in r["priority"] and "🟢" in r["priority"]]
        total_order_val = sum(r["suggested"] for r in results if r["suggested"] > 0)

        row = ctk.CTkFrame(self.insight_frame, fg_color="transparent")
        row.pack(fill="x")

        cards = [
            ("🔴", "Urgent Items", str(len(urgent_items)), "Need reorder immediately", C_RED),
            ("📦", "Total Units to Order", str(total_order_val), f"Across all products", C_ACCENT),
            ("📅", "Forecast Window", f"{forecast} days", "Planning horizon", C_PURPLE),
            ("🟢", "Well Stocked", str(len(ok_items)), "No action needed", C_GREEN),
        ]
        for icon, title, val, sub, clr in cards:
            c = ctk.CTkFrame(row, fg_color=C_CARD, corner_radius=12,
                             border_width=1, border_color=C_BORDER)
            c.pack(side="left", fill="x", expand=True, padx=4)
            ctk.CTkFrame(c, fg_color=clr, height=3, corner_radius=2).pack(fill="x")
            ctk.CTkLabel(c, text=icon, font=ctk.CTkFont(size=22)).pack(pady=(8,2))
            ctk.CTkLabel(c, text=val, font=ctk.CTkFont(size=20, weight="bold"),
                         text_color=C_TEXT).pack()
            ctk.CTkLabel(c, text=title, font=ctk.CTkFont(size=10, weight="bold"),
                         text_color=C_TEXT).pack()
            ctk.CTkLabel(c, text=sub, font=ctk.CTkFont(size=9),
                         text_color=C_MUTED).pack(pady=(0,10))

        # Urgent items callout
        if urgent_items:
            warn = ctk.CTkFrame(self.insight_frame, fg_color="#3d1515",
                                corner_radius=10, border_width=1, border_color=C_RED)
            warn.pack(fill="x", pady=(8,0))
            names = ", ".join(r["name"][:20] for r in urgent_items[:5])
            if len(urgent_items) > 5:
                names += f" +{len(urgent_items)-5} more"
            ctk.CTkLabel(warn, text=f"🚨  Urgent Reorder Needed: {names}",
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color="#ff8080").pack(anchor="w", padx=14, pady=8)


# ══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    if not db_config.test_connection():
        import tkinter as tk
        r = tk.Tk(); r.withdraw()
        messagebox.showerror("Connection Failed",
            "Cannot connect to MySQL.\n\n"
            "1. Ensure MySQL is running\n"
            "2. Update credentials in db_config.py\n"
            "3. Run database_setup.sql first")
        r.destroy()
    else:
        LoginApp().mainloop()
