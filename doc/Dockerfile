# API DOC配信用
FROM tiangolo/uwsgi-nginx-flask:python3.7

RUN mkdir -p /app
COPY . /app

RUN cp /app/server.conf /etc/nginx/conf.d/default.conf
RUN mkdir /root/logs
RUN cd /app && pip install -r requirements.txt && make html
RUN chmod 755 -R /root
RUN chmod 755 -R /app
EXPOSE 5005

CMD ["nginx"]