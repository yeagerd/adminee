import datetime

class EmailContact:
    def __init__(self):
        self.last_seen = datetime.datetime.now()

    def some_method(self):
        now = datetime.datetime.now(datetime.UTC)

    def other_method(self):
        days_since_last_seen = (datetime.datetime.now(datetime.UTC) - self.last_seen).days
