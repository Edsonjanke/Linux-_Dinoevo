#!/bin/bash
# CyberDino - Lanca painel secundario no display virtual :1
# Uso: ./start_panel.sh
# Para parar: ./start_panel.sh stop

DISPLAY_NUM=":1"
RESOLUTION="800x480x24"
VNC_PORT=5901
PANEL_SCRIPT="$(dirname "$0")/secondary_panel.py"

stop_panel() {
    echo "Parando painel..."
    pkill -f "secondary_panel.py" 2>/dev/null
    pkill -f "x11vnc.*display ${DISPLAY_NUM}" 2>/dev/null
    pkill -f "Xvfb ${DISPLAY_NUM}" 2>/dev/null
    echo "Painel parado."
}

if [ "$1" = "stop" ]; then
    stop_panel
    exit 0
fi

# Para processos anteriores se existirem
stop_panel

echo "=== CyberDino Painel Secundario ==="
echo "Display: ${DISPLAY_NUM} (${RESOLUTION})"
echo "VNC porta: ${VNC_PORT}"

# 1. Inicia Xvfb (display virtual)
Xvfb ${DISPLAY_NUM} -screen 0 ${RESOLUTION} &
XVFB_PID=$!
sleep 1

if ! kill -0 $XVFB_PID 2>/dev/null; then
    echo "ERRO: Xvfb falhou ao iniciar"
    exit 1
fi
echo "Xvfb rodando (PID $XVFB_PID)"

# 2. Inicia o painel no display virtual
DISPLAY=${DISPLAY_NUM} python3 "$PANEL_SCRIPT" &
PANEL_PID=$!
sleep 2

if ! kill -0 $PANEL_PID 2>/dev/null; then
    echo "ERRO: Painel falhou ao iniciar"
    kill $XVFB_PID
    exit 1
fi
echo "Painel rodando (PID $PANEL_PID)"

# 3. Inicia x11vnc no display virtual
x11vnc -display ${DISPLAY_NUM} -forever -nopw -listen 0.0.0.0 -rfbport ${VNC_PORT} -noxdamage -cursor none &
VNC_PID=$!
sleep 1

if ! kill -0 $VNC_PID 2>/dev/null; then
    echo "ERRO: x11vnc falhou ao iniciar"
    kill $PANEL_PID $XVFB_PID
    exit 1
fi
echo "x11vnc rodando (PID $VNC_PID) na porta ${VNC_PORT}"

IP=$(hostname -I | awk '{print $1}')
echo ""
echo "=== PRONTO ==="
echo "Da Pi, conecte com:"
echo "  xtigervncviewer ${IP}::${VNC_PORT} -FullScreen"
echo ""
echo "Para parar: $(basename "$0") stop"
echo "Ou Ctrl+C"

# Espera qualquer processo filho morrer
trap "stop_panel; exit 0" INT TERM
wait
