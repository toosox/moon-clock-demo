"""Windows-native Moon Clock Demo interface."""

from __future__ import annotations

import calendar
import math
import os
import sys
import tkinter as tk
from datetime import date, datetime, time
from pathlib import Path
from tkinter import ttk

from PIL import Image, ImageChops, ImageDraw, ImageTk

from moon_phase import calculate_moon_data


WINDOW_WIDTH = 500
WINDOW_HEIGHT = 800
CARD = "#201330"
TEXT = "#f4f1df"
MUTED = "#c4c1d0"
ACCENT = "#a9c58d"
DARK = "#1a2528"


def resource_path(*parts: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base.joinpath(*parts)


def format_clock(moment: datetime, twelve_hour: bool) -> str:
    if twelve_hour:
        shown_time = f"{int(moment.strftime('%I'))}:{moment:%M %p}"
    else:
        shown_time = moment.strftime("%H:%M")
    zone = moment.strftime("%Z")
    suffix = f" {zone}" if zone else ""
    return f"{moment:%A, %B} {moment.day}, {moment.year} at {shown_time}{suffix}"


def format_next_phase(moment: datetime, twelve_hour: bool) -> str:
    if twelve_hour:
        shown_time = f"{int(moment.strftime('%I'))}:{moment:%M %p}"
    else:
        shown_time = moment.strftime("%H:%M")
    zone = moment.strftime("%Z")
    suffix = f" {zone}" if zone else ""
    return f"{moment:%b} {moment.day}, {shown_time}{suffix}"


class MoonClock(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Moon Clock Demo")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)
        self.overrideredirect(True)
        self.configure(bg=CARD)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.settings = {
            "use_12_hour_time": tk.BooleanVar(value=True),
            "show_illumination": tk.BooleanVar(value=False),
            "show_lunar_age": tk.BooleanVar(value=False),
            "show_waxing_waning": tk.BooleanVar(value=True),
            "show_next_phase": tk.BooleanVar(value=True),
        }
        self.current_local_moment: datetime | None = None
        self.current_moon_data = None
        self.calendar_date = datetime.now().astimezone().date()
        self.display_month = self.calendar_date.replace(day=1)
        self._drag_x = 0
        self._drag_y = 0

        self._load_background()
        self._build_interface()
        now = datetime.now().astimezone()
        self.update_clock_label(now)
        self.update_for_datetime(now)
        self.render_calendar()
        self.after(1000, self.refresh_clock)

    def _load_background(self) -> None:
        source = Image.open(resource_path("assets", "purple-celestial-background.png"))
        scale = max(WINDOW_WIDTH / source.width, WINDOW_HEIGHT / source.height)
        resized = source.resize(
            (round(source.width * scale), round(source.height * scale)),
            Image.Resampling.LANCZOS,
        )
        left = resized.width - WINDOW_WIDTH
        top = max(0, (resized.height - WINDOW_HEIGHT) // 2)
        cropped = resized.crop((left, top, left + WINDOW_WIDTH, top + WINDOW_HEIGHT))
        self.background_photo = ImageTk.PhotoImage(cropped)
        background = tk.Label(self, image=self.background_photo, borderwidth=0)
        background.place(x=0, y=0, relwidth=1, relheight=1)

    def _build_interface(self) -> None:
        self.card = tk.Frame(self, bg=CARD, padx=18, pady=14)
        self.card.place(x=28, y=22, width=444, height=756)

        header = tk.Frame(self.card, bg=CARD, cursor="fleur")
        header.pack(fill="x")
        header.bind("<ButtonPress-1>", self.start_drag)
        header.bind("<B1-Motion>", self.drag_window)
        heading = tk.Label(
            header, text="MOON CLOCK DEMO", bg=CARD, fg=ACCENT,
            font=("Segoe UI", 9, "bold"),
        )
        heading.pack(side="left")
        heading.bind("<ButtonPress-1>", self.start_drag)
        heading.bind("<B1-Motion>", self.drag_window)

        for text, command, description in (
            ("⚙", self.show_settings, "Settings"),
            ("—", self.minimize_window, "Minimize"),
            ("×", self.destroy, "Close"),
        ):
            button = tk.Button(
                header, text=text, command=command, bg=CARD, fg=ACCENT,
                activebackground="#35234c", activeforeground=TEXT,
                relief="flat", borderwidth=0, font=("Segoe UI", 12),
                width=2, cursor="hand2",
            )
            button.pack(side="right")
            self._tooltip(button, description)

        self.date_label = tk.Label(
            self.card, bg=CARD, fg=MUTED, anchor="w", justify="left",
            font=("Segoe UI", 9), wraplength=400,
        )
        self.date_label.pack(fill="x", pady=(6, 0))

        self.moon_label = tk.Label(self.card, bg=CARD, borderwidth=0)
        self.moon_label.pack(pady=(2, 0))
        self.phase_label = tk.Label(
            self.card, bg=CARD, fg=TEXT, font=("Segoe UI", 20, "bold"),
        )
        self.phase_label.pack(pady=(0, 4))

        self.details = tk.Frame(self.card, bg=CARD, height=92)
        self.details.pack(fill="x")
        self.details.pack_propagate(False)

        tk.Frame(self.card, bg="#5c5266", height=1).pack(fill="x", pady=(7, 7))
        tk.Label(
            self.card, text="Choose a local date", bg=CARD, fg=MUTED,
            anchor="w", font=("Segoe UI", 9),
        ).pack(fill="x")

        calendar_header = tk.Frame(self.card, bg=CARD)
        calendar_header.pack(fill="x", pady=(3, 2))
        self._calendar_button(calendar_header, "‹", lambda: self.change_month(-1)).pack(side="left")
        self.month_label = tk.Label(
            calendar_header, bg=CARD, fg=TEXT, font=("Segoe UI", 10, "bold"),
        )
        self.month_label.pack(side="left", expand=True)
        self._calendar_button(calendar_header, "›", lambda: self.change_month(1)).pack(side="right")

        self.calendar_grid = tk.Frame(self.card, bg=CARD)
        self.calendar_grid.pack(fill="both", expand=True)

    @staticmethod
    def _tooltip(_widget: tk.Widget, _text: str) -> None:
        # Button labels remain visible; native tooltip dependencies are unnecessary.
        return

    def _calendar_button(self, parent: tk.Widget, text: str, command) -> tk.Button:
        return tk.Button(
            parent, text=text, command=command, bg=CARD, fg=ACCENT,
            activebackground="#35234c", activeforeground=TEXT,
            relief="flat", borderwidth=0, font=("Segoe UI", 12, "bold"),
            cursor="hand2", width=3,
        )

    def start_drag(self, event) -> None:
        self._drag_x = event.x_root - self.winfo_x()
        self._drag_y = event.y_root - self.winfo_y()

    def drag_window(self, event) -> None:
        self.geometry(f"+{event.x_root - self._drag_x}+{event.y_root - self._drag_y}")

    def minimize_window(self) -> None:
        self.overrideredirect(False)
        self.iconify()
        self.bind("<Map>", self._restore_borderless, add="+")

    def _restore_borderless(self, _event=None) -> None:
        self.after(10, lambda: self.overrideredirect(True))

    def refresh_clock(self) -> None:
        self.update_clock_label(datetime.now().astimezone())
        self.after(1000, self.refresh_clock)

    def update_clock_label(self, local_moment: datetime) -> None:
        self.date_label.configure(
            text=format_clock(local_moment, self.settings["use_12_hour_time"].get())
        )

    def change_month(self, offset: int) -> None:
        month = self.display_month.month - 1 + offset
        year = self.display_month.year + month // 12
        self.display_month = date(year, month % 12 + 1, 1)
        self.render_calendar()

    def render_calendar(self) -> None:
        for child in self.calendar_grid.winfo_children():
            child.destroy()
        self.month_label.configure(text=self.display_month.strftime("%B %Y"))
        for column, label in enumerate(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")):
            tk.Label(
                self.calendar_grid, text=label, bg=CARD, fg=MUTED,
                font=("Segoe UI", 8, "bold"),
            ).grid(row=0, column=column, sticky="nsew", pady=(0, 2))
            self.calendar_grid.columnconfigure(column, weight=1)

        weeks = calendar.Calendar(firstweekday=calendar.MONDAY).monthdayscalendar(
            self.display_month.year, self.display_month.month
        )
        for row, week in enumerate(weeks, start=1):
            self.calendar_grid.rowconfigure(row, weight=1)
            for column, day in enumerate(week):
                if day == 0:
                    continue
                candidate = date(self.display_month.year, self.display_month.month, day)
                selected = candidate == self.calendar_date
                button = tk.Button(
                    self.calendar_grid, text=str(day),
                    command=lambda chosen=candidate: self.select_date(chosen),
                    bg="#5f8050" if selected else CARD,
                    fg="#ffffff" if selected else TEXT,
                    activebackground="#739568", activeforeground="#ffffff",
                    relief="flat", borderwidth=0, font=("Segoe UI", 9),
                    cursor="hand2",
                )
                button.grid(row=row, column=column, sticky="nsew", padx=1, pady=1)

    def select_date(self, selected_date: date) -> None:
        self.calendar_date = selected_date
        local_tz = datetime.now().astimezone().tzinfo
        selected = datetime.combine(selected_date, time(12, 0, tzinfo=local_tz))
        self.update_for_datetime(selected)
        self.render_calendar()

    def update_for_datetime(self, local_moment: datetime) -> None:
        self.current_local_moment = local_moment
        data = calculate_moon_data(local_moment)
        self.current_moon_data = data
        self.phase_label.configure(text=data.phase_name)
        self.draw_moon()

        items: list[tuple[str, str]] = []
        if self.settings["show_illumination"].get():
            items.append(("ILLUMINATION", f"{data.illumination_percent:.1f}%"))
        if self.settings["show_lunar_age"].get():
            items.append(("LUNAR AGE", f"{data.age_days:.1f} days"))
        if self.settings["show_waxing_waning"].get():
            items.append(("DIRECTION", "Waxing" if data.waxing else "Waning"))
        if self.settings["show_next_phase"].get():
            next_local = data.next_phase_utc.astimezone(local_moment.tzinfo)
            items.append((
                f"NEXT {data.next_phase_name.upper()}",
                format_next_phase(next_local, self.settings["use_12_hour_time"].get()),
            ))

        for child in self.details.winfo_children():
            child.destroy()
        for column in range(2):
            self.details.columnconfigure(column, weight=1, uniform="details")
        for index, (caption, value) in enumerate(items):
            cell = tk.Frame(self.details, bg=CARD, padx=7, pady=5)
            cell.grid(row=index // 2, column=index % 2, sticky="nsew")
            tk.Label(
                cell, text=value, bg=CARD, fg=TEXT, anchor="w",
                font=("Segoe UI", 10, "bold"), wraplength=182, justify="left",
            ).pack(fill="x")
            tk.Label(
                cell, text=caption, bg=CARD, fg=MUTED, anchor="w",
                font=("Segoe UI", 7),
            ).pack(fill="x")

    def draw_moon(self) -> None:
        if self.current_moon_data is None:
            return
        size = 174
        radius = 58
        center = size // 2
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        for glow_radius, alpha in ((90, 10), (75, 18)):
            draw.ellipse(
                (center - glow_radius, center - glow_radius,
                 center + glow_radius, center + glow_radius),
                fill=(219, 224, 250, alpha),
            )

        moon_mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(moon_mask).ellipse(
            (center - radius, center - radius, center + radius, center + radius), fill=255
        )
        moon = Image.new("RGBA", (size, size), (242, 237, 201, 255))
        image.paste(moon, (0, 0), moon_mask)

        illumination = self.current_moon_data.illumination_percent / 100
        offset = round(2 * radius * illumination)
        shadow_center = center - offset if self.current_moon_data.waxing else center + offset
        shadow_mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(shadow_mask).ellipse(
            (shadow_center - radius, center - radius,
             shadow_center + radius, center + radius), fill=255
        )
        clipped_shadow = ImageChops.multiply(moon_mask, shadow_mask)
        shadow = Image.new("RGBA", (size, size), (26, 37, 40, 255))
        image.paste(shadow, (0, 0), clipped_shadow)
        draw = ImageDraw.Draw(image)
        draw.ellipse(
            (center - radius, center - radius, center + radius, center + radius),
            outline=(169, 197, 141, 145), width=2,
        )
        self.moon_photo = ImageTk.PhotoImage(image)
        self.moon_label.configure(image=self.moon_photo)

    def on_setting_changed(self) -> None:
        self.update_clock_label(datetime.now().astimezone())
        if self.current_local_moment is not None:
            self.update_for_datetime(self.current_local_moment)

    def show_settings(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Moon Clock Demo Settings")
        dialog.geometry("440x510")
        dialog.resizable(False, False)
        dialog.configure(bg=CARD)
        dialog.transient(self)

        style = ttk.Style(dialog)
        style.theme_use("clam")
        style.configure("Moon.TNotebook", background=CARD, borderwidth=0)
        style.configure(
            "Moon.TNotebook.Tab", background="#35234c", foreground=TEXT,
            padding=(10, 7), borderwidth=0,
        )
        style.map("Moon.TNotebook.Tab", background=[("selected", "#5f8050")])
        notebook = ttk.Notebook(dialog, style="Moon.TNotebook")
        notebook.pack(fill="both", expand=True, padx=12, pady=12)

        settings_page = tk.Frame(notebook, bg=CARD, padx=16, pady=14)
        self._settings_heading(settings_page, "DISPLAY")
        for label, key in (
            ("Use 12-hour time", "use_12_hour_time"),
            ("Show waxing or waning", "show_waxing_waning"),
            ("Show next Moon phase", "show_next_phase"),
        ):
            self._setting_check(settings_page, label, key)
        notebook.add(settings_page, text="Settings")

        notebook.add(self._text_page(notebook, "Help", (
            "Using Moon Clock\n\n"
            "01  The clock shows your computer's local date and time.\n\n"
            "02  Choose a date on the calendar to preview the Moon phase for that day.\n\n"
            "03  Choose which Moon details to show using the Display options.\n\n"
            "NEED HELP?\nMoon Clock support"
        )), text="Help")
        notebook.add(self._policy_page(notebook), text="Policy")
        licence_text = resource_path("DEMO-LICENSE.txt").read_text(encoding="utf-8")
        notebook.add(
            self._scroll_text_page(notebook, "Licence and Copyright", licence_text),
            text="Licence",
        )

        tk.Button(
            dialog, text="Close", command=dialog.destroy, bg="#5f8050", fg="#ffffff",
            activebackground="#739568", activeforeground="#ffffff", relief="flat",
            padx=18, pady=7, cursor="hand2",
        ).pack(pady=(0, 12))

    @staticmethod
    def _settings_heading(parent: tk.Widget, text: str, top: int = 0) -> None:
        tk.Label(
            parent, text=text, bg=CARD, fg=ACCENT,
            font=("Segoe UI", 9, "bold"), anchor="w",
        ).pack(fill="x", pady=(top, 5))

    def _setting_check(self, parent: tk.Widget, label: str, key: str) -> None:
        tk.Checkbutton(
            parent, text=label, variable=self.settings[key], command=self.on_setting_changed,
            bg=CARD, fg=TEXT, selectcolor="#35234c", activebackground=CARD,
            activeforeground=TEXT, font=("Segoe UI", 10), anchor="w",
        ).pack(fill="x", pady=3)

    @staticmethod
    def _text_page(parent: tk.Widget, title: str, body: str) -> tk.Frame:
        page = tk.Frame(parent, bg=CARD, padx=14, pady=14)
        tk.Label(
            page, text=title, bg=CARD, fg=TEXT,
            font=("Segoe UI", 18, "bold"), anchor="w",
        ).pack(fill="x", pady=(0, 12))
        tk.Label(
            page, text=body, bg=CARD, fg=TEXT, font=("Segoe UI", 10),
            justify="left", anchor="nw", wraplength=365,
        ).pack(fill="both", expand=True)
        return page

    @staticmethod
    def _scroll_text_page(parent: tk.Widget, title: str, body: str) -> tk.Frame:
        page = tk.Frame(parent, bg=CARD, padx=14, pady=14)
        tk.Label(
            page, text=title, bg=CARD, fg=TEXT,
            font=("Segoe UI", 18, "bold"), anchor="w",
        ).pack(fill="x", pady=(0, 10))
        text_frame = tk.Frame(page, bg=CARD)
        text_frame.pack(fill="both", expand=True)
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical")
        notice = tk.Text(
            text_frame, wrap="word", bg=CARD, fg=TEXT, insertbackground=TEXT,
            relief="flat", borderwidth=0, font=("Segoe UI", 9),
            yscrollcommand=scrollbar.set, padx=2, pady=2,
        )
        scrollbar.configure(command=notice.yview)
        scrollbar.pack(side="right", fill="y")
        notice.pack(side="left", fill="both", expand=True)
        notice.insert("1.0", body)
        notice.configure(state="disabled")
        return page

    @staticmethod
    def _policy_page(parent: tk.Widget) -> tk.Frame:
        page = tk.Frame(parent, bg=CARD)
        canvas = tk.Canvas(page, bg=CARD, highlightthickness=0)
        scrollbar = ttk.Scrollbar(page, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg=CARD, padx=14, pady=14)
        content.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=content, anchor="nw", width=385)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        tk.Label(
            content, text="Privacy Policy", bg=CARD, fg=TEXT,
            font=("Segoe UI", 18, "bold"), anchor="w",
        ).pack(fill="x")
        tk.Label(
            content, text="Last updated: [date]", bg=CARD, fg=MUTED,
            font=("Segoe UI", 9), anchor="w",
        ).pack(fill="x", pady=(0, 12))
        sections = (
            ("Who we are", "TarotByAndrew.com is an online business based in Oklahoma City."),
            ("When we were formed", "TarotByAndrew.com is registered in Oklahoma. The business began operating in 2015."),
            ("Data protection", "TarotByAndrew.com handles personal information in accordance with applicable data protection and privacy laws. Privacy enquiries can be submitted through TarotByAndrew.com."),
            ("What we do with data", "Personal information provided to TarotByAndrew.com in connection with an enquiry or purchase may be processed to respond to the enquiry, fulfil the purchase, provide customer support, maintain necessary business records, and provide information about our products, services, updates, and related offers. TarotByAndrew.com does not sell, share, or provide personal information to third-party companies for their own use, and does not send unsolicited emails."),
            ("How we protect personal information", "TarotByAndrew.com does not collect or store customers’ credit or debit card details. Personal information retained by the business is stored offline and accessed only when needed for business operations, customer support, and accounting. Information may be retained or disclosed where required by law or requested by a competent authority."),
            ("How long we keep data", "TarotByAndrew.com retains personal information for at least one year. Information may be kept longer where needed for business operations, customer support, accounting, or legal obligations. Individuals may request the deletion of personal information held by TarotByAndrew.com. We will review and respond to each request in accordance with applicable data protection laws. Some information may need to be retained where required by law or for legitimate business recordkeeping."),
            ("Contact details", "Privacy enquiries and requests to access, correct, or delete personal information may be submitted through TarotByAndrew.com."),
        )
        for title, body in sections:
            tk.Label(
                content, text=title, bg=CARD, fg=ACCENT,
                font=("Segoe UI", 10, "bold"), anchor="w",
            ).pack(fill="x", pady=(8, 2))
            tk.Label(
                content, text=body, bg=CARD, fg=TEXT, font=("Segoe UI", 9),
                justify="left", anchor="w", wraplength=350,
            ).pack(fill="x")
        return page


def main() -> None:
    app = MoonClock()
    app.mainloop()


if __name__ == "__main__":
    main()
