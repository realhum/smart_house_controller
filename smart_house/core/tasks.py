from __future__ import absolute_import, unicode_literals
from celery import task
import requests
from django.forms.models import model_to_dict
from .models import Setting
from coursera_house.settings import SMART_HOME_ACCESS_TOKEN, SMART_HOME_API_URL
from .views import get_controller_values, post_controller_values
from django.core.mail import send_mail


def save_values(data):
    for control in data:
        sett = Setting.objects.filter(controller_name=control['name'])
        sett.update(value=control['value'])


def create_settings():
    headers = {'Authorization': f'Bearer {SMART_HOME_ACCESS_TOKEN}'}
    res = requests.get(SMART_HOME_API_URL, headers=headers)
    data = res.json()['data']
    for control in data:
        sett = Setting.objects.create(controller_name=control['name'],
                                      label=control['name'],
                                      value=control['value'])
        sett.save()


@task()
def smart_home_manager():
    data_get, code = get_controller_values()
    sett = dict()
    for controller in {'bedroom_target_temperature',
                       'hot_water_target_temperature'}:
        setting = Setting.objects.get(controller_name=controller)
        sett[controller] = model_to_dict(setting)['value']
    data = data_get.copy()
    if data['leak_detector']:
        data['cold_water'] = False
        data['hot_water'] = False
        send_mail(
            'Subject here',
            'Here is the message.',
            'from@me.com',
            ['EMAIL_RECEPIENT']
        )
    if not data['cold_water']:
        data['boiler'] = False
        data['washing_machine'] = 'off' if \
            data['washing_machine'] != 'broken' else 'broken'
    if data['smoke_detector']:
        data['air_conditioner'] = False
        data['bedroom_light'] = False
        data['bathroom_light'] = False
        data['boiler'] = False
        data['washing_machine'] = 'off' if \
            data['washing_machine'] != 'broken' else 'broken'
    if not data['smoke_detector']:
        if data['boiler_temperature'] < (0.9 *
                                         sett['hot_water_target_temperature']):
            if data['cold_water']:
                data['boiler'] = True
        elif data['boiler_temperature'] > (1.1 *
                                           sett['hot_water_target_temperature']):
            data['boiler'] = False
    if data['curtains'] != 'slightly_open':
        if data['outdoor_light'] < 50 and not data['bedroom_light'] and \
                not data['smoke_detector']:
            data['curtains'] = 'open'
        elif data['outdoor_light'] > 50 or data['bedroom_light']:
            data['curtains'] = 'close'
    if not data['smoke_detector']:
        if data['bedroom_temperature'] >= (1.1 *
                                           sett['bedroom_target_temperature']):
            data['air_conditioner'] = True
        elif data['bedroom_temperature'] <= (0.9 *
                                             sett['bedroom_target_temperature']):
            data['air_conditioner'] = False
    if data != data_get:
        controllers = {'controllers': []}
        for controller in data:
            controllers['controllers'].append({
                'name': controller,
                'value': data[controller]
            })
        post_controller_values(controllers)
