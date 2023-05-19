FROM python:3.10.7-alpine3.16

ADD requirements.txt /

RUN pip install -r requirements.txt && \
    rm requirements.txt

ADD helpers.py main.py /

CMD [ "python", "./main.py" ]