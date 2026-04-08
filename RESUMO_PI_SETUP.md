# Setup Painel Touch - Raspberry Pi 4B + BTT PITFT70

## O que estamos fazendo
Configurar a Pi 4B como painel touchscreen remoto do torno CNC.
A Pi roda VNC client fullscreen, espelhando a tela do PC com ProbeBasic.
Todo controle real fica no PC com Mesa 7i92.

## Hardware
- Raspberry Pi 4B
- Tela BTT PITFT70 (7", 1024x600, DSI flat cable, touch capacitivo)
- Tela DSI já conectada na Pi
- Conexão Pi <-> PC via cabo ethernet (sem WiFi)

## Onde paramos (2026-04-08)

### FEITO:
- [x] rpi-imager instalado no PC (`sudo dpkg -i imager_latest_amd64.deb`)
- [x] Tela DSI conectada na Pi

### PROXIMO PASSO: Gravar SD card
```bash
rpi-imager
```
Configurações:
- Dispositivo: Raspberry Pi 4
- SO: Raspberry Pi OS Lite (64-bit)
- Hostname: cyberdino
- Usuario: evo / (definir senha)
- SSH: ativado
- WiFi: desligado (usa cabo ethernet)

### DEPOIS DE GRAVAR:
1. Colocar SD na Pi, conectar ethernet, ligar na energia
2. Esperar boot, tela DSI deve acender
3. Achar o IP da Pi: `ping cyberdino.local` ou verificar no roteador
4. SSH na Pi: `ssh evo@cyberdino.local`
5. Na Pi via SSH:
   ```bash
   sudo apt update
   sudo apt install xorg tigervnc-viewer
   ```
6. No PC (LinuxCNC):
   ```bash
   sudo apt install x11vnc
   x11vnc -display :0 -forever -nopw -listen 0.0.0.0
   ```
7. Na Pi via SSH:
   ```bash
   xtigervncviewer <IP_DO_PC>:0 -fullscreen
   ```
8. Se funcionar, configurar autostart na Pi (boot direto no VNC)
9. Desligar cursor do mouse (touch não precisa)

## Display FYSETC Mini 12864
Descartado - versão NeoPixel, backlight não acende só com 5V (precisa sinal WS2812).
