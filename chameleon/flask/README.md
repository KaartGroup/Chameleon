# Manual Installation

## While in your virtual env and in the `flask` dir. 

### Start celery db instance:
celery -A web.celery worker -l info

### Start the flask app:
flask run 