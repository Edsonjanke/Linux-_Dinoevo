# Programa Ladder AMS32 - Torno Dino Evo

## Instruções para carregar no WPLSoft
1. Abrir WPLSoft (~/wplsoft.sh ou via Wine)
2. Novo projeto → DVP-32ES200R
3. Entrar em modo de edição Ladder ou Instruction List
4. Digitar o programa abaixo
5. Compilar (F4) e transferir para o PLC (F5)
6. Colocar PLC em RUN

## Mapeamento de I/O

### Entradas fisicas (X)
| Entrada | Funcao              | Tipo      |
|---------|---------------------|-----------|
| X0      | Jog X+              | Botao NA  |
| X1      | Jog X-              | Botao NA  |
| X2      | Jog Z+              | Botao NA  |
| X3      | Jog Z-              | Botao NA  |
| X4      | (livre)             |           |
| X5      | Nivel coolant baixo  | Boia NF   |
| X6      | Nivel lube baixo     | Boia NF   |
| X7      | Falha geral / E-stop | NF        |

### Saidas fisicas (Y)
| Saida | Funcao              |
|-------|---------------------|
| Y0    | Bomba coolant       |
| Y1    | Spindle FWD (VFD)   |
| Y2    | Spindle REV (VFD)   |
| Y3    | Bomba lubrificacao  |
| Y4    | Alarme sonoro/visual|

### Reles Modbus - Comandos (LinuxCNC -> PLC)
| Rele | Endereco | Funcao                    |
|------|----------|---------------------------|
| M100 | 2148     | Coolant ON/OFF            |
| M101 | 2149     | Spindle ON                |
| M102 | 2150     | Spindle DIR (0=FWD 1=REV) |
| M103 | 2151     | Lube ciclo ativo          |
| M105 | 2153     | Watchdog (machine-is-on)  |

### Reles Modbus - Status (PLC -> LinuxCNC)
| Rele | Endereco | Funcao                    |
|------|----------|---------------------------|
| M200 | 2248     | Jog X+                    |
| M201 | 2249     | Jog X-                    |
| M202 | 2250     | Jog Z+                    |
| M203 | 2251     | Jog Z-                    |
| M204 | 2252     | (livre)                   |
| M205 | 2253     | Alarme coolant baixo      |
| M206 | 2254     | Alarme lube baixo         |
| M207 | 2255     | Falha geral               |

### Timers e Registradores
| Timer/Reg | Funcao                          |
|-----------|---------------------------------|
| T0        | Debounce jog X+ (100ms)         |
| T1        | Debounce jog X- (100ms)         |
| T2        | Debounce jog Z+ (100ms)         |
| T3        | Debounce jog Z- (100ms)         |
| T10       | Delay alarme coolant (2s)       |
| T11       | Delay alarme lube (2s)          |
| T20       | Lube tempo ON                   |
| T21       | Lube intervalo                  |
| D110      | Lube tempo ON em seg (default 5)|
| D111      | Lube intervalo em seg (def 900) |
| D2000-D2001 | Posicao X (float 32bit, retentivo) |
| D2002-D2003 | Posicao Z (float 32bit, retentivo) |
| D2004     | Flag validacao posicao (0xABCD)   |

---

## Instruction List (digitar no WPLSoft)

