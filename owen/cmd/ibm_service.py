#!/usr/bin/env python
import argparse
import ConfigParser
import code
import re
import sys

from selenium import webdriver
from selenium.webdriver.common.keys import Keys

CONF_FILE = '/root/.owen'
CONF = ConfigParser.RawConfigParser()
CONF.read(CONF_FILE)

def fill_form(driver, data):
    for id,text in data.iteritems():
        el = driver.find_element_by_id(id)
        if not el:
            raise Execption("Element not found with id: {}".format(id))
        el.send_keys(text)

def handle_after_hours_popup(driver, form_win):
    # Find the popup window
    maybe_popup_windows = [ w for w in driver.window_handles if w != form_win ]
    for window in maybe_popup_windows:
        driver.switch_to_window(window)
        done = False
        try:
            service_tomorrow = driver.find_element_by_id("Status_TypeA")
            service_tomorrow.click()
            driver.find_element_by_name("ibm-submit").click()
            done = True
        except Exception:
            pass
        if done:
            break

def submit_ticket(args):
    product_id = args.product
    model_id = args.model
    serial = args.serial
    part = args.part
    comments = args.comment
    if re.match(".*AC1$",  product_id):
        product_id = product_id[:len(product_id)-3]

    # Get driver, login and fill out form
    driver = webdriver.Firefox()
    driver.get("https://www-930.ibm.com/support/esc/signin.jsp")
    fill_form(
        driver,
        {'j_username' : CONF.get('IBM', 'username'),
         'j_password' : CONF.get('IBM', 'password')})
    driver.find_element_by_name('ibm-submit').click()
    driver.get("https://www-930.ibm.com/support/esc/placecall_upr.jsp")
    form_entries = {
        "Customer_Name" : "Argonne Nat. Lab",
        "CustPhoneNumber" : "6302522000",
        "Street" : "9700 S. Cass Ave",
        "City" : "Argonne",
        "State" : "Illinois",
        "Zip" : "60439",
        "Contact_Location" : "Bldg. 240",
        "ContactName" : "Scott Devoid",
        "ContPhoneNumber" : "6302521105",
        "Product" : product_id,
        "Model" : model_id,
        "Serial_Number" : serial,
        "Comments" : comments, # limited to 150 char
    }
    if part:
        form_entries["Part_Number"] = part
    fill_form(driver, form_entries)
    # Before we submit, capture the current window handle
    form_window = driver.current_window_handle
    # Click submit button
    elem = driver.find_element_by_name("ibm-submit")
    elem.click()
    # There may be a popup for after-hours stuff
    handle_after_hours_popup(driver, form_window)
    driver.quit()


def main():
    args = sys.argv[1:]
    desc = "Create ticket with IBM Electronic Service Call"
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('--product', type=str, required=True,
        help="Product model number")
    parser.add_argument('--model', type=str, default="AC1",
        help="Product revision code, e.g. AC1")
    parser.add_argument('--serial', type=str, required=True,
        help="Product serial number")
    parser.add_argument("--part", type=str,
        help="Part FRU number")
    parser.add_argument("--comment", type=str, required=True,
        help="Description to give IBM.")
    options = parser.parse_args(args)
    submit_ticket(options)


if __name__ == '__main__':
    main()
