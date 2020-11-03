import os
import sys
import multiprocessing
import signal
import gnsq
import json
import logging
from flask import Flask, request, flash, render_template
from db import init_db, add_task, get_tasks, task_pending, add_result
from worker import count_words

SQLALCHEMY_DATABASE_URI=os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///test.db')
NSQ_HTTP_HOST=os.getenv('NSQ_HTTP_HOST', 'localhost')
NSQ_HTTP_PORT=os.getenv('NSQ_HTTP_PORT', 4150)
NSQ_TOPIC=os.getenv('NSQ_TOPIC', 'counter')

app = Flask(__name__)
app.logger.setLevel(logging.INFO)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'super secret key')
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# создаем подписчика NSQ, он будет запущен далее в параллельном процессе
# подписчик будет читать из тописка результаты работы "воркера" и писать их в базу
consumer = gnsq.Consumer(NSQ_TOPIC, 'channel', f'{NSQ_HTTP_HOST}:{NSQ_HTTP_PORT}')


@app.route('/tasks', methods = ['GET', 'POST'])
def tasks():
    '''
    Вывод всех результатов задач подсчета слов на сайтах (GET)
    Обработчик запросов адресов (POST) и так же вывод всех реультатов 
    '''
    if request.method == 'POST':
        if not request.form['address']:
            flash('Please enter Site')
        else:
            # пишем в базу данные поступившей задачи
            err, new_task = add_task(request.form['address'])
            if err:
                flash(str(err))
            else:
                task_dict = {
                        'id': new_task.id,
                        'address': new_task.address
                }
                # передача задачи через Celery по подсчету слов на сайте по введенному адресу
                # могут быть исключения, например, недоступен Redis у Celery 
                try:
                    count_words.delay(task_dict)
                except Exception as e:
                    task_dict['error'] = str(e)
                    flash(task_dict['error'])
                    # в случае исключения при передачи задачи,
                    # пишем в базу результат с ошибкой, но БЕЗ статуса "завершено"
                    err = add_result(task_dict, do_finished=False)
                    if err:
                        flash(str(err))
                else:
                    # если задача передалась, то помечаем ее, как "ожидание результата"
                    err = task_pending(new_task)
                    if err:
                        flash(str(err))

    err, tasks = get_tasks()
    if err:
        flash(str(err))
        tasks = []
    return render_template('show_tasks.html', tasks = tasks)


@consumer.on_message.connect
def handler(consumer, message):
    '''
    Обработчик очереди с результатами подсчета слов
    '''
    try:
        task_dict = json.loads(message.body)
        app.logger.info(f'NSQ: {task_dict}')
    except (TypeError, json.JSONDecodeError) as e:
        app.logger.error(f'NSQ: {e}')
    else:
        with app.app_context():
            # пишем результат подсчета в базу
            err = add_result(task_dict)
            if err:
                app.logger.error(f'NSQ: {err}')


def start_consumer():
    '''
    Функция, стартующая подписчика на топик в NSQ
    '''
    app.logger.info('Starting NSQ consumer...')
    consumer.start()


@app.before_first_request
def startup():
    '''
    С первым запросом к серверу стартуем базу данных (init_db),
    а так же параллельный процесс (proc) для записи результатов задач
    '''
    err = init_db(app)
    if err:
        app.logger.error(f'DB: {err}')
        sys.exit(1)
    app.logger.info('DB: connected')
    proc.start()


def signal_handler(sig, frame):
    '''
    Обрабатываем сигнал остановки приложения,
    что бы завершить процесс с подписчиком на топик в NSQ
    '''
    app.logger.warning('Exit via Ctrl+C')
    if proc.is_alive():
        proc.terminate()
    sys.exit(0)


# Стартуем процесс с подписчиком на топик в NSQ и ловим 'Ctrl+C'
proc = multiprocessing.Process(target=start_consumer)
signal.signal(signal.SIGINT, signal_handler)


if __name__ == '__main__':
    app.run()


