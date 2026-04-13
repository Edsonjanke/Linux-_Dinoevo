# Relatório Integração AMS32 + LinuxCNC - Torno Dino Evo
**Data:** 2026-04-13
**Status:** Comunicação OK, falta carregar programa Ladder no PLC

---

## 1. Resumo

Configuração do CLP AMS32 (clone Delta DVP-32ES200R) como módulo de I/O auxiliar para o torno CNC Dino Evo rodando LinuxCNC com ProbeBasic. Comunicação via Modbus ASCII sobre RS-485 (USB-Serial CH340).

### O que foi feito
- Conexão serial USB identificada e fixada com udev (`/dev/ttyAMS32`)
- Comunicação Modbus ASCII testada e confirmada (leitura/escrita coils e registros)
- Tentativa de mudar para Modbus RTU falhou (mb2hal só suporta RTU, AMS32 não persiste config RTU)
- Componente HAL custom em Python (`ams32_hal.py`) criado para bridge Modbus ASCII ↔ HAL
- Componente testado e funcionando dentro do LinuxCNC (zero erros, connected=TRUE)
- Sinal coolant-flood conectado ao PLC (M100 escrito com sucesso via Modbus)
- Programa Ladder completo criado para o AMS32

### O que falta
- **Carregar programa Ladder no AMS32 via WPLSoft** (Wine no Windows ou Linux)
- Conectar demais sinais HAL (spindle, alarmes, lube, etc)
- Testar saídas físicas (Y0-Y4) com o Ladder rodando

---

## 2. Hardware

| Componente | Detalhe |
|---|---|
| CLP | AMS32 (compatível Delta DVP-32ES200R), 16 entradas + 16 saídas |
| Motion Controller | Mesa 7I92 (Ethernet FPGA) |
| Interface CNC | LinuxCNC 2.9 + ProbeBasic (probe_basic_lathe) |
| SO | Debian Linux 6.1.0-41-rt-amd64 |
| Cabo serial | USB-Serial CH340 na USB traseira fixa |
| Comunicação | Modbus ASCII, 9600 baud, 7E1, Slave ID 1 |

---

## 3. Conexão Serial

### Porta USB fixada via udev
```
/dev/ttyAMS32 -> ttyUSB0 (symlink fixo)
```

**Regra udev criada:**
```
/etc/udev/rules.d/99-ams32.rules
SUBSYSTEM=="tty", ENV{ID_PATH}=="pci-0000:00:1d.0-usb-0:1.5:1.0", SYMLINK+="ttyAMS32", MODE="0666"
```

**Porta física:** USB traseira, path PCI `pci-0000:00:1d.0-usb-0:1.5:1.0`
**Chip:** CH340 (ch341-uart), ID `usb-1a86_USB_Serial-if00-port0`
**Usuário evo:** já no grupo `dialout`

### Para recriar a regra udev (se necessário)
```bash
echo 'SUBSYSTEM=="tty", ENV{ID_PATH}=="pci-0000:00:1d.0-usb-0:1.5:1.0", SYMLINK+="ttyAMS32", MODE="0666"' | sudo tee /etc/udev/rules.d/99-ams32.rules
sudo udevadm control --reload-rules
sudo udevadm trigger --action=add /dev/ttyUSB0
```

---

## 4. Comunicação Modbus - Testes

### Protocolo confirmado
| Parâmetro | Valor |
|---|---|
| Protocolo | Modbus **ASCII** (não RTU!) |
| Baudrate | 9600 bps |
| Data bits | 7 |
| Paridade | Even |
| Stop bits | 1 |
| Slave ID | 1 |
| Framer pymodbus | `FramerType.ASCII` |

### Testes realizados (todos OK)
| Teste | Endereço Modbus | FC | Resultado |
|---|---|---|---|
| Entradas X0-X7 | 1024 | FC02 | Leitura OK |
| Saídas Y0-Y7 | 1280 | FC01 | Leitura OK |
| Relés M200-M207 | 2248 | FC01 | Leitura OK |
| Registro D100 | 4196 | FC03 | Leitura OK (valor 0) |
| Escrita M100 ON | 2148 | FC05 | Escrita OK + leitura confirmada |
| Escrita M100 OFF | 2148 | FC05 | Escrita OK + leitura confirmada |

### Teste pymodbus (script para verificar comunicação)
```python
from pymodbus.client import ModbusSerialClient
from pymodbus.framer import FramerType

client = ModbusSerialClient(
    port="/dev/ttyAMS32",
    baudrate=9600, bytesize=7, parity="E", stopbits=1,
    framer=FramerType.ASCII, timeout=2
)
client.connect()
r = client.read_coils(2148, count=1, device_id=1)
print(f"M100 = {r.bits[0]}")
client.close()
```

