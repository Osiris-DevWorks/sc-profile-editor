"""Application theme management.

Themes are applied by swapping the Qt palette on the QApplication. Widgets
that need theme-aware text colors should rely on the palette's
WindowText/Text roles (the default); dim labels mark themselves with
`setProperty("role", "secondary")` and an app-level QSS rule (installed by
`apply_theme`) recolors them when the theme changes.

Ported from sibling project `smart-citizen` to keep visual cohesion across
the Osiris DevWorks app suite. The "Default" theme reuses smart-citizen's
SCLE palette (deep navy + cyan).
"""
import logging
import sys
from pathlib import Path

from PyQt6.QtGui import QColor, QFontDatabase, QPalette
from PyQt6.QtWidgets import QApplication, QProxyStyle, QStyle

logger = logging.getLogger(__name__)


# Branded display font used on the main window title. Loaded from
# assets/fonts/ at app startup via load_application_fonts(). The family name
# is what Qt reports after registering the OTF — the Fontspring demo ships
# with a prefixed family string, which we match here.
BRAND_FONT_FAMILY = "FONTSPRING DEMO - Hyperspace Race Expanded"
_BRAND_FONT_FILE = "HyperspaceRace-ExpandedBold.otf"


def _assets_fonts_dir() -> Path:
    """Resolve the assets/fonts directory for both dev and PyInstaller builds."""
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent.parent
    return base / "assets" / "fonts"


def load_application_fonts() -> None:
    """Register bundled display fonts with Qt. Call once at startup after
    QApplication is constructed and before any widgets use the font."""
    font_path = _assets_fonts_dir() / _BRAND_FONT_FILE
    if not font_path.exists():
        logger.warning(f"Brand font not found at {font_path}; using system fallback")
        return
    font_id = QFontDatabase.addApplicationFont(str(font_path))
    if font_id < 0:
        logger.warning(f"Failed to register brand font {font_path}")
        return
    families = QFontDatabase.applicationFontFamilies(font_id)
    logger.info(f"Registered brand font families: {families}")


THEME_LIGHT = "light"
THEME_DARK = "dark"
THEME_DEFAULT = "default"   # uses the SCLE palette (deep navy + cyan)
THEME_ODW = "odw"
AVAILABLE_THEMES = (THEME_LIGHT, THEME_DARK, THEME_DEFAULT, THEME_ODW)
DEFAULT_THEME = THEME_DEFAULT


def _get_current_theme() -> str:
    """Read the persisted theme. Imported lazily to avoid a circular import
    at module load. Tries the absolute ``src.utils.settings`` path first
    (works during early startup before main_window's sys.path munge) and
    falls back to the bare path used by other modules in src/."""
    try:
        from src.utils.settings import AppSettings
    except ImportError:
        from utils.settings import AppSettings
    return AppSettings().get_theme()


# Secondary/dim text color per theme. A single shade can't stay readable on
# both #C8C8C8 (light window) and #0D1826 (default navy) — so we resolve it
# per-theme and surface it via the app-level QSS rule in `_app_stylesheet_for`.
_SECONDARY_TEXT_COLORS = {
    THEME_LIGHT:   "#2A2A2A",
    THEME_DARK:    "#D5D5D5",
    THEME_DEFAULT: "#D5D5D5",
    THEME_ODW:     "#D4B876",
}


# Header action button colors per theme. SCPE's button vocabulary:
#   import      — Import Profile XML (green family — "bring data in")
#   new_profile — New Profile, Save Profile (blue family — "create/persist")
#   preset      — Load Preset Profile (purple family — "template")
#   save        — alias for new_profile (kept distinct in case it diverges)
#
# Light uses Material 500 shades; dark uses Material 300 so buttons read
# softer against the dark background.
_BUTTON_COLORS = {
    THEME_LIGHT: {
        "import":      "#4CAF50",   # Material green 500
        "new_profile": "#2196F3",   # Material blue 500
        "preset":      "#9C27B0",   # Material purple 500
        "save":        "#2196F3",
    },
    THEME_DARK: {
        "import":      "#81C784",   # green 300
        "new_profile": "#64B5F6",   # blue 300
        "preset":      "#BA68C8",   # purple 300
        "save":        "#64B5F6",
    },
    THEME_DEFAULT: {
        "import":      "#4ADE80",   # bright green that pops against navy
        "new_profile": "#4FD7E8",   # cube-glow cyan
        "preset":      "#9D7FE8",   # softer purple toned for navy
        "save":        "#4FD7E8",
    },
    THEME_ODW: {
        "import":      "#A5B989",   # sage green
        "new_profile": "#D4B876",   # brighter gold
        "preset":      "#C77A4D",   # copper (closest "purple-flavor" in the gold/copper family)
        "save":        "#D4B876",
    },
}

