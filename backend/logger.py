import queue

log_queues = {}

def send_log(client_id, msg):
    """Prints to Docker terminal AND streams to React frontend."""
    print(msg, flush=True)  # flush=True forces it to print immediately
    if client_id and client_id in log_queues:
        log_queues[client_id].put(msg)