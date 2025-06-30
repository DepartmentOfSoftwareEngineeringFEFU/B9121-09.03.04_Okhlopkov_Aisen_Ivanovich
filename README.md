# ВКР Охлопков Айсен Иванович

Тема: Поддержка принятия решения для построения маршрутов морских судов на акватории с ограниченными условиями движения
Научный руководитель: Иваненко Юрий Сергеевич
Группа: Б9121-09.03.04прогин

# Требования:
Python 3.11.5
Node v21.3.0

# Инструкция по деплою (bash):
Развернуть виртуальное окружение
```bash
python -m venv venv
```
Запустить виртуальное окружение
```bash
source venv/Scripts/activate
```
Загрузить зависимости python
```bash
pip install -r requirements.txt
```
Загрузить зависимости js
```bash
cd frontend
```
```bash
npm install
```

Инструкция по запуску (bash):
Запустить виртуальное окружение (если не запущено)
```bash
source venv/Scripts/activate
```
запускаем backend и Парсер
```bash
cd backend
```
```bash
python manage.py runserver
```
```bash
python manage.py parse_ais.py
```
Запускаем frontend
```bash
cd frontend
```
```bash
npm start
```
