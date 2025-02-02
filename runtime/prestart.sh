#!/usr/bin/env bash
# retry several times

retry() {
    local max_num_retries=$1
    shift
    local retry_wait_seconds=$1
    shift
    local description=$1
    shift
    command_to_run=("$@")
    # the command must exit with non-zero code on failure.

    # Usage example:
    #     retry 10 5 "alembic migrations" alembic upgrade head

    for ((i = 1; i <= $max_num_retries; i += 1)); do
        if [[ i -gt 1 ]]; then echo "RETRY ${i} ..."; fi
        echo "RUNNING $description ..."
        "${command_to_run[@]}" && echo "RUNNING $description SUCCESS" && break ||
            (
                echo "FAILED TO RUN $description ON ATTEMPT $i"
                if (($i == $max_num_retries)); then
                    echo >&2 "ERROR: FINALLY FAILED TO RUN $description."
                    exit 1
                else
                    echo "WAITING $retry_wait_seconds SECONDS BEFORE RETRYING $description"
                    sleep $retry_wait_seconds
                fi
            )
    done
}

# Run migrations if this is run as backend service.
_is_backend_service="${HD_IS_BACKEND_SERVICE,,}" # to lower case
if [[ "$_is_backend_service" != "false" && "$_is_backend_service" != "yes" && "$_is_backend_service" != "y" && "$_is_backend_service" != "ok" && "$_is_backend_service" != "1" ]]; then
    retry 10 5 "alembic migrations" alembic upgrade head
fi
