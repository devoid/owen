"""
Service Request Driver API 

"""

class ExtendedAction(object):
    """Add command-line actions specific to a single driver."""
    pass

class ServiceRequestDriver(object):
    def list_requests(self):
        raise NotImplementedError()
    def get_request(self, id):
        raise NotImplementedError()
    def create_request(self, id):
        raise NotImplementedError()


class ServiceRequestTicket(object):
    def details(self):
        raise NotImplementedError()
    def third_party_status(self):
        raise NotImplementedError()
    def case_number(self):
        raise NotImplementedError()
    def close(self):
        raise NotImplementedError()
