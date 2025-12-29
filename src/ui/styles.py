
# Theme Definitions
THEMES = {
    "LIGHT": {
        "bg": "#f9f9f9",           # Milky White / Very Light Grey
        "surface": "#ffffff",       # Pure White for cards
        "text": "#2c3e50",          # Elegant Dark Blue/Grey for text
        "text_sec": "#7f8c8d",      # Grey for secondary text
        "primary": "#607d8b",       # Elegant Blue Grey
        "primary_hover": "#546e7a",
        "border": "#e0e0e0"
    },
    "DARK": {
        "bg": "#1a1a1a",           # 深黑
        "surface": "#242424",      # 深灰卡片
        "text": "#b0b0b0",          # 柔和灰白
        "text_sec": "#707070",     # 暗灰次要文字
        "primary": "#3a3a3a",       # 深灰按钮
        "primary_hover": "#4a4a4a",
        "border": "#333333"
    }
}

def get_style(theme_name="LIGHT"):
    colors = THEMES.get(theme_name, THEMES["LIGHT"])
    
    return f"""
    QMainWindow {{
        background-color: {colors['bg']};
    }}

    QWidget {{
        color: {colors['text']};
        font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
        font-size: 14px;
    }}

    /* Buttons */
    QPushButton {{
        background-color: {colors['primary']};
        color: white;
        border: none;
        border-radius: 8px; /* Softer rounding */
        padding: 8px 16px;
        font-weight: 600;
        font-size: 13px;
    }}

    QPushButton:hover {{
        background-color: {colors['primary_hover']};
    }}

    QPushButton:pressed {{
        background-color: {colors['primary']};
        padding-top: 10px;
    }}

    QPushButton#SecondaryButton {{
        background-color: {colors['surface']};
        border: 1px solid {colors['border']};
        color: {colors['text']};
    }}

    QPushButton#SecondaryButton:hover {{
        background-color: {colors['border']};
        color: {colors['text']};
    }}
    
    QPushButton#ThemeButton {{
        background-color: transparent;
        border: 1px solid {colors['border']};
        color: {colors['text']};
        border-radius: 15px; /* Circle/Pill shape */
        padding: 4px 10px;
    }}
    
    QPushButton#ThemeButton:hover {{
        background-color: {colors['border']};
    }}

    QPushButton#ConvertButton {{
        background-color: {colors['primary']};
        color: {colors['text']};
    }}

    /* List Widget */
    QListWidget {{
        background-color: {colors['surface']};
        border: 1px solid {colors['border']};
        border-radius: 8px;
        padding: 8px;
        outline: none;
    }}

    QListWidget::item {{
        padding: 10px;
        border-radius: 6px;
        margin-bottom: 2px;
        color: {colors['text']};
    }}

    QListWidget::item:selected {{
        background-color: {colors['primary']};
        color: white;
    }}
    
    QListWidget::item:hover:!selected {{
        background-color: {colors['bg']};
    }}

    /* Labels */
    QLabel#TitleLabel {{
        font-size: 26px;
        font-weight: bold;
        color: {colors['text']};
        margin-bottom: 15px;
        font-family: 'Segoe UI Light', 'Microsoft YaHei Light';
    }}

    QLabel#SubtitleLabel {{
        font-size: 14px;
        font-weight: 600;
        color: {colors['text_sec']};
        margin-bottom: 8px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}

    /* Combo Box */
    QComboBox {{
        background-color: {colors['surface']};
        border: 1px solid {colors['border']};
        border-radius: 6px;
        padding: 6px 12px;
        min-width: 120px;
        color: {colors['text']};
    }}

    QComboBox:hover {{
        border: 1px solid {colors['primary']};
    }}
    
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    
    QComboBox::item {{
        color: {colors['text']};
        background-color: {colors['surface']};
    }}

    /* ScrollBar */
    QScrollBar:vertical {{
        border: none;
        background: {colors['bg']};
        width: 8px;
        margin: 0px;
    }}

    QScrollBar::handle:vertical {{
        background: {colors['border']};
        min-height: 20px;
        border-radius: 4px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background: {colors['text_sec']};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    /* Progress Bar */
    QProgressBar {{
        border: none;
        background-color: {colors['border']};
        border-radius: 4px;
        height: 8px;
    }}

    QProgressBar::chunk {{
        background-color: {colors['primary']};
        border-radius: 4px;
    }}
    
    /* Dialogs */
    QMessageBox {{
        background-color: {colors['surface']};
        color: {colors['text']};
    }}

    /* Editors */
    QPlainTextEdit {{
        background-color: {colors['surface']};
        border: 1px solid {colors['border']};
        border-radius: 8px;
        padding: 10px;
        color: {colors['text']};
        selection-background-color: {colors['primary']};
    }}

    QCheckBox {{
        color: {colors['text']};
        spacing: 8px;
        font-size: 12px;
    }}

    /* Tab Widget */
    QTabWidget::pane {{
        border: 1px solid {colors['border']};
        background-color: {colors['surface']};
    }}

    QTabBar::tab {{
        background-color: {colors['surface']};
        color: {colors['text_sec']};
        padding: 8px 16px;
        border: 1px solid {colors['border']};
        border-bottom: none;
        margin-right: 2px;
    }}

    QTabBar::tab:selected {{
        color: {colors['text']};
        background-color: {colors['bg']};
        border-bottom: 1px solid {colors['bg']};
    }}

    QTabBar::tab:hover:!selected {{
        color: {colors['text']};
    }}

    /* Line Edit */
    QLineEdit {{
        background-color: {colors['surface']};
        border: 1px solid {colors['border']};
        border-radius: 6px;
        padding: 6px 12px;
        color: {colors['text']};
    }}

    /* Splitter - 隐藏分割线 */
    QSplitter::handle {{
        background-color: transparent;
    }}

    QSplitter::handle:horizontal {{
        width: 8px;
    }}

    QSplitter::handle:vertical {{
        height: 8px;
    }}
    """
