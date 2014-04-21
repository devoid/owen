""" server.py - Selenium Submission Server . """
import ConfigParser
import flask
import os
import re
import sys
import time

from selenium import webdriver

try:
    import OpenSSL
    _has_ssl = True
except ImportError:
    _has_ssl = False


def fill_form(driver, data):
    for id, text in data.iteritems():
        if text is None:
            text = ''
        el = driver.find_element_by_id(id)
        if not el:
            return
        el.send_keys(text)


def handle_after_hours_popup(driver, form_win):
    # Find the popup window
    done = False
    tries = 0
    while not done and tries < 2:
        maybe_popup_windows = [w for w in driver.window_handles if
                               w != form_win]
        for window in maybe_popup_windows:
            driver.switch_to_window(window)
            try:
                service_tomorrow = driver.find_element_by_id("Status_TypeA")
                service_tomorrow.click()
                driver.find_element_by_name("ibm-submit").click()
                done = True
            except Exception:
                pass
            if done:
                break
        time.sleep(1)
        tries += 1

app = flask.Flask(__name__)
defaults = {'host': '127.0.0.1',
            'port': 8080,
            'private-key-file': None,
            'certificate-file': None}


@app.route('/', methods=['POST'])
def submit_ticket():
    if flask.request.mimetype not in _json_mimes:
        flask.abort(400)
    data = flask.request.get_json(silent=True)
    if data.get('secret', '') != flask.current_app.secret:
        flask.abort(403)
    login_form_keys = ['j_username', 'j_password']
    submit_form_keys = ["Customer_Name", "CustPhoneNumber", "Street",
                        "City", "State", "Zip", "Contact_Location",
                        "ContactName", "ContPhoneNumber", "Product",
                        "Model", "Serial_Number", "Comments"]
    submit_form_optional = ["Part_Number", "Model"]
    login_form, submit_form = ({}, {})
    try:
        for key in login_form_keys:
            login_form[key] = data.get(key)
        for key in submit_form_keys:
            submit_form[key] = data.get(key)
    except KeyError:
        flask.abort(400)
    for key in submit_form_optional:
        try:
            submit_form[key] = data.get(key)
        except KeyError:
            pass

    product = submit_form['Product']
    if re.match(".*AC1$",  product):
        submit_form['Product'] = product[:len(product)-3]
    if not submit_form['Model']:
        submit_form['Model'] = 'AC1'

    # Get driver, login and fill out form
    driver = webdriver.Firefox()
    driver.get("https://www-930.ibm.com/support/esc/signin.jsp")
    fill_form(driver, login_form)
    driver.find_element_by_name('ibm-submit').click()
    driver.get("https://www-930.ibm.com/support/esc/placecall_upr.jsp")
    fill_form(driver, submit_form)
    # Before we submit, capture the current window handle
    form_window = driver.current_window_handle
    # Click submit button
    elem = driver.find_element_by_name("ibm-submit")
    elem.click()
    # There may be a popup for after-hours stuff
    handle_after_hours_popup(driver, form_window)
    time.sleep(8)
    driver.quit()
    response = flask.Response(None, status=200, mimetype='text/plain')
    return response


def main():
    usage = '%s owen.config' % sys.argv[0]
    if len(sys.argv) != 2:
        print >> sys.stderr, usage
        sys.exit()
    configfile = sys.argv[1]
    if not os.path.exists(configfile):
        print >> sys.stderr, "No file found at %s" % configfile
        sys.exit()
    config = ConfigParser.ConfigParser(defaults)
    config.read(configfile)

    # SSL Configuration
    ssl_context = None
    private_key_file = config.get('ssl', 'private-key-file', None)
    certificate_file = config.get('ssl', 'certificate-file', None)
    if _has_ssl and private_key_file and certificate_file:
        ssl_context = OpenSSL.SSL.Context(OpenSSL.SSL.SSLv23_METHOD)
        ssl_context.use_privatekey_file(private_key_file)
        ssl_context.use_certificate_file(certificate_file)
    with app.app_context():
        flask.current_app.secret = config.get('default', 'secret')
    host = config.get('default', 'host')
    port = config.getint('default', 'port')
    app.run(host=host, port=port,  debug=True, ssl_context=ssl_context)

_json_mimes = ['application/json']

if __name__ == '__main__':
    main()
