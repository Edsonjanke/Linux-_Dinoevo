#!/usr/bin/env python3
"""
CyberDino - Feed Override Encoder via BTT Octopus USB
Componente HAL userspace para LinuxCNC

Pins HAL criados:
  feed-encoder.counts      (s32 out) - contagem do encoder
  feed-encoder.button      (bit out) - estado do botao
  feed-encoder.scale       (float in) - escala do feed override (default 0.01 = 1% por click)
  feed-encoder.enable      (bit in)  - habilita/desabilita
  feed-encoder.connected   (bit out) - USB conectado

Uso no INI:
  [HAL]
  HALFILE = ...
  # Adicionar no custom.hal ou arquivo separado:
  # loadusr -W feed_encoder
"""

import hal
import serial
import serial.tools.list_ports
import sys
import time

VENDOR_NAME = "CyberDino"
BAUD = 115200
USB_VID_PID = None  # Auto-detect

def find_octopus():
    """Procura a porta serial do Octopus"""
    for port in serial.tools.list_ports.comports():
        # Tentar por nome do fabricante
        if port.manufacturer and "CyberDino" in port.manufacturer:
            return port.device
        if port.product and "FeedEncoder" in port.product:
            return port.device
    # Fallback: primeiro ttyACM
    for port in serial.tools.list_ports.comports():
        if "ttyACM" in port.device:
            return port.device
    return None

def main():
    h = hal.component("feed-encoder")
    h.newpin("counts", hal.HAL_S32, hal.HAL_OUT)
    h.newpin("button", hal.HAL_BIT, hal.HAL_OUT)
    h.newpin("scale", hal.HAL_FLOAT, hal.HAL_IN)
    h.newpin("enable", hal.HAL_BIT, hal.HAL_IN)
    h.newpin("connected", hal.HAL_BIT, hal.HAL_OUT)
    h.ready()

    h["scale"] = 0.01  # 1% por click
    h["enable"] = True

    ser = None
    last_reconnect = 0

    try:
        while True:
            # Conectar/reconectar
            if ser is None or not ser.is_open:
                h["connected"] = False
                now = time.time()
                if now - last_reconnect < 2:
                    time.sleep(0.1)
                    continue
                last_reconnect = now
                port = find_octopus()
                if port is None:
                    continue
                try:
                    ser = serial.Serial(port, BAUD, timeout=0.05)
                    h["connected"] = True
                except (serial.SerialException, OSError):
                    ser = None
                    continue

            # Ler dados
            try:
                line = ser.readline().decode("ascii", errors="ignore").strip()
                if not line:
                    continue

                # Parse: "E:123 B:0"
                parts = line.split()
                for part in parts:
                    if part.startswith("E:"):
                        try:
                            h["counts"] = int(part[2:])
                        except ValueError:
                            pass
                    elif part.startswith("B:"):
                        try:
                            h["button"] = bool(int(part[2:]))
                        except ValueError:
                            pass

            except (serial.SerialException, OSError):
                ser = None
                continue

    except KeyboardInterrupt:
        pass
    finally:
        if ser and ser.is_open:
            ser.close()

if __name__ == "__main__":
    main()
