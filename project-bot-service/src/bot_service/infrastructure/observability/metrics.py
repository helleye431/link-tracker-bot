from prometheus_client import Counter, Histogram

command_requests_total = Counter(
    "command_requests_total",
    "Суммарное количество обработанных команд",
    ["command"],
)

command_duration_ms_total = Histogram(
    "command_duration_ms_total",
    "Время обработки команды в миллисекундах",
    ["scope", "scope_type"],
    buckets=(5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000),
)

sent_notification_total = Counter(
    "sent_notification_total",
    "Количество отправленных уведомлений",
)
