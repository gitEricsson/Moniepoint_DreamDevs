# Moniepoint Analytics API

**Candidate:** Ericson Raphael

A production-quality REST API that imports massive volumes of merchant activity CSVs into PostgreSQL and exposes extremely fast analytics endpoints, built with Domain-Driven Design (DDD).

---

## 🧠 Problem Solving Approach

### 1. Understanding the Problem

- Analyzed the massive merchant transaction format and data structure constraints
- Identified the key metrics needed:
  - Highest successful sales volume merchant
  - Unique active merchants count per calendar month
  - Most adopted product ID by volume
  - Conversion pipeline for KYC documents
  - Transaction failure breakdown per product

### 2. Breaking Down the Solution

- Separated the monolithic architecture into strict Domain-Driven modules (schemas-models-api-controllers-services-repositories separation per module)

### 3. Data Processing Strategy

- Used `O(Batch_Size)` Python generators to lazily evaluate CSVs and prevent memory exhaustion
- Implemented an `O(1)` in-memory UUID hash set for immediate duplication collision detection
- Created single-pass Postgres aggregations (`SUM(CASE WHEN...)`) to combine data directly in the database rather than Python loops
- Deployed B-Tree and Composite indexing specifically targeting the 5 core metric queries

### 4. API & Systems Design

- Built a modular FastAPI routing system exposing the 5 distinct REST endpoints
- Used Class based components for code reuse, functionality and maintainability
- Designed global exception handling to wrap errors in standardized JSON envelopes
- Implemented middlewares to handle CORS, rate limiting, request logging, and security headers
- Enforced strict OpenAPI (Swagger) documentation with precise schema examples

### 5. Testing and Validation

- Engineered 42 combined unit and integration tests across routers, schemas, and repositories
- Seeded diverse, isolated in-memory SQLite test environments dynamically
- Validated error coercions (e.g. malformed integers) to guarantee the import pipeline survives corrupt data rows

---

## 🏗️ Extensive Design & Architecture Decisions

This section breaks down the *why* behind the tools, languages, and patterns chosen for this system. Considering extensive experience across both Python and TypeScript ecosystems, these choices represent the optimal path for a data-heavy analytics API.

### 1. Language & Framework: Python + FastAPI
- **Why Python over TypeScript (Node.js/Express/NestJS)?** 
  While TS/Node provides fantastic asynchronous I/O, this project heavily involves data aggregation and parsing (CSV ingestion, mathematical aggregations, decimal precision). Python natively excels at data-centric operations. Furthermore, Python's SQLAlchemy 2.0 provides arguably the most mature SQL expression language available across any ecosystem, surpassing TypeORM/Prisma in complex query generation.
- **Why FastAPI?** 
  FastAPI offers the ergonomics of NestJS (Dependency Injection, decorators) and the speed of Express, but with built-in Pydantic validation and automatic OpenAPI (Swagger) generation. It strictly enforces type hints, bridging the gap between Python's dynamic nature and standard static typing.

### 2. Architecture: Domain-Driven Modular Design vs Monolith
- Instead of a flat MVC structure (`controllers/`, `models/`, `services/`), the codebase is separated into **Business Domains** (`src/modules/analytics`, `src/modules/importer`, `src/modules/health`).
- **Why?** Modular/DDD structures scale remarkably better for teams. If Moniepoint adds a "fraud" or "settlements" domain tomorrow, they get their own folder with their own schemas, models, and tests without cluttering the global namespace. It naturally prevents chaotic cross-imports (spaghetti code) and sets the foundation for microservice extraction if ever needed.

### 3. Layered Separation of Concerns (Within Modules)
Each domain follows strict layer boundaries:
- **Router (`api/`)**: Only handles HTTP routing paths.
- **Controllers (`controllers/`)**: Manages HTTP requests, responses, and dependency wiring.
- **Services (`services/`)**: Pure python business logic. Knows nothing about HTTP endpoints.
- **Repositories (`repositories/`)**: The only layer allowed to touch the database or SQLAlchemy models.
- **Schemas (`schemas/`)**: Pydantic DTOs for data validation.
- **Why?** This makes unit testing incredibly easy. We can test the Service layer without spinning up a mock HTTP server. We can swap PostgreSQL for MySQL in the Repository layer without the Service layer ever knowing.

### 4. Database & ORM: PostgreSQL + SQLAlchemy 2.0 + Asyncpg
- **Why Postgres?** It is the gold standard for ACID compliance and analytics. It natively supports robust `UPSERT` operations (`ON CONFLICT`) and partial indexing, crucial for this project.
- **Why SQLAlchemy 2.0 + Asyncpg?** Provides fully asynchronous, non-blocking database queries with connection pooling. `asyncpg` is the fastest Postgres driver for Python.
- **Connection Pooling**: Configured centrally (`src/db/engine.py`) to prevent port exhaustion under high load while ensuring concurrent readiness.

