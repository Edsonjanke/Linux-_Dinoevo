#!/bin/bash
# ============================================================
# MONITOR GPIO AO VIVO - Para testar religacao do encoder
# ============================================================
# Mostra o estado de todos os GPIOs atualizando a cada 0.3s
# Quando voce ligar um fio no DB15 e tocar GND, o GPIO muda.
# Ctrl+C para sair.
#
# Uso: bash test_gpio_live.sh
# Ou para monitorar GPIOs especificos:
#      bash test_gpio_live.sh 025 028 029 032 033
# ============================================================

INTERVAL=0.3

# Se recebeu argumentos, monitorar so esses GPIOs
if [ $# -gt 0 ]; then
    GPIOS="$@"
else
    # Monitorar GPIOs livres do P1 (017-033)
    GPIOS="017 018 019 020 021 022 023 024 025 026 027 028 029 030 031 032 033"
fi

echo "============================================"
echo "  MONITOR GPIO AO VIVO"
echo "  Ctrl+C para sair"
echo "============================================"
echo ""
echo "Monitorando: $GPIOS"
echo ""

# Capturar estado inicial
declare -A PREV
for g in $GPIOS; do
    pin="hm2_7i92.0.gpio.${g}.in"
    val=$(halcmd getp "$pin" 2>/dev/null || echo "N/A")
    PREV[$g]="$val"
done

# Tambem monitorar encoder hardware
ENC_PREV=$(halcmd getp hm2_7i92.0.encoder.00.rawcounts 2>/dev/null || echo "0")

while true; do
    OUTPUT=""
    CHANGES=""

    for g in $GPIOS; do
        pin="hm2_7i92.0.gpio.${g}.in"
        val=$(halcmd getp "$pin" 2>/dev/null || echo "N/A")

        if [ "$val" != "${PREV[$g]}" ]; then
            CHANGES="${CHANGES} gpio.${g}:${PREV[$g]}->${val}"
            PREV[$g]="$val"
            OUTPUT="${OUTPUT} ${g}=[${val}]*"
        else
            OUTPUT="${OUTPUT} ${g}=${val}"
        fi
    done

    # Encoder hardware
    ENC_NOW=$(halcmd getp hm2_7i92.0.encoder.00.rawcounts 2>/dev/null || echo "0")
    if [ "$ENC_NOW" != "$ENC_PREV" ]; then
        ENC_CHANGES=" enc.rawcounts:${ENC_PREV}->${ENC_NOW}"
        ENC_PREV="$ENC_NOW"
    else
        ENC_CHANGES=""
    fi

    # Mostrar linha
    printf "\r%s enc=%s%s" "$OUTPUT" "$ENC_NOW" "$ENC_CHANGES"

    if [ -n "$CHANGES" ]; then
        echo ""
        echo "  >>> MUDOU:$CHANGES"
    fi

    sleep $INTERVAL
done
