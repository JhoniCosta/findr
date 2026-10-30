from importlib import resources

from gi.repository import Gdk, Gtk

from findr.domain.models import ResultGroup, SearchResult
from findr.ui.controller import SearchController
from findr.ui.labels import group_title
from findr.ui.result_row import ResultRow


class LauncherWindow(Gtk.ApplicationWindow):
    """Passive view of the search bar.

    In *overlay* mode (needs a compositor, always true on Wayland) the window is
    a translucent maximized layer with the panel at the upper third of the
    screen, exactly where Spotlight sits; clicking outside the panel closes it.
    Otherwise it falls back to a plain centered window.
    """

    PANEL_WIDTH = 680
    MAX_RESULTS_HEIGHT = 460
    TOP_OFFSET_RATIO = 0.22
    PLACEHOLDER = "Busca Findr"

    def __init__(self, application: Gtk.Application, controller: SearchController,
                 overlay: bool, hide_on_focus_loss: bool) -> None:
        super().__init__(application=application, title="Findr")
        self._controller = controller
        self._hide_on_focus_loss = hide_on_focus_loss
        self._overlay = overlay and self._enable_transparency()

        self._configure_window()
        self._entry = self._build_entry()
        self._list = self._build_list()
        self._scroller = self._build_scroller(self._list)
        self._footer = Gtk.Label(xalign=0)
        self._footer.get_style_context().add_class("findr-footer")
        self._panel = self._build_panel()
        self.add(self._wrap_panel(self._panel))
        # Window.show() maps only the toplevel; children must be shown explicitly.
        # (The results list and footer opt out via set_no_show_all until there are results.)
        self.get_child().show_all()
        self._connect_signals()
        controller.attach(self)

    # ----- LauncherView --------------------------------------------------

    def show_results(self, groups: list[ResultGroup]) -> None:
        for row in self._list.get_children():
            self._list.remove(row)
        for group in groups:
            title = group_title(group)
            for result in group.results:
                self._list.add(ResultRow(result, title))

        has_results = bool(groups)
        self._scroller.set_visible(has_results)
        self._footer.set_visible(has_results)
        self._fit_results_height()
        self._scroller.get_vadjustment().set_value(0)
        if has_results:
            self._list.select_row(self._list.get_row_at_index(0))

    def dismiss(self) -> None:
        self.hide()

    # ----- Public commands ------------------------------------------------

    def summon(self) -> None:
        if self._overlay:
            # Maximize, never fullscreen: Mutter paints an opaque black backdrop
            # behind translucent fullscreen Wayland surfaces.
            self._position_panel()
            self.maximize()
        self.show()
        self.present()
        self._entry.grab_focus()
        self._entry.select_region(0, -1)

    def toggle(self) -> None:
        if self.is_visible():
            self.dismiss()
        else:
            self.summon()

    # ----- Construction ---------------------------------------------------

    def _configure_window(self) -> None:
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG if not self._overlay else Gdk.WindowTypeHint.NORMAL)
        self.get_style_context().add_class("findr-window")
        if self._overlay:
            self.get_style_context().add_class("findr-overlay")
        else:
            self.set_resizable(False)
            self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self._load_css()

    def _enable_transparency(self) -> bool:
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual is None or not screen.is_composited():
            return False
        self.set_visual(visual)
        return True

    @staticmethod
    def _load_css() -> None:
        provider = Gtk.CssProvider()
        provider.load_from_data(resources.files("findr.ui").joinpath("style.css").read_bytes())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _build_entry(self) -> Gtk.SearchEntry:
        entry = Gtk.SearchEntry(placeholder_text=self.PLACEHOLDER)
        entry.get_style_context().add_class("findr-search")
        return entry

    def _build_list(self) -> Gtk.ListBox:
        listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.BROWSE, activate_on_single_click=True)
        listbox.get_style_context().add_class("findr-results")
        listbox.set_header_func(self._update_header)
        return listbox

    def _build_scroller(self, child: Gtk.Widget) -> Gtk.ScrolledWindow:
        scroller = Gtk.ScrolledWindow(
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            propagate_natural_height=True,
            max_content_height=self.MAX_RESULTS_HEIGHT,
        )
        scroller.add(child)
        scroller.set_no_show_all(True)
        child.show()
        return scroller

    def _build_panel(self) -> Gtk.Box:
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        panel.get_style_context().add_class("findr-panel")
        panel.set_size_request(self.PANEL_WIDTH, -1)
        panel.pack_start(self._entry, False, False, 0)
        panel.pack_start(self._scroller, True, True, 0)
        panel.pack_start(self._footer, False, False, 0)
        self._footer.set_no_show_all(True)
        return panel

    def _wrap_panel(self, panel: Gtk.Box) -> Gtk.Widget:
        if not self._overlay:
            return panel
        # Clicks on the panel are swallowed by its EventBox; clicks that reach
        # the outer EventBox therefore landed outside the panel.
        inner = Gtk.EventBox(halign=Gtk.Align.CENTER, valign=Gtk.Align.START)
        inner.add(panel)
        inner.connect("button-press-event", lambda *_: True)
        outer = Gtk.EventBox()
        outer.add(inner)
        outer.connect("button-press-event", lambda *_: self.dismiss() or True)
        return outer

    def _position_panel(self) -> None:
        display = Gdk.Display.get_default()
        monitor = display.get_monitor_at_window(self.get_window()) if self.get_window() else None
        monitor = monitor or display.get_primary_monitor() or display.get_monitor(0)
        if monitor is None:
            return
        # The maximized window starts below the top bar; keep the panel at the
        # same height relative to the whole screen, like Spotlight.
        geometry, workarea = monitor.get_geometry(), monitor.get_workarea()
        offset = int(geometry.height * self.TOP_OFFSET_RATIO) - (workarea.y - geometry.y)
        self._panel.get_parent().set_margin_top(max(0, offset))

    def _connect_signals(self) -> None:
        self._entry.connect("search-changed", lambda entry: self._controller.query_changed(entry.get_text()))
        self._list.connect("row-activated", lambda _list, row: self._controller.activate(row.result))
        self._list.connect("row-selected", self._on_row_selected)
        self.connect("key-press-event", self._on_key_press)
        self.connect("notify::is-active", self._on_active_changed)
        self.connect("delete-event", lambda *_: self.hide_on_delete())

    # ----- Event handlers -------------------------------------------------

    def _on_key_press(self, _widget: Gtk.Widget, event: Gdk.EventKey) -> bool:
        key = event.keyval
        ctrl = bool(event.state & Gdk.ModifierType.CONTROL_MASK)
        if key == Gdk.KEY_Escape:
            if self._entry.get_text():
                self._entry.set_text("")
            else:
                self.dismiss()
            return True
        if key in (Gdk.KEY_Down, Gdk.KEY_Up, Gdk.KEY_Page_Down, Gdk.KEY_Page_Up):
            self._move_selection({Gdk.KEY_Down: 1, Gdk.KEY_Up: -1, Gdk.KEY_Page_Down: 5, Gdk.KEY_Page_Up: -5}[key])
            return True
        if key in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_ISO_Enter):
            selected = self._selected_result()
            if selected:
                self._controller.activate(selected, alternate=ctrl)
            return True
        return False

    def _on_active_changed(self, *_args) -> None:
        if self._hide_on_focus_loss and self.is_visible() and not self.is_active():
            self.dismiss()

    def _on_row_selected(self, _list: Gtk.ListBox, row: ResultRow | None) -> None:
        if row is None:
            return
        self._scroll_to(row)
        hint = f"↵ {row.result.action.label}"
        if row.result.alternate_action:
            hint += f"     Ctrl+↵ {row.result.alternate_action.label}"
        self._footer.set_text(hint + "     Esc fechar")

    # ----- Helpers ---------------------------------------------------------

    def _fit_results_height(self) -> None:
        """Grow/shrink with the results: GTK 3 windows only honour *minimum* size changes."""
        _minimum, natural = self._list.get_preferred_height()
        self._scroller.set_min_content_height(min(natural, self.MAX_RESULTS_HEIGHT))
        if not self._overlay:
            self.resize(self.PANEL_WIDTH, 1)

    def _selected_result(self) -> SearchResult | None:
        row = self._list.get_selected_row()
        return row.result if row else None

    def _move_selection(self, step: int) -> None:
        rows = self._list.get_children()
        if not rows:
            return
        current = self._list.get_selected_row()
        index = current.get_index() if current else -1
        self._list.select_row(rows[max(0, min(len(rows) - 1, index + step))])

    def _scroll_to(self, row: Gtk.ListBoxRow) -> None:
        allocation = row.get_allocation()
        adjustment = self._scroller.get_vadjustment()
        top, bottom = allocation.y, allocation.y + allocation.height
        if top < adjustment.get_value():
            adjustment.set_value(top)
        elif bottom > adjustment.get_value() + adjustment.get_page_size():
            adjustment.set_value(bottom - adjustment.get_page_size())

    @staticmethod
    def _update_header(row: ResultRow, before: ResultRow | None) -> None:
        if before is not None and before.section_title == row.section_title:
            row.set_header(None)
            return
        if row.get_header() is None:
            header = Gtk.Label(label=row.section_title.upper(), xalign=0)
            header.get_style_context().add_class("findr-section")
            row.set_header(header)
