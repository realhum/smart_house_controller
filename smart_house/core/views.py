import json
import requests
from django.http import HttpResponse
from django.views import View
from django.forms.models import model_to_dict
from django.shortcuts import render, redirect
from .models import Setting
from .form import ControllerForm
from coursera_house.settings import SMART_HOME_ACCESS_TOKEN, SMART_HOME_API_URL


def get_controller_values():
    headers = {'Authorization': f'Bearer {SMART_HOME_ACCESS_TOKEN}'}
    resp = requests.get(SMART_HOME_API_URL, headers=headers)
    try:
        data = resp.json()['data']
    except json.JSONDecodeError:
        return {}, 502
    sett_dict = dict()
    if resp.status_code != 200:
        return sett_dict, resp.status_code
    for control in data:
        sett_dict[control['name']] = control['value']
    return sett_dict, resp.status_code


def post_controller_values(data):
    headers = {'Authorization': f'Bearer {SMART_HOME_ACCESS_TOKEN}'}
    resp = requests.post(SMART_HOME_API_URL, json=data, headers=headers)
    print(resp.json())
    return resp.status_code


class ControllerView(View):

    def get(self, request):
        data, code = get_controller_values()
        if code != 200:
            return HttpResponse(status=502)
        for controller in {'bedroom_light',
                           'bathroom_light'}:
            setting = Setting.objects.filter(controller_name=controller)
            setting.update(value=data[controller])
        settings = dict()
        for controller in {'bedroom_target_temperature',
                           'hot_water_target_temperature'}:
            setting = Setting.objects.get(controller_name=controller)
            settings[controller] = model_to_dict(setting)['value']
        form = ControllerForm(initial={
            'bedroom_light': data['bedroom_light'],
            'bathroom_light': data['bathroom_light'],
            'bedroom_target_temperature': settings[
                'bedroom_target_temperature'],
            'hot_water_target_temperature': settings[
                'hot_water_target_temperature']
        })
        return render(request, 'core/control.html', {'form': form,
                                                     'data': data})

    def post(self, request):
        form = ControllerForm(request.POST)
        if form.is_valid():
            context = form.cleaned_data
            for controller in {'bedroom_target_temperature',
                               'hot_water_target_temperature'}:
                settings = Setting.objects.filter(controller_name=controller)
                settings.update(value=context[controller])
            sett = dict()
            for controller in {'bedroom_light',
                               'bathroom_light'}:
                setting = Setting.objects.get(controller_name=controller)
                sett[controller] = model_to_dict(setting)['value']
            controllers = {'controllers': []}
            for controller in {'bedroom_light',
                               'bathroom_light'}:
                controllers['controllers'].append({
                    'name': controller,
                    'value': context[controller]
                })
            if context['bedroom_light'] != sett['bedroom_light'] or \
                    context['bathroom_light'] != sett['bathroom_light']:
                code = post_controller_values(controllers)
                if code != 200:
                    HttpResponse(status=502)
            return redirect('/')
        else:
            return HttpResponse(status=400)

