# LinkTracker Bot

Проект представляет собой монорепозиторий и состоит из трёх сервисов:

* `project-bot-service` — Telegram-бот, который принимает команды пользователя и отправляет уведомления.
* `project-scrapper-service` — сервис, который хранит отслеживаемые ссылки, проверяет обновления и передаёт уведомления.
* `project-ai-service` — AI Agent Service, который получает обновления из Kafka, фильтрует их и выполняет суммаризацию длинных обновлений.

## Структура проекта

Все сервисы находятся в одной корневой директории монорепозитория.

Пример:

```text
tbank_lab/
├── project-bot-service/
├── project-scrapper-service/
├── project-ai-service/
├── docker-compose.yml
```

Файл `docker-compose.yml` находится в корне репозитория, переносить его из сервисов не нужно.

---

# Настройка окружения

Для запуска необходимо создать `.env`-файлы отдельно в каждом сервисе.

---

## 1. `.env` для `project-bot-service`

В корне `project-bot-service` создай файл `.env`:

```env
bot_token="your_telegram_bot_token"


metrics_host=0.0.0.0
metrics_port=8011

scrapper_url=http://localhost:8080
bot_url=http://localhost:8000

scrapper_grpc_target=localhost:50051
bot_grpc_host=0.0.0.0
bot_grpc_port=50052

interservice_transport=http
notification_transport=kafka

kafka_bootstrap_servers=localhost:29092,localhost:29093,localhost:29094
kafka_notification_topic=link.processed_updates
kafka_notification_consumer_group=notifications.senders
kafka_auto_offset_reset=earliest
kafka_enable_auto_commit=false
kafka_notification_dlq_topic=link.processed_updates.dlq
kafka_max_processing_retries=5

schema_registry_url=http://localhost:8081

redis_url=redis://redis:6379/0
redis_delivered_notifications_ttl_seconds=86400

timeout_seconds=5
retry_attempts=5
retry_backoff_seconds=3
retry_enable_exponential_backoff=false
retryable_status_codes=500,400
circuit_error_ratio=0.5
circuit_response_time=5
circuit_recovery_time=10
circuit_broken_time=20
request_limit=5
request_limit_period=second
```

### Описание параметров

