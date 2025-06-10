# IdealMarket

IdealMarket is a simple inventory and sales management application built with Django. It provides a basic cashier interface and an admin dashboard to manage products, categories, warehouses and user permissions.

## Installation

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd idealmarket
   ```
2. **Create virtual environment (optional but recommended)**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. **Install dependencies**
   ```bash
   pip install django django-import-export reportlab pandas
   ```

## Database setup

Run migrations to create the database schema:

```bash
python idealmarket/manage.py migrate
```

To create an admin user:

```bash
python idealmarket/manage.py createsuperuser
```

## Running the development server

Start the application using:

```bash
python idealmarket/manage.py runserver
```

Open `http://127.0.0.1:8000/` in your browser to access the site. The admin panel is available at `/admin/`.

## Features

- Manage products, categories and warehouses
- Cashier interface with cart and checkout functionality
- Sales history and statistics export (PDF/Excel)
- Role-based access for admins and cashiers

## License

This project is provided for demonstration purposes and does not include a specific license.
