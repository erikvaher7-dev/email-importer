# IMAP to Django/Neo4j Email Importer

A robust email importer that connects to IMAP servers (Gmail, Outlook, etc.), parses email data, normalizes it, deduplicates messages, and stores them in either PostgreSQL (via Django) or Neo4j databases. The system handles threading, contacts, and email metadata, creating a people-centric email database suitable for analytics or email client applications.

## Mission

This project provides a comprehensive solution for importing emails from IMAP servers, normalizing data to reduce redundancy, and organizing messages into threads and people-centric graphs. The resulting database can power conversation-focused email clients and enable advanced features such as contact search and complete conversation views.

### Core Objectives

- **Data Normalization**: Clean, standardize, and deduplicate email data
- **Threading**: Group related messages into conversations
- **People-Centric Model**: Connect messages to people, not just email addresses
- **Idempotent Import**: Ensure multiple import runs do not create duplicates
- **Incremental Updates**: Handle large mailboxes efficiently through batch processing

## Features

- **Multi-Account Support**: Import emails from multiple IMAP accounts into a single database
- **IMAP Integration**: Compatible with any IMAP server (Gmail, Outlook, etc.)
- **MIME Parsing**: Extract plain text, HTML body parts, and attachment metadata
- **Global Deduplication**: SHA256 hash-based deduplication across all accounts
- **Thread Building**: Reconstruct email threads using `In-Reply-To` and `References` headers
- **Idempotent Imports**: Safe to re-run without creating duplicates
- **Streaming Mode**: Process large mailboxes (100k+ emails) incrementally
- **Checkpointing**: Resume interrupted imports from the last processed email

## Getting Started

Follow these instructions to set up and run the project locally.

### Prerequisites

- **Python 3.10+**
- **Docker + Docker Compose** (for running databases)
- **Email Account**: Gmail or Outlook account with IMAP access enabled
- **Python Dependencies**: Listed in `requirements.txt`

### Installation

#### 1. Clone the Repository

```bash
git clone https://github.com/your-username/imap2django.git
cd imap2django
```

#### 2. Start Docker Containers

Launch PostgreSQL and Neo4j services using Docker Compose:

```bash
docker compose up -d
```

This starts:
- **PostgreSQL** (for Django/SQL backend)
- **Neo4j** (for graph database backend)

#### 3. Create Python Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

#### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 5. Configure Environment Variables

Copy the example environment file and configure your settings:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=1

DB_NAME=imap2django
DB_USER=imap2django
DB_PASSWORD=imap2django
DB_HOST=localhost
DB_PORT=5432

NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123
```

**Note**: For Gmail or Outlook with 2FA enabled, use an [App Password](https://support.google.com/accounts/answer/185833).

#### 6. Initialize Django Database

Run migrations to set up the database schema:

```bash
python manage.py makemigrations
python manage.py migrate
```

Create a superuser for Django admin access:

```bash
python manage.py createsuperuser
```

#### 7. Configure IMAP Account

Create `config/account.json` with your IMAP credentials:

```json
{
  "account_email": "yourname@outlook.com",
  "provider": "outlook",
  "imap": {
    "host": "outlook.office365.com",
    "port": 993,
    "ssl": true,
    "username": "yourname@outlook.com",
    "password": "YOUR_APP_PASSWORD_HERE"
  }
}
```

**Security Note**: Replace `YOUR_APP_PASSWORD_HERE` with your actual app password. Never commit credentials to version control.

### Usage

#### Running the Importer

Start the email import process:

```bash
python manage.py import_imap --config config/account.json --backend sql --batch 200 --max 10
```

**Parameters**:
- `--config`: Path to IMAP account configuration file
- `--backend`: Database backend (`sql` or `neo4j`)
- `--batch`: Number of emails to process per batch (default: 200)
- `--max`: Maximum number of emails to import (useful for testing)

The importer is idempotent—running it multiple times will not create duplicates.

#### Viewing Imported Data

Start the Django development server:

```bash
python manage.py runserver
```

Access the admin panel at [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

Available data models:
- **Account**: Email accounts
- **Mailbox**: Folders (INBOX, Sent Items, etc.)
- **Messages**: Imported emails
- **Recipients**: Email contacts
- **Threads**: Grouped email conversations

#### Rebuilding Threads

To rebuild conversation threads:

```bash
python manage.py rebuild_threads
```

To use Neo4j instead of PostgreSQL:

1. Ensure the Neo4j container is running (via Docker)
2. Configure Neo4j credentials in your `.env` file:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123
```

3. Run the import with the Neo4j backend:

```bash
python manage.py import_imap --config config/account.json --backend neo4j --batch 200 --max 10
```

## Testing

To ensure the project is working correctly:

- Re-run the import with different folders and verify no duplicates appear
- Check if threads are correctly grouped after running `rebuild_threads`
- Open the Neo4j browser (if using Neo4j) at [http://localhost:7474](http://localhost:7474) to explore the graph of messages, threads, and people
