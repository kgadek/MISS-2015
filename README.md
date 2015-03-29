Preparation
===========

If you want to have sandbox, call:

    virtualenv --no-site-packages -p $(which python3.4) env
    . ./env/bin/activate

Install bottle.py:

    pip install bottle

And that's all.

Usage
=====

Start server:

    python backend.py

Create game:

    curl localhost:8080/new/50/80/44

Make a step:

    curl localhost:8080/step

And another:

    curl localhost:8080/step

…and so on.
