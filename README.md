whirl
=====

A state-of-the-art Slack killer.

Install
-------
Requires: Python 3.4+, Tornado 4.3.

Create and activate a virtualenv:

    pyvenv venv
    source venv/bin/activate

Install dependencies:

    pip install -r requirements.txt

Create a configuration file from the sample:

    cp server.conf.example server.conf

Create a database and its tables:

    python models.py

Run & enjoy:

    python whirl.py