| Параметр                                    | Описание                                                                                                                                                    |
| ------------------------------------------- |-------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `bot_token`                                 | Токен Telegram-бота, полученный через BotFather.                                                                                                            |
| `metrics_host`                             | Host, на котором bot-сервис может поднимать metrics сервер                                                                                                  |
| `metrics_port`                             | Port, на котором bot-сервис может поднимать metrics сервер                                                                                                  |
| `scrapper_url`                              | HTTP-адрес `project-scrapper-service`, к которому обращается bot-сервис.                                                                                    |
| `bot_url`                                   | HTTP-адрес самого bot-сервиса. Используется для входящих HTTP-запросов.                                                                                     |
| `scrapper_grpc_target`                      | gRPC-адрес scrapper-сервиса. Поддерживается для совместимости, но не используется.                                                                          |
| `bot_grpc_host`                             | Host, на котором bot-сервис может поднимать gRPC-сервер. Поддерживается для совместимости, но не используется.                                              |
| `bot_grpc_port`                             | Port, на котором bot-сервис может поднимать gRPC-сервер. Поддерживается для совместимости, но не используется.                                              |
| `interservice_transport`                    | Транспорт для межсервисного взаимодействия bot-сервиса и scrapper-сервиса. Доступное значение: `http`.                                                      |
| `notification_transport`                    | Транспорт для получения уведомлений. Доступные значения: `http` или `kafka`.                                                                                |
| `kafka_bootstrap_servers`                   | Список Kafka-брокеров, к которым подключается bot-сервис.                                                                                                   |
| `kafka_notification_topic`                  | Kafka-topic, из которого bot-сервис получает уведомления.                                                                                                   |
| `kafka_notification_consumer_group`         | Consumer group для чтения уведомлений из Kafka.                                                                                                             |
| `kafka_auto_offset_reset`                   | Поведение Kafka consumer при отсутствии сохранённого offset. Значение `earliest` означает чтение с самого раннего доступного сообщения.                     |
| `kafka_enable_auto_commit`                  | Включает или отключает автоматическое подтверждение прочитанных сообщений. Значение `false` означает, что offset подтверждается вручную.                    |
| `kafka_notification_dlq_topic`              | Kafka-topic для Dead Letter Queue. В него отправляются сообщения, которые не удалось обработать, а также сообщения с ошибками десериализации или валидации. |
| `kafka_max_processing_retries`              | Максимальное количество повторных попыток обработки сообщения при ошибках бизнес-логики.                                                                    |
| `schema_registry_url`                       | URL Schema Registry, используемого для Avro-десериализации сообщений из Kafka.                                                                              |
| `redis_url`                                 | URL Redis, используемого bot-сервисом для хранения информации о доставленных уведомлениях.                                                                  |
| `redis_delivered_notifications_ttl_seconds` | TTL записей о доставленных уведомлениях. Используется для идемпотентности Kafka consumer-а.                                                                 |
| `timeout_seconds`                           | Таймаут HTTP-запросов в секундах.                                                                                                                           |
| `retry_attempts`                            | Максимальное количество повторных попыток запроса при временных ошибках.                                                                                    |
| `retry_backoff_seconds`                     | Базовая задержка между повторными попытками в секундах.                                                                                                     |
| `retry_enable_exponential_backoff`          | Включает экспоненциальное увеличение задержки между retry-попытками.                                                                                        |
| `retryable_status_codes`                    | HTTP-статусы, при которых запрос считается повторяемым.                                                                                                     |
| `circuit_error_ratio`                       | Доля ошибочных запросов, после которой circuit breaker может перейти в состояние `BROKEN`.                                                                  |
| `circuit_response_time`                     | Временное окно в секундах, в течение которого circuit breaker подсчитывает ошибки.                                                                          |
| `circuit_recovery_time`                     | Время в секундах для проверки восстановления клиента после срабатывания circuit breaker-а.                                                                  |
| `circuit_broken_time`                       | Время в секундах, в течение которого circuit breaker блокирует любые запросы.                                                                               |
| `request_limit`                             | Максимальное количество запросов за период rate limit-а.                                                                                                    |
| `request_limit_period`                      | Период rate limit-а. Например, `second` означает ограничение в рамках одной секунды.                                                                        |

### Поддерживаемые значения транспортов

Для межсервисного взаимодействия поддерживается только HTTP:

```env
interservice_transport=http
```

`interservice_transport=grpc` больше **не поддерживается**.

Для транспорта уведомлений доступны два варианта:

```env
notification_transport=http
```

или:

```env
notification_transport=kafka
```

При использовании Kafka необходимо также указать параметры:

```env
kafka_bootstrap_servers=localhost:29092,localhost:29093,localhost:29094
kafka_notification_topic=link.processed_updates
kafka_notification_consumer_group=notifications.senders
kafka_auto_offset_reset=earliest
kafka_enable_auto_commit=false
kafka_notification_dlq_topic=link.processed_updates.dlq
kafka_max_processing_retries=5
schema_registry_url=http://localhost:8081
redis_url=redis://redis:6379/0
redis_delivered_notifications_ttl_seconds=86400
```

---

## 2. `.env` для `project-scrapper-service`

В корне `project-scrapper-service` создай файл `.env`:

