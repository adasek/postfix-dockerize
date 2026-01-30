# kubernetes-postfix

Postgres and dovecot in the single container

 * **Single instance** only (not synchronizing with a backup server)
 * With postgres backend

## Build
```bashc
docker build --tag=postfix:0.0.1  .
```

## Env variables
 * MYDOMAIN - The internet domain name of this mail system. 
 * MYORIGIN -The domain name that locally-posted mail appears to come from
 * MYHOSTNAME - should resolve to the IP of your mailserver. In general that's the Kubernetes worker node the Postfix container runs on
 * PGHOST 
 * PGPORT - defaults to 5432
 * PGUSER
 * PGPASS
 * PGDATABASE
 * SMTPD_TLS_CERT_FILE - mount from host filesystem; e.g. /etc/letsencrypt/live/example.org/fullchain.pem
 * SMTPD_TLS_KEY_FILE - mount from host filesystem; e.g. /etc/letsencrypt/live/example.org/privkey.pem
 * DOVECOT_DH_FILE - generated once with `openssl dhparam -out dhparam/dh4096.pem 4096` e.g. /etc/dh4096.pem
 * SMTPD_TLS_DH1024_PARAM_FILE - generated once with `openssl dhparam -out dhparam/dh2048.pem 2048` e.g. /etc/dh2048.pem
 * SMTPD_TLS_DH512_PARAM_FILE - generated once with `openssl dhparam -out dhparam/dh512.pem 512` e.g. /etc/dh512.pem
 * MESSAGE_SIZE_LIMIT - in bytes, default value 20480000 for 20MB
 * VIRTUAL_MAILBOX_BASE - mount from host filesystem, actual mail storage
 * VIRTUAL_MAILBOX_LIMIT - Limit on the size of virtual mailbox files. In bytes, default value 512000000 for 480MB

### Architecture
Integration via docker-compose with
 * postgresql (used as a database)
 * postfixadmin

Postfixadmin provides an official docker container and runs a migrations on database first time running.

### INSTALLATION
#### Set postfixadmin password
For the first run it is needed to:
 * Run containers (via `docker-compose up`)
 * Access the postfixadmin /setup.php and generate a setup_password hash
   * `http://localhost:8181/setup.php` - enter some string twice and hit [Generate setup_password_hash]
   * a `$CONF['setup_password'] = '$2y$10$somelonghashDO/X9Plg/longlonghash';` line appears
 * Add the generated setup password to the config.local.php inside the container:
   * `docker exec -it postfixadmin bash`
     * `sed -e 's/changeme/$2y$10$somelonghashDO\/pleaseescapebackslashes/' config.local.php > /tmp/a; mv /tmp/a config.local.php` 
     * Note that the forward slashes inside sed subsitution string must be **escaped**!
 * Use this password to add an admin email to the database
   * Visit `http://localhost:8181/setup.php`
   * Enter admin login+password in **Add Superadmin Account**, hit [Add Admin]
Entered credentials should be written into the permanent volume of the database.

#### Create your domain and accounts
You may login to postfixadmin in `http://localhost:8181/`
     
#### IPV6 - open ports in firewall
Docker handles iptables rules for ipv4 for open ports, but it doesn't do the same for ipv6.
If using ubuntu in a host system, you may run this to expose the ports in both ipv4 and ipv6:
```bash
sudo ufw allow 993/tcp
sudo ufw allow 587/tcp
sudo ufw allow 465/tcp
sudo ufw allow 25/tcp
```

### Upgrading
If you are upgrading postgres container use:

##### 1. Dump from old postgres container
```bash
docker exec -t postfix-dockerize-postgresql pg_dumpall -U mail > pg_backup.sql
```
##### 2. Stop and destroy old postgres container
```bash
docker-compose down
docker rm postfix-dockerize-postgresql
```
##### 3. Edit docker-compose.yml
```yml
services:
 postgresql:
   image: postgres:18
   volumes:
     - /root/mail/postgresql18-data:/var/lib/postgresql
```
Note the mountpoint was /var/lib/postgresql/data for postgres17 and bellow.
#### 4. Run the new container and import
```bash
docker-compose up postgresql
docker exec -i postfix-dockerize-postgresql psql -U mail < pg_backup.sql
```


### Testing
Using Python / Pytest with dependencies managed by Poetry.

```bash
poetry install
poetry run pytest
```
Restart / clean the containers
```bash
docker-compose -f tests/docker-compose.test.yml down
sudo snap restart docker
```

For debug, you may show logs when you're running the tests
```bash
docker-compose -f tests/docker-compose.test.yml logs -f
```




### Derived from 
 * [github.com/githubixx/kubernetes-postfix](https://github.com/githubixx/kubernetes-postfix)
 * Blogpost: [Run a Postfix mail server with TLS and SPF in Kubernetes](https://www.tauceti.blog/post/run-postfix-in-kubernetes/).


### Other links 
 * [Postfix PostgreSQL Howto](http://www.postfix.org/PGSQL_README.html)
 * [Postfix-Dovecot-Postgresql-Example](https://github.com/postfixadmin/postfixadmin/blob/master/DOCUMENTS/Postfix-Dovecot-Postgresql-Example.md)
 * [serverfault: Using ENV variables in Postfix and Dovecot configuration files](https://serverfault.com/questions/1042635/using-env-variables-in-postfix-and-dovecot-configuration-files)
