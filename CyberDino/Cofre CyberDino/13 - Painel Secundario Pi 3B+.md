# Painel Secundario - Raspberry Pi 3B+

## Hardware
| Componente | Detalhe |
|------------|---------|
| **Pi** | Raspberry Pi 3B+ |
| **IP WiFi** | 192.168.0.103 (hostname: cyberdino) |
| **Tela** | BTT PITFT70, DSI, **800x480** (nao 1024x600!) |
| **Touch** | Capacitivo USB |
| **PC LinuxCNC** | 192.168.0.113 |

## Arquitetura
```
PC (192.168.0.113):
  Xvfb :1 (800x480) -> secondary_panel.py -> x11vnc porta 5901

Pi (192.168.0.103):
  xtigervncviewer 192.168.0.113::5901 -FullScreen
```
- Separado do ProbeBasic principal (display :0 do PC)
- Pi e terminal burro (VNC client), processamento no PC

## Painel (secondary_panel.py)
- Python3 + PyQt5 + modulo linuxcnc (stat/command)
- DRO posicao X/Z (com offsets G5x + tool)
- Spindle Override: slider + botoes touch (-10/-1/100%/+1/+10)
- Tema escuro com cobre (matching ProbeBasic)
- Reconecta automaticamente se LinuxCNC nao estiver rodando

## Arquivos no PC
| Arquivo | Funcao |
|---------|--------|
| `secondary_panel.py` | Painel PyQt5 |
| `start_panel.sh` | Launcher (Xvfb + painel + x11vnc) |
| `cyberdino-panel.service` | Systemd service autostart |

## Autostart
**PC:** `sudo systemctl enable cyberdino-panel`
**Pi:** `/usr/local/bin/start-vnc.sh` (xinit + matchbox-window-manager + vncviewer)

## Status
Funcionando desde 2026-04-09. Autostart configurado (pendente validar apos reinicio).
