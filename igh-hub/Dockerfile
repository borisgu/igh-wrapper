FROM python:3.10.7-alpine3.16

ENV GROUP_ID=1000 \
    USER_ID=1000

WORKDIR /var/www/

ADD requirements.txt /var/www/

RUN pip install -r requirements.txt && \
    rm requirements.txt && \
    pip install gunicorn

RUN addgroup -g $GROUP_ID www && \
    adduser -D -u $USER_ID -G www www -s /bin/sh

USER www

ADD app.py helpers.py wsgi.py /var/www/

EXPOSE 5000

CMD [ "gunicorn", "-w", "5", "--bind", "0.0.0.0:5000", "wsgi"]
