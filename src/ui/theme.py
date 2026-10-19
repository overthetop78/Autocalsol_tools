APP_STYLE = """
* { font-family: "Segoe UI"; font-size: 13px; color: #24324a; }
QMainWindow, QWidget#appRoot, QScrollArea#page { background: #eef2f7; }
QScrollArea { border: none; }
QFrame#topbar { background: #10233f; border-radius: 12px; }
QLabel#logo { color: white; font-size: 23px; font-weight: 700; }
QLabel#tagline { color: #aebed3; font-size: 12px; }
QLabel#versionBadge { color: #dffaf4; background: #187e76; border-radius: 9px; padding: 6px 10px; font-weight: 700; }
QTabWidget::pane { border: none; background: transparent; }
QTabBar::tab { min-width: 180px; padding: 12px 18px; color: #607089; background: transparent; border-bottom: 3px solid transparent; font-weight: 600; }
QTabBar::tab:selected { color: #0d756d; border-bottom: 3px solid #15978b; }
QFrame#panel { background: white; border: 1px solid #d9e1eb; border-radius: 12px; }
QLabel#panelTitle { font-size: 17px; font-weight: 700; color: #17233a; }
QLabel#muted { color: #68778d; font-size: 12px; }
QLabel#fieldLabel { color: #35445d; font-size: 12px; font-weight: 700; }
QLineEdit, QComboBox, QListWidget, QTableWidget, QTextEdit { background: white; border: 1px solid #c9d4e1; border-radius: 7px; padding: 7px 9px; }
QLineEdit { min-height: 24px; }
QComboBox { min-height: 28px; padding-left: 10px; }
QLineEdit:focus, QComboBox:focus, QListWidget:focus, QTableWidget:focus { border: 2px solid #15978b; padding: 6px 8px; }
QPushButton { min-height: 34px; padding: 0 14px; color: #34435b; background: #f8fafc; border: 1px solid #cbd6e2; border-radius: 7px; font-weight: 600; }
QPushButton:hover { background: #edf3f7; border-color: #9eafc0; }
QPushButton#primary { min-height: 42px; color: white; background: #168f84; border-color: #168f84; font-weight: 700; }
QPushButton#primary:hover { background: #107c73; }
QPushButton#primary:disabled { background: #96beb9; border-color: #96beb9; }
QPushButton#danger { color: #a33a45; }
QCheckBox { spacing: 8px; min-height: 24px; }
QCheckBox::indicator { width: 17px; height: 17px; }
QProgressBar { min-height: 8px; max-height: 8px; background: #dfe7ee; border: none; border-radius: 4px; text-align: center; }
QProgressBar::chunk { background: #15978b; border-radius: 4px; }
QTextEdit#console { background: #0f1d30; color: #d7e4ef; border: none; font-family: "Consolas"; font-size: 12px; padding: 10px; }
QHeaderView::section { background: #edf2f6; color: #34435b; border: none; border-right: 1px solid #d7e0e8; border-bottom: 1px solid #cdd7e1; padding: 8px; font-weight: 700; }
QTableWidget { gridline-color: #e6ebf0; alternate-background-color: #f8fafc; selection-background-color: #d7efec; selection-color: #153c39; }
QLabel#metric { background: #f4f8fb; border: 1px solid #dce5ed; border-radius: 8px; padding: 9px; font-weight: 600; }
QLabel#status { background: #e1f3ef; color: #116a63; border-radius: 7px; padding: 9px; font-weight: 600; }
QSplitter::handle { background: transparent; width: 8px; }
"""