---

## 5. Problema mb2hal (RTU vs ASCII)

### mb2hal NÃO suporta Modbus ASCII
O componente `mb2hal` do LinuxCNC só suporta Modbus RTU e TCP. O AMS32 está configurado como ASCII.

### Tentativa de mudar AMS32 para RTU
- Tentamos escrever M1143=ON (flag RTU COM2) e D1120=0x87 (8E1) via Modbus ASCII
- A escrita foi aceita, mas os valores são **voláteis** — voltam ao padrão ASCII após power cycle
- M1143 é um flag especial que só pode ser persistido via programa Ladder interno
- **Conclusão:** não é possível mudar para RTU sem programa Ladder

### Solução adotada: componente HAL custom em Python
Criado `ams32_hal.py` que usa pymodbus com `FramerType.ASCII` diretamente, substituindo o mb2hal.

---

## 6. Arquivos Criados

### ams32_hal.py — Componente HAL (substitui mb2hal)
**Localização:** `/home/evo/linuxcnc/configs/Dino_Evo/ams32_hal.py`

Componente HAL em Python que faz bridge Modbus ASCII ↔ HAL pins.

**Pins criados:**
| Pin | Tipo | Dir | Função |
|---|---|---|---|
| ams32.cmd.00 | bit | IN | M100 - Coolant ON/OFF |
| ams32.cmd.01 | bit | IN | M101 - Spindle ON |
| ams32.cmd.02 | bit | IN | M102 - Spindle DIR |
| ams32.cmd.03 | bit | IN | M103 - Lube ciclo |
| ams32.cmd.04 | bit | IN | M104 - Reserva |
| ams32.cmd.05 | bit | IN | M105 - Watchdog |
| ams32.cmd.06 | bit | IN | M106 - Reserva |
| ams32.cmd.07 | bit | IN | M107 - Reserva |
| ams32.status.00-15 | bit | OUT | M200-M215 status do PLC |
| ams32.spindle-rpm | float | IN | RPM para D100 |
| ams32.connected | bit | OUT | Status da conexão |
| ams32.num-errors | s32 | OUT | Contador de erros |

**Características:**
- Poll rate: 20Hz (50ms)
- Só escreve comandos quando valor muda (economia de banda serial)
- Reconexão automática em caso de perda de comunicação
- Log em `/tmp/ams32_hal.log`

### ams32_mb2hal.ini — Config mb2hal (NÃO USAR)
**Status:** Arquivo criado mas **não funciona** porque mb2hal não suporta ASCII.
Mantido como referência dos endereços Modbus.

### ams32_torno.hal — Conexões HAL (não carregado)
**Status:** Arquivo criado mas **não é usado** atualmente.
As conexões HAL estão no `probe_basic_postgui_fix.hal`.

### ams32_ladder.md — Programa Ladder completo
**Localização:** `/home/evo/linuxcnc/configs/Dino_Evo/ams32_ladder.md`
**Status:** PRECISA SER CARREGADO NO PLC VIA WPLSOFT

---

## 7. Configuração LinuxCNC Atual

### Dino_Evo.ini — Seção HAL
```ini
[HAL]
HALFILE = Dino_Evo.hal
HALFILE = custom.hal
HALUI = halui
POSTGUI_HALFILE = probe_basic_postgui_fix.hal
```

**IMPORTANTE:** ProbeBasic/QtPyVCP só carrega **um único** POSTGUI_HALFILE. Não usar múltiplos. Tudo deve ir no `probe_basic_postgui_fix.hal`.

### probe_basic_postgui_fix.hal — Linhas adicionadas
```hal
# AMS32 - PLC Modbus ASCII via Python (coolant)
loadusr -Wn ams32 python3 ams32_hal.py

# Coolant M8/M9 -> PLC M100 -> Y0 (bomba)
net coolant-flood    => ams32.cmd.00
```

### Sinais HAL existentes (para futuras conexões)
| Sinal existente | Fonte | Para conectar ao AMS32 |
|---|---|---|
| `coolant-flood` | iocontrol.0.coolant-flood | ams32.cmd.00 ✅ FEITO |
| `spindle-enable` | spindle.0.on | ams32.cmd.01 (futuro) |
| `spindle-ccw` | spindle.0.reverse | ams32.cmd.02 (futuro) |
| `machine-is-on` | halui.machine.is-on | ams32.cmd.05 (futuro) |
| `spindle-at-speed` | near.spindle.out | Substituir por ams32.status.04 (futuro) |

### Conflitos a resolver ao conectar mais sinais
1. **spindle-at-speed:** atualmente vem do `near.spindle` (Dino_Evo.hal:207). Para usar o PLC (M204), precisa `unlinkp spindle.0.at-speed` antes de conectar ams32.status.04
2. **coolant-flood:** já conectado ✅
3. **spindle-enable/ccw:** sinais existentes, basta adicionar `net spindle-enable => ams32.cmd.01`

