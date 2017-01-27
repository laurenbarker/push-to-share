# push-to-share
Application to push metadata from a spreadsheet into [SHARE](https://github.com/CenterForOpenScience/SHARE) --  a free, open dataset of research (meta)data.

## Setup
Clone the push-to-share repository to your computer.

It is useful to set up a [virtual environment](http://virtualenvwrapper.readthedocs.io/en/latest/install.html) to ensure [python3](https://www.python.org/downloads/) is your designated version of python and make the python requirements specific to this project.

    mkvirtualenv share -p `which python3.5`
    workon share

Once in the `share` virtual environment, install the necessary requirements.

    pip install -r requirements.txt

Copy `cp sharepush/settings/source-dist.py` to `sharepush/settings/source.py`. 
NOTE: This is your local settings file, which overrides the settings in `sharepush/settings/base.py`. 
It will not be added to source control, so change it as you wish.

    $ cp sharepush/settings/source-dist.py sharepush/settings/source.py

## Add data
See `data/example-*.csv` for proper formatting.

In the data directory add `works.csv` and other relevant files. Currently supports:
* `works.csv`
* `contributors.csv`
* `funders.csv`
* `awards.csv`

*NOTE: the column headers and column names of the csv files must match the format of the example files. Excluding the first column (i.e., `work_id`), column order does not matter.* 

## Run
Run the following commands from the terminal to load data from the csv files and push the data to SHARE:

    $ python
    $ from sharepush.push import load_data
    $ load_data
    
If errors occur on submission, the graph of the work and the response will print to the terminal.

    
