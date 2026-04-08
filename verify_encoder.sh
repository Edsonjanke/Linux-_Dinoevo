#!/bin/bash
# ============================================================
# VERIFICACAO ENCODER SPINDLE - Apos religar no DB15
# ============================================================
# Roda com LinuxCNC aberto. Verifica se encoder.00 esta lendo.
# Uso: bash verify_encoder.sh
# ============================================================

echo "============================================"
echo "  VERIFICACAO ENCODER SPINDLE"
echo "============================================"
echo ""

# Verificar halcmd
if ! halcmd getp hm2_7i92.0.encoder.00.rawcounts >/dev/null 2>&1; then
    echo "ERRO: LinuxCNC nao esta rodando."
    exit 1
fi

echo "[OK] LinuxCNC detectado."
echo ""

# Estado atual
echo "=== ESTADO ATUAL ==="
INPUT_A=$(halcmd getp hm2_7i92.0.encoder.00.input-a 2>/dev/null)
INPUT_B=$(halcmd getp hm2_7i92.0.encoder.00.input-b 2>/dev/null)
RAW=$(halcmd getp hm2_7i92.0.encoder.00.rawcounts 2>/dev/null)
VEL=$(halcmd getp hm2_7i92.0.encoder.00.velocity 2>/dev/null)
RPM=$(halcmd getp hm2_7i92.0.encoder.00.velocity-rpm 2>/dev/null)

echo "  input-a     = $INPUT_A"
echo "  input-b     = $INPUT_B"
echo "  rawcounts   = $RAW"
echo "  velocity    = $VEL"
echo "  velocity-rpm= $RPM"
echo ""

# Verificar se input-a e input-b nao estao presos em TRUE
if [ "$INPUT_A" = "TRUE" ] && [ "$INPUT_B" = "TRUE" ]; then
    echo ">>> PROBLEMA: input-a e input-b ambos TRUE (presos) <<<"
    echo "    O encoder provavelmente NAO esta conectado nos pinos corretos."
    echo "    Verificar fiacao: A no pino 4, B no pino 3 do DB15."
    echo ""
fi

echo "=== TESTE DINAMICO ==="
echo "Gire o spindle NA MAO devagar..."
echo ""
read -p "Pressione ENTER quando estiver girando..."

echo ""
echo "Monitorando rawcounts por 5 segundos..."

RAW_START=$(halcmd getp hm2_7i92.0.encoder.00.rawcounts 2>/dev/null)
CHANGES=0

for i in $(seq 1 25); do
    sleep 0.2
    RAW_NOW=$(halcmd getp hm2_7i92.0.encoder.00.rawcounts 2>/dev/null)
    VEL_NOW=$(halcmd getp hm2_7i92.0.encoder.00.velocity 2>/dev/null)
    RPM_NOW=$(halcmd getp hm2_7i92.0.encoder.00.velocity-rpm 2>/dev/null)

    if [ "$RAW_NOW" != "$RAW_START" ]; then
        CHANGES=$((CHANGES + 1))
    fi

    printf "\r  rawcounts=%s  vel=%s  rpm=%s  " "$RAW_NOW" "$VEL_NOW" "$RPM_NOW"
done

RAW_END=$(halcmd getp hm2_7i92.0.encoder.00.rawcounts 2>/dev/null)
DIFF=$((RAW_END - RAW_START))

echo ""
echo ""
echo "=== RESULTADO ==="
echo "  rawcounts inicio: $RAW_START"
echo "  rawcounts fim:    $RAW_END"
echo "  diferenca:        $DIFF"
echo "  amostras mudaram: $CHANGES de 25"
echo ""

if [ "$DIFF" -ne 0 ]; then
    echo ">>> ENCODER FUNCIONANDO! <<<"
    echo ""
    if [ "$DIFF" -gt 0 ]; then
        echo "  Direcao: POSITIVA (CW conta pra cima)"
    else
        echo "  Direcao: NEGATIVA (CW conta pra baixo)"
        echo "  Se o spindle girou CW e contou negativo, trocar A/B"
        echo "  ou mudar ENCODER_SCALE para -400 no Dino_Evo.ini"
    fi
    echo ""
    echo "  Pulsos em 5s: $DIFF"
    echo "  Scale configurado: $(halcmd getp hm2_7i92.0.encoder.00.scale 2>/dev/null)"
    echo ""
    echo "  Proximo: testar com M3 S500 e verificar RPM no display."
else
    echo ">>> ENCODER NAO ESTA LENDO! <<<"
    echo ""
    echo "  Verificar:"
    echo "  1. Fio A esta no pino 4 do DB15?"
    echo "  2. Fio B esta no pino 3 do DB15?"
    echo "  3. +5V esta no pino 15 do DB15?"
    echo "  4. GND esta no pino 14 do DB15?"
    echo "  5. Encoder esta acoplado mecanicamente ao spindle?"
    echo "  6. Medir tensao nos fios A/B com multimetro ao girar"
fi
