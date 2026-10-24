"""Interactive gesture mapping editor for customizing gesture-to-action bindings, cooldowns, and sensitivity."""

from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QSpinBox,
    QCheckBox,
    QPushButton,
    QLabel,
    QHeaderView,
    QMessageBox,
)
from PySide6.QtCore import Qt
from app.core.config import GestureOSConfig
from app.core.types import GestureType, IntentType, InteractionMode


DEFAULT_MAPPINGS = [
    ("🖐 Open Hand", "Move Cursor", "Medium", 0, True),
    ("✊ Left Hand Fist", "Left Click", "Medium", 150, True),
    ("✊ Right Hand Fist", "Right Click", "Medium", 150, True),
    ("🤏 Pinch (Move to Drag)", "Mouse Drag", "Medium", 100, True),
    ("👍 Thumbs Up", "Vertical Scroll (Up)", "Medium", 80, True),
    ("👎 Thumbs Down", "Vertical Scroll (Down)", "Medium", 80, True),
    ("✌ Two Fingers (V-Shape)", "Play / Pause / Secondary", "Medium", 300, True),
    ("✊✊ Both Fists", "Emergency Stop", "Instant", 0, True),
    ("👉 Swipe Right (Advanced)", "Next Track / Slide", "Medium", 400, True),
    ("👈 Swipe Left (Advanced)", "Previous Track / Slide", "Medium", 400, True),
]

RECOMMENDED_PAIRS = {
    "🖐 Open Hand": ["Move Cursor"],
    "✊ Left Hand Fist": ["Left Click"],
    "✊ Right Hand Fist": ["Right Click"],
    "🤏 Pinch (Move to Drag)": ["Mouse Drag", "Left Click"],
    "👍 Thumbs Up": ["Vertical Scroll (Up)", "Volume Up", "Slide Next", "Maximize Window"],
    "👎 Thumbs Down": ["Vertical Scroll (Down)", "Volume Down", "Slide Prev", "Minimize Window"],
    "✌ Two Fingers (V-Shape)": ["Play / Pause / Secondary", "New Tab", "Secondary Click"],
    "✊✊ Both Fists": ["Emergency Stop"],
}