```env
bot_http_url=http://localhost:8000
scrapper_http_url=http://localhost:8080

github_base_url=https://api.github.com
stackoverflow_base_url=https://api.stackexchange.com/2.3

scrapper_grpc_host=0.0.0.0
scrapper_grpc_port=50051
bot_grpc_target=localhost:50052

scheduler_interval_seconds=100000
scheduler_batch_size=50
scheduler_workers_count=2

interservice_transport=http
notification_transport=http

db_host=localhost
db_port=5432
db_user=postgres
db_pass="your_postgres_password"
db_name=links_db

access_type=sql

kafka_bootstrap_servers=localhost:29092,localhost:29093,localhost:29094
kafka_notification_topic=link.raw_updates
schema_registry_url=http://localhost:8081

transactional_outbox_mode=false
outbox_processing_delay=5

enable_cache=true
valkey_addresses=localhost:7000,localhost:7001,localhost:7002
valkey_enable_client_cache=true
valkey_cache_ttl=500
valkey_client_cache_ttl=500
valkey_client_cache_maxsize=2000

timeout_seconds=5
retry_attempts=5
retry_backoff_seconds=3
retry_enable_exponential_backoff=false
retryable_status_codes=500,400
circuit_error_ratio=0.5
circuit_response_time=5
circuit_recovery_time=10
circuit_broken_time=20
request_limit=5
request_limit_period=second
```

### Описание параметров

| Параметр                           | Описание                                                                                                                                                              |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `bot_http_url`                     | HTTP-адрес bot-сервиса, на который scrapper-сервис отправляет уведомления при использовании HTTP-транспорта уведомлений.                                              |
| `scrapper_http_url`                | HTTP-адрес самого scrapper-сервиса.                                                                                                                                   |
| `github_base_url`                  | Базовый URL GitHub API для проверки обновлений GitHub-ссылок.                                                                                                         |
| `stackoverflow_base_url`           | Базовый URL StackOverflow / StackExchange API для проверки обновлений StackOverflow-ссылок.                                                                           |
| `scrapper_grpc_host`               | Host, на котором scrapper-сервис может поднимать gRPC-сервер. Поддерживается для совместимости, но не используется.                                                   |
| `scrapper_grpc_port`               | Port, на котором scrapper-сервис может поднимать gRPC-сервер. Поддерживается для совместимости, но не используется.                                                   |
| `bot_grpc_target`                  | gRPC-адрес bot-сервиса. Поддерживается для совместимости, но не используется.                                                                                         |
| `scheduler_interval_seconds`       | Интервал запуска планировщика проверки ссылок в секундах.                                                                                                             |
| `scheduler_batch_size`             | Количество ссылок, которое обрабатывается за один batch.                                                                                                              |
| `scheduler_workers_count`          | Количество параллельных worker-потоков для обработки batch-заданий.                                                                                                   |
| `interservice_transport`           | Транспорт для межсервисного взаимодействия bot-сервиса и scrapper-сервиса. Доступное значение: `http`.                                                                |
| `notification_transport`           | Транспорт для отправки уведомлений из scrapper-сервиса в bot-сервис. Доступные значения: `http` или `kafka`.                                                          |
| `db_host`                          | Host PostgreSQL-базы данных.                                                                                                                                          |
| `db_port`                          | Port PostgreSQL-базы данных.                                                                                                                                          |
| `db_user`                          | Имя пользователя PostgreSQL.                                                                                                                                          |
| `db_pass`                          | Пароль пользователя PostgreSQL. В README лучше не указывать реальный пароль, а использовать placeholder.                                                              |
| `db_name`                          | Название базы данных.                                                                                                                                                 |
| `access_type`                      | Способ работы с базой данных. Возможные значения: `sql` или `orm`.                                                                                                    |
| `kafka_bootstrap_servers`          | Список Kafka-брокеров, к которым подключается scrapper-сервис.                                                                                                        |
| `kafka_notification_topic`         | Kafka-topic, в который scrapper-сервис отправляет уведомления для обработки.                                                                                          |
| `schema_registry_url`              | URL Schema Registry, используемого для Avro-сериализации сообщений перед отправкой в Kafka.                                                                           |
| `transactional_outbox_mode`        | Включает отправку уведомлений через Transactional Outbox. При значении `true` события сначала сохраняются в outbox-таблицу, а затем отправляются отдельным worker-ом. |
| `outbox_processing_delay`          | Задержка между итерациями outbox worker-а в секундах.                                                                                                                 |
| `enable_cache`                     | Включает кэширование результатов запроса `GET /links` в Valkey.                                                                                                       |
| `valkey_addresses`                 | Список адресов Valkey Cluster в формате `host:port,host:port,host:port`.                                                                                              |
| `valkey_enable_client_cache`       | Включает дополнительное кэширование на стороне клиента поверх Valkey.                                                                                                 |
| `valkey_cache_ttl`                 | Время жизни записи в Valkey в секундах.                                                                                                                               |
| `valkey_client_cache_ttl`          | Время жизни записи в client-side cache в секундах.                                                                                                                    |
| `valkey_client_cache_maxsize`      | Максимальное количество ключей, которое может храниться в client-side cache.                                                                                          |
| `timeout_seconds`                  | Таймаут HTTP-запросов в секундах.                                                                                                                                     |
| `retry_attempts`                   | Максимальное количество повторных попыток запроса при временных ошибках.                                                                                              |
| `retry_backoff_seconds`            | Базовая задержка между повторными попытками в секундах.                                                                                                               |
| `retry_enable_exponential_backoff` | Включает экспоненциальное увеличение задержки между retry-попытками.                                                                                                  |
| `retryable_status_codes`           | HTTP-статусы, при которых запрос считается повторяемым.                                                                                                               |
| `circuit_error_ratio`              | Доля ошибочных запросов, после которой circuit breaker может перейти в состояние `BROKEN`.                                                                            |
| `circuit_response_time`            | Временное окно в секундах, в течение которого circuit breaker подсчитывает ошибки.                                                                                    |
| `circuit_recovery_time`            | Время в секундах для проверки восстановления клиента после срабатывания circuit breaker-а.                                                                            |
| `circuit_broken_time`              | Время в секундах, в течение которого circuit breaker блокирует любые запросы.                                                                                         |
| `request_limit`                    | Максимальное количество запросов за период rate limit-а.                                                                                                              |
| `request_limit_period`             | Период rate limit-а. Например, `second` означает ограничение в рамках одной секунды.                                                                                  |

