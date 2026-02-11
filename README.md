# grafana-image-renderer (Python replacement)

Небольшой HTTP-сервис на Python, который рендерит изображения дашбордов Grafana через headless Chrome.  
Проект создан как простая замена устаревшему и снятому с поддержки официальному плагину `grafana-image-renderer`.

Сервис получает URL панели Grafana, логинится в Grafana, открывает страницу в headless-браузере и возвращает PNG-скриншот.

---

## Возможности

- Рендер панелей Grafana в PNG
- Headless Chrome через Selenium
- Автоматическая авторизация в Grafana
- Ожидание «визуальной стабильности» перед снятием скриншота
- Простой HTTP API (`/render`)

---

## Требования

- Python 3.8+
- Chromium или Google Chrome
- chromedriver, совместимый с версией браузера

Python-зависимости:

```bash
pip install flask selenium pillow numpy requests urllib3
```

### Переменные окружения
| Переменная          | Описание                         | Значение по умолчанию                          |
| ------------------- | -------------------------------- | ---------------------------------------------- |
| `CHROME_BIN`        | Путь к бинарнику Chrome/Chromium | `/usr/lib64/chromium-browser/chromium-browser` |
| `CHROMEDRIVER_PATH` | Путь к chromedriver              | `/usr/bin/chromedriver`                        |
| `GRAFANA_URL`       | Базовый URL Grafana              | (обязательно)                                  |
| `GRAFANA_USER`      | Пользователь Grafana             | (обязательно)                                  |
| `GRAFANA_PASS`      | Пароль Grafana                   | (обязательно)                                  |

---
### Systemd service

Пример размещения файла: /etc/systemd/system/grafana-image-renderer.service

```bash
[Unit]
Description=Grafana Image Renderer Service
After=syslog.target
After=network.target

[Service]
EnvironmentFile=/home/grafana-image-renderer/.bash_profile
Type=simple
User=grafana-image-renderer
Group=grafana-image-renderer
WorkingDirectory=/opt/grafana/grafana-image-renderer
ExecStart=/usr/local/bin/gunicorn -w 10 -b 127.0.0.1:5000 grafana-image-renderer:app --timeout=120
Restart=always

[Install]
WantedBy=multi-user.target
```
Запуск и старт:
```bash
systemctl daemon-reload; systemctl enable --now grafana-image-renderer.service
```


---
### Как это работает

Сервис логинится в Grafana через /login.

Получает cookie grafana_session.

Запускает headless Chrome.

Открывает нужный URL панели.

Ждёт, пока изображение стабилизируется визуально.
Делает скриншот и возвращает PNG.

---

### Пример интеграции с Grafana (external renderer)

В grafana.ini:
```bash
[rendering]
server_url = http://127.0.0.1:5000/render
callback_url = https://hostname.example.com/
```

### Ограничения

Требуется совместимость версии Chrome и chromedriver.

Работает через скриншот браузера, а не нативный рендер Grafana.