---

## 8. Programa Ladder AMS32

### Resumo dos blocos
| Bloco | Função | Entrada | Saída |
|---|---|---|---|
| 0 | Inicialização | M1002 (1º scan) | D110=50, D111=9000 |
| 1 | Coolant | M100 AND NOT M205 AND NOT M207 | Y0 |
| 2 | Spindle FWD | M101 AND NOT M102 AND NOT M207 | Y1 |
| 2 | Spindle REV | M101 AND M102 AND NOT M207 | Y2 |
| 3 | At-speed | X4 | M204 |
| 4 | Jog X+/X-/Z+/Z- | X0-X3 (debounce 100ms) | M200-M203 |
| 5 | Alarme coolant | NOT X5 (delay 2s) | M205, Y4 |
| 6 | Alarme lube | NOT X6 (delay 2s) | M206 |
| 7 | Falha geral | NOT X7 | M207, Y4 |
| 8 | Lube temporizada | M103 + timers D110/D111 | Y3 |

### Instruction List completo
Ver arquivo `ams32_ladder.md` para o programa completo pronto para digitar no WPLSoft.

### Para carregar no AMS32
1. Instalar WPLSoft (Windows ou Wine no Linux)
2. Novo projeto → PLC tipo **DVP-32ES200R**
3. Comunicação: COM port do cabo USB-Serial, 9600 8E1 (WPLSoft usa protocolo próprio)
4. Digitar Instruction List ou desenhar Ladder
5. Compilar (F4) → Transferir (F5) → PLC em RUN
6. Testar: M8 no LinuxCNC → LED Y0 acende

---

## 9. Próximos Passos

### Prioridade 1: Carregar Ladder no PLC
- [ ] Instalar WPLSoft (Wine no Linux ou Windows)
- [ ] Digitar programa Ladder do `ams32_ladder.md`
- [ ] Transferir para o AMS32
- [ ] Testar M8 → Y0 acende
- [ ] Testar M3 → Y1 acende
- [ ] Testar alarmes (X5, X6, X7)

### Prioridade 2: Conectar demais sinais HAL
- [ ] Spindle: `net spindle-enable => ams32.cmd.01` + `net spindle-ccw => ams32.cmd.02`
- [ ] At-speed: `unlinkp spindle.0.at-speed` + `net spindle-at-speed-plc ams32.status.04 => spindle.0.at-speed`
- [ ] Watchdog: `net machine-is-on => ams32.cmd.05`
- [ ] Alarmes: criar nets para ams32.status.05/06/07
- [ ] Lube: `net lube-on-cmd iocontrol.0.lube => ams32.cmd.03`
- [ ] Spindle RPM: `net spindle-vel-cmd-rpm-abs => ams32.spindle-rpm`

### Prioridade 3: Extras
- [ ] Salvar posição (ams32_pos_save.py)
- [ ] Jog via PLC (M200-M203 → halui.jog)
- [ ] Monitor visual no terminal (monitor_ams32.py)
- [ ] Mudar protocolo para RTU via Ladder (M1143=ON no programa)

---

## 10. Troubleshooting

### LinuxCNC não carrega ams32_hal.py
- Verificar se está no `probe_basic_postgui_fix.hal` (não em POSTGUI_HALFILE separado)
- ProbeBasic só carrega **um** POSTGUI_HALFILE
- Verificar log: `cat /tmp/ams32_hal.log`

### ams32.connected = FALSE
- Verificar cabo USB: `ls -la /dev/ttyAMS32`
- Se sumiu, recriar udev rule e replug USB
- Verificar se outro processo trava a porta: `fuser /dev/ttyUSB0`

### num-errors aumentando
- Verificar log: `cat /tmp/ams32_hal.log`
- Pode ser timeout de comunicação (cabo solto, PLC desligado)
- O componente reconecta automaticamente

### M8 não funciona (coolant-flood = FALSE)
- Máquina precisa estar: estop reset + machine ON + homed + modo MDI
- Verificar: `halcmd show pin iocontrol.0.coolant-flood`
- Teste manual: `halcmd setp halui.flood.on 1` (depois `halcmd setp halui.flood.on 0`)

### Y0 não acende mesmo com M100 = TRUE
- **PLC precisa de programa Ladder carregado!**
- M100 é relé interno — sem Ladder, não aciona Y0
- Carregar programa do `ams32_ladder.md` via WPLSoft

### Porta serial travada
- Só um processo pode usar `/dev/ttyAMS32` por vez
- Se ams32_hal.py está rodando, não dá para testar com pymodbus
- Para testar: fechar LinuxCNC primeiro
