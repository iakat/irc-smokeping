FROM python:3-alpine
WORKDIR /app
COPY requirements.txt /app
RUN pip3 --no-cache-dir install -r requirements.txt
COPY . /app
CMD ["python3", "app.py"]
