'''
Ver: Soft V1.0
'''


#Bloc des imports
import serial
import sys
import subprocess
import time
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
from PyQt5.QtWidgets import QFormLayout, QLineEdit, QComboBox, QLabel, QSlider, QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QPushButton, QLineEdit
from PyQt5.QtGui import QIcon, QIntValidator, QPixmap, QDoubleValidator
from PyQt5.QtCore import Qt
import sqlite3
from serial.tools import list_ports

import ctypes
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("VIFODE.app") #Pour faire afficher le logo polytech dans la barre des taches --> marche po, c'est du à spyder

#################
#
#Setup
#
#################



COM = 'COM4'
Baud = 115200

title = "VIFODE - Vibration Following Device"

#Taille du buffer circulaire
BUFFER_SIZE = 100
buffer = [(0, 0, 0, 0, 0, 0, 0, 0)] * BUFFER_SIZE
index = 0
periode = 20
SigmaAccX = 1
SigmaAccY = 1
SigmaAccZ = 1
SigmaRotX = 1
SigmaRotY = 1
SigmaRotZ = 1
SigmaTemp = 1 #défini la fenêtre de visualisation des courbes

#Pour définir un zéro non glissant
zero_accx = 0
zero_accy = 0
zero_accz = 9.81
zero_rotx = 0
zero_roty = 0
zero_rotz = 0
zero_temp = 0

#Pour avoir le temps relatif
t0 = time.time()



#Reprends les variable de config.txt mais évite les problèmes en les définissant une fois dans le code
TEMP_ALERT_THRESHOLD = 60.0
DETECTION_LIMIT = 10
ALERT_WINDOW_SECONDS = 3600
BLIND_TIME = 15
last_detection_time = 0
vibration_code_triggered = False
temperature_code_triggered = False

#Ces variables permettent d'éviter d'enregister 24h à 50Hz en cas de dépassement lent et constant.
accx_in_alert = accy_in_alert = accz_in_alert = temp_in_alert = False
rotx_in_alert = roty_in_alert = rotz_in_alert = False
accx_peak = accy_peak = accz_peak = temp_peak = None
rotx_peak = roty_peak = rotz_peak = None
accx_start_time = accy_start_time = accz_start_time = temp_start_time = None
rotx_start_time = roty_start_time = rotz_start_time = None


#################
#
# GESTION DB
#
#################

conn = sqlite3.connect("main_db.db")
cur = conn.cursor()
cur.execute("PRAGMA foreign_keys = ON") #Active les clef étrangères






#################
#
# FONCTIONS
#
#################



#Fonction pour démarrer et arrêter la transmission --> \n est important
def send_data(state):
    
    if not serialConnection or not serialConnection.is_open: #evite de tout faire planter si l'user clique la dessus avant d'avoir lancer la connection
        return
    
    if state:
        message = "data=ON\n"
        serialConnection.write(message.encode('utf-8'))
    else:
        message = "data=OFF\n"
        serialConnection.write(message.encode('utf-8'))

#Fonction pour définir le brightness de l'écran        
def brightness(brightness_value):
    if not serialConnection or not serialConnection.is_open:
        return
    
    message = f"brightness={brightness_value}\n"
    serialConnection.write(message.encode('utf-8'))

#Fonction pour définir la fréquence d'aquisition    
def frequence():
    global periode

    texte = textbox_frequence.text().strip() #Vérifie que le champ ne soit pas vide
    if not texte:
        return
    frequence_value = int(texte)
    if frequence_value <= 0: #Vérifie que le texte soit suppérieur à 0 (y'a une division juste après)
        return

    periode = int((1 / frequence_value) * 1000)

    if serialConnection and serialConnection.is_open:
        message = f"periode={periode}\n"
        serialConnection.write(message.encode('utf-8'))

    timer.start(periode)
    return periode

