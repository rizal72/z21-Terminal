#!/bin/sh
# Dump the database when the data has been quiet for QUIET_MINUTES, keep KEEP
# archives. The trigger is the data, not the clock: the WAL position only moves
# when something is written, so a paused session does not produce snapshots.
#
# Runs as the postgres user on the pi4 (peer auth on the local socket).
# Installed as /usr/local/bin/z21-pg-dump by the systemd timer.
set -eu

QUIET_MINUTES=${QUIET_MINUTES:-15}
SAMPLE_SECONDS=${SAMPLE_SECONDS:-300}
KEEP=${KEEP:-5}
DB=${DB:-z21}
OUT=${OUT:-/mnt/timecapsule/pg}
STATE=${STATE:-/var/lib/postgresql/z21-dump.state}
TMP=/dev/shm/z21-dump.$$

LSN=$(psql -X -tAq -d "$DB" -c 'select pg_current_wal_lsn()')

prev_lsn=""
quiet=0
dumped=""
if [ -f "$STATE" ]; then
    prev_lsn=$(sed -n 1p "$STATE")
    quiet=$(sed -n 2p "$STATE")
    dumped=$(sed -n 3p "$STATE")
fi

if [ "$LSN" = "$prev_lsn" ]; then
    quiet=$((quiet + 1))
else
    quiet=0
fi

save_state() {
    printf '%s\n%s\n%s\n' "$1" "$quiet" "$dumped" > "$STATE"
}

# Nothing written since the last stored dump: nothing to save.
if [ "$LSN" = "$dumped" ]; then
    save_state "$LSN"
    exit 0
fi

# Still recent activity: wait for the next sample.
if [ "$quiet" -lt $((QUIET_MINUTES * 60 / SAMPLE_SECONDS)) ]; then
    save_state "$LSN"
    exit 0
fi

pg_dump -Fc -d "$DB" -f "$TMP"
# Refuse to store an archive that cannot be listed.
pg_restore -l "$TMP" > /dev/null

new_sum=$(sha256sum "$TMP" | cut -d' ' -f1)
newest=$(ls -1t "$OUT"/z21-*.dump 2>/dev/null | head -1 || true)
if [ -n "$newest" ] && [ "$(sha256sum "$newest" | cut -d' ' -f1)" = "$new_sum" ]; then
    rm -f "$TMP"
    dumped=$LSN
    save_state "$LSN"
    exit 0
fi

mv "$TMP" "$OUT/z21-$(date +%Y%m%d-%H%M%S).dump"
dumped=$LSN
save_state "$LSN"

# Prune after the new archive is stored and listed, oldest first, never touching
# the newest one. set -- expands the glob once, so a name with spaces is not split.
set -- "$OUT"/z21-*.dump
[ -e "$1" ] || exit 0
ls -1t "$@" | tail -n +$((KEEP + 1)) | while IFS= read -r old; do
    rm -f -- "$old"
done
