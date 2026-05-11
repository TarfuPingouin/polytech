#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7735.h>
#include <SPI.h>
#include "Adafruit_LEDBackpack.h"

#define TempPin A6
#define TFT_CS 10
#define TFT_DC 9
#define TFT_RST 8
#define PNPPin 7

Adafruit_MPU6050 mpu;
Adafruit_ST7735 tft = Adafruit_ST7735(TFT_CS, TFT_DC, TFT_RST);
Adafruit_8x8matrix matrix = Adafruit_8x8matrix();

//Déclaration de variables globales
int brightness = 50;  // 0 → max, 255 → OFF
bool send_data = true;
int periode = 20;
const char* card_ver = "Card V2.1";
const char* soft_ver = "Soft V1.0";

#define POLYTECH_BLUE 0x04DB  // #069AD8 en RGB565
unsigned long lastTftUpdate = 0;
const unsigned long TFT_PERIOD = 50;  // 50 ms = 20 Hz affichage
unsigned long lastSerialSend = 0;
int db_entry = 0;

void drawBoldText(int x, int y, const char* txt, uint16_t color, uint16_t bg);
void drawTftStatic();
void drawValue(int x, int y, float value, uint8_t decimals);
void drawIntValue(int x, int y, int value);
void updateTftValues(float accX, float accY, float accZ,
                     float rotX, float rotY, float rotZ,
                     float temp);

/////////////////////////////////////
//
//   SETUP!
//
/////////////////////////////////////

void setup(void) {


  //Initialisation du capteur MPU6050
  Serial.begin(115200);

  if (!mpu.begin()) {
    Serial.println("Failed to find MPU6050 chip");
    while (1) {
      delay(10);
    }
  }
  Serial.println("MPU6050 Found!");

  //Définition des plages
  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_44_HZ);


  //Gestion PNP
  pinMode(PNPPin, OUTPUT);
  digitalWrite(PNPPin, HIGH);

  //Initialisation écran
  tft.initR(INITR_BLACKTAB);
  tft.setRotation(2);  // Paysage : 160 x 128 environ
  drawTftStatic();


  //Matrice LED
  matrix.begin(0x72);
}

/////////////////////////////////////
//
//   DESIGN LED
//
/////////////////////////////////////

static const uint8_t PROGMEM
  M8x8_void[] = { B00000000,
                  B00000000,
                  B00000000,
                  B00000000,
                  B00000000,
                  B00000000,
                  B00000000,
                  B00000000 },
  M8x8_cross[] = { B00000000,
                   B00100001,
                   B00010010,
                   B00001100,
                   B00001100,
                   B00010010,
                   B00100001,
                   B00000000 },
  M8x8_check[] = { B00000000,
                   B00001000,
                   B00010100,
                   B00100100,
                   B00000010,
                   B00000010,
                   B00000001,
                   B00000000 },
  M8x8_p[] = { B01111000,
               B00110000,
               B00110000,
               B00111111,
               B10110001,
               B10110001,
               B10110001,
               B01111111 },
  M8x8_emotegood[] = { B00011110,
                       B00100001,
                       B11001100,
                       B11010010,
                       B11000000,
                       B11010010,
                       B00100001,
                       B00011110 },
  M8x8_emotebad[] = { B00011110,
                      B00100001,
                      B11010010,
                      B11001100,
                      B11000000,
                      B11010010,
                      B00100001,
                      B00011110 },
  M8x8_warning[] = { B00001100,
                     B00001100,
                     B00000000,
                     B00001100,
                     B00001100,
                     B00001100,
                     B00001100,
                     B00001100 },
  M8x8_temp[] = { B00000000,
                  B00010000,
                  B00010000,
                  B00010000,
                  B01010100,
                  B11111101,
                  B10000001,
                  B00000000 },
  M8x8_choc[] = { B00000000,
                  B01110111,
                  B01010100,
                  B01110111,
                  B00000000,
                  B01110101,
                  B01000111,
                  B01110101 };


const uint8_t* motifmatrix = M8x8_p;
const uint8_t* lastMotifMatrix = nullptr;






//TFT!!

void drawBoldText(int x, int y, const char* txt, uint16_t color, uint16_t bg) {
  tft.setTextColor(color, bg);
  tft.setCursor(x, y);
  tft.print(txt);
  tft.setCursor(x + 1, y);
  tft.print(txt);
}