#Fonction pour reset l'arduino        
def reset():
    global serialConnection
    
    if not serialConnection or not serialConnection.is_open:
        return
    
    timer.stop()
    
    try:
        message = "RESET\n"
        serialConnection.write(message.encode('utf-8'))
        serialConnection.close()
        time.sleep(2)  # laisse le temps à la carte de redémarrer
        serialConnection = serial.Serial(COM, Baud, timeout=0.05)
    except serial.SerialException as e:
        print("Erreur reset :", e)
        serialConnection = None
    
    finally:
        timer.start(periode)

def resetdb():
    global serialConnection
    
    if not serialConnection or not serialConnection.is_open:
        return
    
    subprocess.Popen([sys.executable, "db_setup.py"])
    
    

#Fonction de calcul des moyennes sur chaque courbes
def moyenne():
    ordered = buffer[index:] + buffer[:index]

    AccX = [vals[0] for *vals, t in ordered][:-1]
    AccY = [vals[1] for *vals, t in ordered][:-1]
    AccZ = [vals[2] for *vals, t in ordered][:-1]
    RotX = [vals[3] for *vals, t in ordered][:-1]
    RotY = [vals[4] for *vals, t in ordered][:-1]
    RotZ = [vals[5] for *vals, t in ordered][:-1]
    Temp = [vals[6] for *vals, t in ordered][:-1]

    return (
        sum(AccX) / len(AccX),
        sum(AccY) / len(AccY),
        sum(AccZ) / len(AccZ),
        sum(RotX) / len(RotX),
        sum(RotY) / len(RotY),
        sum(RotZ) / len(RotZ),
        sum(Temp) / len(Temp),
    )
    

#Permet l'affichage et l'actualisation des moyennes en live
def update_moyenne():
    try:
        AccX, AccY, AccZ, RotX, RotY, RotZ, Temp = moyenne()

        texte = (
            f"AccX: {AccX:.2f} | AccY: {AccY:.2f} | AccZ: {AccZ:.2f}\n"
            f"RotX: {RotX:.3f} | RotY: {RotY:.3f} | RotZ: {RotZ:.3f}\n"
            f"Temp: {Temp:.2f}"
        )

        label_moyenne.setText(texte)

    except:
        pass  # évite crash au démarrage (buffer vide)


#Permet de définir le zéro des courbes selon leur moyenne
def set_zero(SigmaAccX, SigmaAccY, SigmaAccZ, SigmaRotX, SigmaRotY, SigmaRotZ, SigmaTemp):
    MAccX, MAccY, MAccZ, MRotX, MRotY, MRotZ, MTemp = moyenne() #Récupère et store les moyennes dans ces variables
    
    AccXMin = MAccX - SigmaAccX
    AccXMax = MAccX + SigmaAccX
    AccYMin = MAccY - SigmaAccY
    AccYMax = MAccY + SigmaAccY
    AccZMin = MAccZ - SigmaAccZ
    AccZMax = MAccZ + SigmaAccZ
    RotXMin = MRotX - SigmaRotX
    RotXMax = MRotX + SigmaRotX
    RotYMin = MRotY - SigmaRotY
    RotYMax = MRotY + SigmaRotY
    RotZMin = MRotZ - SigmaRotZ
    RotZMax = MRotZ + SigmaRotZ
    TempMin = MTemp - SigmaTemp
    TempMax = MTemp + SigmaTemp

    return (
    AccXMin, AccXMax,
    AccYMin, AccYMax,
    AccZMin, AccZMax,
    RotXMin, RotXMax,
    RotYMin, RotYMax,
    RotZMin, RotZMax,
    TempMin, TempMax
    )

