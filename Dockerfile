FROM alpine:latest

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
        rsyslog \
        dovecot-pgsql \
        runit

COPY service /etc/service
COPY usr/sbin/runit_bootstrap /usr/sbin/runit_bootstrap
COPY etc/rsyslog.conf /etc/rsyslog.conf
COPY etc/postfix/* /etc/postfix/

ENTRYPOINT ["/usr/sbin/runit_bootstrap"]