### Режимы работы кэша

Если `enable_cache=false`, scrapper-сервис не использует Valkey и каждый запрос `GET /links` формируется через основное хранилище.

Если `enable_cache=true`, результат `GET /links` сохраняется в Valkey по ключу пользователя. При добавлении или удалении ссылки пользователя соответствующая запись в кэше удаляется.

Если дополнительно указано `valkey_enable_client_cache=true`, поверх Valkey включается client-side cache в памяти приложения. Его размер ограничивается параметром `valkey_client_cache_maxsize`, а время жизни записей — параметром `valkey_client_cache_ttl`.

### Поддерживаемые значения транспортов

Для межсервисного взаимодействия поддерживается только HTTP:

```env
interservice_transport=http
```

`interservice_transport=grpc` больше **не поддерживается**.

Для транспорта уведомлений доступны два варианта:

```env
notification_transport=http
```

или:

```env
notification_transport=kafka
```

При использовании Kafka необходимо также указать параметры:

```env
kafka_bootstrap_servers=localhost:29092,localhost:29093,localhost:29094
kafka_notification_topic=link.raw_updates
schema_registry_url=http://localhost:8081
```

### Transactional Outbox

Для включения Transactional Outbox:

```env
transactional_outbox_mode=true
outbox_processing_delay=5
```

В этом режиме scrapper-сервис сначала сохраняет событие уведомления в outbox-таблицу в той же транзакции, где обновляет состояние ссылки. Отдельный outbox worker периодически забирает новые события, отправляет их в Kafka и помечает как отправленные.

Для отключения Transactional Outbox:

```env
transactional_outbox_mode=false
```

### Выбор реализации доступа к базе данных

Для использования SQL-реализации:

```env
access_type=sql
```

Для использования ORM-реализации:

```env
access_type=orm
```

