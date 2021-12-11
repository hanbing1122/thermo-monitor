#mPythonType:0
from mpython import *
from bluebit import *
import network
import urequests
import music
import time
import random

wifi_ssid = "jiacheng_teacher"
wifi_password = "jcgz@teacher"
server_addr = "http://192.168.103.100:8080"
sensorkey = "irhTFOIaEDNYEKEs"
maximum_alarm_time = 30

sht20 = SHT20()

# 连接到 WiFi

oled.fill(0)
try:
    oled.DispChar("       正在连接 WiFi", 0, 0, 1)
    oled.DispChar("    '%s'" % wifi_ssid, 0, 16, 1)
    oled.show()
    my_wifi = wifi()
    my_wifi.connectWiFi(wifi_ssid, wifi_password)
    oled.fill(0)
    oled.DispChar("       已连接 WiFi", 0, 0, 1)
    oled.DispChar("     等待服务器连接", 0, 16, 1)
    oled.show()
except:
    oled.DispChar(oled.DispChar("             连接失败", 0, 0, 1))
    oled.DispChar("     请检查 WiFi 配置", 0, 16, 1)
    oled.show()

image_picture = Image()

while True:
    oled.fill(0)
    sensorvalue = sht20.temperature()
    try:
        print("Server Probing")
        upload_data = urequests.get("%s/data_input?sensorkey=%s&sensorvalue=%.2f" %(server_addr, sensorkey, sensorvalue))
        if upload_data.text == '[{"ExecutionStatus": "Alarming"}]':
            timer = 0
            while not button_a.is_pressed():
                print(timer)
                if timer >= 30:
                    break
                music.play('C#5:4')
                oled.fill(0)
                oled.DispChar(str('       温度超标 警告！'), 0, 0, 1)
                oled.blit(image_picture.load('face/System/Alert.pbm', 0), 50, 20)
                oled.show()
                time.sleep(0.3)
                oled.blit(image_picture.load('face/System/Alert.pbm', 1), 50, 20)
                oled.show()
                timer += 1
        elif upload_data.text == '[{"ExecutionStatus": "Succeeded"}]':
            oled.DispChar("             当前温度", 0, 0, 1)
            oled.DispChar("               %.2f" % sensorvalue, 0, 16, 1)
        else:
            oled.DispChar("         0x01上传失败", 0, 0, 1)
            oled.DispChar("     请检查 SensorKey", 0, 16, 1)
            oled.DispChar("     或网络连接问题", 0, 32, 1)
            oled.show()
            break
        oled.show()
    except:
        oled.DispChar("          0x02上传失败", 0, 0, 1)
        oled.DispChar("     请检查 SensorKey", 0, 16, 1)
        oled.DispChar("     或网络连接问题", 0, 32, 1)
        oled.show()
    time.sleep(3)
        
        