# Wardrobe Catalog

An AI-powered clothing care assistant. Photograph a care label → Claude Vision extracts the care instructions → generates a scannable NFC/QR tag. Scan the tag at laundry time to instantly see how to wash the item — no hunting for labels, no decoding cryptic symbols.

## The Problem

Clothes get ruined because care labels are small, cryptic, and easy to ignore. This is especially painful when someone else is doing your laundry and doesn't know which items need special handling.

## The Solution

- **One-time setup:** Photograph a garment's care label → AI extracts the instructions → attach a scannable tag to the garment
- **At laundry time:** Scan the tag → instantly see plain-English care instructions on your phone

## Demo

Live app: [wardrobe-catalog-production.up.railway.app](https://wardrobe-catalog-production.up.railway.app)

## How It Works

```
[Care label photo]
        ↓
[Claude Vision API extracts care rules as JSON]
        ↓
[Saved to Supabase (PostgreSQL)]
        ↓
[NFC/QR tag generated pointing to care page]
        ↓
[Scan tag → mobile-friendly care page loads instantly]
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| AI extraction | Claude Vision API (Anthropic) |
| Backend | Python + Flask |
| Database | Supabase (PostgreSQL) |
| Hosting | Railway |
| Tags | Washable NFC tags |

## Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/sreejith0217/wardrobe-catalog.git
cd wardrobe-catalog
pip3 install -r requirements.txt
```

### 2. Set environment variables

```bash
export ANTHROPIC_API_KEY=your-anthropic-key
export SUPABASE_URL=your-supabase-project-url
export SUPABASE_KEY=your-supabase-secret-key
```

### 3. Set up Supabase

Create a table in your Supabase project:

```sql
create table items (
  item_id text primary key,
  data jsonb not null,
  created_at timestamp with time zone default now()
);
```

### 4. Run locally

```bash
python3 app.py
```

Open `http://localhost:5001` in your browser.

### 5. Catalog an item via command line

```bash
python3 catalog.py /path/to/garment.jpg /path/to/label.jpg "Item Name"
```

## Project Structure

```
wardrobe-catalog/
├── app.py              # Flask web app
├── catalog.py          # CLI cataloging script
├── db.py               # Supabase database helpers
├── requirements.txt
├── Procfile            # Railway deployment config
└── templates/
    ├── index.html      # Item list
    ├── item.html       # Care page (QR/NFC destination)
    ├── add.html        # Mobile-friendly add item form
    └── 404.html
```

## Deploying to Railway

```bash
railway login
railway init
railway up
railway variables set ANTHROPIC_API_KEY=xxx
railway variables set SUPABASE_URL=xxx
railway variables set SUPABASE_KEY=xxx
```

## Built By

[Sreejith Jayan](https://www.linkedin.com/in/sreejithjayan/) — Senior Product Operations Manager at LinkedIn, learning to build AI-powered tools.

---

*Part of my [AI apps portfolio](https://github.com/sreejith0217)*
