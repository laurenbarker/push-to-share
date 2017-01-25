import os
import csv
import logging

logger = logging.getLogger(__name__)


def get_data():
    """ Return dictionaries for each file in the data dir
    """
    data = {}
    for filename in os.listdir('data'):
        with open(os.path.join(os.path.dirname((os.path.dirname(__file__))), 'data/') + filename, 'r') as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = list(reader)
            file_data = {row.pop(0): row for row in rows}
            file_data['headers'] = headers
            data[str(os.path.splitext(filename)[0])] = file_data
    return data