void drawIntValue(int x, int y, int value) {
  char buf[8];
  itoa(value, buf, 10);

  tft.fillRect(x, y, 45, 8, ST77XX_BLACK);
  tft.setCursor(x, y);
  tft.setTextColor(ST77XX_WHITE, ST77XX_BLACK);
  tft.setTextSize(1);
  tft.print(buf);
}

void drawTftStatic() {
  tft.fillScreen(ST77XX_BLACK);

  int W = tft.width();
  int H = tft.height();

  // ===== BANDEAU HAUT =====
  tft.fillRect(0, 0, W, 30, ST77XX_BLACK);

  // Logo rond bleu diamètre 25 px
  tft.fillCircle(14, 15, 10, POLYTECH_BLUE);

  // P blanc centré dans le cercle
  tft.setTextSize(2);
  drawBoldText(10, 8, "P", ST77XX_WHITE, POLYTECH_BLUE);

  // Titre centré dans le bandeau
  tft.setTextSize(2);
  drawBoldText(30, 8, "VI.FO.DE", ST77XX_WHITE, ST77XX_BLACK);

  // Ligne blanche horizontale 2 px
  tft.fillRect(0, 30, W, 2, ST77XX_WHITE);

  // ===== FOOTER =====
  tft.fillRect(0, H - 10, W, 10, ST77XX_BLACK);
  tft.fillRect(0, H - 12, W, 2, ST77XX_WHITE);
  tft.fillRect(W / 2 - 1, H - 10, 2, 10, ST77XX_WHITE);

  tft.setTextSize(1);
  tft.setTextColor(ST77XX_WHITE, ST77XX_BLACK);

  tft.setCursor(3, H - 9);
  tft.print(soft_ver);

  tft.setCursor(W / 2 + 3, H - 9);
  tft.print(card_ver);

  // ===== TABLEAU CENTRAL =====
  int tableX = 5;
  int tableY = 42;
  int tableW = W - 10;
  int tableH = 60;

  int colW = tableW / 2;
  int rowH = tableH / 3;

  tft.drawRect(tableX, tableY, tableW, tableH, ST77XX_WHITE);

  // Séparation verticale
  tft.drawLine(tableX + colW, tableY,
               tableX + colW, tableY + tableH,
               ST77XX_WHITE);

  // Séparations horizontales
  tft.drawLine(tableX, tableY + rowH,
               tableX + tableW, tableY + rowH,
               ST77XX_WHITE);

  tft.drawLine(tableX, tableY + 2 * rowH,
               tableX + tableW, tableY + 2 * rowH,
               ST77XX_WHITE);

  tft.setTextSize(1);
  tft.setTextColor(ST77XX_WHITE, ST77XX_BLACK);

  // Colonne gauche
  tft.setCursor(tableX + 4, tableY + 4);
  tft.print("AccX:");

  tft.setCursor(tableX + 4, tableY + rowH + 4);
  tft.print("AccY:");

  tft.setCursor(tableX + 4, tableY + 2 * rowH + 4);
  tft.print("AccZ:");

  // Colonne droite
  tft.setCursor(tableX + colW + 4, tableY + 4);
  tft.print("RotX:");

  tft.setCursor(tableX + colW + 4, tableY + rowH + 4);
  tft.print("RotY:");

  tft.setCursor(tableX + colW + 4, tableY + 2 * rowH + 4);
  tft.print("RotZ:");

  // ===== INFOS BAS CENTRE =====
  tft.setCursor(10, 112);
  tft.print("Temp:");

  tft.setCursor(10, 127);
  tft.print("DB entries:");
}

void drawValue(int x, int y, float value, uint8_t decimals) {
  char buf[12];
  dtostrf(value, 1, decimals, buf);

  tft.fillRect(x, y, 26, 8, ST77XX_BLACK);
  tft.setCursor(x, y);
  tft.setTextColor(ST77XX_WHITE, ST77XX_BLACK);
  tft.setTextSize(1);
  tft.print(buf);
}

void updateTftValues(float accX, float accY, float accZ,
                     float rotX, float rotY, float rotZ,
                     float temp) {
  // Tableau
  drawValue(35, 46, accX, 2);
  drawValue(94, 46, rotX, 2);

  drawValue(35, 66, accY, 2);
  drawValue(94, 66, rotY, 2);

  drawValue(35, 86, accZ, 2);
  drawValue(94, 86, rotZ, 2);

  // Température
  drawValue(45, 112, temp, 1);

  //Entrées db
  drawIntValue(75, 127, db_entry);
}








