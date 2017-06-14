#!/usr/bin/env python
# -*- coding: utf-8 -*-

from phue import Bridge, PhueRegistrationException
import logging
import time
import sys
import requests
import json
from win10toast import ToastNotifier

HUE_BRIDGE_IP = '192.168.178.20'
# noinspection SpellCheckingInspection
ESPRESSO_MACHINE_NAME = 'Espresso Maschine'
# noinspection SpellCheckingInspection
ESPRESSO_MACHINE_LIGHT_INDICATOR = 'Küche Vorraum'
WARM_UP_TIME = 75
TURN_OFF_TIME = 130

# noinspection SpellCheckingInspection
IFTTT_MAKER_ID = 'L3XjFGgdTPKlUR_WUC5ya'
IFTTT_EVENT_NAME = 'espresso_notification'
IFTTT_MAKER_URL = 'https://maker.ifttt.com/trigger/{0}/with/key/{1}'


def send_notification(header, body):
    logger.info('{0}: > {1}'.format(header, body))
    send_ifttt_notification(header, body)
    send_win10_toast(header, body)


def send_win10_toast(header, body):
    # noinspection PyBroadException
    try:
        notification = ToastNotifier()
        notification.show_toast(header, body, icon_path='icon.ico', duration=20)
    except:
        logger.info('Could not send Windows 10 toast')


def send_ifttt_notification(header, body):
    payload = {'value1': header, 'value2': body}
    url = IFTTT_MAKER_URL.format(IFTTT_EVENT_NAME, IFTTT_MAKER_ID)
    requests.post(url, data=payload)


def sleep_countdown(sleep_timer, blink_indicator_light=False, indicator=None):
    next_light_status = 1
    for countdown in range(sleep_timer, -1, -1):
        logger.info('{0}...'.format(countdown))
        time.sleep(1)

        if blink_indicator_light and indicator is not None:
            change_indicator_light_status(indicator, next_light_status)
            if next_light_status == 0:
                next_light_status = 1
            else:
                next_light_status = 0


def change_indicator_light_status(indicator, light_status):
    if indicator is None:
        return

    # turn off
    if light_status == 0:
        indicator.on = False
        return

    # turn on to red
    if light_status == 1:
        indicator.on = True
        indicator.brightness = 254
        indicator.hue = 0
        indicator.saturation = 100


def create_loggers():
    log_file_name = 'run_{0}.log'.format(time.time())

    # setup logging
    # noinspection SpellCheckingInspection
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename=log_file_name,
                        filemode='w', level=logging.DEBUG)

    # create main_logger
    main_logger = logging.getLogger('main')
    logging_level = logging.DEBUG
    main_logger.setLevel(logging.DEBUG)

    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging_level)

    # create formatter
    # noinspection SpellCheckingInspection
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')

    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to main_logger
    main_logger.addHandler(ch)


create_loggers()
logger = logging.getLogger('main')

# try it silently for the first time
silent = True
while True:
    if not silent:
        logger.debug('Please press the link button on your bridge and press enter to continue.')
        raw_input('')
        silent = True
    logger.info('Connecting to ' + HUE_BRIDGE_IP)
    try:
        logger.debug('Creating bridge object')
        b = Bridge(HUE_BRIDGE_IP)
        b.connect()
    except PhueRegistrationException, e:
        logger.error('Link button was not pressed.')
        continue
    logger.info('Connection successful.')
    break

# print names of all lights connected to the bridge ...
lights = b.lights
logger.debug('Connected lights: ')
counter = 1

# .. and also search for the Espresso Machine
espresso_machine_unit = None
espresso_machine_light_indicator = None

for l in lights:
    if l.name == ESPRESSO_MACHINE_NAME:
        espresso_machine_unit = l
        logger.debug('\t{0}: --> {1} <-- (Found espresso unit)'.format(counter, l.name))
    elif l.name == ESPRESSO_MACHINE_LIGHT_INDICATOR:
        espresso_machine_light_indicator = l
        logger.debug('\t{0}: ~-> {1} <-~ (Found indicator unit)'.format(counter, l.name))
    else:
        logger.debug('\t{0}: {1}'.format(counter, l.name))
    counter += 1

if espresso_machine_unit is None:
    logger.error(
        'Could not find {0} unit. Please change the name of your Espresso machine unit inside the code config.')
    sys.exit('Could not find espresso unit')

# now that we have the unit check if already turned on
if espresso_machine_unit.on:
    send_notification('Warning', 'Machine is already turned on.')
else:
    # turn it on
    espresso_machine_unit.on = True

logger.info('Machine is on...')
logger.info('Warm-up is {0} seconds.'.format(WARM_UP_TIME))

sleep_countdown(WARM_UP_TIME)
send_notification('Ready', 'The machine is ready. It will be turned off again in {0} seconds.'.format(TURN_OFF_TIME))
change_indicator_light_status(espresso_machine_light_indicator, 1)
sleep_countdown(TURN_OFF_TIME, blink_indicator_light=True, indicator=espresso_machine_light_indicator)

espresso_machine_unit.on = False
logger.debug('Machine off')
change_indicator_light_status(espresso_machine_light_indicator, 0)
