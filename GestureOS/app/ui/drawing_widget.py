"""Interactive Air Drawing Canvas widget for GestureOS."""

from __future__ import annotations
import numpy as np
import cv2
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QColorDialog,
    QSpinBox,
    QFileDialog,
    QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from app.modes.drawing_mode import DrawingMode


class DrawingWidget(QWidget):
    """UI view for Air Drawing mode canvas."""

    def __init__(self, drawing_mode: DrawingMode, parent=None) -> None:
        super().__init__(parent)
        self.drawing_mode = drawing_mode
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Toolbar
        toolbar = QHBoxLayout()

        btn_undo = QPushButton("Undo")
        btn_undo.clicked.connect(self._on_undo)
        toolbar.addWidget(btn_undo)

        btn_redo = QPushButton("Redo")
        btn_redo.clicked.connect(self._on_redo)
        toolbar.addWidget(btn_redo)

        btn_clear = QPushButton("Clear Canvas")
        btn_clear.clicked.connect(self._on_clear)
        toolbar.addWidget(btn_clear)

        toolbar.addSpacing(15)

        # Width selector
        toolbar.addWidget(QLabel("Brush Width:"))
        self.spin_width = QSpinBox()
        self.spin_width.setRange(1, 30)
        self.spin_width.setValue(self.drawing_mode.brush_width)
        self.spin_width.valueChanged.connect(self._on_width_changed)
        toolbar.addWidget(self.spin_width)

        toolbar.addSpacing(15)

        # Export button
        btn_export = QPushButton("Export Canvas (PNG)")
        btn_export.setStyleSheet(
            "QPushButton { background-color: #0d6efd; color: #ffffff; border: 1px solid #0d6efd; padding: 6px 14px; font-weight: 500; border-radius: 6px; }"
            "QPushButton:hover { background-color: #0b5ed7; }"
        )
        btn_export.clicked.connect(self._on_export)
        toolbar.addWidget(btn_export)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Visual Gesture Guide Bar
        guide_bar = QLabel("🖐/☝ Draw  |  🤏 Grab  |  ✌ Switch Brush/Eraser  |  ✊ Pause  |  👍 Undo  |  👎 Redo  |  ✊✊ Emergency Stop")
        guide_bar.setStyleSheet(
            "background-color: #2b3035; color: #0dcaf0; border: 1px solid #373b3e; "
            "padding: 6px 14px; border-radius: 6px; font-weight: 500; font-size: 12px;"
        )
        guide_bar.setAlignment(Qt.AlignCenter)
        layout.addWidget(guide_bar)

        # Canvas display
        self.lbl_canvas = QLabel()
        self.lbl_canvas.setAlignment(Qt.AlignCenter)
        self.lbl_canvas.setStyleSheet("background-color: #1a1d20; border: 1px solid #373b3e; border-radius: 6px;")
        layout.addWidget(self.lbl_canvas)

    def _on_undo(self) -> None:
        self.drawing_mode.undo()
        self.update_canvas_display()

    def _on_redo(self) -> None:
        self.drawing_mode.redo()
        self.update_canvas_display()

    def _on_clear(self) -> None:
        self.drawing_mode.clear_canvas()
        self.update_canvas_display()

    def _on_width_changed(self, val: int) -> None:
        self.drawing_mode.brush_width = val

    def _on_export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export Canvas", "gestureos_drawing.png", "Images (*.png *.jpg)")
        if path:
            ok = self.drawing_mode.export_canvas(path)
            if ok:
                QMessageBox.information(self, "Export Successful", f"Saved canvas to:\n{path}")
            else:
                QMessageBox.critical(self, "Export Failed", "Could not save canvas image.")

    def update_canvas_display(self) -> None:
        canvas_bgr = self.drawing_mode.render_canvas()
        h, w, ch = canvas_bgr.shape
        rgb = cv2.cvtColor(canvas_bgr, cv2.COLOR_BGR2RGB)
        q_img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888).copy()
        self.lbl_canvas.setPixmap(QPixmap.fromImage(q_img))
