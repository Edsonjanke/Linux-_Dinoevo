# Setup Painel Touch - Raspberry Pi 3B+ / BTT PITFT70 V2.0

## O que estamos fazendo
Configurar o Pi 3B+ como painel touchscreen remoto do torno CNC.
O Pi roda VNC client fullscreen, espelhando a tela do PC com ProbeBasic.
Todo controle real fica no PC com Mesa 7i92.

## Hardware
- **Raspberry Pi 3B+** (trocou do Pi 4B e da BTT CB1 V2.1 - CB1 nao tem DSI)
- **Tela BTT PITFT70 V2.0** (7", DSI flat cable, touch capacitivo FT5x06)
- **BTT PI4B Adapter V1.0** (carrier board - disponivel mas nao em uso agora)
- **BTT CB1 V2.1** (H616) descartado para display - NAO tem DSI, so HDMI
- Conexao Pi <-> PC via cabo ethernet

## Hardware descartado para este uso
- BTT CB1 V2.1 (H616): sem DSI, nao suporta PITFT70
- FYSETC TFT color (~3"): tela muito pequena para VNC, possivel uso futuro como DRO auxiliar
- FYSETC Mini 12864: versao NeoPixel, backlight nao acende so com 5V

## Onde paramos (2026-04-08)

### FEITO:
- [x] Tentativa com BTT CB1 V2.1 - descartada (sem DSI)
- [x] Pesquisa GitHub BIGTREETECH-TouchScreenHardware e PI4B-Adapter
- [x] Confirmado: CB1 nao tem DSI, PI4B Adapter tem conector mas CB1 nao envia sinal
- [x] Decidido usar Raspberry Pi 3B+ (tem DSI nativo)
- [x] Raspberry Pi Imager instalado no PC Windows
- [x] SD gravado com Raspberry Pi OS Lite (32-bit)
  - Hostname: cyberdino
  - Usuario: evo / senha definida
  - SSH: ativado
  - WiFi: desligado
  - Locale: America/Sao_Paulo, teclado br
- [x] Primeiro boot OK - Pi respondendo: `ping cyberdino.local` (<1ms)
- [x] SSH conectado: `ssh evo@cyberdino.local`
- [x] Sistema atualizado: `sudo apt update && sudo apt upgrade -y`
- [x] VNC client instalado: `sudo apt install -y xorg tigervnc-viewer`
- [x] Tela DSI PITFT70 funcionando (/dev/fb0, driver vc4drmfb)
  - Flat cable no conector DISPLAY (nao CAMERA!)
  - config.txt: display_auto_detect=1, dtoverlay=vc4-kms-v3d
  - Nao precisou de overlay extra
- [x] Touch capacitivo funcionando (FT5x06, event2)
  - Resolucao touch: 800x480 (ABS_X: 0-799, ABS_Y: 0-479)
  - Multitouch ate 10 pontos
  - INPUT_PROP_DIRECT (toque direto)
- [x] Tela mostrando login do Linux (console)

### PROXIMO PASSO: Configurar VNC no PC do LinuxCNC

O PC do torno tem 2 placas de rede:
- eth Mesa: 10.10.10.1 (dedicada Mesa 7i92)
- eth rede local: IP a descobrir (para o Pi)

**No PC do LinuxCNC (via SSH ou presencial):**

1. Descobrir IP da segunda placa de rede:
   ```bash
   ip addr show | grep "inet "
   ```

2. Instalar servidor VNC no PC:
   ```bash
   sudo apt install x11vnc
   ```

3. Testar servidor VNC:
   ```bash
   x11vnc -display :0 -forever -nopw -listen 0.0.0.0
   ```

4. No Pi (via SSH no Pi):
   ```bash
   export DISPLAY=:0
   xtigervncviewer <IP_DO_PC>:0 -fullscreen
   ```

5. Se funcionar, configurar autostart no Pi:
   - Boot direto no VNC client fullscreen
   - Desligar cursor do mouse (touch nao precisa)
   - Reconexao automatica se perder conexao

### DEPOIS DO VNC FUNCIONANDO:
- Configurar autostart do VNC client no boot do Pi
- Esconder cursor do mouse
- Testar touch com ProbeBasic (clicar botoes, navegar)
- Calibrar touch se necessario
- Opcional: adicionar servidor Samba no Pi para G-code
- Opcional: webcam USB para monitoramento

## Credenciais
- **Pi SSH:** `ssh evo@cyberdino.local`
- **User/senha:** evo / (definida no rpi-imager)
- **PC LinuxCNC:** usuario evo, hostname 192 (confirmar)

## Rede
```
PC LinuxCNC (Debian 12)
├── eth0: 10.10.10.1/8 ──── Mesa 7i92 (10.10.10.10)
└── eth1: ???.???.???.??? ── rede "evo" (192.168.0.x)

Pi 3B+ (Raspberry Pi OS Lite 32-bit)
├── eth0: link-local (cabo ethernet direto)
└── wlan0: 192.168.0.103/24 ── WiFi "evo" (senha: evoprint)
```

WiFi habilitado com:
- `sudo raspi-config nonint do_wifi_country BR`
- `sudo rfkill unblock all && sudo systemctl restart NetworkManager`
- `sudo nmcli dev wifi connect "evo" password "evoprint"`
- Conexao salva, reconecta automatico no boot

## Imagem CB1 (gravada no SD da CB1, NAO do Pi)
- CB1_Debian12_minimal_kernel6.6_20241219.img
- Credenciais padrao CB1: biqu/biqu
- Rede CB1: system.cfg na particao BOOT
- HDMI config: armbianEnv.txt → extraargs=video=HDMI-A-1:1024x600-24@60

## Comandos uteis Pi
```bash
# Verificar tela
ls /dev/fb* && cat /proc/fb
# Testar touch
sudo evtest /dev/input/event2
# Ver dispositivos input
sudo evtest
# Config de boot
cat /boot/firmware/config.txt
# Reiniciar
sudo reboot
```

## Usos futuros do Pi 3B+ (alem do painel VNC)
- Servidor Samba para G-code
- Webcam USB + mjpg-streamer (monitoramento)
- DRO dedicado (tela auxiliar FYSETC futura)
- Backup automatico das configs LinuxCNC
