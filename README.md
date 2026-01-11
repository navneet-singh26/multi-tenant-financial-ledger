
# Multi-Entity Financial Ledger with RBAC

A sophisticated multi-tenant financial ledger system built with Django, featuring PostgreSQL schema-based isolation, granular RBAC, and payment gateway integrations.

## 🚀 Features

### Core Capabilities
- **Multi-Tenancy**: PostgreSQL schema-based isolation for complete data segregation
- **RBAC System**: Hierarchical role-based access control with object-level permissions
- **Financial Ledger**: Double-entry bookkeeping with audit trails
- **Payment Integration**: Pluggable adapters for Razorpay, Stripe, and custom gateways
- **API Optimization**: Sub-second response times for million-row datasets
- **Real-time Processing**: Celery-based async task processing
- **Monitoring**: Prometheus metrics and Grafana dashboards

### Technical Highlights
- Django 4.2 with Django Rest Framework
- PostgreSQL 15 with schema-based multi-tenancy
- Redis for caching and message brokering
- Celery for distributed task processing
- JWT authentication with refresh token rotation
- Comprehensive API documentation with Swagger/ReDoc

## 📋 Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optional)

## 🛠️ Installation

### Using Docker (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd financial_ledger