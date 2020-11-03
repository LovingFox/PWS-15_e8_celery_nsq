from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import enum

db = SQLAlchemy()


class TaskStatus (enum.Enum):
    NOT_STARTED = 1
    PENDING = 2
    FINISHED = 3

# Класс с исходными данными (адрес сайта),
# статусом задачи и временем появления задачи
class Task(db.Model):
    __tablename__ = 'task'
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(300), unique=False, nullable=True)
    timestamp = db.Column(db.DateTime(), default=datetime.utcnow)
    task_status = db.Column(db.Enum(TaskStatus), default=TaskStatus.NOT_STARTED)


# Класс с результатами задачи класса Task
# код завершения, число вхождений слова, ошибки, если будут,
# и время завершения работы над задачей
class Result(db.Model):
    __tablename__ = 'result'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey(Task.id))
    task = db.relationship(Task, backref=db.backref('result', uselist=False))
    words_count = db.Column(db.Integer, unique=False, nullable=True)
    http_status_code = db.Column(db.Integer)
    error = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime(), default=datetime.utcnow)

    def __repr__(self):
        tmstmp = self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        delta = round((self.timestamp - self.task.timestamp).total_seconds())
        return f'Duration: {delta} sec ({tmstmp}), Status: {self.http_status_code}, Words: {self.words_count}' + \
                (f', Error: {self.error}' if self.error else '')


def add_task(site):
    '''
    Запись задачи, которая будет передана "воркеру"
    '''
    try:
        new_task = Task(address=site)
        db.session.add(new_task)
        db.session.commit()
    except SQLAlchemyError as e:
        return e, None
    else:
        return None, new_task


def task_pending(task):
    '''
    Просто выставление статуса PENDING для задачи
    '''
    try:
        task.task_status = TaskStatus.PENDING
        db.session.commit()
    except SQLAlchemyError as e:
        return e


def add_result(task_dict, do_finished=True):
    '''
    Добавление результатов обработки задачи
    и установка статуса задачи FINISHED
    Результаты в словаре
    '''
    try:
        new_result = Result(
                task_id=task_dict['id']
        )
        if 'error' in task_dict:
            new_result.error = task_dict['error']
        if 'words_count' in task_dict:
            new_result.words_count = task_dict['words_count']
        if 'http_status_code' in task_dict:
            new_result.http_status_code = task_dict['http_status_code']

        db.session.add(new_result)

        task = Task.query.get(task_dict['id'])
        if do_finished:
            task.task_status = TaskStatus.FINISHED

        db.session.commit()
    except (AttributeError, TypeError, KeyError, SQLAlchemyError) as e:
        return e
    else:
        return None


def get_tasks():
    '''
    Получить все задачи из базы
    '''
    try:
        tasks = Task.query.all()
    except SQLAlchemyError as e:
        return e, None
    else:
        return None, tasks


def init_db(app):
    '''
    Инициализация соединения к базе данных для Flask прилжения
    и создание структуры базы (если ее еще нет)
    '''
    db.init_app(app)
    try:
        with app.app_context():
            db.create_all()
    except SQLAlchemyError as e:
        return e
    else:
        return None
