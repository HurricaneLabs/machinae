FROM python:3

RUN pip3 install machinae

#make sure you have a machinae.yml file to build with
COPY machinae.yml /etc

ENTRYPOINT ["/usr/local/bin/machinae"]
