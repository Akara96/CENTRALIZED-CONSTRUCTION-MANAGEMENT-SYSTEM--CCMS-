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

## 📊 Dashboard Overview

The CCMS Dashboard provides a centralized, real-time view of project health:
- **Progress Metrics**: Visualize overall project completion, including specific civil, architectural, and MEP progress.
- **Financial Summaries**: Track Budget vs. Actual Cost, Invoice statuses, and Pending Variation Orders (VO).
- **Approval Center**: Quick access to pending approvals for Reports, Documents, and Finances, tailored to the logged-in user's role.
- **HSE & Quality Snapshot**: Overview of recent incidents, open NCRs, and site safety metrics.
- **Recent Activities**: A feed of the latest daily reports, uploaded documents, and meeting minutes.

## 🔄 System Workflow

1. **Project Setup & Planning**
   - Admin/HQ creates a new project and assigns contractors, consultants, and the internal team.
   - Initial budgets, Master Schedules, and Bill of Quantities (BoQ) are uploaded.
2. **Execution & Daily Operations (Site Level)**
   - Site Engineers submit **Daily Reports** detailing manpower, equipment, and material usage.
   - Supervisors and QA/QC conduct site inspections and log **HSE Reports**.
   - Logistics update material stock and receive deliveries.
3. **Review & Multi-Tier Approvals**
   - Documents (Shop Drawings, RFIs) and Progress Reports go through a structured approval flow: `Reviewer` ➡️ `Manager` ➡️ `Consultant` ➡️ `HQ Approval`.
   - Finance validates expenses and processes Invoices/VOs based on field data.
4. **Monitoring & Handover**
   - HQ Directors monitor the portfolio via the high-level dashboard.
   - Final progress claims are verified against approved BOQs and Daily Reports.
   - Project handover and document archiving.


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
