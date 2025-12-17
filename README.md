# 🌦️ WeatherHub: Microservices Deployment System

![Project Status](https://img.shields.io/badge/status-active-success.svg)
![Python](https://img.shields.io/badge/python-3.12-blue.svg)
![Docker](https://img.shields.io/badge/docker-v24+-2496ED.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

> **Курсовий проєкт** на тему: "Розробка системи автоматизованого розгортання мікросервісів з використанням Docker Compose".

WeatherHub — це розподілена інформаційна система для моніторингу погодних умов та планування активностей. Проєкт демонструє практичне застосування підходу **Infrastructure as Code (IaC)**, мікросервісної архітектури та технологій **Zero Trust** для безпечного доступу.

---

## 📸 Демонстрація головного інтерфейсу користувача: відображення погоди, плану та історії.

<img width="770" height="970" alt="Screenshot_20251217_190234" src="https://github.com/user-attachments/assets/4b0ce716-6f4a-45d2-970c-071f8ba19061" />

---

## 📑 Зміст
- [Проблематика та Рішення](#-проблематика-та-рішення)
- [Архітектура](#-архітектура-та-uml)
- [Технологічний Стек](#-технологічний-стек)
- [Встановлення та Запуск](#-встановлення-та-запуск)
- [Конфігурація](#-конфігурація)
- [API Ендпоінти](#-api-ендпоінти)
- [Автор](#-автор)

---

## 💡 Проблематика та Рішення

**Проблема:** Ручне розгортання та адміністрування мікросервісних систем на "голому залізі" (Bare Metal) є складним, схильним до помилок та створює ризики безпеки при відкритті портів назовні.

**Рішення:** Повна автоматизація процесу розгортання за допомогою **Docker Compose** та організація захищеного тунелювання через **Cloudflare Tunnel**.

**Ключові особливості:**
- **Zero Configuration Networking:** Не вимагає "білої" IP-адреси або відкритих портів.
- **Resilience:** Патерн *Fallback* забезпечує роботу системи навіть при збоях зовнішніх API.
- **Isolation:** База даних ізольована у внутрішній мережі, недоступній ззовні.

---

## 🏗 Архітектура та UML

Система побудована на базі 5 незалежних контейнерів, об'єднаних у віртуальні мережі.

### Діаграма розгортання (Deployment Diagram)

```mermaid
%%{init: {'theme':'dark','themeVariables': {
  'clusterBkg': '#00000000',
  'edgeLabelBackground': '#00000000',
  'nodeBkg': '#00000000'
}}}%%
graph TD
    user((User)) -->|HTTPS| cf[Cloudflare Edge]
    cf <==>|Secure Tunnel| cloudflared[Cloudflared Container]
    
    subgraph DockerHost["Proxmox VM"]
        subgraph WebNet["Web Network"]
            cloudflared -->|HTTP:80| frontend[Frontend Nginx]
            cloudflared -->|HTTP:8000| gateway[API Gateway]
            gateway -->|REST| weather[Weather Service]
            gateway -->|REST| planner[Planner Service]
            gateway -->|REST| history[History Service]
        end
        
        subgraph InternalNet["Internal Network"]
            history -->|SQL:5432| db[(PostgreSQL)]
        end
    end
    
    weather -.->|Ext API| openmeteo[Open-Meteo API]
    
    classDef box fill:none,stroke:#cfcfcf,stroke-width:2px,color:#ffffff;
    class cloudflared,frontend,gateway,weather,planner,history,db box

    style DockerHost fill:none,stroke:#cfcfcf,stroke-width:1px;
    style WebNet fill:none,stroke:#cfcfcf,stroke-width:1px;
    style InternalNet fill:none,stroke:#cfcfcf,stroke-width:1px;

```

### User Flow (Потік даних)

```mermaid
flowchart TD
    %% Стилі вузлів
    classDef startend fill:#4a6fa5,stroke:#333,stroke-width:2px,color:white,rx:20,ry:20;
    classDef process fill:#f4a261,stroke:#333,stroke-width:2px,color:white;
    classDef decision fill:#e9c46a,stroke:#333,stroke-width:2px,color:black,rx:5,ry:5;
    classDef db fill:#264653,stroke:#333,stroke-width:2px,color:white,shape:cylinder;
    
    Start([Користувач відкриває сайт]) --> Input[/Вводить місто і тисне 'Get Weather'/]
    Input --> Cloudflare{Безпечне з'єднання?}
    
    Cloudflare -- Ні --> Error([Помилка доступу])
    Cloudflare -- Так --> Gateway[API Gateway обробляє запит]
    
    Gateway --> CheckAPI{Чи доступний Weather Service?}
    
    CheckAPI -- Ні (Fallback) --> Mock[Генерація Mock-даних]
    CheckAPI -- Так --> ExternalAPI[Запит до Open-Meteo]
    
    Mock --> Merge[Об'єднання даних]
    ExternalAPI --> Merge
    
    Merge --> Parallel{Паралельні дії}
    
    Parallel --> Planner[Planner: Генерація активностей]
    Parallel --> DB[(PostgreSQL: Запис в історію)]
    
    Planner --> UI[/Відображення погоди та плану/]
    DB -.-> UI
    
    UI --> End([Завершення])

    %% Застосування стилів
    class Start,End,Error startend;
    class Gateway,Mock,ExternalAPI,Planner,Merge,Input,UI process;
    class Cloudflare,CheckAPI,Parallel decision;
    class DB db;
```

---

## 🛠 Технологічний Стек

| Компонент | Технологія | Опис |
| :--- | :--- | :--- |
| **Orchestration** | ![Docker](https://img.shields.io/badge/-Docker_Compose-2496ED?logo=docker&logoColor=white) | Управління контейнерами та мережами |
| **Backend** | ![FastAPI](https://img.shields.io/badge/-FastAPI-009688?logo=fastapi&logoColor=white) | Асинхронний Python-фреймворк |
| **Database** | ![Postgres](https://img.shields.io/badge/-PostgreSQL-336791?logo=postgresql&logoColor=white) | Збереження реляційних даних та JSONB |
| **Frontend** | ![Nginx](https://img.shields.io/badge/-Nginx-009639?logo=nginx&logoColor=white) | Статичний веб-сервер |
| **Security** | ![Cloudflare](https://img.shields.io/badge/-Cloudflare_Zero_Trust-F38020?logo=cloudflare&logoColor=white) | Тунелювання та DDoS-захист |

---

## 🚀 Встановлення та Запуск

### Передумови
- Linux сервер (Debian/Ubuntu)
- Docker Engine v24.0+
- Docker Compose Plugin

### Крок 1. Клонування
```bash
git clone https://github.com/Stanislavwx/WeatherHub.git
cd weatherhub-cloudflare
```

### Крок 2. Налаштування оточення
Створіть файл `.env` на основі приклада:
```bash
cp .env.example .env
nano .env
```
*Необхідно вставити ваш `TUNNEL_TOKEN` від Cloudflare.*

### Крок 3. Запуск
```bash
docker compose up -d --build
```

### Крок 4. Верифікація
```bash
docker compose ps
```
*Усі контейнери повинні мати статус `Up (healthy)`.*

---

## ⚙️ Конфігурація

Приклад файлу `.env`:

```env
# Cloudflare Tunnel Token
TUNNEL_TOKEN=eyJhIjoi...

# Database Credentials
POSTGRES_DB=weatherhub
POSTGRES_USER=user
POSTGRES_PASSWORD=secure_pass

# Service Config
WEATHER_PROVIDER=open-meteo
WEATHER_TIMEOUT_SEC=3
```

---

## 🔌 API Ендпоінти

Система надає REST API для взаємодії. Повна документація доступна за адресою `/docs` (Swagger UI) після запуску.

- `GET /api/weather?city={city}` — Отримати поточну погоду.
- `GET /api/plan?city={city}` — Отримати рекомендації щодо активностей.
- `GET /api/history/weather` — Переглянути останні запити.
- `GET /health` — Перевірка стану системи (Healthcheck).

---

## 👨‍💻 Автор

**Чепара С.Б.**
- Студент групи ФЕП–23
- Львівський національний університет ім. І. Франка
- Факультет елекроніки та компʼютерних технологій
- Львів 2025

