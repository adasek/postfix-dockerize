FROM alpine:3.21.5

RUN apk add --no-cache \
        bash \
        bind-tools \
        ca-certificates \
        dovecot \
        libsasl \
        mailx \
        postfix \
        postfix-policyd-spf-perl \
        postfix-pgsql \
        openssl \
        rsyslog \
        dovecot-pgsql \
        runit

COPY service /etc/service
COPY usr/sbin/runit_bootstrap /usr/sbin/runit_bootstrap
COPY etc/rsyslog.conf /etc/rsyslog.conf
COPY etc/postfix/* /etc/postfix/

RUN mkdir /var/mailstorage
RUN chown 5000:5000 /var/mailstorage
RUN openssl dhparam -out /etc/dovecot/dh.pem 4096

ENTRYPOINT ["/usr/sbin/runit_bootstrap"]
