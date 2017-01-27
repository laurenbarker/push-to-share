# push-to-share
## Installation
### Mac OS X

* Clone the push-to-share repository to your computer. 
* Change to that folder before running the commands below.
* Create and activate your virtualenv.
```
virtualenv env
source env/bin/activate
```
Copy `cp sharepush/settings/source-dist.py` to `sharepush/settings/source.py`. 
NOTE: This is your local settings file, which overrides the settings in `sharepush/settings/base.py`. 
It will not be added to source control, so change it as you wish.

```
$ cp sharepush/settings/source-dist.py sharepush/settings/source.py
```