/////////////////////////////////////
//
//   PROGRAMME!
//
/////////////////////////////////////



void loop() {

  ////////////////////
  //COMMANDES SERIAL//
  ////////////////////

  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();


    //GESTION BRIGHTNESS
    if (cmd.startsWith("brightness=")) {
      String valueStr = cmd.substring(11);
      brightness = valueStr.toInt();

      if (brightness < 0) brightness = 0;
      if (brightness > 255) brightness = 255;

      Serial.print("Brightness set to: ");
      Serial.println(brightness);
    }

    //GESTION ENTRY DB
    if (cmd.startsWith("db=")) {
  db_entry = cmd.substring(3).toInt();

    Serial.print("DB Entry set to: ");
    Serial.println(db_entry);
  }

    //GESTION DES MOTIFS
    if (cmd.startsWith("motifmatrix=")) {
      String valueStr = cmd.substring(12);  // longueur de "motifmatrix="

      if (valueStr == "cross") {
        motifmatrix = M8x8_cross;
      } else if (valueStr == "check") {
        motifmatrix = M8x8_check;
      } else if (valueStr == "void") {
        motifmatrix = M8x8_void;
      } else if (valueStr == "p") {
        motifmatrix = M8x8_p;
      } else if (valueStr == "emotegood") {
        motifmatrix = M8x8_emotegood;
      } else if (valueStr == "emotebad") {
        motifmatrix = M8x8_emotebad;
      } else if (valueStr == "warning") {
        motifmatrix = M8x8_warning;
      } else if (valueStr == "temp") {
        motifmatrix = M8x8_temp;
      } else if (valueStr == "choc") {
        motifmatrix = M8x8_choc;
      }
      Serial.print("Motif set to: ");
      Serial.println(valueStr);
    }

    //GESTION DATA
    if (cmd.startsWith("data=")) {
      String valueStr = cmd.substring(5);

      if (valueStr == "ON") send_data = true;
      if (valueStr == "OFF") send_data = false;

      Serial.print("Data sending set to: ");
      Serial.println(send_data);
    }


    //GESTION RST --> KILL SWITCH attention
    if (cmd == "RESET") {
      ESP.restart();
    }

    //GESTION FREQUENCE
    if (cmd.startsWith("periode=")) {
      String valueStr = cmd.substring(8);
      periode = valueStr.toInt();

      if (periode < 1) periode = 1;

      Serial.print("periode set to: ");
      Serial.println(periode);
    }
  }





  /////////////////
  //RESTE DU CODE//
  /////////////////


  //GESTION THERMOMETRE
  float Vout = analogRead(TempPin) * 3.3 / 4095.0;
  float T = Vout * 100.0;



  //GESTION MPU

  sensors_event_t a, g, tempMPU;
  mpu.getEvent(&a, &g, &tempMPU);

  if (send_data && millis() - lastSerialSend >= (unsigned long)periode) {
    lastSerialSend = millis();

    Serial.print(a.acceleration.x);
    Serial.print(',');
    Serial.print(a.acceleration.y);
    Serial.print(',');
    Serial.print(a.acceleration.z);
    Serial.print(',');
    Serial.print(g.gyro.x);
    Serial.print(',');
    Serial.print(g.gyro.y);
    Serial.print(',');
    Serial.print(g.gyro.z);
    Serial.print(',');
    Serial.println(T);
  }

  //GESTION ÉCRAN TFT
  //Effacer l'écran
  // GESTION ÉCRAN TFT SANS SCINTILLEMENT
  if (millis() - lastTftUpdate >= TFT_PERIOD) {
    lastTftUpdate = millis();

    updateTftValues(
      a.acceleration.x,
      a.acceleration.y,
      a.acceleration.z,
      g.gyro.x,
      g.gyro.y,
      g.gyro.z,
      T);
  }

  // Gestion BACKLIGHTING
  analogWrite(PNPPin, brightness);

  // GESTION MATRICE LED uniquement si le motif change
  if (motifmatrix != lastMotifMatrix) {
    matrix.setRotation(0);
    matrix.clear();
    matrix.drawBitmap(0, 0, motifmatrix, 8, 8, LED_ON);
    matrix.writeDisplay();

    lastMotifMatrix = motifmatrix;
  }
}
