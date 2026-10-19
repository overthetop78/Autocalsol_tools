from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QAbstractItemView, QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from ..services.duplicate_service import DuplicateOccurrence


class Panel(QFrame):
    def __init__(self, title: str, description: str = ""):
        super().__init__(objectName="panel")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(18, 16, 18, 16)
        self.layout.setSpacing(10)
        self.layout.addWidget(QLabel(title, objectName="panelTitle"))
        if description:
            text = QLabel(description, objectName="muted")
            text.setWordWrap(True)
            self.layout.addWidget(text)


class PathField(QWidget):
    browseRequested = Signal()

    def __init__(self, label: str, placeholder: str, button_text: str = "Parcourir"):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        layout.addWidget(QLabel(label, objectName="fieldLabel"))
        row = QHBoxLayout()
        row.setSpacing(7)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.edit.setMinimumHeight(40)
        self.button = QPushButton(button_text)
        self.button.setMinimumHeight(40)
        self.button.clicked.connect(self.browseRequested)
        row.addWidget(self.edit, 1)
        row.addWidget(self.button)
        layout.addLayout(row)
        self.setMinimumHeight(70)

    def text(self) -> str:
        return self.edit.text().strip()

    def setText(self, value: str) -> None:
        self.edit.setText(value)
        self.edit.setCursorPosition(0)


class CheckableFileList(QWidget):
    changed = Signal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(7)
        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list.itemChanged.connect(self.changed)
        layout.addWidget(self.list)

    def add_paths(self, paths: list[str]) -> None:
        existing = {self.list.item(index).data(Qt.ItemDataRole.UserRole) for index in range(self.list.count())}
        self.list.blockSignals(True)
        for path in paths:
            absolute = str(Path(path).resolve())
            if absolute in existing:
                continue
            item = QListWidgetItem(Path(absolute).name)
            item.setToolTip(absolute)
            item.setData(Qt.ItemDataRole.UserRole, absolute)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.list.addItem(item)
            existing.add(absolute)
        self.list.blockSignals(False)
        self.changed.emit()

    def selected_paths(self) -> list[str]:
        return [
            self.list.item(index).data(Qt.ItemDataRole.UserRole)
            for index in range(self.list.count())
            if self.list.item(index).checkState() == Qt.CheckState.Checked
        ]

    def all_paths(self) -> list[str]:
        return [self.list.item(index).data(Qt.ItemDataRole.UserRole) for index in range(self.list.count())]

    def remove_selected(self) -> None:
        for item in self.list.selectedItems():
            self.list.takeItem(self.list.row(item))
        self.changed.emit()

    def clear(self) -> None:
        self.list.clear()
        self.changed.emit()


class ColumnList(QListWidget):
    def set_columns(self, columns: list[str]) -> None:
        self.clear()
        for column in columns:
            item = QListWidgetItem(column)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.addItem(item)

    def checked_columns(self) -> tuple[str, ...]:
        return tuple(
            self.item(index).text()
            for index in range(self.count())
            if self.item(index).checkState() == Qt.CheckState.Checked
        )

    def restore_checked(self, columns: list[str]) -> None:
        if not columns:
            return
        wanted = set(columns)
        for index in range(self.count()):
            item = self.item(index)
            item.setCheckState(
                Qt.CheckState.Checked if item.text() in wanted else Qt.CheckState.Unchecked
            )

    def set_all(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for index in range(self.count()):
            self.item(index).setCheckState(state)

    def invert(self) -> None:
        for index in range(self.count()):
            item = self.item(index)
            item.setCheckState(
                Qt.CheckState.Unchecked if item.checkState() == Qt.CheckState.Checked else Qt.CheckState.Checked
            )


class ResultsTable(QTableWidget):
    HEADERS = ("Colonne", "Valeur", "Type", "Fichier", "Feuille", "Ligne", "Ouvrir")

    def __init__(self):
        super().__init__(0, len(self.HEADERS))
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)

    def populate(self, occurrences: list[DuplicateOccurrence]) -> None:
        self.setSortingEnabled(False)
        self.setRowCount(len(occurrences))
        for row, item in enumerate(occurrences):
            values = (
                item.column, item.value, item.duplicate_type, Path(item.source).name,
                item.sheet, str(item.row_number),
            )
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setToolTip(item.row_content if column == 1 else item.source)
                self.setItem(row, column, cell)
            button = QPushButton("Ouvrir")
            button.clicked.connect(
                lambda checked=False, path=item.source: QDesktopServices.openUrl(QUrl.fromLocalFile(path))
            )
            self.setCellWidget(row, 6, button)
        self.setSortingEnabled(True)
