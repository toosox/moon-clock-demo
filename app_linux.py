"""Moon Clock Demo: a standalone, offline Linux desktop app."""

from __future__ import annotations

from datetime import datetime, time
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk

from moon_phase import calculate_moon_data


class MoonPhaseWindow(Gtk.Window):
    def __init__(self) -> None:
        super().__init__(title="Moon Clock Demo")
        self.set_border_width(28)
        self.set_default_size(500, 800)
        self.set_resizable(False)
        self.set_decorated(False)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.connect("destroy", Gtk.main_quit)

        overlay = Gtk.Overlay()
        self.add(overlay)

        self.background_image = GdkPixbuf.Pixbuf.new_from_file(
            str(Path(__file__).parent / "assets" / "purple-celestial-background.png")
        )
        background = Gtk.DrawingArea()
        background.connect("draw", self.draw_background)
        overlay.add(background)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        card.set_halign(Gtk.Align.FILL)
        card.set_valign(Gtk.Align.FILL)
        card.get_style_context().add_class("content-card")
        overlay.add_overlay(card)

        self.settings = {
            "use_12_hour_time": True,
            "show_illumination": False,
            "show_lunar_age": False,
            "show_waxing_waning": True,
            "show_next_phase": True,
        }
        self.current_local_moment: datetime | None = None
        self.current_moon_data = None

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        eyebrow = Gtk.Label(label="MOON CLOCK DEMO", xalign=0)
        eyebrow.get_style_context().add_class("eyebrow")
        header.pack_start(eyebrow, False, False, 0)

        settings_button = Gtk.Button.new_from_icon_name(
            "emblem-system-symbolic", Gtk.IconSize.BUTTON
        )
        settings_button.set_tooltip_text("Settings")
        settings_button.get_style_context().add_class("settings-button")
        settings_button.connect("clicked", self.show_settings)
        window_controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        window_controls.pack_start(settings_button, False, False, 0)

        minimize_button = Gtk.Button.new_from_icon_name(
            "window-minimize-symbolic", Gtk.IconSize.BUTTON
        )
        minimize_button.set_tooltip_text("Minimize")
        minimize_button.get_style_context().add_class("window-control")
        minimize_button.connect("clicked", lambda _button: self.iconify())
        window_controls.pack_start(minimize_button, False, False, 0)

        close_button = Gtk.Button.new_from_icon_name(
            "window-close-symbolic", Gtk.IconSize.BUTTON
        )
        close_button.set_tooltip_text("Close")
        close_button.get_style_context().add_class("window-control")
        close_button.connect("clicked", lambda _button: self.destroy())
        window_controls.pack_start(close_button, False, False, 0)
        header.pack_end(window_controls, False, False, 0)

        drag_area = Gtk.EventBox()
        drag_area.set_visible_window(False)
        drag_area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        drag_area.connect("button-press-event", self.begin_window_move)
        drag_area.add(header)
        card.pack_start(drag_area, False, False, 0)

        self.date_label = Gtk.Label(xalign=0)
        self.date_label.set_line_wrap(True)
        self.date_label.get_style_context().add_class("muted")
        card.pack_start(self.date_label, False, False, 0)

        self.phase_label = Gtk.Label(xalign=0.5)
        self.phase_label.get_style_context().add_class("phase")

        self.moon_graphic = Gtk.DrawingArea()
        self.moon_graphic.set_size_request(-1, 196)
        self.moon_graphic.connect("draw", self.draw_moon)
        card.pack_start(self.moon_graphic, False, False, 0)
        card.pack_start(self.phase_label, False, False, 0)

        self.details_grid = Gtk.Grid(column_spacing=16, row_spacing=0)
        self.details_grid.set_column_homogeneous(True)
        card.pack_start(self.details_grid, False, False, 4)

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        card.pack_start(separator, False, False, 6)

        chooser_label = Gtk.Label(label="Choose a local date", xalign=0)
        chooser_label.get_style_context().add_class("muted")
        card.pack_start(chooser_label, False, False, 0)

        self.calendar = Gtk.Calendar()
        self.calendar.connect("day-selected", self.on_date_selected)
        card.pack_start(self.calendar, False, False, 0)

        self.load_styles()
        now = datetime.now().astimezone()
        self.update_clock_label(now)
        self.update_for_datetime(now)
        GLib.timeout_add_seconds(1, self.refresh_clock)

    def load_styles(self) -> None:
        css = b"""
            window {
                background-color: #111a1c;
            }
            .content-card {
                color: #f4f1df;
                background-color: rgba(20, 12, 40, 0.72);
            }
            .content-card label { color: #f4f1df; }
            .eyebrow { color: #a9c58d; font-size: 10pt; font-weight: bold; }
            .title { font-size: 20pt; font-weight: bold; }
            .phase { color: #f4f1df; font-size: 21pt; font-weight: bold; }
            .muted { color: #c4c1d0; }
            .detail-cell { padding: 10px 8px; }
            .detail-value { color: #f4f1df; font-size: 11pt; font-weight: 600; }
            .detail-caption { color: #b8b4c7; font-size: 9pt; }
            .detail-divider { background-color: rgba(220, 234, 181, 0.16); }
            .help-section-title { color: #dceab5; font-size: 10pt; font-weight: bold; }
            .help-number { color: #a9c58d; font-size: 9pt; font-weight: bold; }
            .help-copy { color: #f4f1df; font-size: 10pt; }
            .policy-copy { color: #f4f1df; font-size: 9pt; }
            .settings-button {
                color: #dceab5;
                background: transparent;
                border: none;
                box-shadow: none;
            }
            .window-control {
                color: #dceab5;
                background: transparent;
                border: none;
                box-shadow: none;
            }
            separator { background-color: rgba(244, 241, 223, 0.22); }
            calendar { color: #f4f1df; }
            calendar.header { color: #f4f1df; }
            calendar:selected { background-color: #5f8050; color: #ffffff; }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            self.get_screen(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def begin_window_move(self, _header: Gtk.Box, event) -> bool:
        """Allow the custom top bar to move the undecorated window."""
        if event.button == 1:
            self.begin_move_drag(event.button, event.x_root, event.y_root, event.time)
        return False

    def on_date_selected(self, _calendar: Gtk.Calendar) -> None:
        year, month_zero_based, day = self.calendar.get_date()
        local_tz = datetime.now().astimezone().tzinfo
        selected_date = datetime(year, month_zero_based + 1, day).date()
        now = datetime.now().astimezone()
        selected_time = time(12, 0, tzinfo=local_tz)
        selected = datetime.combine(
            selected_date, selected_time
        )
        self.update_for_datetime(selected)

    def refresh_clock(self) -> bool:
        """Keep the top date and time synced to the computer's local clock."""
        self.update_clock_label(datetime.now().astimezone())
        return True

    def update_clock_label(self, local_moment: datetime) -> None:
        time_format = "%-I:%M %p" if self.settings["use_12_hour_time"] else "%H:%M"
        self.date_label.set_text(
            f"{local_moment.strftime('%A, %B %-d, %Y at ')}"
            f"{local_moment.strftime(time_format)} {local_moment.strftime('%Z')}"
        )

    def draw_background(self, area: Gtk.DrawingArea, context) -> bool:
        """Cover the window with the saved celestial artwork."""
        width = area.get_allocated_width()
        height = area.get_allocated_height()

        source_width = self.background_image.get_width()
        source_height = self.background_image.get_height()
        scale = max(width / source_width, height / source_height)
        offset_x = width - source_width * scale
        offset_y = (height - source_height * scale) / 2

        context.save()
        context.translate(offset_x, offset_y)
        context.scale(scale, scale)
        Gdk.cairo_set_source_pixbuf(context, self.background_image, 0, 0)
        context.paint()
        context.restore()

        return False

    def show_settings(self, _button: Gtk.Button) -> None:
        dialog = Gtk.Dialog(title="Settings", transient_for=self, flags=0)
        dialog.add_button("Close", Gtk.ResponseType.CLOSE)
        dialog.set_default_size(390, 440)

        content = dialog.get_content_area()
        content.set_border_width(18)
        content.set_spacing(10)

        pages = Gtk.Stack()
        pages.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        switcher = Gtk.StackSwitcher()
        switcher.set_stack(pages)
        switcher.set_halign(Gtk.Align.CENTER)
        content.pack_start(switcher, False, False, 0)

        settings_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        settings_page.pack_start(
            self.make_settings_section(
                "Display",
                (
                    ("Use 12-hour time", "use_12_hour_time"),
                    ("Show waxing or waning", "show_waxing_waning"),
                    ("Show next Moon phase", "show_next_phase"),
                ),
            ),
            False,
            False,
            0,
        )
        pages.add_titled(settings_page, "settings", "Settings")
        pages.add_titled(self.make_help_page(), "help", "Help")
        policy_scroll = Gtk.ScrolledWindow()
        policy_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        policy_scroll.add(self.make_policy_page())
        pages.add_titled(policy_scroll, "policy", "Policy")
        copyright_scroll = Gtk.ScrolledWindow()
        copyright_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        copyright_scroll.add(self.make_copyright_page())
        pages.add_titled(copyright_scroll, "copyright", "Licence")
        content.pack_start(pages, True, True, 0)

        dialog.connect("response", lambda current_dialog, _response: current_dialog.destroy())
        dialog.show_all()

    @staticmethod
    def make_help_page() -> Gtk.Box:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        page.set_border_width(10)
        heading = Gtk.Label(label="Help", xalign=0)
        heading.get_style_context().add_class("title")
        page.pack_start(heading, False, False, 0)
        intro = Gtk.Label(label="Using Moon Clock", xalign=0)
        intro.get_style_context().add_class("help-section-title")
        page.pack_start(intro, False, False, 0)

        tips = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=11)
        for number, text in enumerate((
            "The clock shows your computer's local date and time.",
            "Choose a date on the calendar to preview the Moon phase for that day.",
            "Choose which Moon details to show using the Display options.",
        ), start=1):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            number_label = Gtk.Label(label=f"{number:02}", xalign=0)
            number_label.get_style_context().add_class("help-number")
            row.pack_start(number_label, False, False, 0)
            text_label = Gtk.Label(label=text, xalign=0)
            text_label.set_line_wrap(True)
            text_label.set_max_width_chars(42)
            text_label.set_xalign(0)
            text_label.get_style_context().add_class("help-copy")
            row.pack_start(text_label, True, True, 0)
            tips.pack_start(row, False, False, 0)
        page.pack_start(tips, False, False, 0)

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        page.pack_start(separator, False, False, 2)

        contact = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        contact_heading = Gtk.Label(label="NEED HELP?", xalign=0)
        contact_heading.get_style_context().add_class("help-section-title")
        contact.pack_start(contact_heading, False, False, 0)
        contact_placeholder = Gtk.Label(label="Moon Clock support", xalign=0)
        contact_placeholder.get_style_context().add_class("muted")
        contact.pack_start(contact_placeholder, False, False, 0)
        page.pack_start(contact, False, False, 0)

        return page

    @staticmethod
    def make_policy_page() -> Gtk.Widget:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        page.set_border_width(10)
        heading = Gtk.Label(label="Privacy Policy", xalign=0)
        heading.get_style_context().add_class("title")
        page.pack_start(heading, False, False, 0)
        intro = Gtk.Label(
            label="Last updated: [date]",
            xalign=0,
        )
        intro.set_line_wrap(True)
        intro.set_max_width_chars(46)
        intro.get_style_context().add_class("muted")
        page.pack_start(intro, False, False, 0)

        sections = (
            (
                "Who we are",
                "TarotByAndrew.com is an online business based in Oklahoma City.",
            ),
            (
                "When we were formed",
                "TarotByAndrew.com is registered in Oklahoma. The business began operating in 2015.",
            ),
            (
                "Data protection",
                "TarotByAndrew.com handles personal information in accordance with applicable data protection and privacy laws. Privacy enquiries can be submitted through TarotByAndrew.com.",
            ),
            (
                "What we do with data",
                "Personal information provided to TarotByAndrew.com in connection with an enquiry or purchase may be processed to respond to the enquiry, fulfil the purchase, provide customer support, maintain necessary business records, and provide information about our products, services, updates, and related offers. TarotByAndrew.com does not sell, share, or provide personal information to third-party companies for their own use, and does not send unsolicited emails.",
            ),
            (
                "How we protect personal information",
                "TarotByAndrew.com does not collect or store customers’ credit or debit card details. Personal information retained by the business is stored offline and accessed only when needed for business operations, customer support, and accounting. Information may be retained or disclosed where required by law or requested by a competent authority.",
            ),
            (
                "How long we keep data",
                "TarotByAndrew.com retains personal information for at least one year. Information may be kept longer where needed for business operations, customer support, accounting, or legal obligations. Individuals may request the deletion of personal information held by TarotByAndrew.com. We will review and respond to each request in accordance with applicable data protection laws. Some information may need to be retained where required by law or for legitimate business recordkeeping.",
            ),
            (
                "Contact details",
                "Privacy enquiries and requests to access, correct, or delete personal information may be submitted through TarotByAndrew.com.",
            ),
        )
        for title, body in sections:
            section = Gtk.Expander(label=title)
            section.set_expanded(False)
            text = Gtk.Label(label=body, xalign=0, yalign=0)
            text.set_line_wrap(True)
            text.set_max_width_chars(48)
            text.set_selectable(True)
            text.set_margin_start(8)
            text.set_margin_top(6)
            text.set_margin_bottom(8)
            text.get_style_context().add_class("policy-copy")
            section.add(text)
            page.pack_start(section, False, False, 0)
        return page

    @staticmethod
    def make_copyright_page() -> Gtk.Box:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.set_border_width(10)
        heading = Gtk.Label(label="Licence and Copyright", xalign=0)
        heading.get_style_context().add_class("title")
        page.pack_start(heading, False, False, 0)

        notice = Gtk.Label(
            label=(Path(__file__).parent / "DEMO-LICENSE.txt").read_text(encoding="utf-8"),
            xalign=0,
            yalign=0,
        )
        notice.set_line_wrap(True)
        notice.set_max_width_chars(48)
        notice.set_selectable(True)
        notice.get_style_context().add_class("policy-copy")
        page.pack_start(notice, False, False, 0)
        return page

    @staticmethod
    def make_blank_page(title: str) -> Gtk.Box:
        """Create an empty settings page ready for its future content."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        heading = Gtk.Label(label=title, xalign=0)
        heading.get_style_context().add_class("title")
        page.pack_start(heading, False, False, 0)
        return page

    def make_settings_section(
        self, title: str, options: tuple[tuple[str, str], ...]
    ) -> Gtk.Box:
        section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)

        section_title = Gtk.Label(label=title, xalign=0)
        section_title.get_style_context().add_class("eyebrow")
        section.pack_start(section_title, False, False, 0)

        for label, setting_name in options:
            check = Gtk.CheckButton(label=label)
            check.set_active(self.settings[setting_name])
            check.connect("toggled", self.on_setting_toggled, setting_name)
            section.pack_start(check, False, False, 0)

        return section

    def on_setting_toggled(self, check: Gtk.CheckButton, setting_name: str) -> None:
        self.settings[setting_name] = check.get_active()
        self.update_clock_label(datetime.now().astimezone())
        if self.current_local_moment is not None:
            self.update_for_datetime(self.current_local_moment)

    def draw_moon(self, area: Gtk.DrawingArea, context) -> bool:
        """Draw the calculated lunar phase without relying on a static image."""
        if self.current_moon_data is None:
            return False

        width = area.get_allocated_width()
        height = area.get_allocated_height()
        radius = min(width, height) * 0.37
        center_x = width / 2
        center_y = height / 2

        context.save()
        # Soft, restrained halo behind the Moon.
        for glow_radius, alpha in ((radius * 1.55, 0.025), (radius * 1.28, 0.045)):
            context.arc(center_x, center_y, glow_radius, 0, 2 * 3.141592653589793)
            context.set_source_rgba(0.86, 0.88, 0.98, alpha)
            context.fill()

        context.arc(center_x, center_y, radius, 0, 2 * 3.141592653589793)
        context.set_source_rgb(0.10, 0.15, 0.16)
        context.fill_preserve()
        context.clip()

        context.arc(center_x, center_y, radius, 0, 2 * 3.141592653589793)
        context.set_source_rgb(0.95, 0.93, 0.79)
        context.fill()

        illumination = self.current_moon_data.illumination_percent / 100
        shadow_offset = 2 * radius * illumination
        shadow_x = (
            center_x - shadow_offset
            if self.current_moon_data.waxing
            else center_x + shadow_offset
        )
        context.arc(shadow_x, center_y, radius, 0, 2 * 3.141592653589793)
        context.set_source_rgb(0.10, 0.15, 0.16)
        context.fill()
        context.restore()

        context.arc(center_x, center_y, radius, 0, 2 * 3.141592653589793)
        context.set_source_rgba(0.66, 0.77, 0.55, 0.5)
        context.set_line_width(1.4)
        context.stroke()
        return False

    def update_for_datetime(self, local_moment: datetime) -> None:
        self.current_local_moment = local_moment
        data = calculate_moon_data(local_moment)
        self.current_moon_data = data
        time_format = "%-I:%M %p" if self.settings["use_12_hour_time"] else "%H:%M"
        self.phase_label.set_text(data.phase_name)
        next_local = data.next_phase_utc.astimezone(local_moment.tzinfo)
        detail_items: list[tuple[str, str]] = []
        if self.settings["show_illumination"]:
            detail_items.append(("ILLUMINATION", f"{data.illumination_percent:.1f}%"))
        if self.settings["show_lunar_age"]:
            detail_items.append(("LUNAR AGE", f"{data.age_days:.1f} days"))
        if self.settings["show_waxing_waning"]:
            detail_items.append(("DIRECTION", "Waxing" if data.waxing else "Waning"))
        if self.settings["show_next_phase"]:
            detail_items.append(
                (
                    f"NEXT {data.next_phase_name.upper()}",
                    f"{next_local.strftime('%b %-d, %-I:%M %p' if self.settings['use_12_hour_time'] else '%b %-d, %H:%M')} {next_local.strftime('%Z')}",
                )
            )

        for child in self.details_grid.get_children():
            self.details_grid.remove(child)
        for index, (caption, value) in enumerate(detail_items):
            cell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            cell.set_halign(Gtk.Align.FILL)
            cell.get_style_context().add_class("detail-cell")
            value_label = Gtk.Label(label=value, xalign=0)
            value_label.get_style_context().add_class("detail-value")
            caption_label = Gtk.Label(label=caption, xalign=0)
            caption_label.get_style_context().add_class("detail-caption")
            cell.pack_start(value_label, False, False, 0)
            cell.pack_start(caption_label, False, False, 0)
            self.details_grid.attach(cell, index % 2, index // 2, 1, 1)

        if len(detail_items) > 1:
            divider = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
            divider.get_style_context().add_class("detail-divider")
            self.details_grid.attach(divider, 0, 1, 2, 1)
            if len(detail_items) == 4:
                vertical_divider = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
                vertical_divider.get_style_context().add_class("detail-divider")
                self.details_grid.attach(vertical_divider, 1, 0, 1, 2)
        self.details_grid.show_all()
        self.moon_graphic.queue_draw()


def main() -> None:
    window = MoonPhaseWindow()
    window.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
