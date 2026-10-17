# Ecomm

A Django-based storefront for browsing products, managing a session-backed shopping cart, and completing checkout through Razorpay. The project also includes customer registration with email verification and a Django admin interface for managing catalog data.

## Features

- Product catalog with categories, images, and size and color variants
- Product detail pages with variant-based pricing
- Shopping cart with quantity updates and item removal
- Razorpay order creation and payment-signature verification
- Customer registration, login, and email verification
- Django admin management for products, categories, product images, and variants
- SQLite database for local development

## Technology

- Python
- Django 6.1.1
- SQLite
- Razorpay Checkout
- Pillow for image fields

## Getting started

### Requirements

- Python compatible with Django 6.1.1
- pip

### Install

From the project root, create and activate a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the application dependencies:

```bash
python -m pip install "Django==6.1.1" Pillow
```

Apply database migrations and create an administrator account:

```bash
python manage.py migrate
python manage.py createsuperuser
```

Start the development server:

```bash
python manage.py runserver
```

Visit [http://127.0.0.1:8000/](http://127.0.0.1:8000/) for the storefront and [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/) for the admin site. Add categories, products, and product images through the admin before browsing the catalog.

## Configuration

The application reads the following optional settings from process environment variables. The project does not load `.env` files automatically; set these variables in your shell or hosting environment.

| Variable | Purpose | Default |
| --- | --- | --- |
| `RAZORPAY_KEY_ID` | Razorpay API key ID and checkout key | Empty |
| `RAZORPAY_KEY_SECRET` | Razorpay API key secret; used to verify payment signatures | Empty |
| `EMAIL_BACKEND` | Django email backend | SMTP backend |
| `EMAIL_HOST` | SMTP server host | `smtp.gmail.com` |
| `EMAIL_PORT` | SMTP server port | `587` |
| `EMAIL_USE_TLS` | Enable SMTP TLS (`true` or `false`) | `true` |
| `EMAIL_HOST_USER` | SMTP account username / sender address | Empty |
| `EMAIL_HOST_PASSWORD` | SMTP account password or app password | Empty |
| `DEFAULT_FROM_EMAIL` | From address for outgoing messages | `EMAIL_HOST_USER` |
| `SITE_URL` | Public base URL used in account-verification links | `http://127.0.0.1:8000` |

For example, in PowerShell:

```powershell
$env:RAZORPAY_KEY_ID = "your-key-id"
$env:RAZORPAY_KEY_SECRET = "your-key-secret"
$env:EMAIL_HOST_USER = "you@example.com"
$env:EMAIL_HOST_PASSWORD = "your-smtp-app-password"
$env:SITE_URL = "http://127.0.0.1:8000"
```

In production, use Razorpay credentials intended for the appropriate environment and keep all credentials out of source control. Without both Razorpay variables, checkout is unavailable. Configure working SMTP settings to send registration-verification emails.

## Main routes

| URL | Description |
| --- | --- |
| `/` | Storefront and product listing |
| `/products/<slug>/` | Product detail |
| `/products/<slug>/add-to-cart/` | Add a product to the cart |
| `/products/cart/` | View the cart |
| `/products/checkout/` | Start checkout |
| `/accounts/register/` | Register an account |
| `/accounts/login/` | Log in |
| `/accounts/activate/<token>/` | Verify an account email |
| `/admin/` | Django administration |

## Project layout

```text
accounts/      Registration, login, profiles, and email verification
base/          Shared model and email utilities
ecomm/         Django project settings and root URL configuration
home/          Storefront landing page
products/      Catalog, variants, cart, and payment workflows
media/         User-uploaded product and category images
public/static/ Project static assets
templates/     Django HTML templates
manage.py      Django management commands
```

## Static files and media

During local development, Django serves uploaded media from `media/` while `DEBUG` is enabled. For deployment, configure a persistent media storage location and a production static-file host. Collect static assets with:

```bash
python manage.py collectstatic
```

## Production notes

The checked-in settings are for local development. Before deploying, use a unique secret key supplied securely through configuration, set `DEBUG = False`, configure `ALLOWED_HOSTS`, use a production-ready database and static/media storage, and review Django's deployment checklist. Do not use the development database or development server as a production setup.

## Tests

Run the Django test suite with:

```bash
python manage.py test
```
