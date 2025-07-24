# SPDX-License-Identifier: MIT
import os
import time
import board
import adafruit_bme680
import wifi
import adafruit_logging as logger
import adafruit_connection_manager
import adafruit_minimqtt.adafruit_minimqtt

# Log file
log = logger.getLogger("bme688.out")

testing = False
if testing:
    log.setLevel(logger.DEBUG)
    sensor_wait_time = 10
else:
    log.setLevel(logger.INFO)
    sensor_wait_time = 600

# MQTT
radio = wifi.radio
pool = adafruit_connection_manager.get_radio_socketpool(radio)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(radio)

# Remote
mqtt_remote_server = os.getenv("mqtt_remote_server")
mqtt_remote_username = os.getenv("mqtt_remote_username")
mqtt_remote_key = os.getenv("mqtt_remote_key")

remote_mqtt = adafruit_minimqtt.adafruit_minimqtt.MQTT(
    broker=mqtt_remote_server
    , username=mqtt_remote_username
    , password=mqtt_remote_key
    , socket_pool=pool
    , ssl_context=ssl_context
)

sensor_feed = mqtt_remote_username + "/feeds/" + os.getenv("mqtt_remote_feed")

# WiFi
connected = False
while not connected:
    try:
        wifi.radio.connect(os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD"))
        ssid = str(wifi.radio.ap_info.ssid)
        log_msg = f'Connected to {ssid}!'
        log.info(log_msg)
        connected = True
    except ConnectionError:
        log.error("Failed to connect to WiFi")

# Bosch BMD688 sensor
i2c = board.STEMMA_I2C()
sensor = adafruit_bme680.Adafruit_BME680_I2C(i2c)

def print_or_publish(feed, message):
    if testing:
        log.debug("TESTING:")
        log.debug(message)
    else:
        log.info("Publishing data")
        remote_mqtt.connect()
        remote_mqtt.publish(feed, message)
        remote_mqtt.disconnect()

# Average pressure in Kona at sea level
sensor.sea_level_pressure = 1013.25
# Temperature offset for more accurate reading
temperature_offset = -5

last_reading = None
while True:
    temperature = sensor.temperature
    publish_temperature = 'Temperature: {}\u00b0C'.format(round((temperature * 0.750061683)))
    pressure = sensor.pressure
    publish_pressure = 'Pressure: {:.2f} mmHG'.format(round((pressure * 0.750061683), 2))
    humidity = sensor.humidity
    publish_humidity = 'Humidity: {}%'.format(round(humidity))
    gas = sensor.gas
    publish_gas = 'Gas: %d ohm' % gas
    altitude = sensor.altitude
    publish_altitude = 'Altitude: {} meters'.format(round(altitude))

    publish_data = f"""{publish_temperature}
{publish_pressure}
{publish_humidity}
{publish_gas}
{publish_altitude}
"""

    if last_reading is None or time.monotonic() > last_reading + sensor_wait_time:
        print_or_publish(sensor_feed, publish_data)
        last_reading = time.monotonic()

    time.sleep(0.5)