#Fonction pour faire le lien entre le bouton et la maj des +/-
def apply_sigma():
    AccXMin, AccXMax, AccYMin, AccYMax, AccZMin, AccZMax, RotXMin, RotXMax, RotYMin, RotYMax, RotZMin, RotZMax, TempMin, TempMax = set_zero(
        float(sigma_accx.text().replace(',', '.')),
        float(sigma_accy.text().replace(',', '.')),
        float(sigma_accz.text().replace(',', '.')),
        float(sigma_rotx.text().replace(',', '.')),
        float(sigma_roty.text().replace(',', '.')),
        float(sigma_rotz.text().replace(',', '.')),
        float(sigma_temp.text().replace(',', '.')),
    )

    plot1.setYRange(AccXMin, AccXMax)
    plot2.setYRange(AccYMin, AccYMax)
    plot3.setYRange(AccZMin, AccZMax)
    plot4.setYRange(RotXMin, RotXMax)
    plot5.setYRange(RotYMin, RotYMax)
    plot6.setYRange(RotZMin, RotZMax)
    plot7.setYRange(TempMin, TempMax)
    
    
    
    

#Fonction d'update des datas, c'est la fonction principale
def update():
    global index, buffer, serialConnection

    if not serialConnection or not serialConnection.is_open:
        return

    try:
        values = []
        line = None

        # Lire uniquement la dernière ligne dispo
        while serialConnection.in_waiting > 0:
            line = serialConnection.readline().decode(errors="ignore").strip()

        if not line:
            return

        values = list(map(float, line.split(',')))
        
        if len(values) != 7:
            return
        threshold(values)
        
        if index % 50 == 0: #Tous les 50 cycles on écrit dans la DB --> évite le spam disque
            conn.commit()
            check_db_alerts()
            db_entry()
        
    except serial.SerialException as e:
        print("Erreur série :", e)
        return
    except:
        return

    timestamp = time.time() - t0

    # Stockage dans le buffer circulaire
    buffer[index] = (*values, timestamp)
    index = (index + 1) % BUFFER_SIZE

    ordered = buffer[index:] + buffer[:index]

    x = [t for *vals, t in ordered]
    
    AccX = [vals[0] for *vals, t in ordered]
    AccY = [vals[1] for *vals, t in ordered]
    AccZ = [vals[2] for *vals, t in ordered]
    RotX = [vals[3] for *vals, t in ordered]
    RotY = [vals[4] for *vals, t in ordered]
    RotZ = [vals[5] for *vals, t in ordered]
    Temp = [vals[6] for *vals, t in ordered]

    curve1.setData(x,AccX)
    curve2.setData(x,AccY)
    curve3.setData(x,AccZ)
    curve4.setData(x,RotX)
    curve5.setData(x,RotY)
    curve6.setData(x,RotZ)
    curve7.setData(x,Temp)
    
    




#Fonction pour definir un zéro non glissant --> detection d'évolutions lentes, à faire une fois au début de fait.
def calibrate_zero():
    global zero_accx, zero_accy, zero_accz, zero_rotx, zero_roty, zero_rotz, zero_temp

    zero_accx, zero_accy, zero_accz, zero_rotx, zero_roty, zero_rotz, zero_temp = moyenne()





#Fonction pour détecter les overshoots (au secours)