# Hover shades — slightly darker for light/default, slightly lighter for
# dark/odw. Computed by hand from the base colors so we don't drag in a
# color-arithmetic dependency.
_BUTTON_HOVER_COLORS = {
    THEME_LIGHT: {
        "import":      "#45a049",
        "new_profile": "#0b7dda",
        "preset":      "#7B1FA2",
        "save":        "#0b7dda",
    },
    THEME_DARK: {
        "import":      "#A5D6A7",
        "new_profile": "#90CAF9",
        "preset":      "#CE93D8",
        "save":        "#90CAF9",
    },
    THEME_DEFAULT: {
        "import":      "#22C55E",
        "new_profile": "#22B8CD",
        "preset":      "#7C5FCC",
        "save":        "#22B8CD",
    },
    THEME_ODW: {
        "import":      "#8DA376",
        "new_profile": "#C9A961",
        "preset":      "#A8623A",
        "save":        "#C9A961",
    },
}


def get_button_color(role: str) -> str:
    """Return the button background color for the given role."""
    theme = _get_current_theme()
    palette = _BUTTON_COLORS.get(theme, _BUTTON_COLORS[DEFAULT_THEME])
    return palette.get(role, palette["new_profile"])


def get_button_hover_color(role: str) -> str:
    theme = _get_current_theme()
    palette = _BUTTON_HOVER_COLORS.get(theme, _BUTTON_HOVER_COLORS[DEFAULT_THEME])
    return palette.get(role, palette["new_profile"])


def get_button_text_color() -> str:
    """Return the readable text color for action buttons.

    Material 500 (light) and the default theme's mid-luminance accents both
    work better with white text. The dark and ODW themes use lighter button
    fills where black reads better.
    """
    theme = _get_current_theme()
    if theme == THEME_DARK or theme == THEME_ODW:
        return "black"
    return "white"


def action_button_stylesheet(role: str) -> str:
    """Return the complete QSS for a header action button at the current theme.

    Mirrors the inline pattern used today in main_window.py so callers can do
    `btn.setStyleSheet(action_button_stylesheet("import"))` instead of
    splicing color hex into a long format string.
    """
    bg = get_button_color(role)
    hover = get_button_hover_color(role)
    text = get_button_text_color()
    return (
        f"QPushButton {{ padding: 10px 20px; font-size: 14px; "
        f"background-color: {bg}; color: {text}; border: none; border-radius: 4px; }} "
        f"QPushButton:hover {{ background-color: {hover}; }} "
        f"QPushButton:disabled {{ background-color: palette(button); color: palette(disabled-text); }}"
    )


# Per-theme color for the branded title label. Each pair ties to the theme's
# signature accent so the header reads as "of" that theme.
_TITLE_COLORS = {
    THEME_LIGHT:   "#1565C0",   # rich blue
    THEME_DARK:    "#64B5F6",   # soft sky blue
    THEME_DEFAULT: "#4FD7E8",   # cube-glow cyan
    THEME_ODW:     "#C9A961",   # Osiris gold
}


def get_title_color() -> str:
    return _TITLE_COLORS.get(_get_current_theme(), _TITLE_COLORS[DEFAULT_THEME])


