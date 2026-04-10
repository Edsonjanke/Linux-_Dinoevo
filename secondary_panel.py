#!/usr/bin/env python3
"""
CyberDino - Painel Secundario (Pi Touch)
DRO (X/Z) + Tool/Feed + Spindle Override + Rapid Override
Roda no PC, exibido na Pi via VNC
"""

import sys
import os
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QGridLayout
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

# linuxcnc importado sob demanda para nao interferir com ProbeBasic
linuxcnc = None
LIVE = False

def _import_linuxcnc():
    global linuxcnc, LIVE
    if linuxcnc is not None:
        return True
    try:
        import importlib
        linuxcnc = importlib.import_module('linuxcnc')
        LIVE = True
        return True
    except ImportError:
        return False

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
        font-size: 16px;
        font-weight: bold;
    }}
    QLabel#axis-label {{
        color: {COPPER};
        font-size: 36px;
        font-weight: bold;
    }}
    QLabel#dro-value {{
        color: {TEXT_WHITE};
        font-size: 36px;
        font-weight: bold;
        font-family: "Monospace";
    }}
    QLabel#override-value {{
        color: {COPPER_LIGHT};
        font-size: 52px;
        font-weight: bold;
        font-family: "Monospace";
    }}
    QLabel#override-label {{
        color: {TEXT_DIM};
        font-size: 16px;
    }}
    QLabel#unit {{
        color: {TEXT_DIM};
        font-size: 20px;
    }}
    QLabel#info-label {{
        color: {COPPER};
        font-size: 22px;
        font-weight: bold;
    }}
    QLabel#info-value {{
        color: {TEXT_WHITE};
        font-size: 28px;
        font-weight: bold;
        font-family: "Monospace";
    }}
    QPushButton#ovr-btn {{
        background-color: {BG_BUTTON};
        color: {COPPER_LIGHT};
        border: 2px solid {COPPER_DIM};
        border-radius: 8px;
        font-size: 24px;
        font-weight: bold;
        min-width: 55px;
        min-height: 45px;
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
        font-size: 14px;
        font-weight: bold;
        min-width: 55px;
        min-height: 35px;
    }}
    QPushButton#ovr-100:pressed {{
        background-color: {COPPER_DIM};
        color: black;
    }}
    QPushButton#rapid-btn {{
        background-color: {BG_BUTTON};
        color: {COPPER_LIGHT};
        border: 2px solid {COPPER_DIM};
        border-radius: 8px;
        font-size: 18px;
        font-weight: bold;
        min-height: 42px;
    }}
    QPushButton#rapid-btn:pressed {{
        background-color: {COPPER_DIM};
        color: black;
    }}
    QPushButton#rapid-btn-active {{
        background-color: {COPPER_DIM};
        color: black;
        border: 2px solid {COPPER_LIGHT};
        border-radius: 8px;
        font-size: 18px;
        font-weight: bold;
        min-height: 42px;
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
        self._reconnect_counter = 0
        self.rapid_buttons = []
        self.cycle_start_time = None
        self.cycle_elapsed = 0
        self._prev_interp_state = None
        self._build_ui()

        # Update timer - 10Hz
        self.timer = QTimer()
        self.timer.timeout.connect(self._update)
        self.timer.start(100)

    def _build_ui(self):
        main = QHBoxLayout(self)
        main.setContentsMargins(10, 10, 10, 10)
        main.setSpacing(10)

        # === LEFT: DRO + Tool/Feed ===
        left_frame = QFrame()
        left_frame.setObjectName("panel")
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(15, 10, 15, 10)
        left_layout.setSpacing(6)

        title_dro = QLabel("POSICAO")
        title_dro.setObjectName("title")
        title_dro.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(title_dro)

        # X axis
        x_row = QHBoxLayout()
        x_label = QLabel("X")
        x_label.setObjectName("axis-label")
        x_label.setFixedWidth(50)
        x_label.setAlignment(Qt.AlignCenter)
        self.x_value = QLabel("+000.000")
        self.x_value.setObjectName("dro-value")
        self.x_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        x_unit = QLabel("mm")
        x_unit.setObjectName("unit")
        x_unit.setFixedWidth(40)
        x_row.addWidget(x_label)
        x_row.addWidget(self.x_value, 1)
        x_row.addWidget(x_unit)
        left_layout.addLayout(x_row)

        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setStyleSheet(f"color: {COPPER_DIM};")
        left_layout.addWidget(sep1)

        # Z axis
        z_row = QHBoxLayout()
        z_label = QLabel("Z")
        z_label.setObjectName("axis-label")
        z_label.setFixedWidth(50)
        z_label.setAlignment(Qt.AlignCenter)
        self.z_value = QLabel("+000.000")
        self.z_value.setObjectName("dro-value")
        self.z_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        z_unit = QLabel("mm")
        z_unit.setObjectName("unit")
        z_unit.setFixedWidth(40)
        z_row.addWidget(z_label)
        z_row.addWidget(self.z_value, 1)
        z_row.addWidget(z_unit)
        left_layout.addLayout(z_row)

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet(f"color: {COPPER_DIM};")
        left_layout.addWidget(sep2)

        # Tool + Feed (centered)
        info_row = QHBoxLayout()
        info_row.setSpacing(8)
        info_row.addStretch()
        tool_label = QLabel("FERR")
        tool_label.setObjectName("info-label")
        self.tool_value = QLabel("T0")
        self.tool_value.setObjectName("info-value")
        feed_label = QLabel("F")
        feed_label.setObjectName("info-label")
        self.feed_value = QLabel("0")
        self.feed_value.setObjectName("info-value")
        feed_unit = QLabel("mm/min")
        feed_unit.setObjectName("unit")
        cycle_label = QLabel("CICLO")
        cycle_label.setObjectName("info-label")
        self.cycle_value = QLabel("00:00")
        self.cycle_value.setObjectName("info-value")
        info_row.addWidget(tool_label)
        info_row.addWidget(self.tool_value)
        info_row.addSpacing(12)
        info_row.addWidget(feed_label)
        info_row.addWidget(self.feed_value)
        info_row.addSpacing(12)
        info_row.addWidget(cycle_label)
        info_row.addWidget(self.cycle_value)
        info_row.addStretch()
        left_layout.addLayout(info_row)

        # G-code viewer (5 before + current + 5 after)
        self.gcode_label = QLabel("")
        self.gcode_label.setStyleSheet(f"color: #cccc00; font-size: 17px; font-weight: bold; font-family: Monospace; background-color: {BG_DARK}; padding: 4px;")
        self.gcode_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        left_layout.addWidget(self.gcode_label, 1)

        self._gcode_lines = []
        self._gcode_file = ""
        main.addWidget(left_frame, 3)

        # === RIGHT: Spindle Override + Rapid Override ===
        right_frame = QFrame()
        right_frame.setObjectName("panel")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(15, 10, 15, 10)
        right_layout.setSpacing(4)

        # -- Spindle Override --
        title_ovr = QLabel("SPINDLE")
        title_ovr.setObjectName("title")
        title_ovr.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(title_ovr)

        self.ovr_value = QLabel("100%")
        self.ovr_value.setObjectName("override-label")
        self.ovr_value.setAlignment(Qt.AlignCenter)
        self.ovr_value.setStyleSheet(f"color: {COPPER_LIGHT}; font-size: 28px; font-weight: bold;")
        right_layout.addWidget(self.ovr_value)

        # 5 buttons in 3 rows: [50%] / [75%  100%] / [150%  200%]
        self.spindle_buttons = []

        sovr_row1 = QHBoxLayout()
        sovr_row1.setSpacing(6)
        btn = QPushButton("50%")
        btn.setObjectName("rapid-btn")
        btn.clicked.connect(lambda _, p=50: self._set_override(p))
        sovr_row1.addWidget(btn)
        self.spindle_buttons.append((50, btn))
        right_layout.addLayout(sovr_row1)

        sovr_row2 = QHBoxLayout()
        sovr_row2.setSpacing(6)
        for pct in [75, 100]:
            btn = QPushButton(f"{pct}%")
            btn.setObjectName("rapid-btn")
            btn.clicked.connect(lambda _, p=pct: self._set_override(p))
            sovr_row2.addWidget(btn)
            self.spindle_buttons.append((pct, btn))
        right_layout.addLayout(sovr_row2)

        sovr_row3 = QHBoxLayout()
        sovr_row3.setSpacing(6)
        for pct in [150, 200]:
            btn = QPushButton(f"{pct}%")
            btn.setObjectName("rapid-btn")
            btn.clicked.connect(lambda _, p=pct: self._set_override(p))
            sovr_row3.addWidget(btn)
            self.spindle_buttons.append((pct, btn))
        right_layout.addLayout(sovr_row3)

        # Fine adjust: -10  -1  +1  +10
        fine_row = QHBoxLayout()
        fine_row.setSpacing(6)
        for text, delta in [("-10", -10), ("-1", -1), ("+1", 1), ("+10", 10)]:
            btn = QPushButton(text)
            btn.setObjectName("ovr-btn")
            btn.clicked.connect(lambda _, d=delta: self._adjust_override(d))
            fine_row.addWidget(btn)
        right_layout.addLayout(fine_row)

        # -- Separator --
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.HLine)
        sep3.setStyleSheet(f"color: {COPPER_DIM};")
        right_layout.addSpacing(6)
        right_layout.addWidget(sep3)
        right_layout.addSpacing(4)

        # -- Rapid Override (G0) --
        rapid_title = QLabel("G0 RAPID")
        rapid_title.setObjectName("title")
        rapid_title.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(rapid_title)

        self.rapid_value_label = QLabel("100%")
        self.rapid_value_label.setObjectName("override-label")
        self.rapid_value_label.setAlignment(Qt.AlignCenter)
        self.rapid_value_label.setStyleSheet(f"color: {COPPER_LIGHT}; font-size: 28px; font-weight: bold;")
        right_layout.addWidget(self.rapid_value_label)

        # 5 buttons in 3 rows: [5%] / [25%  50%] / [75%  100%]
        self.rapid_buttons = []

        rapid_row1 = QHBoxLayout()
        rapid_row1.setSpacing(6)
        btn = QPushButton("5%")
        btn.setObjectName("rapid-btn")
        btn.clicked.connect(lambda _, p=5: self._set_rapid(p))
        rapid_row1.addWidget(btn)
        self.rapid_buttons.append((5, btn))
        right_layout.addLayout(rapid_row1)

        rapid_row2 = QHBoxLayout()
        rapid_row2.setSpacing(6)
        for pct in [25, 50]:
            btn = QPushButton(f"{pct}%")
            btn.setObjectName("rapid-btn")
            btn.clicked.connect(lambda _, p=pct: self._set_rapid(p))
            rapid_row2.addWidget(btn)
            self.rapid_buttons.append((pct, btn))
        right_layout.addLayout(rapid_row2)

        rapid_row3 = QHBoxLayout()
        rapid_row3.setSpacing(6)
        for pct in [75, 100]:
            btn = QPushButton(f"{pct}%")
            btn.setObjectName("rapid-btn")
            btn.clicked.connect(lambda _, p=pct: self._set_rapid(p))
            rapid_row3.addWidget(btn)
            self.rapid_buttons.append((pct, btn))
        right_layout.addLayout(rapid_row3)

        right_layout.addStretch()
        main.addWidget(right_frame, 4)

    def _adjust_override(self, delta):
        if self.stat:
            try:
                current = int(self.stat.spindle[0]['override'] * 100)
                self._set_override(max(10, min(200, current + delta)))
            except Exception:
                pass

    def _set_override(self, percent):
        self.ovr_value.setText(f"{percent}%")
        if self.cmd:
            try:
                self.cmd.spindleoverride(percent / 100.0, 0)
            except Exception:
                pass

    def _update_spindle_buttons(self, current_pct):
        for pct, btn in self.spindle_buttons:
            if abs(pct - current_pct) < 2:
                btn.setObjectName("rapid-btn-active")
            else:
                btn.setObjectName("rapid-btn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _set_rapid(self, percent):
        self.rapid_value_label.setText(f"{percent}%")
        if self.cmd:
            try:
                self.cmd.rapidrate(percent / 100.0)
            except Exception:
                pass

    def _update_rapid_buttons(self, current_pct):
        for pct, btn in self.rapid_buttons:
            if abs(pct - current_pct) < 2:
                btn.setObjectName("rapid-btn-active")
            else:
                btn.setObjectName("rapid-btn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _linuxcnc_ready(self):
        """Verifica se milltask E probe_basic estao rodando via /proc."""
        found_milltask = False
        found_display = False
        try:
            for pid in os.listdir('/proc'):
                if not pid.isdigit():
                    continue
                try:
                    with open(f'/proc/{pid}/comm', 'r') as f:
                        comm = f.read().strip()
                    if comm == 'milltask':
                        found_milltask = True
                    if not found_display:
                        with open(f'/proc/{pid}/cmdline', 'rb') as f:
                            cmdline = f.read().decode('utf-8', errors='ignore')
                        if 'probe_basic_lathe' in cmdline:
                            found_display = True
                except (IOError, OSError):
                    continue
                if found_milltask and found_display:
                    return True
            return False
        except Exception:
            return False

    def _try_reconnect(self):
        """Tenta criar conexao com LinuxCNC. So conecta se tudo estiver pronto."""
        if not self._linuxcnc_ready():
            return
        if not _import_linuxcnc():
            return
        try:
            self.stat = linuxcnc.stat()
            self.stat.poll()
            self.cmd = linuxcnc.command()
            # Reset state ao conectar
            self.cycle_start_time = None
            self.cycle_elapsed = 0
            self._prev_interp_state = None
            self._gcode_file = ""
            self._gcode_lines = []
        except Exception:
            self.stat = None
            self.cmd = None

    def _update(self):
        if self.stat is None:
            # Sem conexao - tenta reconectar a cada 2s (20 ciclos de 100ms)
            self._reconnect_counter += 1
            if self._reconnect_counter >= 20:
                self._reconnect_counter = 0
                self._try_reconnect()
            return

        # Verifica se LinuxCNC ainda esta rodando a cada 2s
        self._reconnect_counter += 1
        if self._reconnect_counter >= 20:
            self._reconnect_counter = 0
            if not self._linuxcnc_ready():
                self.stat = None
                self.cmd = None
                self._reset_display()
                return

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
            # Tool number
            tool_num = self.stat.tool_in_spindle
            self.tool_value.setText(f"T{tool_num}")
            # Feed rate (settings[1] = F value in mm/min)
            feed = self.stat.settings[1]
            self.feed_value.setText(f"{feed:.0f}")
            # Spindle override
            ovr = int(self.stat.spindle[0]['override'] * 100)
            self.ovr_value.setText(f"{ovr}%")
            self._update_spindle_buttons(ovr)
            # Cycle time (interp_state: 1=reading, 2=paused, 3=waiting)
            interp = self.stat.interp_state
            if interp == linuxcnc.INTERP_READING and self._prev_interp_state != linuxcnc.INTERP_READING:
                if self.cycle_start_time is None:
                    self.cycle_start_time = time.time()
                    self.cycle_elapsed = 0
            elif interp == linuxcnc.INTERP_IDLE and self._prev_interp_state != linuxcnc.INTERP_IDLE:
                if self.cycle_start_time is not None:
                    self.cycle_elapsed = time.time() - self.cycle_start_time
                    self.cycle_start_time = None
            self._prev_interp_state = interp

            if self.cycle_start_time is not None:
                elapsed = time.time() - self.cycle_start_time
            else:
                elapsed = self.cycle_elapsed
            mins = int(elapsed) // 60
            secs = int(elapsed) % 60
            self.cycle_value.setText(f"{mins:02d}:{secs:02d}")

            # G-code viewer
            gcode_file = self.stat.file
            if gcode_file and gcode_file != self._gcode_file:
                try:
                    with open(gcode_file, 'r') as f:
                        self._gcode_lines = f.readlines()
                    self._gcode_file = gcode_file
                except Exception:
                    self._gcode_lines = []
            if gcode_file and self._gcode_lines:
                line = self.stat.motion_line if interp != linuxcnc.INTERP_IDLE else 0
                idx = max(0, line - 1)
                start = max(0, idx - 5)
                end = min(len(self._gcode_lines), idx + 6)
                display = []
                for i in range(start, end):
                    num = i + 1
                    txt = self._gcode_lines[i].rstrip()[:40]
                    if i == idx and line > 0:
                        display.append(f'<span style="color:{COPPER_LIGHT};">{num:4d}▸ {txt}</span>')
                    else:
                        display.append(f'{num:4d}  {txt}')
                self.gcode_label.setText('<pre>' + '\n'.join(display) + '</pre>')
            else:
                self.gcode_label.setText("")

            # Rapid override
            rapid_pct = int(self.stat.rapidrate * 100)
            self.rapid_value_label.setText(f"{rapid_pct}%")
            self._update_rapid_buttons(rapid_pct)

        except Exception:
            # Conexao perdida
            self.stat = None
            self.cmd = None
            self._reconnect_counter = 0
            self._reset_display()

    def _reset_display(self):
        self.x_value.setText("+000.000")
        self.z_value.setText("+000.000")
        self.tool_value.setText("T0")
        self.feed_value.setText("0")
        self.cycle_value.setText("00:00")
        self.ovr_value.setText("--")
        self.rapid_value_label.setText("--")
        self.gcode_label.setText("")
        self.cycle_start_time = None
        self.cycle_elapsed = 0
        self._prev_interp_state = None
        self._gcode_file = ""
        self._gcode_lines = []


def main():
    app = QApplication(sys.argv)
    app.setOverrideCursor(Qt.BlankCursor)  # Hide mouse cursor (touch only)
    panel = SecondaryPanel()
    panel.showFullScreen()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
