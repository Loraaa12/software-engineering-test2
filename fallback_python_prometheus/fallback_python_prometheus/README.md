# Python Fallback + Prometheus Demo

Това проектче покрива:
1. Fallback между 2 backend-а
2. Prometheus Counter за fallback-а
3. JSON логове при fallback
4. Prometheus в Docker за визуализация на counter-а

## Структура
- `app.py` - Flask приложението
- `requirements.txt` - Python зависимости
- `Dockerfile` - контейнер за app-а
- `docker-compose.yml` - app + Prometheus
- `prometheus/prometheus.yml` - scrape конфигурация за Prometheus

## Как работи
- Endpoint `/todos` първо вика primary backend:
  - `https://jsonplaceholder.typicode.com/todos`
- Ако той fail-не, минава на fallback backend:
  - `https://dummyjson.com/todos`
- При всеки fallback:
  - се увеличава `fallback_triggered_total`
  - се записва JSON лог
- Endpoint `/metrics` връща метриките за Prometheus

## Вариант 1: Най-лесно, всичко през Docker

### 1) Отвори терминал в папката на проекта
```bash
docker compose up --build
```

### 2) Отвори тези адреси
- App: `http://localhost:8000/`
- Todos: `http://localhost:8000/todos`
- Metrics: `http://localhost:8000/metrics`
- Prometheus: `http://localhost:9090`

### 3) Тествай нормална заявка
```bash
curl "http://localhost:8000/todos"
```

Това трябва да върне данни от primary backend.

### 4) Тествай fallback-а
```bash
curl "http://localhost:8000/todos?failPrimary=true"
curl "http://localhost:8000/todos?failPrimary=true"
curl "http://localhost:8000/todos?failPrimary=true"
```

Тук primary backend-ът се чупи нарочно за тест и приложението минава към fallback backend-а.

### 5) Провери метриката
Отвори:
- `http://localhost:8000/metrics`

Там трябва да видиш нещо такова:
```text
fallback_triggered_total 3.0
```

### 6) Провери в Prometheus UI
Отвори:
- `http://localhost:9090`

В полето **Expression** напиши:
```text
fallback_triggered_total
```

Натисни **Execute**.

После отвори таб **Graph**.

## Вариант 2: App локално, Prometheus в Docker

### 1) Инсталирай зависимостите
```bash
pip install -r requirements.txt
```

### 2) Пусни Python app-а
```bash
python app.py
```

### 3) Пусни само Prometheus
```bash
docker run --name fallback-prometheus -p 9090:9090 -v "${PWD}/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml" prom/prometheus
```

> Забележка: този вариант може да иска корекция на target-а в `prometheus.yml` според OS-а ти. Най-сигурният вариант е `docker compose up --build`.

## Как изглеждат JSON логовете
При fallback ще видиш лог в конзолата, подобен на:
```json
{"timestamp":"2026-04-15T10:00:00+00:00","level":"INFO","logger":"fallback_app","message":"Fallback activated","event":"fallback_triggered","primary_backend":"https://jsonplaceholder.typicode.com/todos","fallback_backend":"https://dummyjson.com/todos","reason":"Primary backend failure was forced for testing.","path":"/todos","query":"failPrimary=true","remote_addr":"127.0.0.1"}
```

## Какво да предадеш
Най-добре предай:
1. Цялата project папка или zip
2. Screenshot от Prometheus UI, където се вижда `fallback_triggered_total`
3. По желание - screenshot от терминала с JSON логовете

## Как точно да направиш screenshot за т.4
1. Пусни:
```bash
docker compose up --build
```
2. В нов терминал изпълни:
```bash
curl "http://localhost:8000/todos?failPrimary=true"
curl "http://localhost:8000/todos?failPrimary=true"
curl "http://localhost:8000/todos?failPrimary=true"
```
3. Отвори `http://localhost:9090`
4. Напиши:
```text
fallback_triggered_total
```
5. Натисни **Execute**
6. Отиди на **Graph**
7. Направи screenshot

## Какво да кажеш при защита
- Имам primary и fallback backend.
- При проблем с primary backend приложението автоматично минава към втория.
- Всеки път когато fallback-ът се задейства, Counter метриката `fallback_triggered_total` се увеличава.
- Метриките се expose-ват през `/metrics`.
- Prometheus scrape-ва този endpoint и визуализира стойността на Counter-а.
- При всяко fallback събитие се записва JSON лог.
