# Centralized Construction Management System (CCMS)

A comprehensive, web-based platform designed to streamline and digitize construction project management. Built with Django, CCMS facilitates seamless collaboration between the head office, site personnel, and external stakeholders (such as consultants and clients).

## 🚀 Key Features

- **Project & Company Management**: Manage multiple projects, contractors, consultants, vendors, and subcontractors in one place.
- **Role-Based Access Control**: Tailored dashboards and permissions for various roles including HQ Directors, Project Managers, Site Engineers, HSE Officers, QA/QC, Document Controllers, and Clients.
- **Daily & Progress Reporting**: Track daily site activities, manpower, equipment, and material usage. Submit and review overall project progress with photo and document attachments.
- **Cost Control & Invoicing**: Monitor project budgets, manage Variation Orders (VO), process project invoices (Progress, Advance, Final), and track financial records.
- **Document Control**: Centralized repository for Shop Drawings, Method Statements, RFIs, NCRs, and Letters, featuring a multi-stage approval workflow.
- **Quality Assurance (QA/QC) & HSE**: Manage QA/QC site inspections, and track HSE reports (Incidents, Near Misses, Unsafe Acts/Conditions, Audits).
- **Schedule Management**: Track planned vs. actual project timelines, activity durations, and completion weights.
- **Meeting & Action Tracking**: Record meeting minutes (Site, Management, Design, etc.) and track assigned action items to closure.
- **Risk Register**: Identify, assess, and mitigate project risks.

## 🛠️ Technology Stack

- **Backend**: Python / Django
- **Frontend**: HTML5, CSS3, JavaScript (Django Templates)
- **Database**: SQLite (Development) / PostgreSQL or MySQL (Production ready)

## 📦 Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Akara96/CENTRALIZED-CONSTRUCTION-MANAGEMENT-SYSTEM--CCMS-.git
   cd CENTRALIZED-CONSTRUCTION-MANAGEMENT-SYSTEM--CCMS-
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   
   # Windows
   .venv\Scripts\activate
   
   # macOS/Linux
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply database migrations:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **(Optional) Seed initial data or create a superuser:**
   ```bash
   python manage.py createsuperuser
   ```

6. **Start the development server:**
   ```bash
   python manage.py runserver
   ```
   *The application will be available at `http://127.0.0.1:8000/`*
