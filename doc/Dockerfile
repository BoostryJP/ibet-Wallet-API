# API DOC配信用
FROM nginx

RUN mkdir -p /app
COPY . /app

RUN cp /app/server.conf /etc/nginx/conf.d/default.conf
RUN mkdir /root/logs
RUN chmod 755 -R /root
EXPOSE 5005

CMD ["nginx", "-g", "daemon off;"]