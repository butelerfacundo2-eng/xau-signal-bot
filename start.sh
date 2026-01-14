gunicorn -w 1 -b 0.0.0.0:$PORT signal_bot:app
