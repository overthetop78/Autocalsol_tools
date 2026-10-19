from __future__ import annotations

import traceback
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QSettings, Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QMainWindow, QMessageBox, QProgressBar, QPushButton, QScrollArea,
    QSplitter, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)

from ..services.autocalsol_service import ConversionOptions, convert_to_autocalsol
from ..services.duplicate_service import (
    DuplicateAnalysis, DuplicateOptions, analyze_duplicates, export_duplicates,
    get_available_columns, supported_files_in_folder,
)
from .theme import APP_STYLE
from .components import CheckableFileList, ColumnList, Panel, PathField, ResultsTable


class Worker(QObject):
    finished = Signal(object)
    failed = Signal(str)
    progress = Signal(str)

    def __init__(self, function, with_progress: bool = False):
        super().__init__()
        self.function = function
        self.with_progress = with_progress

    @Slot()
    def run(self):
        try:
            result = self.function(self.progress.emit) if self.with_progress else self.function()
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(f"{exc}\n\n{traceback.format_exc()}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("AutocalsolTools", "AutocalsolTools")
        self._threads: list[QThread] = []
        # Garder une référence Python vers chaque worker jusqu'à la fin du
        # thread. Sans cela, PySide peut détruire le QObject avant que
        # QThread.started n'appelle run() : l'interface reste alors en attente
        # indéfiniment sans journal ni fichier produit.
        self._workers: list[Worker] = []
        self.last_duplicate_result: DuplicateAnalysis | None = None
        self.setWindowTitle("Autocalsol Tools")
        self.setMinimumSize(1000, 700)
        self.resize(1280, 820)
        self.setStyleSheet(APP_STYLE)

        root = QWidget(objectName="appRoot")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(18, 16, 18, 16)
        root_layout.setSpacing(10)
        root_layout.addWidget(self._topbar())
        self.tabs = QTabWidget()
        self.tabs.addTab(self._conversion_page(), "Conversion des courbes")
        self.tabs.addTab(self._duplicates_page(), "Duplicate Finder")
        root_layout.addWidget(self.tabs, 1)
        self.setCentralWidget(root)
        self._restore_settings()

    def _topbar(self) -> QFrame:
        frame = QFrame(objectName="topbar")
        frame.setFixedHeight(66)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20, 13, 18, 13)
        titles = QVBoxLayout()
        titles.setSpacing(1)
        titles.addWidget(QLabel("Autocalsol Tools", objectName="logo"))
        titles.addWidget(QLabel("Courbes de charge et contrôle de données", objectName="tagline"))
        layout.addLayout(titles)
        layout.addStretch()
        layout.addWidget(QLabel("ENEDIS · CSV · EXCEL", objectName="versionBadge"))
        return frame

    def _conversion_page(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(12)

        controls = Panel(
            "Paramètres d’export",
            "Choisissez la source, le dossier fixe de sortie et le pas attendu par Autocalsol.",
        )
        controls.setMinimumWidth(390)
        controls.setMaximumWidth(470)
        self.base_folder = PathField("Dossier de base", "Emplacement de travail par défaut", "Choisir")
        self.base_folder.browseRequested.connect(self._choose_base_folder)
        self.curve_source = PathField("Fichier XLSX ou CSV", "Aucun fichier sélectionné")
        self.curve_source.browseRequested.connect(self._choose_curve_source)
        self.curve_output = PathField("Dossier de sortie", "Dossier des exports", "Choisir")
        self.curve_output.browseRequested.connect(self._choose_curve_output)
        controls.layout.addWidget(self.base_folder)
        controls.layout.addWidget(self.curve_source)
        controls.layout.addWidget(self.curve_output)

        controls.layout.addWidget(QLabel("Pas de sortie", objectName="fieldLabel"))
        self.step_combo = QComboBox()
        for label, minutes in (("5 minutes", 5), ("10 minutes", 10), ("15 minutes", 15), ("30 minutes (défaut)", 30), ("1 heure", 60)):
            self.step_combo.addItem(label, minutes)
        self.step_combo.setCurrentIndex(3)
        self.step_combo.currentIndexChanged.connect(self._save_settings)
        controls.layout.addWidget(self.step_combo)
        hint = QLabel(
            "Nombre de lignes annuel : 105 120 (5 min), 52 560 (10 min), 35 040 (15 min), 17 520 (30 min) ou 8 760 (1 h). Les années bissextiles sont adaptées automatiquement.",
            objectName="muted",
        )
        hint.setWordWrap(True)
        controls.layout.addWidget(hint)
        controls.layout.addStretch()
        self.convert_button = QPushButton("Lancer la conversion", objectName="primary")
        self.convert_button.clicked.connect(self._convert)
        controls.layout.addWidget(self.convert_button)
        self.convert_progress = QProgressBar()
        self.convert_progress.setRange(0, 1)
        controls.layout.addWidget(self.convert_progress)

        report = Panel("Journal de conversion", "Chaque compteur et chaque année produisent un fichier indépendant.")
        self.convert_log = QTextEdit(objectName="console")
        self.convert_log.setReadOnly(True)
        self.convert_log.setPlaceholderText("Prêt. Sélectionnez un fichier pour commencer.")
        report.layout.addWidget(self.convert_log, 1)
        self.open_curve_output = QPushButton("Ouvrir le dossier de sortie")
        self.open_curve_output.clicked.connect(lambda: self._open_folder(self.curve_output.text()))
        report.layout.addWidget(self.open_curve_output)
        layout.addWidget(controls)
        layout.addWidget(report, 1)
        return page

    def _duplicates_page(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(12)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        scroll = QScrollArea(objectName="page")
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(430)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        controls_host = QWidget()
        controls_layout = QVBoxLayout(controls_host)
        controls_layout.setContentsMargins(0, 0, 5, 0)
        controls_layout.setSpacing(10)

        files_panel = Panel("Sources à analyser", "Ajoutez des fichiers ou un dossier complet. La sélection est conservée au prochain lancement.")
        self.duplicate_files = CheckableFileList()
        self.duplicate_files.setMinimumHeight(150)
        self.duplicate_files.changed.connect(self._duplicate_sources_changed)
        files_panel.layout.addWidget(self.duplicate_files)
        file_actions = QHBoxLayout()
        add_files = QPushButton("Fichiers…")
        add_files.clicked.connect(self._add_duplicate_files)
        add_folder = QPushButton("Dossier…")
        add_folder.clicked.connect(self._add_duplicate_folder)
        remove = QPushButton("Retirer", objectName="danger")
        remove.clicked.connect(self.duplicate_files.remove_selected)
        file_actions.addWidget(add_files)
        file_actions.addWidget(add_folder)
        file_actions.addWidget(remove)
        files_panel.layout.addLayout(file_actions)
        self.recursive_checkbox = QCheckBox("Inclure les sous-dossiers")
        self.recursive_checkbox.setChecked(True)
        self.recursive_checkbox.toggled.connect(self._save_settings)
        files_panel.layout.addWidget(self.recursive_checkbox)
        controls_layout.addWidget(files_panel)

        columns_panel = Panel("Colonnes", "Analyse automatique de toutes les colonnes, ou sélection métier précise.")
        self.business_mode = QCheckBox("Sélection manuelle des colonnes")
        self.business_mode.toggled.connect(self._toggle_columns)
        self.business_mode.toggled.connect(self._save_settings)
        columns_panel.layout.addWidget(self.business_mode)
        self.column_list = ColumnList()
        self.column_list.setMaximumHeight(150)
        self.column_list.setVisible(False)
        columns_panel.layout.addWidget(self.column_list)
        column_actions = QWidget()
        column_row = QHBoxLayout(column_actions)
        column_row.setContentsMargins(0, 0, 0, 0)
        for label, callback in (("Tout", lambda: self.column_list.set_all(True)), ("Aucun", lambda: self.column_list.set_all(False)), ("Inverser", self.column_list.invert)):
            button = QPushButton(label)
            button.clicked.connect(callback)
            column_row.addWidget(button)
        column_actions.setVisible(False)
        self.column_actions = column_actions
        columns_panel.layout.addWidget(column_actions)
        controls_layout.addWidget(columns_panel)

        options_panel = Panel("Règles de comparaison")
        self.trim_checkbox = QCheckBox("Nettoyer les espaces")
        self.lower_checkbox = QCheckBox("Ignorer la casse")
        self.zero_checkbox = QCheckBox("Ignorer les valeurs zéro")
        self.unnamed_checkbox = QCheckBox("Ignorer les colonnes sans nom")
        for checkbox in (self.trim_checkbox, self.lower_checkbox, self.zero_checkbox, self.unnamed_checkbox):
            checkbox.setChecked(True)
            checkbox.toggled.connect(self._save_settings)
            options_panel.layout.addWidget(checkbox)
        controls_layout.addWidget(options_panel)

        export_panel = Panel("Dossier fixe des rapports")
        self.duplicate_output = PathField("Emplacement", "Dossier des rapports", "Choisir")
        self.duplicate_output.browseRequested.connect(self._choose_duplicate_output)
        export_panel.layout.addWidget(self.duplicate_output)
        self.analyze_button = QPushButton("Analyser les doublons", objectName="primary")
        self.analyze_button.clicked.connect(self._analyze_duplicates)
        export_panel.layout.addWidget(self.analyze_button)
        controls_layout.addWidget(export_panel)
        controls_layout.addStretch()
        scroll.setWidget(controls_host)

        results = Panel("Résultats", "Doublons internes au même fichier et doublons externes entre fichiers.")
        metric_row = QHBoxLayout()
        self.metric_groups = QLabel("0 groupe", objectName="metric")
        self.metric_internal = QLabel("0 interne", objectName="metric")
        self.metric_external = QLabel("0 externe", objectName="metric")
        self.metric_values = QLabel("0 occurrence", objectName="metric")
        for metric in (self.metric_groups, self.metric_internal, self.metric_external, self.metric_values):
            metric_row.addWidget(metric)
        results.layout.addLayout(metric_row)
        self.duplicate_table = ResultsTable()
        results.layout.addWidget(self.duplicate_table, 1)
        export_row = QHBoxLayout()
        self.export_csv_button = QPushButton("Exporter CSV")
        self.export_xlsx_button = QPushButton("Exporter Excel")
        self.export_csv_button.clicked.connect(lambda: self._export_duplicate_result("csv"))
        self.export_xlsx_button.clicked.connect(lambda: self._export_duplicate_result("xlsx"))
        self.export_csv_button.setEnabled(False)
        self.export_xlsx_button.setEnabled(False)
        export_row.addWidget(self.export_csv_button)
        export_row.addWidget(self.export_xlsx_button)
        export_row.addStretch()
        self.duplicate_status = QLabel("Prêt à analyser.", objectName="status")
        export_row.addWidget(self.duplicate_status)
        results.layout.addLayout(export_row)

        splitter.addWidget(scroll)
        splitter.addWidget(results)
        splitter.setSizes([430, 700])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        layout.addWidget(splitter)
        return page

    def _choose_curve_source(self):
        start = self.base_folder.text() or self.settings.value("conversion/source_dir", "", str)
        path, _ = QFileDialog.getOpenFileName(self, "Courbe de charge", start, "Données (*.xlsx *.xlsm *.csv)")
        if path:
            self.curve_source.setText(path)
            self.settings.setValue("conversion/source_dir", str(Path(path).parent))
            self.settings.setValue("conversion/source_file", path)
            if not self.curve_output.text():
                self.curve_output.setText(str(Path(path).parent / f"{Path(path).stem}_Autocalsol"))

    def _choose_curve_output(self):
        path = QFileDialog.getExistingDirectory(self, "Dossier de sortie", self.curve_output.text())
        if path:
            self.curve_output.setText(path)
            self.settings.setValue("conversion/output_dir", path)

    def _choose_base_folder(self):
        start = self.base_folder.text() or str(Path.home())
        path = QFileDialog.getExistingDirectory(self, "Dossier de base", start)
        if not path:
            return
        self.base_folder.setText(path)
        self.settings.setValue("general/base_dir", path)
        if not self.curve_output.text():
            self.curve_output.setText(str(Path(path) / "Sorties_Autocalsol"))
        if not self.duplicate_output.text():
            self.duplicate_output.setText(str(Path(path) / "Rapports_Doublons"))

    def _convert(self):
        source, output = self.curve_source.text(), self.curve_output.text()
        if not source or not output:
            QMessageBox.warning(self, "Informations manquantes", "Sélectionnez le fichier source et le dossier de sortie.")
            return
        step = int(self.step_combo.currentData())
        self._save_settings()
        self.convert_button.setEnabled(False)
        self.convert_progress.setRange(0, 0)
        self.convert_log.setPlainText(f"Analyse de {Path(source).name}\nPas demandé : {step} minutes\n")
        self._start_worker(
            lambda progress: convert_to_autocalsol(
                source, output,
                options=ConversionOptions(output_step_minutes=step),
                progress=progress,
            ),
            self._conversion_done,
            self._conversion_failed,
            progress=self._conversion_progress,
        )

    def _conversion_progress(self, message: str):
        self.convert_log.append(message)
        scrollbar = self.convert_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _conversion_done(self, results):
        self.convert_button.setEnabled(True)
        self.convert_progress.setRange(0, 1)
        self.convert_progress.setValue(1)
        lines = [f"TERMINÉ — {len(results)} fichier(s) créé(s)", ""]
        for result in results:
            lines.append(f"✓ {result.path.name}\n  {result.row_count:,} lignes · {result.missing_points:,} créneaux complétés · {result.duplicate_points} doublon(s)")
        self.convert_log.setPlainText("\n".join(lines).replace(",", " "))

    def _conversion_failed(self, message: str):
        self.convert_button.setEnabled(True)
        self.convert_progress.setRange(0, 1)
        self.convert_progress.setValue(0)
        self.convert_log.setPlainText(message)
        QMessageBox.critical(self, "Conversion impossible", message.split("\n", 1)[0])

    def _add_duplicate_files(self):
        start = self.settings.value("duplicates/source_dir", "", str)
        paths, _ = QFileDialog.getOpenFileNames(self, "Fichiers à analyser", start, "Tables (*.csv *.xlsx *.xlsm *.xls *.ods)")
        if paths:
            self.settings.setValue("duplicates/source_dir", str(Path(paths[0]).parent))
            self.duplicate_files.add_paths(paths)

    def _add_duplicate_folder(self):
        start = self.settings.value("duplicates/source_dir", "", str)
        folder = QFileDialog.getExistingDirectory(self, "Dossier à analyser", start)
        if folder:
            self.settings.setValue("duplicates/source_dir", folder)
            paths = supported_files_in_folder(folder, self.recursive_checkbox.isChecked())
            self.duplicate_files.add_paths([str(path) for path in paths])
            self.duplicate_status.setText(f"{len(paths)} fichier(s) trouvé(s) dans le dossier.")

    def _duplicate_sources_changed(self):
        paths = self.duplicate_files.selected_paths()
        self.settings.setValue("duplicates/files", self.duplicate_files.all_paths())
        if not paths:
            self.column_list.clear()
            return
        columns, errors = get_available_columns(paths)
        self.column_list.set_columns(columns)
        saved_columns = self.settings.value("duplicates/selected_columns", [], list)
        if self.business_mode.isChecked():
            self.column_list.restore_checked(saved_columns)
        self.duplicate_status.setText(f"{len(paths)} fichier(s) · {len(columns)} colonne(s) détectée(s).")
        if errors:
            self.duplicate_status.setToolTip("\n".join(errors))

    def _toggle_columns(self, enabled: bool):
        self.column_list.setVisible(enabled)
        self.column_actions.setVisible(enabled)

    def _choose_duplicate_output(self):
        path = QFileDialog.getExistingDirectory(self, "Dossier des rapports", self.duplicate_output.text())
        if path:
            self.duplicate_output.setText(path)
            self.settings.setValue("duplicates/output_dir", path)

    def _analyze_duplicates(self):
        paths = self.duplicate_files.selected_paths()
        if not paths:
            QMessageBox.warning(self, "Aucune source", "Ajoutez ou cochez au moins un fichier.")
            return
        selected = self.column_list.checked_columns() if self.business_mode.isChecked() else None
        if self.business_mode.isChecked() and not selected:
            QMessageBox.warning(self, "Aucune colonne", "Cochez au moins une colonne à analyser.")
            return
        options = DuplicateOptions(
            selected_columns=selected,
            trim_values=self.trim_checkbox.isChecked(),
            lowercase_values=self.lower_checkbox.isChecked(),
            ignore_zero_values=self.zero_checkbox.isChecked(),
            ignore_unnamed_columns=self.unnamed_checkbox.isChecked(),
        )
        self.analyze_button.setEnabled(False)
        self.duplicate_status.setText("Analyse en cours…")
        self._start_worker(lambda: analyze_duplicates(paths, options), self._duplicates_done, self._duplicates_failed)

    def _duplicates_done(self, result: DuplicateAnalysis):
        self.last_duplicate_result = result
        self.analyze_button.setEnabled(True)
        self.duplicate_table.populate(result.occurrences)
        summary = result.summary
        self.metric_groups.setText(f"{summary.group_count} groupe(s)")
        self.metric_internal.setText(f"{summary.internal_count} interne(s)")
        self.metric_external.setText(f"{summary.external_count} externe(s)")
        self.metric_values.setText(f"{summary.occurrence_count} occurrence(s)")
        enabled = bool(result.occurrences)
        self.export_csv_button.setEnabled(enabled)
        self.export_xlsx_button.setEnabled(enabled)
        message = f"Terminé · {summary.scanned_value_count:,} valeurs parcourues · {summary.ignored_value_count:,} ignorées"
        if result.errors:
            message += f" · {len(result.errors)} erreur(s)"
        self.duplicate_status.setText(message.replace(",", " "))
        self.duplicate_status.setToolTip("\n".join(result.errors))

    def _duplicates_failed(self, message: str):
        self.analyze_button.setEnabled(True)
        self.duplicate_status.setText("Échec de l’analyse.")
        QMessageBox.critical(self, "Analyse impossible", message.split("\n", 1)[0])

    def _export_duplicate_result(self, extension: str):
        if not self.last_duplicate_result:
            return
        folder = self.duplicate_output.text() or str(Path.cwd() / "output")
        Path(folder).mkdir(parents=True, exist_ok=True)
        name = f"doublons_{datetime.now():%Y%m%d_%H%M%S}.{extension}"
        path = export_duplicates(self.last_duplicate_result, Path(folder) / name)
        self.duplicate_status.setText(f"Rapport créé : {path.name}")

    def _open_folder(self, folder: str):
        if folder:
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices
            Path(folder).mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(folder).resolve())))

    def _restore_settings(self):
        base = self.settings.value("general/base_dir", str(Path.home()), str)
        self.base_folder.setText(base)
        source = self.settings.value("conversion/source_file", "", str)
        if source and Path(source).is_file():
            self.curve_source.setText(source)
        self.curve_output.setText(self.settings.value("conversion/output_dir", "", str))
        step = int(self.settings.value("conversion/step", 30))
        index = self.step_combo.findData(step)
        self.step_combo.setCurrentIndex(index if index >= 0 else 3)
        default_reports = str(Path.cwd() / "output")
        self.duplicate_output.setText(self.settings.value("duplicates/output_dir", default_reports, str))
        self.recursive_checkbox.setChecked(self.settings.value("duplicates/recursive", True, bool))
        self.business_mode.setChecked(self.settings.value("duplicates/business_mode", False, bool))
        self.trim_checkbox.setChecked(self.settings.value("duplicates/trim", True, bool))
        self.lower_checkbox.setChecked(self.settings.value("duplicates/lowercase", True, bool))
        self.zero_checkbox.setChecked(self.settings.value("duplicates/ignore_zero", True, bool))
        self.unnamed_checkbox.setChecked(self.settings.value("duplicates/ignore_unnamed", True, bool))
        saved_files = self.settings.value("duplicates/files", [], list)
        existing = [path for path in saved_files if Path(path).is_file()]
        if existing:
            self.duplicate_files.add_paths(existing)

    def _save_settings(self, *_):
        self.settings.setValue("general/base_dir", self.base_folder.text())
        self.settings.setValue("conversion/source_file", self.curve_source.text())
        self.settings.setValue("conversion/output_dir", self.curve_output.text())
        self.settings.setValue("conversion/step", int(self.step_combo.currentData()))
        self.settings.setValue("duplicates/output_dir", self.duplicate_output.text())
        self.settings.setValue("duplicates/files", self.duplicate_files.all_paths())
        self.settings.setValue("duplicates/recursive", self.recursive_checkbox.isChecked())
        self.settings.setValue("duplicates/business_mode", self.business_mode.isChecked())
        self.settings.setValue("duplicates/trim", self.trim_checkbox.isChecked())
        self.settings.setValue("duplicates/lowercase", self.lower_checkbox.isChecked())
        self.settings.setValue("duplicates/ignore_zero", self.zero_checkbox.isChecked())
        self.settings.setValue("duplicates/ignore_unnamed", self.unnamed_checkbox.isChecked())
        self.settings.setValue("duplicates/selected_columns", list(self.column_list.checked_columns()))
        self.settings.sync()

    def _start_worker(self, function, success, failure, progress=None):
        thread, worker = QThread(self), Worker(function, with_progress=progress is not None)
        self._workers.append(worker)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(success)
        worker.failed.connect(failure)
        if progress is not None:
            worker.progress.connect(progress)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._workers.remove(worker) if worker in self._workers else None)
        thread.finished.connect(lambda: self._threads.remove(thread) if thread in self._threads else None)
        self._threads.append(thread)
        thread.start()

    def closeEvent(self, event):
        self._save_settings()
        super().closeEvent(event)


def run_gui() -> int:
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("Autocalsol Tools")
    app.setOrganizationName("AutocalsolTools")
    app.setFont(QFont("Segoe UI", 10))
    window = MainWindow()
    window.show()
    return app.exec()
