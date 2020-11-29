# PWS-15_e8_celery_nsq

## Доступен по адресу:
https://sf.rtru.tk/tasks

### Реализовано
- flask-приложение (webserver/app.py, webserver/db.py)
  - ввод адресов, на сайтах которых будет выполняться подсчет количества встречающихся слов 'python'
  - сохранение параметров Задачи в базу данных (класс Task)
  - передача Задачи подсчета "воркеру" через Celery
  - прием Результатов подсчета из топика очереди NSQ и занесение их в базу (класс Result); запускается отдельным тредом при старте flask
  - вывод Результатов подсчета прошлых запросов
  - примененные основные модули: Flask-SQLAlchemy + psycopg2, celery + redis, gnsq
- celery-воркер (worker/worker.py)
  - обработка очереди с Задачами, поступающими от flask-приложения
  - запрос страницы по адресу из Задачи и подсчет на ней количества слов 'python'
  - передача Результата работы в топик очереди NSQ с помощью requests по протоколу http
  - примененные модули: celery + redis, requests
- вспомогательные сервисы
  - Postgress
  - Redis
  - NSQ
- классы для баззы данных: Result ссылается на Task (см. ниже их структуру)
- обработка всевозможных ошибок
- развертывание всех сервисов и приложений через docker-compose

### Схема взаимодействия сервисов
```
app.py + db.py
  ├── second-thread ─ gnsq-consumer ←─────┐
  │                           ↓           │
  └── main-thread ─ Flask ⟷ Postgress     │
                     ↓                    │
                  Celery-Redis           NSQ
                     ↓                    ↑
worker.py ─── celery-worker ──────────────┘
```
### Классы для базы данных
```
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
```

### Установка
- скачать проект и перейти в директорию проекта
```
$ git clone https://github.com/LovingFox/PWS-15_e8_celery_nsq
$ cd PWS-15_e8_celery_nsq
```
- собрать контейнеры
```
$ docker-compose build
```
- запустить контейнеры
```
$ docker-compose up
```
### Использование
В браузере:

http://localhost:5000/tasks
