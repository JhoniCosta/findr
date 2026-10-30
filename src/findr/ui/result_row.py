from gi.repository import Gio, GLib, Gtk, Pango

from findr.domain.models import SearchResult


class ResultRow(Gtk.ListBoxRow):
    ICON_SIZE = 32
    FALLBACK_ICON = "application-x-executable"

    def __init__(self, result: SearchResult, section_title: str) -> None:
        super().__init__()
        self.result = result
        self.section_title = section_title
        self.get_style_context().add_class("findr-row")

        layout = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        layout.pack_start(self._icon(), False, False, 0)
        layout.pack_start(self._texts(), True, True, 0)
        self.add(layout)
        self.show_all()

    def _icon(self) -> Gtk.Image:
        image = Gtk.Image.new_from_gicon(self._resolve_icon(self.result.icon), Gtk.IconSize.DND)
        image.set_pixel_size(self.ICON_SIZE)
        return image

    def _texts(self) -> Gtk.Box:
        texts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1, valign=Gtk.Align.CENTER)
        texts.pack_start(self._label(self.result.title, "findr-title", Pango.EllipsizeMode.END), False, False, 0)
        if self.result.subtitle:
            texts.pack_start(
                self._label(self.result.subtitle, "findr-subtitle", Pango.EllipsizeMode.MIDDLE), False, False, 0
            )
        return texts

    @staticmethod
    def _label(text: str, css_class: str, ellipsize: Pango.EllipsizeMode) -> Gtk.Label:
        label = Gtk.Label(label=text, xalign=0, ellipsize=ellipsize)
        label.get_style_context().add_class(css_class)
        return label

    @classmethod
    def _resolve_icon(cls, descriptor: str | None) -> Gio.Icon:
        if descriptor:
            try:
                return Gio.Icon.new_for_string(descriptor)
            except GLib.Error:
                pass
        return Gio.ThemedIcon.new(cls.FALLBACK_ICON)
