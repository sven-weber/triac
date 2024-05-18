#!/usr/bin/env bash

# Read in the environment variables from /proc/1/environ
# (since systemd wont....)
# Code stolen from: https://unix.stackexchange.com/a/381138
for e in $(tr "\000" "\n" < /proc/1/environ); do
        eval "export $e"
done

# Start the actual postgres init script
/bin/bash -c "/usr/local/bin/docker-entrypoint.sh postgres"