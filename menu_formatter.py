"""
MenuFormatter - NSAttributedString formatting for rumps menu items.

Provides rich text formatting (font sizes, bold, colors) for menu items
by accessing the underlying NSMenuItem via rumps._menuitem.
"""

from Foundation import NSAttributedString, NSMutableAttributedString
from AppKit import NSFont, NSColor, NSFontAttributeName, NSForegroundColorAttributeName


class MenuFormatter:
    """Helper class for applying rich text formatting to rumps MenuItems"""

    # Font sizes
    FONT_SIZE_HEADER = 13.0  # Section headers like "━━━ Cost ━━━"
    FONT_SIZE_LARGE = 12.0  # Important values
    FONT_SIZE_NORMAL = 11.0  # Regular menu items
    FONT_SIZE_SMALL = 10.0  # Secondary info (token counts)

    # Pre-created fonts for performance
    _font_cache = {}

    @classmethod
    def _get_font(cls, size, bold=False):
        """Get or create a cached font"""
        key = (size, bold)
        if key not in cls._font_cache:
            if bold:
                cls._font_cache[key] = NSFont.boldSystemFontOfSize_(size)
            else:
                cls._font_cache[key] = NSFont.systemFontOfSize_(size)
        return cls._font_cache[key]

    @classmethod
    def format_header(cls, text):
        """Format a section header (e.g., '━━━ Cost ━━━')"""
        attr_string = NSMutableAttributedString.alloc().initWithString_(text)
        font = cls._get_font(cls.FONT_SIZE_HEADER, bold=True)
        range_all = (0, len(text))
        attr_string.addAttribute_value_range_(NSFontAttributeName, font, range_all)
        return attr_string

    @classmethod
    def format_cost_summary(cls, label, cost_str, tokens_str=None):
        """Format a cost summary line with bold label and normal values"""
        if tokens_str:
            text = f"{label}: {cost_str} · {tokens_str} tokens"
        else:
            text = f"{label}: {cost_str}"

        attr_string = NSMutableAttributedString.alloc().initWithString_(text)

        # Bold label
        label_len = len(label) + 1  # Include the colon
        attr_string.addAttribute_value_range_(
            NSFontAttributeName,
            cls._get_font(cls.FONT_SIZE_NORMAL, bold=True),
            (0, label_len),
        )

        # Normal cost value
        cost_start = label_len + 1
        cost_end = cost_start + len(cost_str)
        attr_string.addAttribute_value_range_(
            NSFontAttributeName,
            cls._get_font(cls.FONT_SIZE_NORMAL),
            (cost_start, cost_end - cost_start),
        )

        # Smaller font for token count if present
        if tokens_str:
            token_start = text.find("·")
            attr_string.addAttribute_value_range_(
                NSFontAttributeName,
                cls._get_font(cls.FONT_SIZE_SMALL),
                (token_start, len(text) - token_start),
            )

        return attr_string

    @classmethod
    def format_project_line(cls, project_name, cost_str, tokens_str):
        """Format a project line with emphasis on the project name"""
        text = f"{project_name}: {cost_str} · {tokens_str}"
        attr_string = NSMutableAttributedString.alloc().initWithString_(text)

        # Normal font for project name
        project_len = len(project_name)
        attr_string.addAttribute_value_range_(
            NSFontAttributeName,
            cls._get_font(cls.FONT_SIZE_NORMAL),
            (0, project_len),
        )

        # Normal font for cost
        cost_start = project_len + 2
        cost_end = cost_start + len(cost_str)
        attr_string.addAttribute_value_range_(
            NSFontAttributeName,
            cls._get_font(cls.FONT_SIZE_NORMAL),
            (cost_start, cost_end - cost_start),
        )

        # Smaller font for tokens
        token_start = text.find("·")
        attr_string.addAttribute_value_range_(
            NSFontAttributeName,
            cls._get_font(cls.FONT_SIZE_SMALL),
            (token_start, len(text) - token_start),
        )

        return attr_string

    @classmethod
    def format_with_color_threshold(cls, text, cost_value, threshold=5.0):
        """Format text with color based on cost threshold (red for high costs)"""
        attr_string = NSMutableAttributedString.alloc().initWithString_(text)
        range_all = (0, len(text))

        # Set font
        attr_string.addAttribute_value_range_(
            NSFontAttributeName, cls._get_font(cls.FONT_SIZE_NORMAL), range_all
        )

        # Set color if cost exceeds threshold
        if cost_value >= threshold:
            red_color = NSColor.colorWithRed_green_blue_alpha_(0.8, 0.2, 0.2, 1.0)
            attr_string.addAttribute_value_range_(
                NSForegroundColorAttributeName, red_color, range_all
            )

        return attr_string

    @classmethod
    def apply_to_menuitem(cls, menuitem, attributed_string):
        """Apply NSAttributedString to a rumps MenuItem"""
        try:
            if hasattr(menuitem, "_menuitem"):
                menuitem._menuitem.setAttributedTitle_(attributed_string)
            else:
                # Handle case where it's already an NSMenuItem
                menuitem.setAttributedTitle_(attributed_string)
        except Exception:
            # Fallback: if formatting fails, item will keep its plain text
            pass