### Настройка планировщика

Можно изменить интервал проверки ссылок, размер batch и количество worker-потоков:

```env
scheduler_interval_seconds=100000
scheduler_batch_size=50
scheduler_workers_count=2
```

Где:

* `scheduler_interval_seconds` — как часто запускается проверка ссылок;
* `scheduler_batch_size` — сколько ссылок обрабатывается за одну итерацию;
* `scheduler_workers_count` — сколько обработчиков работает параллельно.

---

## 3. `.env` для `project-ai-service`

В корне `project-ai-service` создай файл `.env`:

```env
kafka_bootstrap_servers=localhost:29092,localhost:29093,localhost:29094
kafka_updates_consumer_group=link.senders
kafka_auto_offset_reset=earliest
kafka_enable_auto_commit=false
kafka_processed_updates_topic=link.processed_updates
kafka_raw_updates_topic=link.raw_updates
kafka_raw_updates_dlq_topic=link.raw_updates.dlq
kafka_max_processing_retries=5

schema_registry_url=http://localhost:8081

ai_token="your_huggingface_token"
```

### Описание параметров `.env`

| Параметр                        | Описание                                                                                                                                                                    |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `kafka_bootstrap_servers`       | Список Kafka-брокеров, к которым подключается AI-сервис.                                                                                                                    |
| `kafka_updates_consumer_group`  | Consumer group для чтения сырых обновлений из Kafka.                                                                                                                        |
| `kafka_auto_offset_reset`       | Поведение Kafka consumer при отсутствии сохранённого offset. Значение `earliest` означает чтение с самого раннего доступного сообщения.                                     |
| `kafka_enable_auto_commit`      | Включает или отключает автоматическое подтверждение прочитанных сообщений. Значение `false` означает, что offset подтверждается вручную после успешной обработки сообщения. |
| `kafka_raw_updates_topic`       | Kafka-topic, из которого AI-сервис получает сырые обновления от scrapper-сервиса.                                                                                           |
| `kafka_processed_updates_topic` | Kafka-topic, в который AI-сервис отправляет обработанные обновления после фильтрации и суммаризации.                                                                        |
| `kafka_raw_updates_dlq_topic`   | Kafka-topic для Dead Letter Queue сырых обновлений. В него попадают сообщения, которые не удалось обработать.                                                               |
| `kafka_max_processing_retries`  | Максимальное количество повторных попыток обработки сообщения перед отправкой в DLQ.                                                                                        |
| `schema_registry_url`           | URL Schema Registry, используемого для Avro-сериализации и десериализации Kafka-сообщений.                                                                                  |
| `ai_token`                      | Токен доступа к AI-модели                                                                                                                                                   |

### `processing_config.yml` для `project-ai-service`

В корне `project-ai-service` также необходимо создать файл `processing_config.yml`:

```yaml
ai-agent:
  processing-model: Qwen/Qwen3-4B-Instruct-2507
  filtering:
    stop-words:
      - api
      - ads
      - promo
    excluded-authors:
      - user123
    min-length: 50
  summarization:
    threshold: 200
  prioritization:
    high-keywords:
      - critical
      - urgent
      - breaking
      - security
    low-keywords:
      - minor
      - typo
      - chore
      - docs
  grouping:
    window-ms: 3000
```

### Описание параметров `processing_config.yml`

