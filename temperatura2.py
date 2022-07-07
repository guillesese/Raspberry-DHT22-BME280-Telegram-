#!/usr/bin/python3

import sys
import time
import adafruit_dht
import requests
import math
import sqlite3
import thingspeak
import board
from adafruit_bme280 import basic as adafruit_bme280
from urllib.request import urlopen
from sqlite3 import Error
from datetime import datetime


def crear_conexion(db):
    """
    Crea una conexión a una BD Sqlite especificada por db
    :param db: fichero de BD
    :return: objeto de conexión o None"""
    conn = None
    try:
        conn = sqlite3.connect(db)
    except Error as e:
        print(e)

    return conn

def insertar_temperatura(conn, registro):
    """
    Crea un registro con los valores recibidos del sensor
    y lo inserta en la BD
    :param conn: objeto conexión a la BD
    :param registro: array de valores para construir el Insert"""

    sql = ''' INSERT INTO DATOS(temperatura, humedad, fecha)
              VALUES(?,?,?) '''
    cur = conn.cursor()
    cur.execute(sql, registro)
    conn.commit()
    return cur.lastrowid

def calculo_indice_calor(temperatura, humedad):
    """ """
    temperatura = (temperatura * 1.8) + 32
    hi = 0.5 * (temperatura + 61.0 + ((temperatura - 68.0) * 1.2) + (humedad * 0.094))
    if(hi > 79):
        hi = -42.379 + 2.04901523 * temperatura + 10.14333127 * humedad
        hi += -0.22475541 * temperatura * humedad
        hi += -0.00683783 * pow(temperatura,2) -0.05481717 * pow(humedad,2)
        hi += 0.00122874 * pow(temperatura, 2) * humedad + 0.00085282 * temperatura * pow(humedad,2)
        hi += -0.00000199 * pow(temperatura, 2) * pow(humedad,2)
        if((humedad < 13) and (temperatura >= 80) and (temperatura <= 112)):
            hi -= ((13.0 - humedad) * 0.25) * math.sqrt((17.0 - abs(temperatura - 95.0)) * 0.05882)
        elif((humedad > 85) and (temperatura >= 80) and (temperatura <= 87)):
            hi += ((humedad - 85) * 0.1) * ((87 - temperatura) * 0.2)
    hi = (hi - 32) * 0.555
    return hi

def telegram_bot_sendtext(bot_message):
    bot_token = '%BOT_TOKEN%'
    bot_chatID = '%BOT_CHATID%'
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message

    response = requests.get(send_text)
    return response.json()


def main():
    db = r"/home/pi/datostemperatura22.db"

    conn = crear_conexion(db)
    pin = 23
    sensor = adafruit_dht.DHT22(pin)
    i2c = board.I2C()
    bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)
    bme280.sea_level_pressure = 1013.25
    #Conexion con ThingSpeak
    channel_id = 1600659
    key = '%KEY%'
    #channel = thingspeak.Channel(id=channel_id, write_key=key)
    BASE_URL = "https://api.thingspeak.com/update?api_key={}".format(key)

    with conn:
       #datos del dht22
       humedad = sensor.humidity
       temperatura = sensor.temperature
       #datos del bme280
       humedad_bme280  = round(bme280.humidity,2)
       temperatura_bme280 = round(bme280.temperature,2)
       presion_bme280 = round(bme280.pressure,2)
       altitud_bme280 = round(bme280.altitude,2)
       #calculos y conversiones
       ahora = datetime.now()
       dt_ahora = ahora.strftime("%d/%m/%Y %H:%M:%S")
       reg_temperatura = (temperatura, humedad, dt_ahora)
       insertar_temperatura(conn, reg_temperatura)
       indice_calor = calculo_indice_calor(temperatura, humedad)
       indice_calor_bme280 = calculo_indice_calor(temperatura_bme280, humedad_bme280)
       mensaje = 'DHT22: Fecha: ' + dt_ahora + ' / Temperatura: ' + str(temperatura) + 'ºC Humedad: ' + str(humedad) + '% Indice calor: '+  str(round(indice_calor,2)) + 'ºC'
       telegram_bot_sendtext(mensaje)
       mensaje_bme280 = 'BME280: Fecha: ' + dt_ahora + '/ Temperatura: ' + str(temperatura_bme280) + 'ºC Humedad: ' + str(humedad_bme280) + '% Indice calor: '+ str(round(indice_calor_bme280,2)) +'ºC Presion: ' + str(presion_bme280) + 'hPa Altitud: ' + str(altitud_bme280) + 'm'
       telegram_bot_sendtext(mensaje_bme280)
       thingspeakhttp = BASE_URL + "&field1={:.2f}&field2={:.2f}&field3={:.2f}".format(temperatura,humedad,indice_calor)
       tsconn = urlopen(thingspeakhttp)
       tsconn.close()

if __name__ == '__main__':
    main()