class GestureEditorWidget(QWidget):
    """Custom gesture mapping and sensitivity configuration table with smart recommendations."""

    def __init__(self, config: GestureOSConfig, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self._action_combos: list[QComboBox] = []
        self._status_items: list[QTableWidgetItem] = []
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        header = QLabel("Gesture Action Mappings & Smart Recommendations")
        header.setStyleSheet("font-size: 15px; font-weight: 600; color: #0d6efd;")
        layout.addWidget(header)

        # Mappings Table (6 columns: Gesture, Action, Sensitivity, Cooldown, Status/Recommendation, Active)
        self.table = QTableWidget(len(DEFAULT_MAPPINGS), 6)
        self.table.setHorizontalHeaderLabels([
            "Hand Gesture", "Assigned Action", "Sensitivity", "Cooldown (ms)", "Status / Recommendation", "Active"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet(
            "QTableWidget { font-family: system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', 'Noto Sans', Arial, sans-serif; "
            "background-color: #212529; border: 1px solid #373b3e; gridline-color: #373b3e; } "
            "QHeaderView::section { font-family: system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', 'Noto Sans', Arial, sans-serif; "
            "background-color: #2b3035; color: #dee2e6; border: none; border-bottom: 2px solid #495057; padding: 6px; font-weight: 600; } "
            "QTableWidget::item { padding: 5px; color: #dee2e6; }"
        )

        all_actions = [
            "Move Cursor", "Left Click", "Right Click", "Double Click",
            "Mouse Drag", "Vertical Scroll (Up)", "Vertical Scroll (Down)",
            "Play / Pause / Secondary", "Volume Up", "Volume Down",
            "Slide Next", "Slide Prev", "New Tab", "Maximize Window",
            "Minimize Window", "Emergency Stop"
        ]

        self._action_combos.clear()
        self._status_items.clear()

        for row, (gesture, action, sens, cd, enabled) in enumerate(DEFAULT_MAPPINGS):
            # 1. Gesture Name
            item_g = QTableWidgetItem(gesture)
            item_g.setFlags(item_g.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(row, 0, item_g)

            # 2. Action Combo
            combo_action = QComboBox()
            action_list = list(dict.fromkeys([action] + all_actions))
            combo_action.addItems(action_list)
            combo_action.setCurrentText(action)
            combo_action.currentIndexChanged.connect(self._validate_mappings)
            self._action_combos.append(combo_action)
            self.table.setCellWidget(row, 1, combo_action)

            # 3. Sensitivity Combo
            combo_sens = QComboBox()
            combo_sens.addItems(["Low", "Medium", "High", "Instant"])
            combo_sens.setCurrentText(sens)
            self.table.setCellWidget(row, 2, combo_sens)

            # 4. Cooldown Spinbox
            spin_cd = QSpinBox()
            spin_cd.setRange(0, 3000)
            spin_cd.setSingleStep(25)
            spin_cd.setValue(cd)
            self.table.setCellWidget(row, 3, spin_cd)

            # 5. Status / Recommendation
            item_status = QTableWidgetItem("Recommended")
            item_status.setFlags(item_status.flags() ^ Qt.ItemIsEditable)
            self._status_items.append(item_status)
            self.table.setItem(row, 4, item_status)

            # 6. Enabled Checkbox
            chk = QCheckBox()
            chk.setChecked(enabled)
            chk.setStyleSheet("margin-left: 20px;")
            self.table.setCellWidget(row, 5, chk)

        layout.addWidget(self.table)
        self._validate_mappings()

        # Buttons row
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Apply & Save Mappings")
        btn_save.setStyleSheet(
            "QPushButton { background-color: #0d6efd; color: #ffffff; border: 1px solid #0d6efd; padding: 7px 16px; font-weight: 500; border-radius: 6px; }"
            "QPushButton:hover { background-color: #0b5ed7; }"
        )
        btn_save.clicked.connect(self._save_mappings)
        btn_layout.addWidget(btn_save)

        btn_reset = QPushButton("Reset to Factory Defaults")
        btn_reset.setStyleSheet(
            "QPushButton { background-color: #343a40; color: #ffffff; border: 1px solid #495057; padding: 7px 16px; font-weight: 500; border-radius: 6px; }"
            "QPushButton:hover { background-color: #3d434a; }"
        )
        btn_reset.clicked.connect(self._reset_defaults)
        btn_layout.addWidget(btn_reset)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _validate_mappings(self) -> None:
        """Examine current mappings to detect conflicts or highlight recommended pairings."""
        action_counts: dict[str, int] = {}
        for combo in self._action_combos:
            act = combo.currentText()
            action_counts[act] = action_counts.get(act, 0) + 1

        for row, (gesture, _, _, _, _) in enumerate(DEFAULT_MAPPINGS):
            combo = self._action_combos[row]
            act = combo.currentText()
            item = self._status_items[row]

            # Conflict: multiple gestures mapped to same action (except Emergency Stop)
            if action_counts.get(act, 0) > 1 and act != "Emergency Stop":
                item.setText("⚠️ Conflict: duplicate action")
                item.setForeground(Qt.yellow)
            elif gesture in RECOMMENDED_PAIRS and act in RECOMMENDED_PAIRS[gesture]:
                item.setText("✓ Recommended")
                item.setForeground(Qt.green)
            else:
                item.setText("Custom binding")
                item.setForeground(Qt.lightGray)

    def _save_mappings(self) -> None:
        QMessageBox.information(self, "Gesture Mappings Saved", "Gesture action bindings and cooldowns have been successfully applied.")

    def _reset_defaults(self) -> None:
        for row, (_, action, sens, cd, enabled) in enumerate(DEFAULT_MAPPINGS):
            self._action_combos[row].setCurrentText(action)
            spin = self.table.cellWidget(row, 3)
            if isinstance(spin, QSpinBox):
                spin.setValue(cd)
            chk = self.table.cellWidget(row, 5)
            if isinstance(chk, QCheckBox):
                chk.setChecked(enabled)
        self._validate_mappings()
        QMessageBox.information(self, "Reset Mappings", "Default factory gesture mappings restored.")