| Параметр                                | Описание                                                                                                                                                                              |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ai-agent.processing-model`             | Модель, используемая AI-сервисом для обработки и суммаризации обновлений.                                                                                                             |
| `ai-agent.filtering.stop-words`         | Список стоп-слов. Если текст обновления содержит одно из этих слов, обновление может быть отфильтровано.                                                                              |
| `ai-agent.filtering.excluded-authors`   | Список авторов, обновления от которых должны быть исключены из обработки.                                                                                                             |
| `ai-agent.filtering.min-length`         | Минимальная длина текста обновления. Обновления короче этого значения не проходят дальнейшую обработку.                                                                               |
| `ai-agent.summarization.threshold`      | Порог длины текста, после которого выполняется суммаризация обновления.                                                                                                               |
| `ai-agent.prioritization.high-keywords` | Список ключевых слов, при наличии которых обновление получает высокий приоритет `HIGH`.                                                                                               |
| `ai-agent.prioritization.low-keywords`  | Список ключевых слов, при наличии которых обновление получает низкий приоритет `LOW`, если не были найдены ключевые слова высокого приоритета.                                        |
| `ai-agent.grouping.window-ms`           | Временное окно группировки обновлений в миллисекундах. В течение этого окна несколько обновлений для одного `tgChatId` накапливаются и отправляются одним сгруппированным сообщением. |

### Назначение AI Agent Service

`project-ai-service` работает как промежуточное звено между `project-scrapper-service` и `project-bot-service`.

---

# Kafka, Schema Registry, Redis и PostgreSQL

Проект использует:

* PostgreSQL — основная база данных scrapper-сервиса;
* Kafka — асинхронная доставка и обработка уведомлений;
* Schema Registry — хранение Avro-схем сообщений Kafka;
* Redis — хранение информации об уже доставленных уведомлениях для идемпотентности bot consumer-а.

Kafka-topic-и:

```text
link.raw_updates
link.raw_updates.dlq
link.processed_updates
link.processed_updates.dlq
```

| Topic                             | Назначение                                                                                                                                                                                      |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `link.raw_updates`                | Используется для передачи сырых обновлений в AI-сервис.                                                                                                                                         |
| `link.raw_updates.dlq`            | Используется для Dead Letter Queue сырых обновлений. Туда попадают сообщения, которые невозможно обработать после повторных попыток, а также сообщения с ошибками десериализации или валидации. |
| `link.processed_updates`          | Используется для передачи обработанных AI-сервисом обновлений.                                                                                                                                  |
| `link.processed_updates.dlq`      | Используется для Dead Letter Queue обработанных обновлений. Туда попадают сообщения, которые невозможно обработать после повторных попыток, а также сообщения с ошибками десериализации или валидации. |
---

### 4. Отказоустойчивость HTTP-запросов в bot service и scrapper service

Параметры `timeout_seconds`, `retry_*`, `circuit_*` и `request_limit*` используются для повышения устойчивости HTTP-взаимодействий с внешними сервисами и между сервисами проекта.

`timeout_seconds` ограничивает максимальное время ожидания HTTP-запроса. Retry-политика повторяет запросы при статусах из `retryable_status_codes` с учётом количества попыток `retry_attempts` и задержки `retry_backoff_seconds`.

Circuit breaker отслеживает ошибки в течение временного окна `circuit_response_time`. Если доля ошибок превышает `circuit_error_ratio`, circuit breaker переходит в состояние `BROKEN` и блокирует запросы на время `circuit_broken_time`. После этого в течение `circuit_recovery_time` проверяется восстановление клиента.

Rate limit ограничивает частоту исходящих запросов значениями `request_limit` и `request_limit_period`.

# Запуск через Docker

Файл `docker-compose.yml` находится в корне монорепозитория.

Пример структуры:

```text
tbank_lab/
├── project-bot-service/
├── project-scrapper-service/
├── project-ai-service/
├── docker-compose.yml
```

## Запуск проекта

Из корневой директории выполни:

```bash
docker compose up --build
```

После запуска будут подняты сервисы проекта, PostgreSQL, Redis, Kafka-кластер, Schema Registry и Kafka UI. Логи появятся в терминале.

## Остановка проекта

```bash
docker compose down
```

---

# Локальный запуск тестов

Тесты запускаются отдельно в каждой папке сервиса.

## `project-bot-service`

```bash
cd project-bot-service
poetry run pytest
```

## `project-scrapper-service`

```bash
cd project-scrapper-service
poetry run pytest
```

## `project-ai-service`

```bash
cd project-ai-service
poetry run pytest
```
