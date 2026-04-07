/*
 * CyberDino - Feed Override Encoder
 * BTT Octopus v1.1 (STM32F446ZET6)
 *
 * Encoder FYSETC EC11 -> STOP_0 (A), STOP_1 (B), STOP_2 (Button)
 * Saida USB CDC Serial: "E:<count> B:<0|1>\n" a cada 20ms
 *
 * Pinout Octopus v1.1 endstops:
 *   STOP_0 = PG6   -> Encoder A
 *   STOP_1 = PG9   -> Encoder B
 *   STOP_2 = PG10  -> Botao push
 */

#include <Arduino.h>

// === PINOS - AJUSTAR SE NECESSARIO ===
#define ENC_A   PG6
#define ENC_B   PG9
#define BTN     PG10

// LED onboard para heartbeat
#define LED     PA13

volatile long encoderCount = 0;
volatile uint8_t lastA = 0;
volatile uint8_t lastB = 0;

void encoderISR() {
    uint8_t a = digitalRead(ENC_A);
    uint8_t b = digitalRead(ENC_B);

    // Decodificacao quadratura simples
    if (a != lastA) {
        if (a == b) {
            encoderCount--;
        } else {
            encoderCount++;
        }
    }
    if (b != lastB) {
        if (a == b) {
            encoderCount++;
        } else {
            encoderCount--;
        }
    }
    lastA = a;
    lastB = b;
}

void setup() {
    Serial.begin(115200);

    pinMode(ENC_A, INPUT_PULLUP);
    pinMode(ENC_B, INPUT_PULLUP);
    pinMode(BTN, INPUT_PULLUP);
    pinMode(LED, OUTPUT);

    lastA = digitalRead(ENC_A);
    lastB = digitalRead(ENC_B);

    attachInterrupt(digitalPinToInterrupt(ENC_A), encoderISR, CHANGE);
    attachInterrupt(digitalPinToInterrupt(ENC_B), encoderISR, CHANGE);
}

unsigned long lastSend = 0;
bool ledState = false;

void loop() {
    unsigned long now = millis();

    if (now - lastSend >= 20) {
        lastSend = now;

        noInterrupts();
        long count = encoderCount;
        interrupts();

        uint8_t btn = !digitalRead(BTN);  // Pull-up: LOW=pressionado

        Serial.print("E:");
        Serial.print(count);
        Serial.print(" B:");
        Serial.println(btn);

        // Heartbeat LED a cada 500ms
        static uint8_t tick = 0;
        if (++tick >= 25) {
            tick = 0;
            ledState = !ledState;
            digitalWrite(LED, ledState);
        }
    }
}
