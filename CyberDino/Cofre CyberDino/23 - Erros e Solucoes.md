# Erros e Solucoes

## Placa Chinesa Mesa 7i92

### Pinos P2 (DB25) nao funcionam como entrada
**Problema:** Optoacopladores no P2 sao unidirecionais - so saida.
**Solucao:** Usar DB15 (P1) ou pontos soldados para entradas.

### Conectores mortos na placa
**Problema:** Pontos soldados para GPIOs podem NAO estar conectados ao FPGA.
**Solucao:** Sempre testar GPIO com `halcmd setp/getp` antes de confiar.

## ProbeBasic / QtPyVCP

### Crash ao importar linuxcnc
**Problema:** ProbeBasic crashava ao importar modulo linuxcnc fora do ambiente CNC.
**Solucao:** Import lazy do linuxcnc + deteccao de processos ativos.

### POSTGUI_HALFILE so carrega 1
**Problema:** QtPyVCP usa `ini.find()` (retorna primeiro), nao `findall()`.
**Solucao:** Colocar tudo em um unico `probe_basic_postgui_fix.hal`.

### Pins HAL usam hifen, nao underscore
**Problema:** Widget name `mpg_indicator` no Qt gera pin `mpg-indicator` no HAL.
**Solucao:** Sempre usar hifen nos nomes de sinal HAL: `qtpyvcp.mpg-indicator.in`

### HalButton permite click mesmo com pin controlado
**Problema:** HalButton padrao aceita click do mouse, sobreescrevendo o estado do pin.
**Solucao:** Criar widget custom `ReadOnlyAction` que bloqueia mouse.

## CFW-07

### Motor nao gira mesmo com referencia
**Verificar:**
1. DI1 (borne 09) esta em 0V? (Habilita Geral)
2. DI4 (borne 12) esta em 0V? (Habilita Rampa)
3. P220 = 1? (modo REMOTO)
4. Display mostra "rdy"?
5. AI1 (borne 02) tem tensao proporcional?

### Display mostra erro
Ver [[20 - Parametros CFW-07#Mensagens de Erro]]