```
// ============================================================
// BLOCO 0: Inicializacao (roda 1x no power-on)
// Configura COM1 (RS-232) como Modbus escravo
// e seta defaults dos timers de lubrificacao
// M1002 = pulso de primeiro scan
// ============================================================
LD    M1002
// --- COM1 RS-232: Modbus ASCII escravo, 9600, 7E1 ---
// D1036 = formato COM1: H87 = 9600bps, 7 data, Even parity, 1 stop
MOV   H87       D1036
// M1139=OFF = COM1 em modo escravo Modbus (padrao)
RST   M1139
// Lubrificacao defaults
MOV   K50       D110
MOV   K9000     D111

// ============================================================
// BLOCO 1: COOLANT (M8/M9)
// M100 (Modbus) AND NOT alarme coolant AND NOT falha geral
// => Y0 (bomba coolant)
// ============================================================
LD    M100
ANI   M205
ANI   M207
OUT   Y0

// ============================================================
// BLOCO 2: SPINDLE
// M101=ON + M102=0 => Y1 (FWD)
// M101=ON + M102=1 => Y2 (REV)
// Bloqueado por falha geral (M207)
// ============================================================
// Spindle FWD: M101 AND NOT M102 AND NOT falha
LD    M101
ANI   M102
ANI   M207
OUT   Y1

// Spindle REV: M101 AND M102 AND NOT falha
LD    M101
AND   M102
ANI   M207
OUT   Y2

// ============================================================
// BLOCO 4: JOG MANUAL (botoes fisicos com debounce 100ms)
// X0-X3 => T0-T3 (debounce) => M200-M203 (status Modbus)
// Timer base = 10ms, K10 = 100ms
// ============================================================
// Jog X+
LD    X0
TMR   T0    K10
LD    T0
OUT   M200

// Jog X-
LD    X1
TMR   T1    K10
LD    T1
OUT   M201

// Jog Z+
LD    X2
TMR   T2    K10
LD    T2
OUT   M202

// Jog Z-
LD    X3
TMR   T3    K10
LD    T3
OUT   M203

// ============================================================
// BLOCO 5: ALARME COOLANT BAIXO
// X5 = boia NF (normal=fechado=TRUE, alarme=aberto=FALSE)
// Delay 2s para evitar falso alarme por sloshing
// Timer base = 100ms, K20 = 2s
// ============================================================
LDI   X5
TMR   T10   K20
LD    T10
OUT   M205
// Alarme sonoro se coolant baixo
LD    M205
OUT   Y4

// ============================================================
// BLOCO 6: ALARME LUBE BAIXO
// X6 = boia NF (normal=fechado=TRUE, alarme=aberto=FALSE)
// Delay 2s
// ============================================================
LDI   X6
TMR   T11   K20
LD    T11
OUT   M206

// ============================================================
// BLOCO 7: FALHA GERAL
// X7 = cadeia NF (normal=fechado=TRUE, falha=aberto=FALSE)
// Imediato - sem delay (seguranca)
// Bloqueia spindle, coolant, ativa alarme
// ============================================================
LDI   X7
OUT   M207
// Alarme sonoro tambem em falha geral
LD    M207
OR    M205
OUT   Y4

// ============================================================
// BLOCO 8: LUBRIFICACAO TEMPORIZADA
// M103 = ciclo ativo (LinuxCNC rodando programa)
// D110 = tempo ON em decimos de segundo (K50 = 5s)
// D111 = intervalo em decimos de segundo (K9000 = 900s)
// M10 = flag lube rodando ciclo
// ============================================================
// Timer do intervalo: conta enquanto M103 ativo e lube OFF
LD    M103
ANI   M10
TMR   T21   D111

// Quando intervalo termina, SET lube ON
LD    T21
SET   M10

// Timer da bomba ON: conta enquanto M10 ativo
LD    M10
TMR   T20   D110

// Quando tempo ON termina, RST lube OFF
LD    T20
RST   M10

// Saida bomba lube: M10 AND NOT alarme lube AND NOT falha
LD    M10
ANI   M206
ANI   M207
OUT   Y3

// ============================================================
// FIM DO PROGRAMA
// ============================================================
END
```

## Notas
- Timers T0-T3: base 10ms (K10 = 100ms debounce)
- Timers T10-T11: base 100ms (K20 = 2s delay alarme)
- Timers T20-T21: usam valor dos registradores D110/D111
- D110 default K50 = 5.0s (bomba lube ON)
- D111 default K9000 = 900s = 15min (intervalo entre ciclos)
- M1002 = flag especial Delta: pulso no primeiro scan (inicializacao)
- Alarme sonoro Y4 ativa por coolant baixo OU falha geral
- E-Stop DEVE ser hardwired, M207 é alarme adicional via software
