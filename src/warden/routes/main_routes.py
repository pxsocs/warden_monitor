import os
from decorators import MWT
from flask import (Blueprint, redirect, render_template, abort, flash, session,
                   request, current_app, url_for)
from flask_login import login_user, logout_user, current_user, login_required
import jinja2
from utils import pickle_it
from datetime import datetime

warden = Blueprint("warden", __name__)

# Minimum TemplateData used for render_template in all routes
# This ensures FX and current_app are sent to the render page
# at all times
templateData = {
    "title": "WARden Monitor",
    "FX": current_app.settings['PORTFOLIO']['base_fx'],
    "current_app": current_app,
}


# Main page for WARden
@warden.route("/", methods=['GET'])
@warden.route("/warden_monitor", methods=['GET'])
def main_page():
    templateData['title'] = "WARden Node Monitor"
    templateData['servers'] = pickle_it('load', 'mps_server_status.pkl')
    return (render_template('warden/warden_monitor.html', **templateData))


# GreyScale Template Sample renderer
@warden.route("/gstemplate", methods=['GET'])
def gstemplate():
    return (render_template('warden/gray_scale_template.html', **templateData))


# -------------------------------------------------
#  START JINJA 2 Filters
# -------------------------------------------------
# Jinja2 filter to format time to a nice string
# Formating function, takes self +
# number of decimal places + a divisor


@jinja2.contextfilter
@warden.app_template_filter()
def jformat(context, n, places, divisor=1):
    if n is None:
        return "-"
    else:
        try:
            n = float(n)
            n = n / divisor
            if n == 0:
                return "-"
        except ValueError:
            return "-"
        except TypeError:
            return (n)
        try:
            form_string = "{0:,.{prec}f}".format(n, prec=places)
            return form_string
        except (ValueError, KeyError):
            return "-"


# Jinja filter - epoch to time string
@jinja2.contextfilter
@warden.app_template_filter()
def epoch(context, epoch):
    time_r = datetime.fromtimestamp(epoch).strftime("%m-%d-%Y (%H:%M)")
    return time_r


# Jinja filter - fx details
@jinja2.contextfilter
@warden.app_template_filter()
def fxsymbol(context, fx, output='symbol'):
    # Gets an FX 3 letter symbol and returns the HTML symbol
    # Sample outputs are:
    # "EUR": {
    # "symbol": "",
    # "name": "Euro",
    # "symbol_native": "",
    # "decimal_digits": 2,
    # "rounding": 0,
    # "code": "EUR",
    # "name_plural": "euros"
    try:
        from utils import current_path
        filename = os.path.join(current_path(),
                                'static/json_files/currency.json')
        with open(filename) as fx_json:
            fx_list = json.load(fx_json, encoding='utf-8')
        out = fx_list[fx][output]
    except Exception:
        out = fx
    return (out)


@jinja2.contextfilter
@warden.app_template_filter()
def jencode(context, url):
    return urllib.parse.quote_plus(url)


# Jinja filter - time to time_ago
@jinja2.contextfilter
@warden.app_template_filter()
def time_ago(context, time=False):
    if type(time) is str:
        try:
            time = int(time)
        except TypeError:
            return time
        except ValueError:
            try:
                # Try different parser
                time = datetime.strptime(time, '%m-%d-%Y (%H:%M)')
            except Exception:
                return time
    now = datetime.utcnow()
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time, datetime):
        diff = now - time
    elif not time:
        diff = now - now
    else:
        return ("")
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ""

    if day_diff == 0:
        if second_diff < 10:
            return "Just Now"
        if second_diff < 60:
            return str(int(second_diff)) + " seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return str(int(second_diff / 60)) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str(int(second_diff / 3600)) + " hours ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(int(day_diff)) + " days ago"
    if day_diff < 31:
        return str(int(day_diff / 7)) + " weeks ago"
    if day_diff < 365:
        return str(int(day_diff / 30)) + " months ago"
    return str(int(day_diff / 365)) + " years ago"


# END WARDEN ROUTES ----------------------------------------
