#!/usr/bin/env python3
"""
ams32_hal.py - Componente HAL para AMS32 (Delta DVP clone) via Modbus ASCII
Substitui mb2hal para comunicacao ASCII que o mb2hal nao suporta.

Pins HAL criados (mesmo padrao do mb2hal):
  ams32.cmd.00-07       (bit IN)  - Comandos LinuxCNC -> PLC (M100-M107)
  ams32.status.00-15    (bit OUT) - Status PLC -> LinuxCNC (M200-M215)
  ams32.spindle-rpm     (float IN)- RPM para o PLC (D100)
  ams32.num-errors      (s32 OUT) - Contador de erros de comunicacao

Uso no HAL:
  loadusr -Wn ams32 python3 ams32_hal.py
"""

import hal
import time
import sys
import logging
from pymodbus.client import ModbusSerialClient
from pymodbus.framer import FramerType

# --- Logging ---
LOG_FILE = "/tmp/ams32_hal.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("ams32")

# --- Config ---
SERIAL_PORT = "/dev/ttyAMS32"
BAUDRATE = 9600
SLAVE_ID = 1
POLL_RATE = 0.05  # 50ms = 20Hz

# Enderecos Modbus
ADDR_CMD    = 2148   # M100-M107 (escrita coils)
ADDR_STATUS = 2248   # M200-M215 (leitura coils)
ADDR_RPM    = 4196   # D100 (escrita registro)

NUM_CMD    = 8
NUM_STATUS = 16


def main():
    log.info("=== ams32_hal iniciando ===")

    try:
        # Criar componente HAL
        h = hal.component("ams32")
        log.info("Componente HAL criado")

        # Pins de comando (LinuxCNC -> PLC)
        cmd_pins = []
        for i in range(NUM_CMD):
            h.newpin(f"cmd.{i:02d}", hal.HAL_BIT, hal.HAL_IN)
            cmd_pins.append(f"cmd.{i:02d}")

        # Pins de status (PLC -> LinuxCNC)
        status_pins = []
        for i in range(NUM_STATUS):
            h.newpin(f"status.{i:02d}", hal.HAL_BIT, hal.HAL_OUT)
            status_pins.append(f"status.{i:02d}")

        # Pin RPM
        h.newpin("spindle-rpm", hal.HAL_FLOAT, hal.HAL_IN)

        # Contador de erros
        h.newpin("num-errors", hal.HAL_S32, hal.HAL_OUT)

        # Pin de conexao ativa
        h.newpin("connected", hal.HAL_BIT, hal.HAL_OUT)

        h.ready()
        log.info("Pins criados, componente ready")

    except Exception as e:
        log.exception("Erro criando componente HAL")
        sys.exit(1)

    # Conectar ao AMS32
    client = ModbusSerialClient(
        port=SERIAL_PORT,
        baudrate=BAUDRATE,
        bytesize=7,
        parity="E",
        stopbits=1,
        framer=FramerType.ASCII,
        timeout=1,
        retries=1,
    )

    errors = 0
    connected = False
    last_cmd = [False] * NUM_CMD
    last_rpm = 0.0

    log.info(f"Configurado: {SERIAL_PORT} ASCII 9600 7E1")
    print(f"ams32_hal: Iniciando em {SERIAL_PORT} ASCII 9600 7E1, log em {LOG_FILE}")

    try:
        while True:
            loop_start = time.monotonic()

            # Reconectar se necessario
            if not connected:
                try:
                    if client.connect():
                        connected = True
                        h["connected"] = True
                        log.info("Conectado ao AMS32")
                    else:
                        log.warning("Falha ao conectar, tentando em 1s")
                        time.sleep(1)
                        continue
                except Exception:
                    log.exception("Erro ao conectar")
                    time.sleep(1)
                    continue

            # --- 1. Ler status M200-M215 (PLC -> LinuxCNC) ---
            try:
                r = client.read_coils(ADDR_STATUS, count=NUM_STATUS, device_id=SLAVE_ID)
                if not r.isError():
                    for i in range(NUM_STATUS):
                        h[status_pins[i]] = r.bits[i]
                else:
                    errors += 1
                    log.warning(f"Erro leitura status: {r}")
            except Exception:
                errors += 1
                log.exception("Excecao leitura status")
                connected = False
                h["connected"] = False
                client.close()
                continue

            # --- 2. Escrever comandos M100-M107 (LinuxCNC -> PLC) ---
            # So escreve se algum valor mudou
            current_cmd = [h[cmd_pins[i]] for i in range(NUM_CMD)]
            if current_cmd != last_cmd:
                try:
                    r = client.write_coils(ADDR_CMD, current_cmd, device_id=SLAVE_ID)
                    if not r.isError():
                        last_cmd = current_cmd[:]
                        log.info(f"Cmd escrito: {current_cmd}")
                    else:
                        errors += 1
                        log.warning(f"Erro escrita cmd: {r}")
                except Exception:
                    errors += 1
                    log.exception("Excecao escrita cmd")

            # --- 3. Escrever RPM (D100) se mudou ---
            current_rpm = h["spindle-rpm"]
            if abs(current_rpm - last_rpm) > 0.5:
                try:
                    rpm_int = max(0, min(65535, int(current_rpm)))
                    r = client.write_register(ADDR_RPM, rpm_int, device_id=SLAVE_ID)
                    if not r.isError():
                        last_rpm = current_rpm
                    else:
                        errors += 1
                except Exception:
                    errors += 1
                    log.exception("Excecao escrita RPM")

            h["num-errors"] = errors

            # Manter taxa de polling
            elapsed = time.monotonic() - loop_start
            sleep_time = POLL_RATE - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except Exception as e:
        log.exception("Excecao no loop principal")
    finally:
        client.close()
        log.info("=== ams32_hal encerrado ===")
        print("ams32_hal: Encerrado")


if __name__ == "__main__":
    main()
