from prometheus_client import Gauge, Histogram


links_on_track_total = Gauge(
    "links_on_track_total",
    "Количество ссылок в БД, поставленных на мониторинг",
    ["tracked_source"],
)

request_duration_ms_total = Histogram(
    "request_duration_ms_total",
    "Время выполнения запроса в миллисекундах",
    ["scope", "scope_type"],
    buckets=(5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000),
)
