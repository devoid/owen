"""
ibm.py - API into IBM Electronic Service Call Data
"""

import re
from BeautifulSoup import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys

from owen.driver.api import ServiceRequestDriver, ServiceRequestTicket
from owen.driver.api import ExtendedAction

def _fill_form(driver, data):
    "Helper function to fill form"
    for id,text in data.iteritems():
        el = driver.find_element_by_id(id)
        if not el:
            raise Execption("Element not found with id: {}".format(id))
        el.send_keys(text)

def _get_table(soup_table):
    headers = None
    rows = []
    for row in soup_table.findAll('tr'):
        if headers == None:
            headers = [ h.text for h in row.findAll('th') ]
        else:
            row = [ r.text for r in row.findAll('td') ]
            rows.append(dict(map(None, headers,row)))
    return rows

def _get_soup(driver):
    raw = unicode(driver.page_source).encode('utf-8')
    return BeautifulSoup(raw)


class ElectronicServiceRequest(ServiceReuqestDriver):
    """Class for managing initial interactions with ESC"""
    def __init__(self, username=None, password=None, driver=None):
        if not driver:
            driver = webdriver.Firefox()
        self.driver = driver
        self.username = username
        self.password = password
        # TODO(devoid): Make login a basic check?
        self._login()

    def _login(self):
        self.driver.get("https://www-930.ibm.com/support/esc/signin.jsp")
        _fill_form(self.driver, {'j_username' : self.username,
                                 'j_password' : self.password,})
        self.driver.find_element_by_name('ibm-submit').click()

    def _list_requests(self):
        self.driver.get("https://www-930.ibm.com/support/esc/"
                        "viewcalls.wss?view=selfreg")
        soup = _get_soup(self.driver)
        rows = _get_table(soup.find('table'))
        ticket_nums = [ row["IBM problem number"] for row in rows ]
        ticket_ids = []
        for el in self.driver.find_elements_by_name("count"):
            href = el.get_attribute('href') 
            match = re.match(".*callid=(.*)$", href)
            ticket_ids.append(match.group(1))
        assert len(ticket_nums) == len(ticket_ids) 
        return zip(ticket_ids, ticket_nums)

    def get_request(self, id):
        reqs = self._list_requests()
        for req_id, req_case in reqs:
            if id == req_id:
                return IBMServiceTicket(req_id, req_case, self.driver)
        return None

    def list_requests(self):
        "Returns a list of request objects."
        reqs = self._list_requests()
        tickets = []
        for req_id, req_case in reqs:
            tickets.append(IBMServiceTicket(req_id, req_case, self.driver))
        return tickets

    def _handle_after_hours_popup(self, form_win):
        # Find the popup window
        windows = self.driver.window_handles
        maybe_popup_windows = [ w for w in windows if w != form_win ]
        for window in maybe_popup_windows:
            self.driver.switch_to_window(window)
            complete = False
            try:
                el = self.driver.find_element_by_id("Status_TypeA")
                if not el:
                    continue
                el.click()
                self.driver.find_element_by_name("ibm-submit").click()
                complete = True
            except:
                pass
            if complete:
                break

    def create_request(self, product=None, model=None, serial=None, part=None,
                       comments = None):
        self.driver.get("https://www-930.ibm.com/support/esc/"
                        "placecall_upr.jsp")
        # TODO(devoid): default model is probably bad
        if not model:
            model = 'AC1'
        if re.match(".*AC1$",  product):
            product_id = product[:len(product)-3]

        # TODO(devoid): Make settings here configurable from ~/.ibm_esc
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
            "Product" : product,
            "Model" : model,
            "Serial_Number" : serial,
            "Comments" : comments, # limited to 150 char
        }
        if part:
            form_entries["Part_Number"] = part
        fill_form(self.driver, form_entries)
        # Before we submit, capture the current window handle
        form_window = self.driver.current_window_handle
        # Click submit button
        elem = self.driver.find_element_by_name("ibm-submit")
        elem.click()
        # There may be a popup for after-hours stuff
        self._handle_after_hours_popup(form_window)


class IBMServiceTicket(ServiceRequestTicket):
    """Class for dealing with a specific ticket"""
    def __init__(self, id, ticket, driver):
        self.id = id
        self.ticket = ticket
        self.driver = driver

    def details(self):
        self.driver.get("https://www-930.ibm.com/support/esc/"
                        "viewcalldetailtext.wss?callid=%s" % (self.id))
        return self.driver.find_element_by_tag_name("body").text

    def third_party_status(self):
        raise NotImplementedError()

    def case_number(self):
        return self.ticket

    def _submit_comment(self, comment):
        if len(comment) > 150:
            comment = comment[:149]
        _fill_form(self.driver, {'Comments' : comment })
        self.driver.find_element_by_name('ibm-submit').click()
        return True

    def _update_state(self, state, comment):
        self.driver.get("https://www-930.ibm.com/support/esc/"
                        "statusupdate.jsp?uniqcallid=%s&actionflag=%s"
                        "&ibmnum=%s" % (state, self.id, self.ticket))
        return self._submit_comment(comment)

    def add_info(self, comment):
        self.driver.get("https://www-930.ibm.com/support/esc/"
                        "additionalcomments.jsp?uniqcallid=%s&ibmnum=%s"
                        % (self.id, self.ticket))
        return self._submit_comment(comment)
    
    def cancel_request(self, comment):
        return self._update_state('CA', comment)

    def call_back_request(self, comment):
        return self._update_state('CB', comment)

