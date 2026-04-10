# PLC AMS32ES2

## Status: PENDENTE - Aguardando adaptador USB-RS485

## Especificacoes
- 16 DI / 16 DO
- RS-485 Modbus RTU (via mb2hal no LinuxCNC)

## Comunicacao
| Porta | Tipo | Protocolo | Uso |
|-------|------|-----------|-----|
| COM1 (Mini-DIN) | RS-232 | Proprietario FX | **NAO suporta Modbus** |
| COM2/COM3 (terminais D+/D-/SG) | RS-485 | Modbus RTU | **Caminho correto** |

## Funcoes Planejadas
- Encoder FYSETC (EC11) -> PLC X0/X1 -> feed override
- Botoes jog X+/X-/Z+/Z- via PLC
- Display FYSETC Mini 12864 (SPI) -> feed override % (a definir driver)

## Hardware Descartado
- BTT Octopus (impressora 3D) - nao adequado
