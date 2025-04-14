#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Class for formatting and coloring text in the console using ANSI codes.
"""

class Colors:
    """
    Class that provides methods to color text in the console.
    Includes text colors, background colors, and text styles.
    """
    
    # Reset codes
    RESET = "\033[0m"
    
    # Private constants for basic color codes
    _FG_BLACK = "\033[30m"
    _FG_RED = "\033[31m"
    _FG_GREEN = "\033[32m"
    _FG_YELLOW = "\033[33m"
    _FG_BLUE = "\033[34m"
    _FG_MAGENTA = "\033[35m"
    _FG_CYAN = "\033[36m"
    _FG_WHITE = "\033[37m"
    _FG_DEFAULT = "\033[39m"
    
    # Basic background color codes
    _BG_BLACK = "\033[40m"
    _BG_RED = "\033[41m"
    _BG_GREEN = "\033[42m"
    _BG_YELLOW = "\033[43m"
    _BG_BLUE = "\033[44m"
    _BG_MAGENTA = "\033[45m"
    _BG_CYAN = "\033[46m"
    _BG_WHITE = "\033[47m"
    _BG_DEFAULT = "\033[49m"
    
    # Constants for text styles
    _BOLD = "\033[1m"
    _DIM = "\033[2m"
    _ITALIC = "\033[3m"
    _UNDERLINE = "\033[4m"
    _BLINK = "\033[5m"
    _REVERSE = "\033[7m"
    _HIDDEN = "\033[8m"
    _STRIKETHROUGH = "\033[9m"
    
    # Methods for text colors (foreground)
    @staticmethod
    def fg_black(text):
        """Black text"""
        return f"{Colors._FG_BLACK}{text}{Colors.RESET}"
    
    @staticmethod
    def fg_red(text):
        """Red text"""
        return f"{Colors._FG_RED}{text}{Colors.RESET}"
    
    @staticmethod
    def fg_green(text):
        """Green text"""
        return f"{Colors._FG_GREEN}{text}{Colors.RESET}"
    
    @staticmethod
    def fg_yellow(text):
        """Yellow text"""
        return f"{Colors._FG_YELLOW}{text}{Colors.RESET}"
    
    @staticmethod
    def fg_blue(text):
        """Blue text"""
        return f"{Colors._FG_BLUE}{text}{Colors.RESET}"
    
    @staticmethod
    def fg_magenta(text):
        """Magenta text"""
        return f"{Colors._FG_MAGENTA}{text}{Colors.RESET}"
    
    @staticmethod
    def fg_cyan(text):
        """Cyan text"""
        return f"{Colors._FG_CYAN}{text}{Colors.RESET}"
    
    @staticmethod
    def fg_white(text):
        """White text"""
        return f"{Colors._FG_WHITE}{text}{Colors.RESET}"
    
    # Methods for background colors
    @staticmethod
    def bg_black(text):
        """Text with black background"""
        return f"{Colors._BG_BLACK}{text}{Colors.RESET}"
    
    @staticmethod
    def bg_red(text):
        """Text with red background"""
        return f"{Colors._BG_RED}{text}{Colors.RESET}"
    
    @staticmethod
    def bg_green(text):
        """Text with green background"""
        return f"{Colors._BG_GREEN}{text}{Colors.RESET}"
    
    @staticmethod
    def bg_yellow(text):
        """Text with yellow background"""
        return f"{Colors._BG_YELLOW}{text}{Colors.RESET}"
    
    @staticmethod
    def bg_blue(text):
        """Text with blue background"""
        return f"{Colors._BG_BLUE}{text}{Colors.RESET}"
    
    @staticmethod
    def bg_magenta(text):
        """Text with magenta background"""
        return f"{Colors._BG_MAGENTA}{text}{Colors.RESET}"
    
    @staticmethod
    def bg_cyan(text):
        """Text with cyan background"""
        return f"{Colors._BG_CYAN}{text}{Colors.RESET}"
    
    @staticmethod
    def bg_white(text):
        """Text with white background"""
        return f"{Colors._BG_WHITE}{text}{Colors.RESET}"
    
    # Methods for text styles
    @staticmethod
    def bold(text):
        """Bold text"""
        return f"{Colors._BOLD}{text}{Colors.RESET}"
    
    @staticmethod
    def dim(text):
        """Dimmed text"""
        return f"{Colors._DIM}{text}{Colors.RESET}"
    
    @staticmethod
    def italic(text):
        """Italic text"""
        return f"{Colors._ITALIC}{text}{Colors.RESET}"
    
    @staticmethod
    def underline(text):
        """Underlined text"""
        return f"{Colors._UNDERLINE}{text}{Colors.RESET}"
    
    @staticmethod
    def blink(text):
        """Blinking text (may not work in all terminals)"""
        return f"{Colors._BLINK}{text}{Colors.RESET}"
    
    @staticmethod
    def reverse(text):
        """Reverses text and background colors"""
        return f"{Colors._REVERSE}{text}{Colors.RESET}"
    
    @staticmethod
    def hidden(text):
        """Hidden text"""
        return f"{Colors._HIDDEN}{text}{Colors.RESET}"
    
    @staticmethod
    def strikethrough(text):
        """Strikethrough text"""
        return f"{Colors._STRIKETHROUGH}{text}{Colors.RESET}"
    
    # Methods to combine styles
    @staticmethod
    def combine(*args, text):
        """
        Combines multiple styles into a single text
        Example: Colors.combine(Colors._FG_RED, Colors._BG_WHITE, Colors._BOLD, text="Text")
        """
        styles = "".join(args)
        return f"{styles}{text}{Colors.RESET}"
    
    # Methods for RGB colors
    @staticmethod
    def fg_rgb(r, g, b, text):
        """
        Text with custom RGB color
        Values r, g, b must be between 0-255
        """
        return f"\033[38;2;{r};{g};{b}m{text}{Colors.RESET}"
    
    @staticmethod
    def bg_rgb(r, g, b, text):
        """
        Text with custom RGB background color
        Values r, g, b must be between 0-255
        """
        return f"\033[48;2;{r};{g};{b}m{text}{Colors.RESET}"
    
    # Method to color a string with a custom code
    @staticmethod
    def custom(code, text):
        """
        Applies a custom ANSI code to the text
        Example: Colors.custom(33, "Yellow text")
        """
        return f"\033[{code}m{text}{Colors.RESET}"


# Usage example
"""
if __name__ == "__main__":
    
    print(Colors.fg_red("This text is red"))
    print(Colors.bg_cyan("This text has a cyan background"))
    print(Colors.bold("This text is bold"))
    print(Colors.combine(Colors._FG_YELLOW, Colors._BG_BLUE, text="Yellow text on blue background"))
    print(Colors.fg_rgb(255, 100, 50, "This text has a custom RGB color"))
    print(f"Normal text {Colors.fg_green('green text')} normal text again")
    print(Colors.underline(Colors.fg_magenta("Underlined magenta text")))
"""

