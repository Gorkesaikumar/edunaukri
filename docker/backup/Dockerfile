FROM postgres:16-alpine

# Install bash, tar, gzip, tzdata, and file/find utilities for robust archiving and test restores
RUN apk add --no-cache bash tar gzip tzdata findutils coreutils

WORKDIR /app

# Copy backup scripts and crontab schedule
COPY docker/backup/ /app/docker/backup/
RUN chmod +x /app/docker/backup/*.sh

# Create required backup directories and log storage
RUN mkdir -p /backups/daily /backups/weekly /backups/logs

# Register cron schedule with Alpine crond
RUN crontab /app/docker/backup/crontab

# Run crond in foreground (-f) with log level 8 (-l 8 outputs executed jobs cleanly)
CMD ["crond", "-f", "-l", "8"]