### 5. API Integrations & Best Practices
- **Global Error Handling**: A centralized error middleware (`src/middleware/error_handler.py`) catches custom Domain exceptions (`AppException`, `DataProcessingError`) and standardizes the JSON response wrapper. No leaking of stack traces to the client.
- **Security Middleware**: Built-in strict security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security`, `X-XSS-Protection`) to mitigate clickjacking, MIME-sniffing, and enforce HTTPS-only routing (HSTS).
- **CORS**: Out-of-the-box Cross-Origin Resource Sharing logic decoupled into its own middleware.
- **Logging & Timing**: Structured JSON-ready logging (`logging_setup.py`) and a custom `X-Process-Time` timing middleware tracking endpoint latency.
- **Configuration (Settings)**: Managed via Pydantic `BaseSettings` reading from `.env`. Cached via `@lru_cache` to execute the Singleton pattern—cheap, thread-safe, and instantiated exactly once per Python process.

### 6. Background Processing: Lifespan Tasks vs Celery/Redis
- **Why native async instead of Celery/Redis?** 
  The project requires processing CSVs precisely *once* at startup. Introducing Celery, Redis, and a dedicated worker dyno for a one-off ingestion task violates YAGNI (You Aren't Gonna Need It). A FastAPI `lifespan` context accurately achieves non-blocking background ingestion with zero external infrastructure overhead.

### 7. Performance & Data Structure Algorithms (DSA)
- **O(Batch_Size) Streaming**: The massive CSVs are evaluated using lazy Python generators, inserting via batch chunks (default 5,000). The server memory footprint remains flat (`O(Batch_Size)`) regardless of whether the CSV is 10MB or 50GB.
- **In-Memory Duplicate Detection**: O(1) duplicate collision checks using a `set[uuid.UUID]` of seen hashes during the import pipeline execution.
- **Optimized SQL Indexes**: The database utilizes Composite indexes (`status`, `product`), Partial indexes (for the KYC funnel), and B-Tree indexes on timestamps, pushing runtime complexity for analytics queries toward an optimal `O(log N)` index scan.
- **Single-Pass DB Aggregations**: All 5 analytics endpoints execute exactly **1** query against the database using `CASE WHEN` and conditional SUMs. No Python-level for-loops over data.

### 8. Testing Strategy
- **Unit & Integration Tests**: 42 automated tests covering schemas, validation rejection, repository queries, and HTTP endpoints via `pytest`.
- **In-Memory SQLite Fast-Track**: `conftest.py` is configured to spin up an ephemeral SQLite `sqlite+aiosqlite:///:memory:` instance. This eliminates the need for standing up Dockerized Postgres for CI/CD test runs, running the entire 42-test suite in under 3 seconds.

---

## 🏗️ Architecture Directory Structure

```
src/
├── api/             # FastAPI app factory + central router
├── conftest.py      # Shared test fixtures (SQLite DB, test clients)
├── core/            # Settings singleton (@lru_cache), exceptions, logging
├── db/              # Async engine (singleton), session factory, DeclarativeBase
├── middleware/      # CORS, timing, logging, security, and global error handlers
├── modules/         # Domain-Driven boundaries
│   ├── analytics/   # Analytics domain (models, schemas, repos, services, API)
│   ├── health/      # Operational readiness domain
│   └── importer/    # CSV data ingestion pipeline domain
├── tasks/           # FastAPI lifespan startup task (triggers CSV import)
├── utils/           # Shared helpers (date parsing, validators, formatters)
└── main.py          # Uvicorn entrypoint execution
```

---

## 🛠️ Tech Stack Quick Look

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI + Uvicorn |
| Database | PostgreSQL + async SQLAlchemy 2.0 + asyncpg |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Testing | pytest + pytest-asyncio + httpx |
| Documentation | Swagger + ReDoc |

---

## 🚀 Setup & Run

> [!IMPORTANT]
> **Highlighted Prerequisites:**
> - **Python 3.11+**
> - **PostgreSQL 14+** running locally

### 1. How to Install Dependencies
1. Clone the repository and navigate into the folder.
2. Create and activate a virtual environment:
```bash
git clone <repo-url>
cd <repo-folder>
python -m venv .venv
# Windows: .venv\Scripts\activate | macOS/Linux: source .venv/bin/activate
```
3. Install the required packages:
```bash
pip install -r requirements.txt
```

### 2. Required Environment Variables
> [!WARNING]
> The application requires a `.env` file to establish database connections.

Duplicate the provided example environment file:
```bash
cp .env.example .env
```
Open `.env` and configure the following required variables:
- `DATABASE_URL`: Connection string to your local PostgreSQL (e.g., `postgresql+asyncpg://postgres:<password>@localhost:5432/moniepoint`)
- `DATA_DIR`: Path to the directory housing your CSV files (default: `./data`)
- `API_PORT`: Port designated for the API to serve on (default: `8080`)

### 3. Database & Migrations
Create your database inside Postgres (`CREATE DATABASE moniepoint;`), then run the automated Alembic migrations to construct the tables and indices:
```bash
alembic upgrade head
```

### 4. How to Start the Application
Ensure your `activities_YYYYMMDD.csv` files are deposited inside the `./data` folder. Then start the Uvicorn server:
```bash
python -m src.main
```

> [!NOTE]
> The server starts on **http://localhost:8080**. The CSV ingestion automatically orchestrates silently in the background. Visit `http://localhost:8080/docs` to interact with the interactive Swagger UI!

---

## 📡 API Endpoints 

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/analytics/top-merchant` | Merchant with highest total successful transaction volume |
| GET | `/analytics/monthly-active-merchants` | Unique active merchants per calendar month |
| GET | `/analytics/product-adoption` | Unique merchant count per product (sorted desc) |
| GET | `/analytics/kyc-funnel` | KYC conversion funnel: documents → verification → tier upgrade |
| GET | `/analytics/failure-rates` | Failure rate per product, sorted descending |
| GET | `/health` | Availability and uptime health check |

---

## 🧪 Testing

```bash
# Execute the full 42-test suite against the isolated in-memory DB
pytest

# Execute with coverage
pytest --cov=src --cov-report=term-missing
```

---

## 📝 Assumptions
1. **Product adoption** counts any valid status per product (SUCCESS, PENDING, FAILED) per the spec wording.
2. **Top merchant**, **Monthly active**, and **KYC funnel** specifically depend on `SUCCESS` states.
3. **Failure rate** formulas exclude trailing/unresolved `PENDING` states.
4. Invalid amounts are coerced to `0.00` rather than entirely dropping valid rows to preserve activity integrity.
