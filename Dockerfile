# Build Python 3.7 from source in first stage of build.
# Kopf requires Python 3.7, and we don't want all of the build junk still sitting around
# taking up space is our final image.
FROM centos:7 AS python-builder

USER root

RUN yum groupinstall -y "Development Tools" && \
    yum install -y gcc openssl-devel bzip2-devel libffi libffi-devel wget && \
    cd /root && \
    wget https://www.python.org/ftp/python/3.7.0/Python-3.7.0.tgz && \
    tar zxvf Python-3.7.0.tgz && \
    cd Python-3.7.0 && \
    ./configure --enable-optimizations && \
    make altinstall && \
    rm -f /root/Python-3.7.0.tgz

# Now we start our final image build.
FROM centos:7

USER root

# Copy the Python3.7 we just compiled/built from the previous stage.
COPY --from=python-builder /usr/local/lib/python3.7 /usr/local/lib/python3.7
COPY --from=python-builder /usr/local/bin/python3.7 /usr/local/bin/python3.7
COPY --from=python-builder /usr/local/bin/pip3.7 /usr/local/bin/pip3.7

COPY requirements.txt /tmp/requirements.txt

RUN pip3.7 install -r /tmp/requirements.txt && \
    rm -f /tmp/requirements.txt

COPY application /opt/application

RUN useradd service-user && \
    chown -R service-user:service-user /opt/application

WORKDIR /opt/application

USER service-user

CMD [ "kopf", "run", "main.py" ]
