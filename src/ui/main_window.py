import sys
import os
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QFileDialog,
    QComboBox, QMessageBox, QProgressBar, QApplication,
    QFrame, QPlainTextEdit, QCheckBox, QTextBrowser,
    QSplitter, QTabWidget, QLineEdit
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    WEB_ENGINE_AVAILABLE = True
except Exception:
    # Fallback to QTextBrowser when WebEngine is not available
    from PyQt5.QtWidgets import QTextBrowser as QWebEngineView
    WEB_ENGINE_AVAILABLE = False
from pathlib import Path
from src.core.manager import batch_convert
from src.core.settings import load_settings, save_settings
from src.core.exporter import export_content, ExportError
from src.core.i18n import t, set_language, get_language

# Import the function instead of the constant
from .styles import get_style

class ConversionWorker(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(list)

    def __init__(self, files, target_format, output_dir=None):
        super().__init__()
        self.files = files
        self.target_format = target_format
        self.output_dir = output_dir
        self.cancel_requested = False
        self.pause_requested = False

    def request_cancel(self):
        self.cancel_requested = True

    def request_pause(self, pause: bool):
        self.pause_requested = pause

    def run(self):
        base_dir = None
        try:
            import os
            common = os.path.commonpath(self.files)
            if common and os.path.isdir(common):
                from pathlib import Path
                base_dir = Path(common)
        except Exception:
            base_dir = None

        results = batch_convert(
            self.files,
            self.target_format,
            lambda current, total, name: self.progress.emit(current, total, name),
            output_dir=self.output_dir,
            base_dir=base_dir,
            cancel_callback=lambda: self.cancel_requested,
            pause_callback=lambda: self.pause_requested,
        )
        self.finished.emit(results)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1000, 700)
        self.setAcceptDrops(True)

        # Set window icon
        icon_path = Path(__file__).parent.parent.parent / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # State & settings
        self.settings = load_settings()
        self.current_theme = self.settings.get("theme", "LIGHT")
        self.current_lang = self.settings.get("language", "en")
        set_language(self.current_lang)
        self.output_dir = self.settings.get("output_dir")
        self.recent_files = self.settings.get("recent_files", [])
        self.last_browse_dir = self.settings.get("last_browse_dir", "")
        self.preview_source_path = None
        self.last_output_dir = self.output_dir
        self.apply_theme()

        self._init_ui()
        self._update_texts()

    def _init_ui(self):
        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.layout = QVBoxLayout(central_widget)
        self.layout.setContentsMargins(40, 40, 40, 40)
        self.layout.setSpacing(20)

        # Header
        header_layout = QHBoxLayout()

        # Title Stack
        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        self.title_label = QLabel()
        self.title_label.setObjectName("TitleLabel")
        self.subtitle_label = QLabel()
        self.subtitle_label.setObjectName("SubtitleLabel")
        self.subtitle_label.setStyleSheet("font-size: 11px; margin-bottom: 0px;")
        self.copyright_label = QLabel()
        self.copyright_label.setObjectName("SubtitleLabel")
        self.copyright_label.setStyleSheet("font-size: 10px; color: #888;")

        title_box.addWidget(self.title_label)
        title_box.addWidget(self.subtitle_label)
        title_box.addWidget(self.copyright_label)

        header_layout.addLayout(title_box)
        header_layout.addStretch()

        # Language Toggle
        self.btn_lang = QPushButton("EN/中")
        self.btn_lang.setCursor(Qt.PointingHandCursor)
        self.btn_lang.setObjectName("ThemeButton")
        self.btn_lang.setFixedSize(60, 30)
        self.btn_lang.clicked.connect(self.toggle_language)
        header_layout.addWidget(self.btn_lang)

        # Theme Toggle
        self.btn_theme = QPushButton("🌗")
        self.btn_theme.setCursor(Qt.PointingHandCursor)
        self.btn_theme.setObjectName("ThemeButton")
        self.btn_theme.setFixedSize(40, 30)
        self.btn_theme.clicked.connect(self.toggle_theme)
        header_layout.addWidget(self.btn_theme)

        self.layout.addLayout(header_layout)

        # Main Tab Widget
        self.main_tabs = QTabWidget()
        self.layout.addWidget(self.main_tabs)

        # Tab 1: Batch Conversion
        self._init_batch_tab()

        # Tab 2: Web Crawler
        self._init_crawler_tab()

    def _init_batch_tab(self):
        """批量转换标签页"""
        batch_widget = QWidget()
        batch_layout = QVBoxLayout(batch_widget)
        batch_layout.setContentsMargins(0, 10, 0, 0)
        batch_layout.setSpacing(15)

        # Controls Area
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(15)

        # Buttons
        self.btn_add_files = QPushButton()
        self.btn_add_files.setCursor(Qt.PointingHandCursor)
        self.btn_add_files.setMinimumHeight(36)
        self.btn_add_files.clicked.connect(self.add_files)

        self.btn_add_folder = QPushButton()
        self.btn_add_folder.setObjectName("SecondaryButton")
        self.btn_add_folder.setCursor(Qt.PointingHandCursor)
        self.btn_add_folder.setMinimumHeight(36)
        self.btn_add_folder.clicked.connect(self.add_folder)

        self.btn_clear = QPushButton()
        self.btn_clear.setObjectName("SecondaryButton")
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.setMinimumHeight(36)
        self.btn_clear.clicked.connect(self.clear_list)

        self.btn_output_dir = QPushButton()
        self.btn_output_dir.setObjectName("SecondaryButton")
        self.btn_output_dir.setCursor(Qt.PointingHandCursor)
        self.btn_output_dir.setMinimumHeight(36)
        self.btn_output_dir.clicked.connect(self.choose_output_dir)
        self.output_dir_label = QLabel()
        self.output_dir_label.setObjectName("SubtitleLabel")
        self.output_dir_label.setStyleSheet("margin-left: 6px;")

        controls_layout.addWidget(self.btn_add_files)
        controls_layout.addWidget(self.btn_add_folder)
        controls_layout.addWidget(self.btn_clear)
        controls_layout.addWidget(self.btn_output_dir)
        controls_layout.addWidget(self.output_dir_label)
        controls_layout.addStretch()

        # Format Selection Removed - Auto Detection Logic
        self.info_label = QLabel()
        self.info_label.setObjectName("SubtitleLabel")
        self.info_label.setStyleSheet("color: #2962ff; font-weight: bold; font-size: 11px; margin-top: 5px;")
        controls_layout.addWidget(self.info_label)

        batch_layout.addLayout(controls_layout)

        # Splitter: left (files/status) | right (preview)
        splitter = QSplitter(Qt.Horizontal)
        batch_layout.addWidget(splitter)

        # Left panel
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(12)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.file_list.setFrameShape(QFrame.NoFrame)
        left_layout.addWidget(self.file_list)

        # Recent files (session)
        self.recent_label = QLabel()
        self.recent_label.setObjectName("SubtitleLabel")
        left_layout.addWidget(self.recent_label)
        self.recent_list = QListWidget()
        self.recent_list.setFrameShape(QFrame.NoFrame)
        self.recent_list.setMaximumHeight(120)
        self.recent_list.itemDoubleClicked.connect(self.add_recent_to_list)
        left_layout.addWidget(self.recent_list)
        if self.recent_files:
            self.recent_list.addItems(self.recent_files)

        # Status & Progress
        status_layout = QHBoxLayout()
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #7f8c8d; font-weight: 500;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        self.btn_open_output = QPushButton()
        self.btn_open_output.setObjectName("SecondaryButton")
        self.btn_open_output.clicked.connect(self.open_output_dir)
        status_layout.addWidget(self.btn_open_output)
        left_layout.addLayout(status_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)

        # Convert Button row
        convert_row = QHBoxLayout()
        self.btn_convert = QPushButton()
        self.btn_convert.setObjectName("ConvertButton")
        self.btn_convert.setCursor(Qt.PointingHandCursor)
        self.btn_convert.clicked.connect(self.start_conversion)
        self.btn_convert.setMinimumHeight(56)
        self.btn_convert.setStyleSheet("font-size: 14px; letter-spacing: 1px;")

        self.btn_cancel = QPushButton()
        self.btn_cancel.setObjectName("SecondaryButton")
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_conversion)

        self.btn_pause = QPushButton()
        self.btn_pause.setObjectName("SecondaryButton")
        self.btn_pause.setCursor(Qt.PointingHandCursor)
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self.toggle_pause)

        convert_row.addWidget(self.btn_convert)
        convert_row.addWidget(self.btn_pause)
        convert_row.addWidget(self.btn_cancel)
        left_layout.addLayout(convert_row)

        # Log panel
        self.log_label = QLabel()
        self.log_label.setObjectName("SubtitleLabel")
        left_layout.addWidget(self.log_label)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(140)
        left_layout.addWidget(self.log_view)

        splitter.addWidget(left_panel)

        # Right panel (preview)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(10)
        right_layout.setContentsMargins(0, 0, 0, 0)

        preview_bar = QHBoxLayout()
        preview_bar.setSpacing(10)
        self.preview_btn = QPushButton()
        self.preview_btn.setObjectName("SecondaryButton")
        self.preview_btn.clicked.connect(self.load_preview_from_selection)
        self.preview_live = QCheckBox()
        self.preview_live.stateChanged.connect(self.on_live_toggle)
        self.preview_mode = QComboBox()
        self.preview_mode_label = QLabel()
        preview_bar.addWidget(self.preview_btn)
        preview_bar.addWidget(self.preview_live)
        preview_bar.addWidget(self.preview_mode_label)
        preview_bar.addWidget(self.preview_mode)
        preview_bar.addStretch()
        right_layout.addLayout(preview_bar)

        self.preview_input = QPlainTextEdit()
        self.preview_input.textChanged.connect(self.on_preview_changed)

        self.preview_tabs = QTabWidget()
        self.preview_output_plain = QPlainTextEdit()
        self.preview_output_plain.setReadOnly(True)
        self.preview_output_rendered = QWebEngineView()
        self.preview_tabs.addTab(self.preview_output_rendered, "Rendered")
        self.preview_tabs.addTab(self.preview_output_plain, "Plain")
        if not WEB_ENGINE_AVAILABLE:
            self.preview_tabs.setCurrentWidget(self.preview_output_plain)

        preview_split = QSplitter(Qt.Vertical)
        preview_split.addWidget(self.preview_input)
        preview_split.addWidget(self.preview_tabs)
        preview_split.setSizes([300, 400])

        right_layout.addWidget(preview_split)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        # Export options (PDF/DOCX)
        export_bar = QHBoxLayout()
        export_bar.setSpacing(10)
        self.export_label = QLabel()
        self.export_label.setObjectName("SubtitleLabel")
        self.export_choice = QComboBox()
        self.export_choice.addItems(["None", "PDF", "DOCX"])
        self.export_css_path = None
        self.btn_export_css = QPushButton()
        self.btn_export_css.setObjectName("SecondaryButton")
        self.btn_export_css.clicked.connect(self.pick_export_css)
        self.export_css_label = QLabel()
        self.export_css_label.setObjectName("SubtitleLabel")
        export_bar.addWidget(self.export_label)
        export_bar.addWidget(self.export_choice)
        export_bar.addWidget(self.btn_export_css)
        export_bar.addWidget(self.export_css_label)
        export_bar.addStretch()
        batch_layout.addLayout(export_bar)

        self.main_tabs.addTab(batch_widget, "Batch Convert")

    def _init_crawler_tab(self):
        """爬虫标签页"""
        crawler_widget = QWidget()
        crawler_layout = QVBoxLayout(crawler_widget)
        crawler_layout.setContentsMargins(0, 10, 0, 0)
        crawler_layout.setSpacing(15)

        # Output directory row
        output_row = QHBoxLayout()
        self.crawler_output_btn = QPushButton()
        self.crawler_output_btn.setObjectName("SecondaryButton")
        self.crawler_output_btn.setCursor(Qt.PointingHandCursor)
        self.crawler_output_btn.setMinimumHeight(36)
        self.crawler_output_btn.clicked.connect(self.choose_output_dir)
        self.crawler_output_label = QLabel()
        self.crawler_output_label.setObjectName("SubtitleLabel")
        output_row.addWidget(self.crawler_output_btn)
        output_row.addWidget(self.crawler_output_label)
        output_row.addStretch()
        crawler_layout.addLayout(output_row)

        # URL Fetch Row
        url_layout = QHBoxLayout()
        url_layout.setSpacing(10)
        self.url_input = QLineEdit()
        self.url_input.setMinimumHeight(36)
        self.url_input.returnPressed.connect(self.fetch_url)
        self.chk_extract_main = QCheckBox()
        self.chk_browser_mode = QCheckBox()
        self.btn_fetch = QPushButton()
        self.btn_fetch.setCursor(Qt.PointingHandCursor)
        self.btn_fetch.setMinimumHeight(36)
        self.btn_fetch.clicked.connect(self.fetch_url)
        self.fetch_format = QComboBox()
        self.fetch_format.addItems(["MD", "HTML", "PDF", "DOCX"])
        self.fetch_format.setMinimumHeight(30)
        url_layout.addWidget(self.url_input, 1)
        url_layout.addWidget(self.chk_extract_main)
        url_layout.addWidget(self.chk_browser_mode)
        url_layout.addWidget(self.fetch_format)
        url_layout.addWidget(self.btn_fetch)
        crawler_layout.addLayout(url_layout)

        # Status label for crawler
        self.crawler_status = QLabel()
        self.crawler_status.setStyleSheet("color: #7f8c8d; font-weight: 500;")
        crawler_layout.addWidget(self.crawler_status)

        # Preview area
        preview_label = QLabel()
        preview_label.setObjectName("SubtitleLabel")
        preview_label.setText("Preview")
        crawler_layout.addWidget(preview_label)

        self.crawler_preview = QPlainTextEdit()
        self.crawler_preview.setReadOnly(True)
        crawler_layout.addWidget(self.crawler_preview)

        self.main_tabs.addTab(crawler_widget, "Web Crawler")

    def _update_texts(self):
        """更新所有UI文本"""
        self.setWindowTitle(t("window_title"))
        self.title_label.setText(t("title"))
        self.subtitle_label.setText(t("subtitle"))
        self.copyright_label.setText(t("copyright"))
        self.btn_theme.setToolTip(t("toggle_theme"))
        self.btn_add_files.setText(t("add_files"))
        self.btn_add_folder.setText(t("add_folder"))
        self.btn_clear.setText(t("clear"))
        self.btn_output_dir.setText(t("output_dir"))
        self.output_dir_label.setText(self.output_dir if self.output_dir else t("default_output"))
        self.info_label.setText(t("auto_detect"))
        self.recent_label.setText(t("recent_files"))
        self.status_label.setText(t("ready"))
        self.btn_open_output.setText(t("open_output"))
        self.btn_convert.setText(t("start_convert"))
        self.btn_cancel.setText(t("cancel"))
        self.btn_pause.setText(t("pause"))
        self.log_label.setText(t("log"))
        self.preview_btn.setText(t("preview_selected"))
        self.preview_live.setText(t("live_convert"))
        self.preview_mode_label.setText(t("preview_mode"))
        self.preview_mode.clear()
        self.preview_mode.addItems([t("rendered"), t("plain")])
        self.preview_input.setPlaceholderText(t("source_placeholder"))
        self.preview_output_plain.setPlaceholderText(t("output_placeholder"))
        self.export_label.setText(t("export_label"))
        self.btn_export_css.setText(t("pick_css"))
        self.export_css_label.setText(t("no_css") if not self.export_css_path else Path(self.export_css_path).name)
        # Crawler tab
        self.url_input.setPlaceholderText(t("url_placeholder"))
        self.chk_extract_main.setText(t("extract_main"))
        self.btn_fetch.setText(t("fetch_url"))
        self.crawler_output_btn.setText(t("output_dir"))
        self.crawler_output_label.setText(self.output_dir if self.output_dir else t("default_output"))
        self.crawler_status.setText(t("ready"))
        # Tab titles
        self.main_tabs.setTabText(0, t("batch_convert") if get_language() == "zh" else "Batch Convert")
        self.main_tabs.setTabText(1, t("web_crawler") if get_language() == "zh" else "Web Crawler")
        # Tooltips
        self.btn_add_files.setToolTip(t("tip_add_files"))
        self.btn_add_folder.setToolTip(t("tip_add_folder"))
        self.btn_clear.setToolTip(t("tip_clear"))
        self.btn_output_dir.setToolTip(t("tip_output_dir"))
        self.btn_fetch.setToolTip(t("tip_fetch"))
        self.chk_extract_main.setToolTip(t("tip_extract_main"))
        self.chk_browser_mode.setText(t("browser_mode"))
        self.chk_browser_mode.setToolTip(t("tip_browser_mode"))
        self.btn_convert.setToolTip(t("tip_convert"))
        self.export_choice.setToolTip(t("tip_export"))
        self.btn_export_css.setToolTip(t("tip_css"))

    def toggle_language(self):
        self.current_lang = "zh" if self.current_lang == "en" else "en"
        set_language(self.current_lang)
        self.settings["language"] = self.current_lang
        save_settings(self.settings)
        self._update_texts()
        
    def apply_theme(self):
        style = get_style(self.current_theme)
        self.setStyleSheet(style)
        
    def toggle_theme(self):
        if self.current_theme == "LIGHT":
            self.current_theme = "DARK"
        else:
            self.current_theme = "LIGHT"
        self.apply_theme()
        self.settings["theme"] = self.current_theme
        save_settings(self.settings)

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, t("select_files"), self.last_browse_dir,
            "All Supported (*.html *.md);;HTML Files (*.html);;Markdown Files (*.md)"
        )
        if files:
            self.last_browse_dir = os.path.dirname(files[0])
            self.settings["last_browse_dir"] = self.last_browse_dir
            save_settings(self.settings)
            self.add_files_to_list(files)
            
    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, t("select_folder"), self.last_browse_dir)
        if folder:
            self.last_browse_dir = folder
            self.settings["last_browse_dir"] = self.last_browse_dir
            save_settings(self.settings)
            files = []
            for root, _, filenames in os.walk(folder):
                for filename in filenames:
                    if filename.lower().endswith(('.html', '.md')):
                        files.append(os.path.join(root, filename))

            if files:
                self.add_files_to_list(files)
                self.status_label.setText(t("added_files", count=len(files)))
            else:
                self.status_label.setText(t("no_files_found"))

    def add_files_to_list(self, files):
        existing_items = {self.file_list.item(i).text() for i in range(self.file_list.count())}
        for f in files:
            if f not in existing_items:
                self.file_list.addItem(f)
                self._remember_recent(f)
                
    def clear_list(self):
        self.file_list.clear()
        self.status_label.setText("List cleared.")

    def choose_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_dir = folder
            self.output_dir_label.setText(folder)
            self.crawler_output_label.setText(folder)
            self.settings["output_dir"] = folder
        else:
            self.output_dir = None
            self.output_dir_label.setText("Default (same folder)")
            self.crawler_output_label.setText(t("default_output"))
            self.settings["output_dir"] = None
        save_settings(self.settings)

    def pick_export_css(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select CSS file",
            "",
            "CSS Files (*.css);;All Files (*.*)"
        )
        if file_path:
            self.export_css_path = file_path
            self.export_css_label.setText(Path(file_path).name)
        else:
            self.export_css_path = None
            self.export_css_label.setText("No CSS")

    def start_conversion(self):
        count = self.file_list.count()
        if count == 0:
            QMessageBox.warning(self, "Warning", "Please add files to convert.")
            return

        # Auto format
        target_format = 'auto'
        
        files = [self.file_list.item(i).text() for i in range(count)]
        
        # UI State
        self.btn_convert.setEnabled(False)
        self.btn_convert.setText("SMART PROCESSING...")
        self.btn_cancel.setEnabled(True)
        self.btn_pause.setEnabled(True)
        self.btn_pause.setText("Pause")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.log("Start conversion...")
        
        self.worker = ConversionWorker(files, target_format, output_dir=self.output_dir)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.conversion_finished)
        self.worker.start()

    def cancel_conversion(self):
        if hasattr(self, "worker") and self.worker.isRunning():
            self.worker.request_cancel()
            self.status_label.setText("Cancelling...")
            self.btn_cancel.setEnabled(False)
            self.log("Cancellation requested")

    def toggle_pause(self):
        if not hasattr(self, "worker") or not self.worker.isRunning():
            return
        paused = self.worker.pause_requested
        self.worker.request_pause(not paused)
        self.btn_pause.setText("Resume" if not paused else "Pause")
        self.status_label.setText("Paused" if not paused else "Processing...")
        self.log("Paused" if not paused else "Resumed")
        
    def update_progress(self, current, total, filename):
        percentage = int((current / total) * 100)
        self.progress_bar.setValue(percentage)
        self.status_label.setText(f"Processing: {os.path.basename(filename)}")
        
    def conversion_finished(self, results):
        self.btn_convert.setEnabled(True)
        self.btn_convert.setText("START SMART CONVERSION")
        self.btn_cancel.setEnabled(False)
        self.btn_pause.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_label.setText("Ready")
        
        success_count = sum(1 for r in results if r.success)
        failed = [r for r in results if not r.success]
        cancelled = any(r.message == "Cancelled" for r in results)
        
        msg = f"Completed!\n\n✅ Success: {success_count}\n❌ Failed: {len(failed)}"
        if failed:
            msg += "\n\nFailures:\n" + "\n".join([f"{os.path.basename(r.file_path)}: {r.message}" for r in failed[:5]])
            
        for r in results:
            if r.success:
                self._remember_recent(r.file_path)
                if getattr(r, "output_path", None):
                    self.last_output_dir = os.path.dirname(r.output_path)
                self.log(f"[ok] {r.file_path} -> {r.message}")
            else:
                self.log(f"[fail] {r.file_path}: {r.message}")

        # Optional export
        export_mode = self.export_choice.currentText().lower()
        exported_paths = []
        if export_mode != "none":
            css_text = None
            if self.export_css_path:
                try:
                    css_text = Path(self.export_css_path).read_text(encoding="utf-8")
                except Exception:
                    css_text = None
            for r in results:
                if not r.success or not getattr(r, "output_path", None):
                    continue
                try:
                    out_path = Path(r.output_path)
                    text = out_path.read_text(encoding="utf-8")
                    content_type = "html" if out_path.suffix.lower() == ".html" else "md"
                    export_path = export_content(text, content_type, export_mode, out_path, css_text=css_text)
                    exported_paths.append(str(export_path))
                except ExportError as e:
                    msg += f"\nExport failed for {os.path.basename(r.file_path)}: {e}"
                except Exception as e:
                    msg += f"\nExport failed for {os.path.basename(r.file_path)}: {e}"

        if exported_paths:
            msg += "\nExports:\n" + "\n".join(exported_paths)
        if cancelled:
            msg = "Cancelled.\n" + msg

        if len(failed) == 0:
            QMessageBox.information(self, "Success", msg)
        else:
            QMessageBox.warning(self, "Result", msg)

    def _remember_recent(self, path):
        if path in self.recent_files:
            self.recent_files.remove(path)
        self.recent_files.insert(0, path)
        self.recent_files = self.recent_files[:10]
        self.recent_list.clear()
        self.recent_list.addItems(self.recent_files)
        self.settings["recent_files"] = self.recent_files
        save_settings(self.settings)

    def add_recent_to_list(self, item):
        self.add_files_to_list([item.text()])

    def load_preview_from_selection(self):
        items = self.file_list.selectedItems()
        if not items:
            QMessageBox.information(self, "Preview", "Select a file to preview.")
            return
        path = items[0].text()
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.preview_input.setPlainText(content)
            self.preview_source_path = path
            self.run_preview_conversion()
        except Exception as e:
            QMessageBox.warning(self, "Preview error", str(e))

    def on_preview_changed(self):
        if self.preview_live.isChecked():
            self.run_preview_conversion()

    def on_live_toggle(self, state):
        if state:
            self.run_preview_conversion()

    def run_preview_conversion(self):
        text = self.preview_input.toPlainText()
        if not text.strip():
            self.preview_output_plain.setPlainText("")
            self._set_rendered_html("<p></p>")
            return

        target = "md"
        if self.preview_source_path and self.preview_source_path.lower().endswith(".md"):
            target = "html"
        try:
            if target == "md":
                from src.core.html_to_md import html_to_markdown
                md_text = html_to_markdown(text)
                self.preview_output_plain.setPlainText(md_text)
                # Render MD -> HTML for preview
                from src.core.md_to_html import markdown_to_html
                html = markdown_to_html(md_text)
                self._set_rendered_html(html)
            else:
                from src.core.md_to_html import markdown_to_html
                html = markdown_to_html(text)
                self.preview_output_plain.setPlainText(html)
                self._set_rendered_html(html)
            if self.preview_mode.currentText().lower().startswith("render"):
                self.preview_tabs.setCurrentWidget(self.preview_output_rendered)
            else:
                self.preview_tabs.setCurrentWidget(self.preview_output_plain)
        except Exception as e:
            self.preview_output_plain.setPlainText(f"Error: {e}")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                path = url.toLocalFile()
                if path.lower().endswith((".html", ".md")):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            paths = [url.toLocalFile() for url in event.mimeData().urls()]
            valid = [p for p in paths if p.lower().endswith((".html", ".md"))]
            if valid:
                self.add_files_to_list(valid)
                self.status_label.setText(f"Added {len(valid)} file(s) via drag & drop")
                event.acceptProposedAction()
                return
        event.ignore()

    def open_output_dir(self):
        path = self.output_dir or self.last_output_dir
        if not path:
            QMessageBox.information(self, "Output", "No output directory selected.")
            return
        self._open_path(path)

    def _open_path(self, path: str):
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            elif sys.platform == "darwin":
                os.system(f'open "{path}"')
            else:
                os.system(f'xdg-open "{path}"')
        except Exception as e:
            QMessageBox.warning(self, "Open path failed", str(e))

    def _set_rendered_html(self, html: str):
        # Wrap with MathJax for nicer math display
        template = f"""
        <html>
          <head>
            <meta charset="utf-8" />
            <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
          </head>
          <body>{html}</body>
        </html>
        """
        try:
            self.preview_output_rendered.setHtml(template)
        except Exception:
            # Fallback: set plain text if WebEngine not available
            self.preview_output_plain.setPlainText(html)

    def log(self, message: str):
        self.log_view.appendPlainText(message)

    def fetch_url(self):
        url = self.url_input.text().strip()
        if not url:
            return
        # 检查输出目录
        if not self.output_dir:
            QMessageBox.warning(self, t("warning"), t("no_output_dir"))
            return
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        self.btn_fetch.setEnabled(False)
        self.btn_fetch.setText(t("fetching"))
        QApplication.processEvents()
        try:
            from src.core.fetch_url import fetch_url as do_fetch
            main_only = self.chk_extract_main.isChecked()
            use_browser = self.chk_browser_mode.isChecked()
            content, title = do_fetch(url, main_only=main_only, use_browser=use_browser)
            # 自动保存
            fmt = self.fetch_format.currentText().upper()
            safe_title = "".join(c if c.isalnum() or c in ' -_' else '_' for c in title)[:50]
            path = Path(self.output_dir) / f"{safe_title}.{fmt.lower()}"
            if fmt == "HTML":
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.crawler_preview.setPlainText(content)
            elif fmt == "MD":
                from src.core.html_to_md import html_to_markdown
                md = html_to_markdown(content)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(md)
                self.crawler_preview.setPlainText(md)
            elif fmt in ("PDF", "DOCX"):
                from src.core.html_to_md import html_to_markdown
                md = html_to_markdown(content)
                export_content(md, "md", fmt.lower(), path, css_text=None)
                self.crawler_preview.setPlainText(md)
            self.crawler_status.setText(f"Saved: {path.name}")
            self.log(f"Fetched & saved: {path}")
        except Exception as e:
            self.crawler_status.setText(t("fetch_error", error=str(e)[:50]))
            self.log(f"Fetch error: {e}")
        finally:
            self.btn_fetch.setText(t("fetch_url"))
            self.btn_fetch.setEnabled(True)

    def closeEvent(self, event):
        save_settings(self.settings)
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Enable High DPI
    try:
        app.setAttribute(Qt.AA_EnableHighDpiScaling)
        app.setAttribute(Qt.AA_UseHighDpiPixmaps)
    except:
        pass
        
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
