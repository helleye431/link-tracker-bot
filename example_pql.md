# LinkTracker Dashboard: PromQL-запросы

## Общая информация

В этом файле приведён набор PromQL-запросов, на основе которых построены панели Grafana dashboard для проекта **LinkTracker**.

### Grafana variable

```text
$app = bot|scrapper
```

### Prometheus datasource

```text
uid: prometheus
```

### Используемые сервисы

```text
bot
scrapper
```

---

# Bot Service

## 1. Количество пользовательских сообщений в секунду

Показывает скорость обработки пользовательских сообщений ботом.
Метрика рассчитывается через `rate` по счётчику `command_requests_total`.

```promql
sum(rate(command_requests_total{job=~"$app"}[$__rate_interval]))
```

---

## 2. Количество запросов к боту в Telegram по командам

Показывает количество Telegram-запросов к боту за выбранный диапазон времени с группировкой по команде.

```promql
sum by (command) (
  increase(command_requests_total{job=~"$app"}[$__range])
)
```

---

## 3. Количество отправленных уведомлений

Показывает общее количество уведомлений, успешно отправленных ботом за выбранный диапазон времени.

```promql
sum(
  increase(sent_notification_total{job=~"$app"}[$__range])
)
```

---

## 4. Перцентили времени обработки команды

Показывает 50-й, 95-й и 99-й перцентили времени обработки одной команды ботом.
Используется histogram-метрика `command_duration_ms_total_bucket`.

### p50

```promql
histogram_quantile(
  0.50,
  sum by (le) (
    rate(command_duration_ms_total_bucket{job=~"$app"}[$__rate_interval])
  )
)
```

### p95

```promql
histogram_quantile(
  0.95,
  sum by (le) (
    rate(command_duration_ms_total_bucket{job=~"$app"}[$__rate_interval])
  )
)
```

### p99

```promql
histogram_quantile(
  0.99,
  sum by (le) (
    rate(command_duration_ms_total_bucket{job=~"$app"}[$__rate_interval])
  )
)
```

---

## 5. Использование памяти Bot

Показывает потребление памяти сервисом `bot`.

Используются две метрики:

* `process_resident_memory_bytes` — фактически используемая RAM;
* `process_virtual_memory_bytes` — виртуальная память процесса.

### Resident memory, MB

```promql
(
  (process_resident_memory_bytes{job="bot"} / 1024 / 1024)
  and on(job, instance)
  up{job=~"$app"}
)
```

### Virtual memory, MB

```promql
(
  (process_virtual_memory_bytes{job="bot"} / 1024 / 1024)
  and on(job, instance)
  up{job=~"$app"}
)
```

---

## 6. Bot RED: частота запросов

Показывает количество HTTP-запросов к сервису `bot` в секунду.

```promql
sum(
  rate(requests_total{job=~"$app", app_name="bot"}[$__rate_interval])
)
```

---

## 7. Bot RED: частота ошибок

Показывает количество HTTP-ответов сервиса `bot` со статусами `5xx` в секунду.

```promql
sum(
  rate(requests_total{
    job=~"$app",
    app_name="bot",
    status_code=~"5.."
  }[$__rate_interval])
)
```

---

## 8. Bot RED: p95 длительности запросов

Показывает 95-й перцентиль времени обработки HTTP-запросов сервисом `bot`.

Значение умножается на `1000`, чтобы перевести секунды в миллисекунды.

```promql
histogram_quantile(
  0.95,
  sum by (le) (
    rate(request_processing_time_bucket{
      job=~"$app",
      app_name="bot"
    }[$__rate_interval])
  )
) * 1000
```

---

# Scrapper Service

## 9. Количество активных ссылок по доменам

Показывает количество активных ссылок в БД, поставленных на мониторинг, по источникам `github` и `stackoverflow`.

```promql
links_on_track_total{
  job=~"$app",
  tracked_source=~"github|stackoverflow"
}
```

---

## 10. Перцентили времени scrape-операций по источникам

Показывает 50-й, 95-й и 99-й перцентили времени одной scrape-операции по внешнему источнику.

Используются источники:

```text
github
stackoverflow
```

### p50

```promql
histogram_quantile(
  0.50,
  sum by (le, scope_type) (
    rate(request_duration_ms_total_bucket{
      job=~"$app",
      scope="external_source",
      scope_type=~"github|stackoverflow"
    }[$__rate_interval])
  )
)
```

### p95

```promql
histogram_quantile(
  0.95,
  sum by (le, scope_type) (
    rate(request_duration_ms_total_bucket{
      job=~"$app",
      scope="external_source",
      scope_type=~"github|stackoverflow"
    }[$__rate_interval])
  )
)
```

### p99

```promql
histogram_quantile(
  0.99,
  sum by (le, scope_type) (
    rate(request_duration_ms_total_bucket{
      job=~"$app",
      scope="external_source",
      scope_type=~"github|stackoverflow"
    }[$__rate_interval])
  )
)
```

---

## 11. Использование памяти Scrapper

Показывает потребление памяти сервисом `scrapper`.

Используются две метрики:

* `process_resident_memory_bytes` — фактически используемая RAM;
* `process_virtual_memory_bytes` — виртуальная память процесса.

### Resident memory, MB

```promql
(
  (process_resident_memory_bytes{job="scrapper"} / 1024 / 1024)
  and on(job, instance)
  up{job=~"$app"}
)
```

### Virtual memory, MB

```promql
(
  (process_virtual_memory_bytes{job="scrapper"} / 1024 / 1024)
  and on(job, instance)
  up{job=~"$app"}
)
```

---

## 12. Scrapper RED: частота запросов

Показывает количество HTTP-запросов к сервису `scrapper` в секунду.

```promql
sum(
  rate(requests_total{
    job=~"$app",
    app_name="scrapper"
  }[$__rate_interval])
)
```

---

## 13. Scrapper RED: частота ошибок

Показывает количество HTTP-ответов сервиса `scrapper` со статусами `5xx` в секунду.

```promql
sum(
  rate(requests_total{
    job=~"$app",
    app_name="scrapper",
    status_code=~"5.."
  }[$__rate_interval])
)
```

---

## 14. Scrapper RED: p95 длительности запросов

Показывает 95-й перцентиль времени обработки HTTP-запросов сервисом `scrapper`.

Значение умножается на `1000`, чтобы перевести секунды в миллисекунды.

```promql
histogram_quantile(
  0.95,
  sum by (le) (
    rate(request_processing_time_bucket{
      job=~"$app",
      app_name="scrapper"
    }[$__rate_interval])
  )
) * 1000
```

---

# Grafana Alert

На метрику потребления RAM добавлен alert через **Grafana Alerting**.

В качестве основной RAM-метрики используется:

```promql
process_resident_memory_bytes
```

Пример PromQL-запроса для alert rule сервиса `bot`:

```promql
process_resident_memory_bytes{job="bot"} / 1024 / 1024
```

Пример PromQL-запроса для alert rule сервиса `scrapper`:

```promql
process_resident_memory_bytes{job="scrapper"} / 1024 / 1024
```

Пример условия срабатывания:

```text
RAM usage > 500 MB в течение 5 минут
```

---

# JSON дашборда и alert
monitoring/grafana/dashboards/linktracker-dashboard.json

monitoring/grafana/provisioning/alerting/ram-alerts.yml
т.п)