def _light_palette() -> QPalette:
    """Return a palette matching the Fusion light defaults with adjusted placeholder."""
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window,          QColor(200, 200, 200))
    p.setColor(QPalette.ColorRole.WindowText,      QColor(25, 25, 25))
    p.setColor(QPalette.ColorRole.Base,            QColor(215, 215, 215))
    p.setColor(QPalette.ColorRole.AlternateBase,   QColor(208, 208, 208))
    p.setColor(QPalette.ColorRole.ToolTipBase,     QColor(240, 240, 218))
    p.setColor(QPalette.ColorRole.ToolTipText,     QColor(25, 25, 25))
    p.setColor(QPalette.ColorRole.Text,            QColor(25, 25, 25))
    p.setColor(QPalette.ColorRole.Button,          QColor(200, 200, 200))
    p.setColor(QPalette.ColorRole.ButtonText,      QColor(25, 25, 25))
    p.setColor(QPalette.ColorRole.BrightText,      QColor(255, 0, 0))
    p.setColor(QPalette.ColorRole.Highlight,       QColor(21, 101, 192))   # #1565C0
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    p.setColor(QPalette.ColorRole.Link,            QColor(0, 102, 204))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(90, 90, 90))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(100, 100, 100))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text,       QColor(100, 100, 100))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(100, 100, 100))
    return p


def _dark_palette() -> QPalette:
    """Return a dark palette inspired by the Qt-community 'Fusion dark' pattern."""
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window,          QColor(30, 30, 30))
    p.setColor(QPalette.ColorRole.WindowText,      QColor(232, 232, 232))
    p.setColor(QPalette.ColorRole.Base,            QColor(30, 30, 30))
    p.setColor(QPalette.ColorRole.AlternateBase,   QColor(45, 45, 48))
    p.setColor(QPalette.ColorRole.ToolTipBase,     QColor(45, 45, 48))
    p.setColor(QPalette.ColorRole.ToolTipText,     QColor(232, 232, 232))
    p.setColor(QPalette.ColorRole.Text,            QColor(232, 232, 232))
    p.setColor(QPalette.ColorRole.Button,          QColor(55, 55, 58))
    p.setColor(QPalette.ColorRole.ButtonText,      QColor(232, 232, 232))
    p.setColor(QPalette.ColorRole.BrightText,      QColor(255, 80, 80))
    p.setColor(QPalette.ColorRole.Highlight,       QColor(59, 130, 246))   # #3B82F6
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    p.setColor(QPalette.ColorRole.Link,            QColor(100, 170, 255))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(175, 175, 175))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(150, 150, 150))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text,       QColor(150, 150, 150))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(150, 150, 150))
    return p


def _default_palette() -> QPalette:
    """SCPE 'Default' — deep navy + cyan highlights (mirrors smart-citizen's
    SCLE palette for suite-wide brand cohesion)."""
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window,          QColor(13, 24, 38))    # #0D1826 deep navy
    p.setColor(QPalette.ColorRole.WindowText,      QColor(216, 232, 240)) # #D8E8F0 silver-blue
    p.setColor(QPalette.ColorRole.Base,            QColor(13, 24, 38))
    p.setColor(QPalette.ColorRole.AlternateBase,   QColor(21, 37, 56))    # #152538
    p.setColor(QPalette.ColorRole.ToolTipBase,     QColor(21, 37, 56))
    p.setColor(QPalette.ColorRole.ToolTipText,     QColor(216, 232, 240))
    p.setColor(QPalette.ColorRole.Text,            QColor(216, 232, 240))
    p.setColor(QPalette.ColorRole.Button,          QColor(26, 45, 68))    # #1A2D44 raised panel
    p.setColor(QPalette.ColorRole.ButtonText,      QColor(216, 232, 240))
    p.setColor(QPalette.ColorRole.BrightText,      QColor(255, 138, 66))  # #FF8A42 orange accent
    p.setColor(QPalette.ColorRole.Highlight,       QColor(0, 153, 204))   # #0099CC
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(10, 18, 32))
    p.setColor(QPalette.ColorRole.Link,            QColor(79, 215, 232))  # #4FD7E8
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(111, 181, 208))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(88, 120, 144))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text,       QColor(88, 120, 144))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(88, 120, 144))
    return p


