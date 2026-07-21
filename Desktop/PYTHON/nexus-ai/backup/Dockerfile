FROM alpine:3.20

# postgresql-client provides pg_dump; mongodb-tools provides mongodump
RUN apk add --no-cache \
    postgresql16-client \
    mongodb-tools \
    bash \
    dcron \
    tzdata

# Non-root backup user
RUN addgroup -g 1001 backupgroup \
 && adduser  -u 1001 -G backupgroup -D -H backupuser

COPY --chown=backupuser:backupgroup entrypoint.sh /entrypoint.sh
COPY --chown=backupuser:backupgroup backup.sh     /backup.sh
RUN chmod +x /entrypoint.sh /backup.sh

# /backups is the volume mount point
RUN mkdir -p /backups && chown backupuser:backupgroup /backups

USER backupuser
ENTRYPOINT ["/entrypoint.sh"]
