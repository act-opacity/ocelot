broker_url = 'amqp://guest:guest@rabbitmq:5672'
result_backend = 'redis://redis:6379/0'
broker_heartbeat = 60
broker_heartbeat_checkrate = 2
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
enable_utc = True
worker_prefetch_multiplier = 1
task_acks_late = True

task_routes = { 
    "primary.*":{"queue":"primary_queue"},
    "download.*":{"queue":"download_queue"},
    "upload.*":{"queue":"upload_queue"},
    "uploads-fileparts.*":{"queue":"upload_queue_fileparts"},
    "metadata.*":{"queue":"metadata_queue"}}