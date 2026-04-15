#!/usr/bin/env python3
"""
pos_restore.py - Restaura posicao dos eixos salva no PLC AMS32
Roda como loadusr apos ams32_hal.py, aguarda pos-valid e aplica
a posicao salva via G10 L20 (seta coordenada sem mover).

Uso no HAL (postgui):
  loadusr -W python3 pos_restore.py
"""

import hal
import time
import sys
import linuxcnc

TIMEOUT = 10  # segundos max para esperar ams32 ficar pronto


def main():
    # Esperar o componente ams32 existir e ter pos-valid
    print("pos_restore: Aguardando ams32...")
    h = hal.component("pos_restore")
    h.newpin("done", hal.HAL_BIT, hal.HAL_OUT)
    h.ready()

    start = time.monotonic()
    while time.monotonic() - start < TIMEOUT:
        try:
            valid = hal.get_value("ams32.pos-valid")
            if valid:
                break
        except Exception:
            pass
        time.sleep(0.5)
    else:
        print("pos_restore: Timeout ou sem posicao salva - homing normal necessario")
        h["done"] = True
        # Manter componente vivo brevemente para LinuxCNC nao reclamar
        time.sleep(2)
        return

    # Ler posicoes salvas
    saved_x = hal.get_value("ams32.pos-saved-x")
    saved_z = hal.get_value("ams32.pos-saved-z")
    print(f"pos_restore: Posicao salva: X={saved_x:.4f} Z={saved_z:.4f}")

    # Esperar LinuxCNC estar pronto (ESTOP off, machine on)
    s = linuxcnc.stat()
    c = linuxcnc.command()

    for _ in range(TIMEOUT * 2):
        s.poll()
        if s.task_state == linuxcnc.STATE_ON:
            break
        time.sleep(0.5)
    else:
        print("pos_restore: LinuxCNC nao ficou ON a tempo - homing normal necessario")
        h["done"] = True
        time.sleep(2)
        return

    # Fazer home dos joints (immediate home, so seta posicao 0)
    try:
        c.mode(linuxcnc.MODE_MANUAL)
        c.wait_complete()
        c.home(0)  # joint 0 (X)
        c.home(1)  # joint 1 (Z)
        time.sleep(1)

        # Verificar se homed
        s.poll()
        if not (s.homed[0] and s.homed[1]):
            print("pos_restore: Homing falhou - aguardando...")
            time.sleep(2)
            s.poll()

        if s.homed[0] and s.homed[1]:
            # Usar G10 L20 P1 para setar a posicao atual no sistema de coordenadas
            # G10 L20 = seta coordenada relativa a posicao atual
            c.mode(linuxcnc.MODE_MDI)
            c.wait_complete()
            c.mdi(f"G10 L20 P1 X{saved_x:.4f} Z{saved_z:.4f}")
            c.wait_complete(5)
            print(f"pos_restore: Posicao restaurada! X={saved_x:.4f} Z={saved_z:.4f}")
            c.mode(linuxcnc.MODE_MANUAL)
            c.wait_complete()
        else:
            print("pos_restore: Joints nao fizeram home - restauracao cancelada")

    except Exception as e:
        print(f"pos_restore: Erro restaurando posicao: {e}")

    h["done"] = True
    time.sleep(2)


if __name__ == "__main__":
    main()