def threshold(values):
    try:
        global zero_accx, zero_accy, zero_accz
        global zero_rotx, zero_roty, zero_rotz, zero_temp

        global accx_in_alert, accy_in_alert, accz_in_alert, temp_in_alert
        global rotx_in_alert, roty_in_alert, rotz_in_alert

        global accx_peak, accy_peak, accz_peak, temp_peak
        global rotx_peak, roty_peak, rotz_peak

        global accx_start_time, accy_start_time, accz_start_time, temp_start_time
        global rotx_start_time, roty_start_time, rotz_start_time

        global last_detection_time
        current_time = time.time()
        in_blind = (current_time - last_detection_time < BLIND_TIME)
            

        accx, accy, accz, rotx, roty, rotz, temp = values
        timestamp = current_time

        # Sigma UI
        sAccX = float(sigma_accx.text().replace(',', '.'))
        sAccY = float(sigma_accy.text().replace(',', '.'))
        sAccZ = float(sigma_accz.text().replace(',', '.'))
        sRotX = float(sigma_rotx.text().replace(',', '.'))
        sRotY = float(sigma_roty.text().replace(',', '.'))
        sRotZ = float(sigma_rotz.text().replace(',', '.'))
        #sTemp = float(sigma_temp.text().replace(',', '.'))

        # ===== ACCX =====
        delta = abs(accx - zero_accx)

        
        if not in_blind and not accx_in_alert and delta > sAccX:
            accx_in_alert = True
            accx_start_time = timestamp
            accx_peak = accx

            cur.execute("""
            INSERT INTO threshold (ID_Name, Value_threshold, Timestamp_threshold)
            VALUES (?, ?, ?)
            """, (1, accx, timestamp))
            
            last_detection_time = current_time

        elif accx_in_alert:
            if abs(accx - zero_accx) > abs(accx_peak - zero_accx):
                accx_peak = accx

            if delta < sAccX * 0.9: #Hysteresis pour eviter le bouncing 
                if not in_blind:
                    cur.execute("""
                    INSERT INTO threshold (ID_Name, Value_threshold, Timestamp_threshold)
                    VALUES (?, ?, ?)
                    """, (1, accx_peak, timestamp))

                accx_in_alert = False
                accx_peak = None
                accx_start_time = None

        # ===== ACCY =====
        delta = abs(accy - zero_accy)

        if not in_blind and not accy_in_alert and delta > sAccY:
            accy_in_alert = True
            accy_start_time = timestamp
            accy_peak = accy

            cur.execute("""
            INSERT INTO threshold (ID_Name, Value_threshold, Timestamp_threshold)
            VALUES (?, ?, ?)
            """, (2, accy, timestamp))
            
            last_detection_time = current_time
            

        elif accy_in_alert:
            if abs(accy - zero_accy) > abs(accy_peak - zero_accy):
                accy_peak = accy

            if delta < sAccY * 0.9:
                if not in_blind: 
                    cur.execute("""
                    INSERT INTO threshold (ID_Name, Value_threshold, Timestamp_threshold)
                    VALUES (?, ?, ?)
                    """, (2, accy_peak, timestamp))

                accy_in_alert = False
                accy_peak = None
                accy_start_time = None

        # ===== ACCZ =====
        delta = abs(accz - zero_accz)

        if not in_blind and not accz_in_alert and delta > sAccZ:
            accz_in_alert = True
            accz_start_time = timestamp
            accz_peak = accz

            cur.execute("""
            INSERT INTO threshold (ID_Name, Value_threshold, Timestamp_threshold)
            VALUES (?, ?, ?)
            """, (3, accz, timestamp))
            
            last_detection_time = current_time

        elif accz_in_alert:
            if abs(accz - zero_accz) > abs(accz_peak - zero_accz):
                accz_peak = accz

            if delta < sAccZ * 0.9:
                if not in_blind:
                    cur.execute("""
                    INSERT INTO threshold (ID_Name, Value_threshold, Timestamp_threshold)
                    VALUES (?, ?, ?)
                    """, (3, accz_peak, timestamp))

                accz_in_alert = False
                accz_peak = None
                accz_start_time = None

        # ===== ROTX =====
        delta = abs(rotx - zero_rotx)

        if not in_blind and not rotx_in_alert and delta > sRotX:
            rotx_in_alert = True
            rotx_start_time = timestamp
            rotx_peak = rotx

            cur.execute("""
            INSERT INTO threshold (ID_Name, Value_threshold, Timestamp_threshold)
            VALUES (?, ?, ?)
            """, (4, rotx, timestamp))
            
            last_detection_time = current_time

        elif rotx_in_alert:
            if abs(rotx - zero_rotx) > abs(rotx_peak - zero_rotx):
                rotx_peak = rotx

            if delta < sRotX * 0.9:
                if not in_blind:
                    cur.execute("""
                    INSERT INTO threshold (ID_Name, Value_threshold, Timestamp_threshold)
                    VALUES (?, ?, ?)
                    """, (4, rotx_peak, timestamp))

                rotx_in_alert = False
                rotx_peak = None
                rotx_start_time = None

        # ===== ROTY =====
        delta = abs(roty - zero_roty)

        if not in_blind and not roty_in_alert and delta > sRotY:
            roty_in_alert = True
            roty_start_time = timestamp
            roty_peak = roty

            cur.execute("""
            INSERT INTO threshold (ID_Name, Value_threshold, Timestamp_threshold)
            VALUES (?, ?, ?)
            """, (5, roty, timestamp))
            
            last_detection_time = current_time

        elif roty_in_alert:
            if abs(roty - zero_roty) > abs(roty_peak - zero_roty):
                roty_peak = roty

            if delta < sRotY * 0.9:
                if not in_blind:
                    cur.execute("""
                    INSERT INTO threshold (ID_Name, Value_threshold, Timestamp_threshold)
                    VALUES (?, ?, ?)
                    """, (5, roty_peak, timestamp))

                roty_in_alert = False
                roty_peak = None
                roty_start_time = None

        # ===== ROTZ =====
        delta = abs(rotz - zero_rotz)

        if not in_blind and not rotz_in_alert and delta > sRotZ:
            rotz_in_alert = True
            rotz_start_time = timestamp
            rotz_peak = rotz

            cur.execute("""
            INSERT INTO threshold (ID_Name, Value_threshold, Timestamp_threshold)
            VALUES (?, ?, ?)
            """, (6, rotz, timestamp))
            
            last_detection_time = current_time

        elif rotz_in_alert:
            if abs(rotz - zero_rotz) > abs(rotz_peak - zero_rotz):
                rotz_peak = rotz

            if delta < sRotZ * 0.9:
                if not in_blind:
                    cur.execute("""
                    INSERT INTO threshold (ID_Name, Value_threshold, Timestamp_threshold)
                    VALUES (?, ?, ?)
                    """, (6, rotz_peak, timestamp))

                rotz_in_alert = False
                rotz_peak = None
                rotz_start_time = None



        # ===== TEMP =====
        if not in_blind and not temp_in_alert and temp > TEMP_ALERT_THRESHOLD: #Ici on change de méthode, si T° > à valeur maxi --> pas bon
            temp_in_alert = True
            temp_start_time = timestamp
            temp_peak = temp
        
            cur.execute("""
            INSERT INTO threshold (ID_Name, Value_threshold, Timestamp_threshold)
            VALUES (?, ?, ?)
            """, (7, temp, timestamp))
            
            last_detection_time = current_time
        
        elif temp_in_alert:
            if temp > temp_peak:
                temp_peak = temp
        
            if temp < TEMP_ALERT_THRESHOLD * 0.98:   # petite hystérésis --> 2% d'erreur
                if not in_blind:
                    cur.execute("""
                    INSERT INTO threshold (ID_Name, Value_threshold, Timestamp_threshold)
                    VALUES (?, ?, ?)
                    """, (7, temp_peak, timestamp))
        
                temp_in_alert = False
                temp_peak = None
                temp_start_time = None
        

            

    except:
        pass

