FROM python:3.7
WORKDIR /app
COPY ./worker/worker.py /app
COPY ./webserver/app.py /app
COPY ./webserver/db.py /app
COPY ./webserver/templates/show_tasks.html /app/templates/
COPY ./webserver/requirements.txt /app/
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000
RUN pip install -r requirements.txt
CMD ["flask", "run"]