def _odw_palette() -> QPalette:
    """Osiris DevWorks branded palette — navy charcoal + antique gold."""
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window,          QColor(26, 31, 46))    # #1A1F2E navy
    p.setColor(QPalette.ColorRole.WindowText,      QColor(240, 230, 207)) # #F0E6CF cream
    p.setColor(QPalette.ColorRole.Base,            QColor(26, 31, 46))
    p.setColor(QPalette.ColorRole.AlternateBase,   QColor(36, 41, 56))    # #242938 panel
    p.setColor(QPalette.ColorRole.ToolTipBase,     QColor(36, 41, 56))
    p.setColor(QPalette.ColorRole.ToolTipText,     QColor(240, 230, 207))
    p.setColor(QPalette.ColorRole.Text,            QColor(240, 230, 207))
    p.setColor(QPalette.ColorRole.Button,          QColor(36, 41, 56))
    p.setColor(QPalette.ColorRole.ButtonText,      QColor(240, 230, 207))
    p.setColor(QPalette.ColorRole.BrightText,      QColor(199, 122, 77))  # #C77A4D copper
    p.setColor(QPalette.ColorRole.Highlight,       QColor(212, 160, 23))  # #D4A017
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(26, 31, 46))
    p.setColor(QPalette.ColorRole.Link,            QColor(212, 184, 118))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(160, 140, 90))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(100, 90, 70))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text,       QColor(100, 90, 70))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(100, 90, 70))
    return p


def _palette_for(theme: str) -> QPalette:
    if theme == THEME_DARK:
        return _dark_palette()
    if theme == THEME_DEFAULT:
        return _default_palette()
    if theme == THEME_ODW:
        return _odw_palette()
    return _light_palette()


def _app_stylesheet_for(theme: str) -> str:
    """QSS applied at the QApplication level. Used for widget-role rules that
    need to re-color on live theme swap without walking every tracked label."""
    secondary = _SECONDARY_TEXT_COLORS.get(theme, _SECONDARY_TEXT_COLORS[DEFAULT_THEME])
    return f'QLabel[role="secondary"] {{ color: {secondary}; }}'


# Qt default tooltip wake-up delay is ~700ms, which feels twitchy on densely
# labeled toolbars. Bump cold delay so the tooltip only appears on a
# deliberate hover, and zero out fall-asleep so every tooltip is a cold
# wake-up rather than Qt's default "second tooltip pops instantly" behavior.
_TOOLTIP_WAKE_UP_DELAY_MS = 800
_TOOLTIP_FALL_ASLEEP_DELAY_MS = 0


class _SCPEProxyStyle(QProxyStyle):
    """Fusion style with a longer, consistent tooltip wake-up delay."""

    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == QStyle.StyleHint.SH_ToolTip_WakeUpDelay:
            return _TOOLTIP_WAKE_UP_DELAY_MS
        if hint == QStyle.StyleHint.SH_ToolTip_FallAsleepDelay:
            return _TOOLTIP_FALL_ASLEEP_DELAY_MS
        return super().styleHint(hint, option, widget, returnData)


def apply_theme(app: QApplication, theme: str) -> None:
    """Apply the named theme to the application.

    Forces Fusion style (wrapped in a proxy that lengthens the tooltip
    wake-up delay) on the first call so palette changes render consistently
    regardless of the OS theme. Re-calling setStyle on a live app can crash
    Qt 6 during widget re-polish, so subsequent calls only swap the palette.
    """
    if theme not in AVAILABLE_THEMES:
        logger.warning(f"Unknown theme {theme!r}; using {DEFAULT_THEME}")
        theme = DEFAULT_THEME

    # "Already applied?" check: PyQt slices QProxyStyle back to QCommonStyle
    # when you call app.style(), so isinstance() can't see our subclass.
    # The style hint value itself survives the slicing — probe it directly.
    current_delay = app.style().styleHint(QStyle.StyleHint.SH_ToolTip_WakeUpDelay)
    if current_delay != _TOOLTIP_WAKE_UP_DELAY_MS:
        app.setStyle(_SCPEProxyStyle("Fusion"))
    app.setPalette(_palette_for(theme))
    app.setStyleSheet(_app_stylesheet_for(theme))
    logger.info(f"Applied theme: {theme}")