#Fonction pour fetch les ports
def refresh_com_ports():
    combo_com.clear()
    ports = list_ports.comports()
    for port in ports:
        combo_com.addItem(port.device)   # ex: COM3, COM4


#Fonction pour se connecter proprement avec exceptions et tests pour eviter que ça plante
def connect_serial():
    global serialConnection, COM

    selected_port = combo_com.currentText()
    if not selected_port:
        print("Aucun port sélectionné")
        return

    COM = selected_port

    try:
        if serialConnection and serialConnection.is_open:
            serialConnection.close()
    except:
        pass

    try:
        serialConnection = serial.Serial(COM, Baud, timeout=0.05)
        print(f"Connecté sur {COM}")
    except serial.SerialException as e:
        print(f"Impossible d'ouvrir le port {COM} : {e}")
        serialConnection = None


#Le port COM est mort, vive le port COM! (Fonction pour se déconnecter)
def disconnect_serial():
    global serialConnection
    try:
        if serialConnection and serialConnection.is_open:
            serialConnection.close()
            print("Port série fermé")
    except:
        pass
    serialConnection = None


#Fonction pour load la config    
def load_config():
    global TEMP_ALERT_THRESHOLD, DETECTION_LIMIT, ALERT_WINDOW_SECONDS, BLIND_TIME

    try:
        with open("config.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                if not line or line.startswith("#"):
                    continue

                if "=" not in line:
                    continue

                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                if key == "TEMP_ALERT_THRESHOLD": #Température maximale admissible
                    TEMP_ALERT_THRESHOLD = float(value)
                elif key == "DETECTION_LIMIT": #Nombre maximales de détection dans la DB avant de sonner l'alerte
                    DETECTION_LIMIT = int(value)
                elif key == "ALERT_WINDOW_SECONDS": #Temps glissant: si j'ai X détections pendant X temps --> alerte
                    ALERT_WINDOW_SECONDS = int(value)
                elif key == "BLIND_TIME": #Temps en secondes pendant lequel la lecture est sourde.
                    BLIND_TIME = int(value)

    except FileNotFoundError:
        print("config.txt introuvable, valeurs par défaut utilisées")
    except Exception as e:
        print("Erreur lecture config.txt :", e)    


#Ce machin regarde combien il y a eu de trigger dans la DB sur une période passée définie selon un seuil défini, et appelle d'autres fonctions en cas de.
def check_db_alerts():
    global temperature_code_triggered, vibration_code_triggered

    try:
        now = time.time()
        time_limit = now - ALERT_WINDOW_SECONDS

        # Température sur la fenêtre glissante
        cur.execute("""
            SELECT COUNT(*)
            FROM threshold
            WHERE ID_Name = 7
              AND Timestamp_threshold >= ?
        """, (time_limit,))
        temp_count = cur.fetchone()[0]

        # Vibrations / accélérations sur la fenêtre glissante
        cur.execute("""
            SELECT COUNT(*)
            FROM threshold
            WHERE ID_Name IN (1, 2, 3, 4, 5, 6)
              AND Timestamp_threshold >= ?
        """, (time_limit,))
        vibration_count = cur.fetchone()[0]

        if temp_count >= DETECTION_LIMIT and not temperature_code_triggered:
            temperature_code_triggered = True
            temp_overshoot()

        if vibration_count >= DETECTION_LIMIT and not vibration_code_triggered:
            vibration_code_triggered = True
            choc()

        # Réarmement automatique
        if temp_count < DETECTION_LIMIT:
            temperature_code_triggered = False

        if vibration_count < DETECTION_LIMIT:
            vibration_code_triggered = False

    except Exception as e:
        print("Erreur check_db_alerts :", e)


def temp_overshoot():
    if not serialConnection or not serialConnection.is_open:
        return
    
    message = "motifmatrix=temp\n"
    serialConnection.write(message.encode('utf-8'))

def db_entry():
    if not serialConnection or not serialConnection.is_open:
        return

    try:
        cur.execute("SELECT COUNT(*) FROM threshold")
        entries = cur.fetchone()[0]

        message = f"db={entries}\n"
        serialConnection.write(message.encode('utf-8'))

    except Exception as e:
        print("Erreur DB Entry :", e)

def choc():
    if not serialConnection or not serialConnection.is_open:
        return
    
    message = "motifmatrix=choc\n"
    serialConnection.write(message.encode('utf-8'))

#################
#
#NON Ouverture serial
#
#################


serialConnection = None
load_config() #Chargement de la config




#################
#
# Application Qt
#
#################





app = QtWidgets.QApplication([])
app.setWindowIcon(QIcon("media/icon.ico"))


# Fenêtre principale Qt
main_window = QWidget()
main_layout = QVBoxLayout()
main_window.setWindowIcon(QIcon("media/icon.png"))


#Zone des graphs Qt
win = pg.GraphicsLayoutWidget(title=title)

plot1 = win.addPlot(title="AccX")
win.nextRow()
plot2 = win.addPlot(title="AccY")
win.nextRow()
plot3 = win.addPlot(title="AccZ")
win.nextRow()
plot4 = win.addPlot(title="RotX")
win.nextRow()
plot5 = win.addPlot(title="RotY")
win.nextRow()
plot6 = win.addPlot(title="RotZ")
win.nextRow()
plot7 = win.addPlot(title="Temp")


#Esthétique des courbes
curve1 = plot1.plot([], [], symbol=None, pen="r")
curve2 = plot2.plot([], [], symbol=None, pen="g")
curve3 = plot3.plot([], [], symbol=None, pen="b")
curve4 = plot4.plot([], [], symbol=None, pen="c")
curve5 = plot5.plot([], [], symbol=None, pen="m")
curve6 = plot6.plot([], [], symbol=None, pen="y")
curve7 = plot7.plot([], [], symbol=None, pen="r")

AccXMin, AccXMax, AccYMin, AccYMax, AccZMin, AccZMax, RotXMin, RotXMax, RotYMin, RotYMax, RotZMin, RotZMax, TempMin, TempMax = set_zero(
    SigmaAccX, SigmaAccY, SigmaAccZ, SigmaRotX, SigmaRotY, SigmaRotZ, SigmaTemp
)

plot1.setYRange(AccXMin, AccXMax)
plot2.setYRange(AccYMin, AccYMax)
plot3.setYRange(AccZMin, AccZMax)
plot4.setYRange(RotXMin, RotXMax)
plot5.setYRange(RotYMin, RotYMax)
plot6.setYRange(RotZMin, RotZMax)
plot7.setYRange(TempMin, TempMax)







#To send data or not to send data?
checkbox_data = QCheckBox("Envoyer données?")
checkbox_data.setChecked(True) #Coche la case par défaut
checkbox_data.stateChanged.connect(send_data)


#Brightness de l'écran tft
label_brightness = QLabel("Brightness :")
slider_brightness = QSlider(Qt.Horizontal)
slider_brightness.setMinimum(0)
slider_brightness.setMaximum(255)
slider_brightness.setValue(0)
slider_brightness.valueChanged.connect(
    lambda: brightness(slider_brightness.value()) #Ce machin empêche l'envoi de 150000 requêtes à la suite
    )

label_moyenne = QLabel("Moyennes :")


#Définir la fréquence d'aquisition
textbox_frequence = QLineEdit()
textbox_frequence.setValidator(QIntValidator())
textbox_frequence.setPlaceholderText("Fréquence")
textbox_button = QPushButton("Submit")
textbox_button.clicked.connect(frequence)       

#Killswitch reset Arduino
reset_button = QPushButton("RESET UNO")
reset_button.clicked.connect(reset)
reset_button.setStyleSheet("""
    QPushButton {
        background-color: red;
        color: white;
        font-weight: bold;
        border-radius: 5px;
        padding: 6px;
    }
""")

#Killswitch reset DB
resetdb_button = QPushButton("RESET DB")
resetdb_button.clicked.connect(resetdb)
resetdb_button.setStyleSheet("""
    QPushButton {
        background-color: red;
        color: white;
        font-weight: bold;
        border-radius: 5px;
        padding: 6px;
    }
""")


#Zero
set_zero_button = QPushButton("SET ZERO")
set_zero_button.clicked.connect(calibrate_zero)


# Sélecteur de port COM
combo_com = QComboBox() #Combo = dropdown

refresh_com_button = QPushButton("Rafraîchir ports")
connect_com_button = QPushButton("Connecter")
disconnect_com_button = QPushButton("Déconnecter")

refresh_com_button.clicked.connect(refresh_com_ports)
connect_com_button.clicked.connect(connect_serial)
disconnect_com_button.clicked.connect(disconnect_serial)

refresh_com_ports()


#Ajout des features graphiques à l'appli

#Sigma table
sigma_layout = QFormLayout()

sigma_accx = QLineEdit()
sigma_accx.setPlaceholderText("σ accélération X")
sigma_accx.setValidator(QDoubleValidator())
sigma_accx.setText("0,5")

sigma_accy = QLineEdit()
sigma_accy.setPlaceholderText("σ accélération Y")
sigma_accy.setValidator(QDoubleValidator())
sigma_accy.setText("0,5")

sigma_accz = QLineEdit()
sigma_accz.setPlaceholderText("σ accélération Z")
sigma_accz.setValidator(QDoubleValidator())
sigma_accz.setText("0,5")

sigma_rotx = QLineEdit()
sigma_rotx.setPlaceholderText("σ rotation X")
sigma_rotx.setValidator(QDoubleValidator())
sigma_rotx.setText("0,5")

sigma_roty = QLineEdit()
sigma_roty.setPlaceholderText("σ rotation Y")
sigma_roty.setValidator(QDoubleValidator())
sigma_roty.setText("0,5")

sigma_rotz = QLineEdit()
sigma_rotz.setPlaceholderText("σ rotation Z")
sigma_rotz.setValidator(QDoubleValidator())
sigma_rotz.setText("0,5")

sigma_temp = QLineEdit()
sigma_temp.setPlaceholderText("σ température")
sigma_temp.setValidator(QDoubleValidator())
sigma_temp.setText("10")

sigma_layout.addRow("Sigma AccX", sigma_accx)
sigma_layout.addRow("Sigma AccY", sigma_accy)
sigma_layout.addRow("Sigma AccZ", sigma_accz)
sigma_layout.addRow("Sigma RotX", sigma_rotx)
sigma_layout.addRow("Sigma RotY", sigma_roty)
sigma_layout.addRow("Sigma RotZ", sigma_rotz)
sigma_layout.addRow("Sigma Temp", sigma_temp)

sigma_button = QPushButton("APPLY σ")
sigma_button.clicked.connect(apply_sigma)



#Topbar
top_bar = QHBoxLayout()
logo_top_bar = QLabel()
logo_top_bar.setPixmap(QPixmap("media/logo.png").scaledToHeight(40))
title_top_bar = QLabel(title)
title_top_bar.setStyleSheet("font-size: 16px; font-weight: bold; font-family: 'Cascadia Mono SemiBold';")
top_bar.addWidget(logo_top_bar)
top_bar.addWidget(title_top_bar)
top_bar.addStretch()

#Rightbar
right_bar = QVBoxLayout()
right_bar.addWidget(label_moyenne)
right_bar.addLayout(sigma_layout)
right_bar.addWidget(sigma_button)
right_bar.addWidget(checkbox_data)
right_bar.addWidget(set_zero_button)
right_bar.addWidget(label_brightness)
right_bar.addWidget(slider_brightness)
right_bar.addWidget(textbox_frequence)
right_bar.addWidget(textbox_button)
right_bar.addWidget(reset_button)
right_bar.addWidget(resetdb_button)

#A bouger dans section dédiée
right_bar.addWidget(QLabel("Port COM"))
right_bar.addWidget(combo_com)
right_bar.addWidget(refresh_com_button)
right_bar.addWidget(connect_com_button)
right_bar.addWidget(disconnect_com_button)


right_widget = QWidget()
right_widget.setLayout(right_bar)
right_widget.setFixedWidth(250)

#Gestion de la partie centrale divisée en deux
center_layout = QHBoxLayout()
center_layout.addWidget(win)
center_layout.addWidget(right_widget)

#Gestion de la main avec la top bar et la central bar
main_layout.addLayout(top_bar)
main_layout.addLayout(center_layout)


main_window.setLayout(main_layout)
main_window.setWindowTitle(title)
main_window.show()

#Appel propre du def
timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.timeout.connect(update_moyenne)
timer.start(periode)


#################
#
#Gestion fin de programme
#
#################



try:
    app.exec()
except KeyboardInterrupt:
    print("Arrêt du programme")

if serialConnection and serialConnection.is_open:
    serialConnection.close()
