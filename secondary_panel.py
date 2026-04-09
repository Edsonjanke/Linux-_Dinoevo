#!/usr/bin/env python3
"""
CyberDino - Painel Secundario (Pi Touch)
DRO (X/Z) + Spindle Override com controle touch
Roda no PC, exibido na Pi via VNC
"""

import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QFrame, QGridLayout
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

# Tenta importar linuxcnc, senao usa modo demo
try:
    import linuxcnc
    LIVE = True
except ImportError:
    LIVE = False

# -- Cores tema cobre (matching ProbeBasic custom) --
BG_DARK = "#1a1a1a"
BG_PANEL = "#2a2a2a"
BG_BUTTON = "#3a3a3a"
COPPER = "#da8728"
COPPER_LIGHT = "#e8a040"
COPPER_DIM = "#b86410"
TEXT_WHITE = "#e0e0e0"
TEXT_DIM = "#888888"

STYLESHEET = f"""
    QWidget {{
        background-color: {BG_DARK};
        color: {TEXT_WHITE};
    }}
    QFrame#panel {{
        background-color: {BG_PANEL};
        border: 2px solid {COPPER_DIM};
        border-radius: 10px;
    }}
    QLabel#title {{
        color: {COPPER};
        font-size: 18px;
        font-weight: bold;
    }}
    QLabel#axis-label {{
        color: {COPPER};
        font-size: 38px;
        font-weight: bold;
    }}
    QLabel#dro-value {{
        color: {TEXT_WHITE};
        font-size: 56px;
        font-weight: bold;
        font-family: "Monospace";
    }}
    QLabel#override-value {{
        color: {COPPER_LIGHT};
        font-size: 72px;
        font-weight: bold;
        font-family: "Monospace";
    }}
    QLabel#override-label {{
        color: {TEXT_DIM};
        font-size: 20px;
    }}
    QLabel#unit {{
        color: {TEXT_DIM};
        font-size: 22px;
    }}
    QPushButton#ovr-btn {{
        background-color: {BG_BUTTON};
        color: {COPPER_LIGHT};
        border: 2px solid {COPPER_DIM};
        border-radius: 8px;
        font-size: 28px;
        font-weight: bold;
        min-width: 65px;
        min-height: 55px;
    }}
    QPushButton#ovr-btn:pressed {{
        background-color: {COPPER_DIM};
        color: black;
    }}
    QPushButton#ovr-100 {{
        background-color: {BG_BUTTON};
        color: {TEXT_DIM};
        border: 2px solid {COPPER_DIM};
        border-radius: 8px;
        font-size: 16px;
        font-weight: bold;
        min-width: 65px;
        min-height: 40px;
    }}
    QPushButton#ovr-100:pressed {{
        background-color: {COPPER_DIM};
        color: black;
    }}
    QSlider::groove:horizontal {{
        border: 1px solid {COPPER_DIM};
        height: 16px;
        background: {BG_BUTTON};
        border-radius: 8px;
    }}
    QSlider::handle:horizontal {{
        background: {COPPER};
        border: 2px solid {COPPER_LIGHT};
        width: 40px;
        margin: -8px 0;
        border-radius: 12px;
    }}
    QSlider::sub-page:horizontal {{
        background: {COPPER_DIM};
        border-radius: 8px;
    }}
"""


class SecondaryPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CyberDino - Painel")
        self.setFixedSize(800, 480)
        self.setStyleSheet(STYLESHEET)

        # LinuxCNC connection
        self.stat = None
        self.cmd = None
        if LIVE:
            try:
                self.stat = linuxcnc.stat()
                self.cmd = linuxcnc.command()
                self.stat.poll()
            except linuxcnc.error:
                self.stat = None
                self.cmd = None

        self._build_ui()

        # Update timer - 10Hz
        self.timer = QTimer()
        self.timer.timeout.connect(self._update)
        self.timer.start(100)

    def _build_ui(self):
        main = QHBoxLayout(self)
        main.setContentsMargins(15, 15, 15, 15)
        main.setSpacing(15)

        # === LEFT: DRO ===
        dro_frame = QFrame()
        dro_frame.setObjectName("panel")
        dro_layout = QVBoxLayout(dro_frame)
        dro_layout.setContentsMargins(20, 15, 20, 15)
        dro_layout.setSpacing(10)

        title_dro = QLabel("POSICAO")
        title_dro.setObjectName("title")
        title_dro.setAlignment(Qt.AlignCenter)
        dro_layout.addWidget(title_dro)

        dro_layout.addSpacing(10)

        # X axis
        x_row = QHBoxLayout()
        x_label = QLabel("X")
        x_label.setObjectName("axis-label")
        x_label.setFixedWidth(60)
        x_label.setAlignment(Qt.AlignCenter)
        self.x_value = QLabel("+000.000")
        self.x_value.setObjectName("dro-value")
        self.x_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        x_unit = QLabel("mm")
        x_unit.setObjectName("unit")
        x_unit.setFixedWidth(50)
        x_row.addWidget(x_label)
        x_row.addWidget(self.x_value, 1)
        x_row.addWidget(x_unit)
        dro_layout.addLayout(x_row)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {COPPER_DIM};")
        dro_layout.addWidget(sep)

        # Z axis
        z_row = QHBoxLayout()
        z_label = QLabel("Z")
        z_label.setObjectName("axis-label")
        z_label.setFixedWidth(60)
        z_label.setAlignment(Qt.AlignCenter)
        self.z_value = QLabel("+000.000")
        self.z_value.setObjectName("dro-value")
        self.z_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        z_unit = QLabel("mm")
        z_unit.setObjectName("unit")
        z_unit.setFixedWidth(50)
        z_row.addWidget(z_label)
        z_row.addWidget(self.z_value, 1)
        z_row.addWidget(z_unit)
        dro_layout.addLayout(z_row)

        dro_layout.addStretch()
        main.addWidget(dro_frame, 3)

        # === RIGHT: Spindle Override ===
        ovr_frame = QFrame()
        ovr_frame.setObjectName("panel")
        ovr_layout = QVBoxLayout(ovr_frame)
        ovr_layout.setContentsMargins(20, 15, 20, 15)
        ovr_layout.setSpacing(8)

        title_ovr = QLabel("SPINDLE")
        title_ovr.setObjectName("title")
        title_ovr.setAlignment(Qt.AlignCenter)
        ovr_layout.addWidget(title_ovr)

        # Override value display
        self.ovr_value = QLabel("100%")
        self.ovr_value.setObjectName("override-value")
        self.ovr_value.setAlignment(Qt.AlignCenter)
        ovr_layout.addWidget(self.ovr_value)

        ovr_label = QLabel("OVERRIDE")
        ovr_label.setObjectName("override-label")
        ovr_label.setAlignment(Qt.AlignCenter)
        ovr_layout.addWidget(ovr_label)

        ovr_layout.addSpacing(5)

        # Slider
        self.ovr_slider = QSlider(Qt.Horizontal)
        self.ovr_slider.setRange(50, 120)
        self.ovr_slider.setValue(100)
        self.ovr_slider.setSingleStep(1)
        self.ovr_slider.setPageStep(10)
        self.ovr_slider.valueChanged.connect(self._slider_changed)
        ovr_layout.addWidget(self.ovr_slider)

        ovr_layout.addSpacing(5)

        # Buttons row: -10  -1  100%  +1  +10
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        for text, delta in [("-10", -10), ("-1", -1)]:
            btn = QPushButton(text)
            btn.setObjectName("ovr-btn")
            btn.clicked.connect(lambda _, d=delta: self._adjust_override(d))
            btn_row.addWidget(btn)

        btn_100 = QPushButton("100%")
        btn_100.setObjectName("ovr-100")
        btn_100.clicked.connect(lambda: self._set_override(100))
        btn_row.addWidget(btn_100)

        for text, delta in [("+1", 1), ("+10", 10)]:
            btn = QPushButton(text)
            btn.setObjectName("ovr-btn")
            btn.clicked.connect(lambda _, d=delta: self._adjust_override(d))
            btn_row.addWidget(btn)

        ovr_layout.addLayout(btn_row)
        ovr_layout.addStretch()
        main.addWidget(ovr_frame, 2)

    def _slider_changed(self, value):
        self._set_override(value)

    def _adjust_override(self, delta):
        current = self.ovr_slider.value()
        new_val = max(50, min(120, current + delta))
        self.ovr_slider.setValue(new_val)

    def _set_override(self, percent):
        self.ovr_slider.blockSignals(True)
        self.ovr_slider.setValue(percent)
        self.ovr_slider.blockSignals(False)
        self.ovr_value.setText(f"{percent}%")
        if self.cmd:
            try:
                self.cmd.spindleoverride(percent / 100.0, 0)
            except linuxcnc.error:
                pass

    def _update(self):
        if self.stat:
            try:
                self.stat.poll()
                # DRO - work coordinates = actual - g5x - g92 - tool
                x = self.stat.actual_position[0]
                z = self.stat.actual_position[2]
                g5x = self.stat.g5x_offset
                g92 = self.stat.g92_offset
                tool = self.stat.tool_offset
                x -= g5x[0] + g92[0] + tool[0]
                z -= g5x[2] + g92[2] + tool[2]
                # Lathe: X in diameter (x2) to match ProbeBasic
                x *= 2
                self.x_value.setText(f"{x:+09.3f}")
                self.z_value.setText(f"{z:+09.3f}")
                # Spindle override
                ovr = int(self.stat.spindle[0]['override'] * 100)
                self.ovr_slider.blockSignals(True)
                self.ovr_slider.setValue(ovr)
                self.ovr_slider.blockSignals(False)
                self.ovr_value.setText(f"{ovr}%")
            except Exception:
                # Conexao perdida - volta para modo reconexao
                self.stat = None
                self.cmd = None
        else:
            # Sem conexao - tenta conectar ao LinuxCNC
            if LIVE:
                try:
                    self.stat = linuxcnc.stat()
                    self.cmd = linuxcnc.command()
                    self.stat.poll()
                except Exception:
                    self.stat = None
                    self.cmd = None


def main():
    app = QApplication(sys.argv)
    app.setOverrideCursor(Qt.BlankCursor)  # Hide mouse cursor (touch only)
    panel = SecondaryPanel()
    panel.showFullScreen()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
