# Receipt Expense API

A REST API built with Python and FastAPI for managing receipts and tracking expenses.

## Features

- Create receipts
- Retrieve all receipts
- Retrieve individual receipts
- Update receipts
- Delete receipts
- Filter receipts by category and currency
- Paginate receipt records
- Generate expense summaries
- Health check endpoint
- Automated API testing

## Technologies

- Python
- FastAPI
- Pydantic
- SQLite
- Pytest
- Docker

## Project Structure

```text
receipt-api/
├── app/
├── data/
├── tests/
├── Dockerfile
├── compose.yaml
├── requirements.txt
├── .dockerignore
├── .gitignore
└── README.md
```

## Installation

Clone the repository:

```bash
git clone YOUR_REPOSITORY_URL
cd receipt-api
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run the API

```bash
uvicorn app.main:app --reload
```

The API will be available at:

`http://127.0.0.1:8000`

Interactive API documentation:

`http://127.0.0.1:8000/docs`

## Run Tests

```bash
pytest -v
```

## Run with Docker

```bash
docker compose up --build
```

## Database

The application uses SQLite to store receipt information.

The default database location is:

`data/receipts.db`

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/receipts` | Create receipt |
| GET | `/receipts` | Retrieve receipts |
| GET | `/receipts/{receipt_id}` | Retrieve a receipt |
| PATCH | `/receipts/{receipt_id}` | Update receipt |
| DELETE | `/receipts/{receipt_id}` | Delete receipt |
| GET | `/receipts/summary` | Expense summary |

## Purpose

This project demonstrates REST API development, database integration, data validation, automated testing and containerization using Python and FastAPI.