import os
import csv
import logging

logger = logging.getLogger(__name__)


def get_data():
    """ Return dictionaries for each file in the data dir
    """
    data = {}
    for filename in os.listdir('data'):
        if not filename.startswith('.'):
            with open(os.path.join(os.path.dirname((os.path.dirname(__file__))), 'data/') + filename, 'r') as f:
                reader = csv.reader(f)
                headers = next(reader)
                rows = list(reader)

                # map the headers onto each row
                row_map = {row.pop(0): dict(zip(headers, row)) for row in rows}
                data[str(os.path.splitext(filename)[0])] = row_map
    return data
