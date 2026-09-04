from django.shortcuts import render, redirect, reverse
from django.test import RequestFactory
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required

from django.db import transaction
from django.db.models import Sum, Avg, Q, Count, Max
from django.utils import timezone
from .models import (
    UserProfile, Company, Project, ProjectTeam, ProgressReport,
    DailyReport, ProgressPhoto, DailyReportDocument, SiteActivity, WorkItem, CostSummary,
    DailyReportWorkProgress, DailyReportMaterialUsage, DailyReportManpowerUsage, DailyReportEquipmentUsage,
    VariationOrder, Invoice, FinancialRecord, FinancialRecordHistory, Schedule, QAQCInspection, HSEReport,
    Meeting, MeetingAction, Document, DocumentRevisionHistory, Approval, RiskRegister,
    MaterialTest, MaterialRequest, MaterialWaste, BIMModel, BIMClash, InterimPaymentCertificate,
    MaterialItem, StockTransaction, LogisticsRecord, RFI, NCR, SiteInstruction, Manpower, Attendance, Equipment, EquipmentUsage, EquipmentMaintenance, Notification,
    ChatRoom, ChatMessage, ProjectReadinessChecklist, PurchaseRequest, ItemProgressReport
)
from .services import workflow as wf
import datetime
import csv
import io
import re
import urllib.request
from decimal import Decimal, InvalidOperation


LOGISTICS_ROLES = ['LOGISTICS', 'STOREKEEPER', 'PROJECT_MANAGER', 'SITE_ENGINEER', 'ADMIN_SYSTEM']
ALL_ACCESS_ROLES = {'ADMIN_SYSTEM', 'HQ_DIRECTOR', 'PROJECT_DIRECTOR'}

ALL_DASHBOARD_TABS = {
    'hq-dashboard',
    'project-setup',
    'site-operation',
    'review-validation',
    'approval-system',
    'boq-workitems',
    'material-supply',
    'logistics',
    'inventory',
    'manpower',
    'equipment',
    'notifications',
    'cost-control',
    'rfi-site-instruction',
    'qa-qc',
    'hse',
    'document-register',
    'reports',
    'report-per-item',
    'bim-clash',
}

ROLE_DASHBOARD_TABS = {
    'PROJECT_MANAGER': {
        'hq-dashboard', 'project-setup', 'site-operation', 'review-validation',
        'approval-system', 'boq-workitems', 'material-supply', 'logistics',
        'inventory', 'manpower', 'equipment', 'notifications', 'cost-control',
        'rfi-site-instruction', 'qa-qc', 'hse', 'document-register', 'reports', 'report-per-item',
    },
    'SITE_ENGINEER': {
        'hq-dashboard', 'site-operation', 'review-validation', 'boq-workitems',
        'material-supply', 'equipment', 'notifications', 'rfi-site-instruction',
        'document-register', 'reports', 'report-per-item',
    },
    'SUPERVISOR': {
        'hq-dashboard', 'site-operation', 'review-validation', 'boq-workitems',
        'material-supply', 'equipment', 'notifications', 'rfi-site-instruction',
        'reports', 'report-per-item',
    },
    'COST_ENGINEER': {
        'hq-dashboard', 'review-validation', 'approval-system', 'boq-workitems',
        'cost-control', 'notifications', 'reports', 'report-per-item',
    },
    'FINANCE_HQ': {
        'hq-dashboard', 'approval-system', 'cost-control', 'notifications',
        'reports', 'report-per-item',
    },
    'FINANCE_SITE': {
        'hq-dashboard', 'approval-system', 'cost-control', 'notifications',
        'reports', 'report-per-item',
    },
    'HSE_OFFICER': {
        'hq-dashboard', 'review-validation', 'hse', 'notifications', 'reports', 'report-per-item',
    },
    'QA_QC': {
        'hq-dashboard', 'review-validation', 'qa-qc', 'notifications', 'reports', 'report-per-item',
    },
    'STOREKEEPER': {
        'hq-dashboard', 'material-supply', 'inventory', 'logistics',
        'notifications', 'reports', 'report-per-item',
    },
    'LOGISTICS': {
        'hq-dashboard', 'material-supply', 'logistics', 'inventory',
        'notifications', 'reports', 'report-per-item',
    },
    'ADMIN_SITE': {
        'hq-dashboard', 'manpower', 'equipment', 'site-operation',
        'notifications', 'reports', 'report-per-item',
    },
    'DOC_CONTROLLER': {
        'hq-dashboard', 'document-register', 'rfi-site-instruction',
        'notifications', 'reports', 'report-per-item',
    },
    'CONSULTANT': {
        'hq-dashboard', 'review-validation', 'approval-system',
        'rfi-site-instruction', 'qa-qc', 'hse', 'document-register',
        'notifications', 'reports', 'report-per-item',
    },
    'CLIENT': {
        'hq-dashboard', 'boq-workitems', 'reports', 'report-per-item', 'notifications',
    },
    'BIM_MANAGER': {
        'hq-dashboard', 'bim-clash', 'document-register', 'notifications',
        'reports', 'report-per-item',
    },
    'ENV_SPECIALIST': {
        'hq-dashboard', 'hse', 'notifications', 'reports', 'report-per-item',
    },
}


def _parse_decimal(value, default='0'):
    try:
        return Decimal(str(value or default))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(default)


def _status_for_logistics_type(record_type):
    return {
        'DELIVERY_TRACKING': 'ON_DELIVERY',
        'MATERIAL_RECEIVING': 'RECEIVED',
        'STOCK_ISSUE': 'ISSUED',
        'STOCK_RETURN': 'RETURNED',
        'STOCK_TRANSFER': 'TRANSFERRED',
    }.get(record_type, 'PLANNED')


def _stock_type_for_logistics_type(record_type):
    return {
        'MATERIAL_RECEIVING': 'IN',
        'STOCK_ISSUE': 'OUT',
        'STOCK_RETURN': 'RETURN',
        'STOCK_TRANSFER': 'OUT',
    }.get(record_type)


def _import_project_boq_from_url(user, project, boq_csv_url):
    if not boq_csv_url:
        return False
    before_count = WorkItem.objects.filter(project=project).count()
    factory = RequestFactory()
    request = factory.post(reverse('import_boq_excel'), {
        'project_id': str(project.id),
        'boq_csv_url': boq_csv_url,
        'overwrite': 'on',
    })
    request.user = user
    request.session = {}
    request._messages = FallbackStorage(request)
    import_boq_excel(request)
    return WorkItem.objects.filter(project=project).count() > before_count


def _add_months(date_value, months):
    month = date_value.month - 1 + months
    year = date_value.year + month // 12
    month = month % 12 + 1
    days_in_month = [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    day = min(date_value.day, days_in_month[month - 1])
    return datetime.date(year, month, day)


def _planned_progress_on_date(project, target_date):
    start_date = project.start_date
    end_date = project.end_date
    if not start_date or not end_date or end_date <= start_date:
        return 0.0
    if target_date <= start_date:
        return 0.0
    if target_date >= end_date:
        return 100.0
    total_days = (end_date - start_date).days
    elapsed_days = (target_date - start_date).days
    return max(0.0, min((elapsed_days / total_days) * 100.0, 100.0))


def _latest_progress_on_or_before(project, target_date=None):
    progress_qs = project.progress_reports.order_by('-report_date')
    if target_date:
        progress_qs = progress_qs.filter(report_date__lte=target_date)
    latest_report = progress_qs.first()
    if latest_report:
        return float(latest_report.overall_progress or 0)

    daily_qs = project.daily_reports.filter(status='APPROVED').order_by('-date')
    if target_date:
        daily_qs = daily_qs.filter(date__lte=target_date)
    approved_daily = daily_qs.first()
    if approved_daily:
        return float(approved_daily.progress_percentage or 0)

    avg = project.work_items.aggregate(Avg('progress_percent'))['progress_percent__avg']
    return float(avg or 0)


def _project_actual_cost(project, target_date=None):
    qs = project.cost_summaries.all()
    if target_date:
        dated_total = qs.filter(report_date__isnull=False, report_date__lte=target_date).aggregate(total=Sum('actual'))['total']
        if dated_total is not None:
            return float(dated_total or 0)
    total = qs.aggregate(total=Sum('actual'))['total']
    if total:
        return float(total)
    return float(project.invoices.filter(status='PAID').aggregate(total=Sum('amount'))['total'] or 0)


def _project_delay_count(project, today):
    return project.schedules.filter(
        Q(status='DELAYED') |
        Q(planned_finish__lt=today, status__in=['NOT_STARTED', 'IN_PROGRESS'])
    ).count()


def _project_low_stock_count(project):
    return sum(
        1 for item in project.material_items.all()
        if item.minimum_stock > 0 and item.is_low_stock
    )


def _build_executive_kpis(project, today, *, actual_progress, labor_data, total_budget, total_actual):
    latest_actual = 0.0
    valid_actual = [value for value in actual_progress if value is not None]
    if valid_actual:
        latest_actual = float(valid_actual[-1])
    else:
        latest_actual = _latest_progress_on_or_before(project, today)

    planned_today = _planned_progress_on_date(project, today)
    delay_gap = max(planned_today - latest_actual, 0.0)
    delay_count = _project_delay_count(project, today)
    budget_used = (total_actual / total_budget * 100) if total_budget > 0 else 0.0
    low_stock_count = _project_low_stock_count(project)
    pending_approvals = project.approvals.filter(status__in=['PENDING', 'REVIEWED']).count()
    material_pending = project.material_requests.filter(status__in=['SUBMITTED', 'APPROVED', 'DELIVERED']).count()
    material_usage = DailyReportMaterialUsage.objects.filter(daily_report__project=project).count()
    progress_reports_week = project.daily_reports.filter(
        date__gte=today - datetime.timedelta(days=6),
        date__lte=today,
        status='APPROVED',
    ).order_by('date')
    week_progress_values = [float(report.progress_percentage or 0) for report in progress_reports_week]
    progress_delta_week = max(week_progress_values) - min(week_progress_values) if len(week_progress_values) > 1 else 0.0
    labor_total_week = sum(labor_data)
    productivity = (progress_delta_week / labor_total_week) if labor_total_week else 0.0
    open_rfi_count = project.rfis.filter(status__in=['SUBMITTED', 'IN_REVIEW']).count()
    open_ncr_count = project.ncrs.filter(status__in=['OPEN', 'UNDER_REVIEW', 'CORRECTIVE_ACTION']).count()
    incident_count = project.hse_reports.filter(report_type='INCIDENT').count()
    near_miss_count = project.hse_reports.filter(report_type='NEAR_MISS').count()
    unsafe_act_count = project.hse_reports.filter(report_type='UNSAFE_ACT').count()
    unsafe_condition_count = project.hse_reports.filter(report_type='UNSAFE_CONDITION').count()
    active_manpower = project.manpowers.filter(is_active=True).count()

    decision_status = 'ON TRACK'
    if delay_gap > 10 or budget_used > 100 or open_ncr_count > 0:
        decision_status = 'CRITICAL'
    elif delay_gap > 5 or budget_used > (latest_actual + 15) or pending_approvals > 0 or low_stock_count > 0:
        decision_status = 'WATCH'

    alerts = []
    if delay_gap > 5 or delay_count > 0:
        alerts.append({
            'severity': 'danger' if delay_gap > 10 or delay_count > 0 else 'warning',
            'title': 'Delay Alert',
            'message': f'Actual {latest_actual:.2f}% vs planned {planned_today:.2f}%. {delay_count} schedule activity delayed.',
            'action': 'Review schedule baseline and recovery plan.',
        })
    if total_budget > 0 and (budget_used > latest_actual + 15 or budget_used >= 90):
        alerts.append({
            'severity': 'warning' if budget_used < 100 else 'danger',
            'title': 'Budget vs Actual',
            'message': f'Budget used {budget_used:.2f}% while progress is {latest_actual:.2f}%.',
            'action': 'Check cost category, committed cost, and payment claims.',
        })
    if low_stock_count > 0:
        alerts.append({
            'severity': 'warning',
            'title': 'Material Stock',
            'message': f'{low_stock_count} material item is at or below minimum stock.',
            'action': 'Prepare material request or purchase request.',
        })
    if material_pending > 0:
        alerts.append({
            'severity': 'info',
            'title': 'Material Request',
            'message': f'{material_pending} material request is still open.',
            'action': 'Follow approval, delivery, and receiving status.',
        })
    if pending_approvals > 0:
        alerts.append({
            'severity': 'info',
            'title': 'Pending Approval',
            'message': f'{pending_approvals} approval item is waiting for action.',
            'action': "Open Approval System and resolve step that waiting for.",
        })
    if open_ncr_count > 0 or open_rfi_count > 0:
        alerts.append({
            'severity': 'warning' if open_ncr_count else 'info',
            'title': 'Open Issue',
            'message': f'{open_rfi_count} RFI and {open_ncr_count} NCR/issue are open.',
            'action': 'Assign owner and target closure date.',
        })
    if not alerts:
        alerts.append({
            'severity': 'success',
            'title': 'No Critical Alert',
            'message': 'Project indicators are within expected range.',
            'action': 'Continue monitoring daily reports and approvals.',
        })

    recommendations = []
    if decision_status == 'CRITICAL':
        recommendations.append('Escalate in management meeting and agree corrective action.')
    if delay_gap > 5:
        recommendations.append('Update recovery schedule and monitor progress daily.')
    if total_budget > 0 and budget_used > latest_actual + 15:
        recommendations.append('Review high-cost categories before next payment approval.')
    if pending_approvals > 0:
        recommendations.append('Clear pending approvals to avoid workflow bottleneck.')
    if low_stock_count > 0:
        recommendations.append('Prioritize procurement for low-stock materials.')
    if not recommendations:
        recommendations.append('Maintain current execution plan and monitoring cadence.')

    return {
        'progress_percent': round(latest_actual, 2),
        'planned_progress_percent': round(planned_today, 2),
        'delay_gap_percent': round(delay_gap, 2),
        'delay_count': delay_count,
        'budget_used_percent': round(budget_used, 2),
        'material_usage_count': material_usage,
        'material_pending_count': material_pending,
        'low_stock_count': low_stock_count,
        'productivity': round(productivity, 4),
        'pending_approval_count': pending_approvals,
        'open_rfi_count': open_rfi_count,
        'open_ncr_count': open_ncr_count,
        'incident_count': incident_count,
        'near_miss_count': near_miss_count,
        'unsafe_act_count': unsafe_act_count,
        'unsafe_condition_count': unsafe_condition_count,
        'safety_total_count': incident_count + near_miss_count + unsafe_act_count + unsafe_condition_count,
        'active_manpower': active_manpower,
        'labor_today': labor_data[-1] if labor_data else 0,
        'decision_status': decision_status,
        'recommendations': recommendations,
        'alerts': alerts,
    }


def _build_dashboard_chart_data(projects):
    dashboard_data = {}
    today = datetime.date.today()

    for project in projects:
        start_date = project.start_date or today
        progress_labels = []
        planned_progress = []
        actual_progress = []

        reports = {
            report.report_date: float(report.overall_progress or 0)
            for report in project.progress_reports.order_by('report_date')
        }
        latest_actual = 0.0

        for index in range(12):
            point_date = _add_months(start_date, index)
            progress_labels.append(point_date.strftime('%b %Y'))
            planned_progress.append(round(_planned_progress_on_date(project, point_date), 2))

            for report_date in sorted(reports):
                if report_date <= point_date:
                    latest_actual = reports[report_date]
            actual_progress.append(round(latest_actual, 2) if point_date <= today else None)

        labor_dates = [today - datetime.timedelta(days=offset) for offset in range(6, -1, -1)]
        labor_labels = [date_value.strftime('%d-%b') for date_value in labor_dates]
        labor_data = [
            int(project.daily_reports.filter(date=date_value).aggregate(total=Sum('manpower_count'))['total'] or 0)
            for date_value in labor_dates
        ]

        material_labels = ['Submitted', 'Approved', 'Delivered', 'Received']
        material_statuses = ['SUBMITTED', 'APPROVED', 'DELIVERED', 'RECEIVED']
        material_data = [
            project.material_requests.filter(status=status).count()
            for status in material_statuses
        ]

        rfi_labels = ['Submitted', 'In Review', 'Closed']
        rfi_statuses = ['SUBMITTED', 'IN_REVIEW', 'CLOSED']
        rfi_data = [
            project.rfis.filter(status=status).count()
            for status in rfi_statuses
        ]

        cost_labels = []
        planned_cost = []
        actual_cost = []
        budget = float(project.budget or 0)
        for index in range(9):
            point_date = _add_months(start_date, index)
            cost_labels.append(point_date.strftime('%b %Y'))
            planned_cost.append(round((budget * _planned_progress_on_date(project, point_date) / 100.0) / 1000000, 2))
            actual_value = project.cost_summaries.filter(
                report_date__isnull=False,
                report_date__lte=point_date,
            ).aggregate(total=Sum('actual'))['total']
            if actual_value is None and point_date <= today:
                actual_value = project.cost_summaries.aggregate(total=Sum('actual'))['total'] or 0
            actual_cost.append(round(float(actual_value or 0) / 1000000, 2) if point_date <= today else None)

        cost_rows = list(
            project.cost_summaries.values('category')
            .annotate(total=Sum('actual'))
            .order_by('-total')[:5]
        )
        cost_category_labels = [row['category'] for row in cost_rows]
        cost_category_data = [round(float(row['total'] or 0), 2) for row in cost_rows]
        if not any(cost_category_data):
            work_item_rows = list(
                project.work_items.values('category')
                .annotate(total=Sum('boq_amount'))
                .order_by('-total')[:5]
            )
            cost_category_labels = [row['category'] or 'Uncategorized' for row in work_item_rows]
            cost_category_data = [round(float(row['total'] or 0), 2) for row in work_item_rows]

        total_budget = float(project.budget or 0)
        total_actual = _project_actual_cost(project)
        kpis = _build_executive_kpis(
            project,
            today,
            actual_progress=actual_progress,
            labor_data=labor_data,
            total_budget=total_budget,
            total_actual=total_actual,
        )

        dashboard_data[str(project.id)] = {
            'name': project.name,
            'progress': {
                'labels': progress_labels,
                'planned': planned_progress,
                'actual': actual_progress,
            },
            'labor': {
                'labels': labor_labels,
                'data': labor_data,
            },
            'material': {
                'labels': material_labels,
                'data': material_data,
            },
            'rfi': {
                'labels': rfi_labels,
                'data': rfi_data,
            },
            'cost_curve': {
                'labels': cost_labels,
                'planned': planned_cost,
                'actual': actual_cost,
            },
            'cost_category': {
                'labels': cost_category_labels,
                'data': cost_category_data,
            },
            'cost_performance': {
                'budget': round(total_budget, 2),
                'actual': round(total_actual, 2),
                'variance': round(total_budget - total_actual, 2),
                'used_percent': round((total_actual / total_budget * 100), 2) if total_budget > 0 else 0,
            },
            'kpis': kpis,
            'alerts': kpis['alerts'],
            'recommendations': kpis['recommendations'],
        }

    aggregate_payload = _build_all_projects_dashboard_payload(projects, today)
    return {'all': aggregate_payload, **dashboard_data}


def _build_all_projects_dashboard_payload(projects, today):
    project_list = list(projects)
    project_count = len(project_list)
    month_start = today.replace(day=1)
    progress_points = [_add_months(month_start, index - 11) for index in range(12)]
    progress_labels = [point.strftime('%b %Y') for point in progress_points]

    if project_count:
        planned_progress = [
            round(sum(_planned_progress_on_date(project, point) for project in project_list) / project_count, 2)
            for point in progress_points
        ]
        actual_progress = [
            round(sum(_latest_progress_on_or_before(project, point) for project in project_list) / project_count, 2)
            for point in progress_points
        ]
    else:
        planned_progress = [0 for _ in progress_points]
        actual_progress = [0 for _ in progress_points]

    labor_dates = [today - datetime.timedelta(days=offset) for offset in range(6, -1, -1)]
    labor_labels = [date_value.strftime('%d-%b') for date_value in labor_dates]
    labor_data = [
        int(DailyReport.objects.filter(project__in=project_list, date=date_value).aggregate(total=Sum('manpower_count'))['total'] or 0)
        for date_value in labor_dates
    ]

    material_labels = ['Submitted', 'Approved', 'Delivered', 'Received']
    material_statuses = ['SUBMITTED', 'APPROVED', 'DELIVERED', 'RECEIVED']
    material_data = [
        MaterialRequest.objects.filter(project__in=project_list, status=status).count()
        for status in material_statuses
    ]

    rfi_labels = ['Submitted', 'In Review', 'Closed']
    rfi_statuses = ['SUBMITTED', 'IN_REVIEW', 'CLOSED']
    rfi_data = [
        RFI.objects.filter(project__in=project_list, status=status).count()
        for status in rfi_statuses
    ]

    cost_points = [_add_months(month_start, index - 8) for index in range(9)]
    cost_labels = [point.strftime('%b %Y') for point in cost_points]
    planned_cost = []
    actual_cost = []
    for point in cost_points:
        planned_cost.append(round(sum(
            float(project.budget or 0) * _planned_progress_on_date(project, point) / 100.0
            for project in project_list
        ) / 1000000, 2))
        actual_cost.append(round(sum(_project_actual_cost(project, point) for project in project_list) / 1000000, 2))

    cost_rows = list(
        CostSummary.objects.filter(project__in=project_list).values('category')
        .annotate(total=Sum('actual'))
        .order_by('-total')[:5]
    )
    cost_category_labels = [row['category'] or 'Uncategorized' for row in cost_rows]
    cost_category_data = [round(float(row['total'] or 0), 2) for row in cost_rows]
    if not any(cost_category_data):
        work_item_rows = list(
            WorkItem.objects.filter(project__in=project_list).values('category')
            .annotate(total=Sum('boq_amount'))
            .order_by('-total')[:5]
        )
        cost_category_labels = [row['category'] or 'Uncategorized' for row in work_item_rows]
        cost_category_data = [round(float(row['total'] or 0), 2) for row in work_item_rows]

    total_budget = sum(float(project.budget or 0) for project in project_list)
    total_actual = sum(_project_actual_cost(project) for project in project_list)
    planned_today = (
        sum(_planned_progress_on_date(project, today) for project in project_list) / project_count
        if project_count else 0.0
    )
    actual_today = actual_progress[-1] if actual_progress else 0.0
    delay_gap = max(planned_today - actual_today, 0.0)
    delay_count = sum(_project_delay_count(project, today) for project in project_list)
    low_stock_count = sum(_project_low_stock_count(project) for project in project_list)
    pending_approvals = Approval.objects.filter(project__in=project_list, status__in=['PENDING', 'REVIEWED']).count()
    material_pending = MaterialRequest.objects.filter(project__in=project_list, status__in=['SUBMITTED', 'APPROVED', 'DELIVERED']).count()
    material_usage = DailyReportMaterialUsage.objects.filter(daily_report__project__in=project_list).count()
    open_rfi_count = RFI.objects.filter(project__in=project_list, status__in=['SUBMITTED', 'IN_REVIEW']).count()
    open_ncr_count = NCR.objects.filter(project__in=project_list, status__in=['OPEN', 'UNDER_REVIEW', 'CORRECTIVE_ACTION']).count()
    incident_count = HSEReport.objects.filter(project__in=project_list, report_type='INCIDENT').count()
    near_miss_count = HSEReport.objects.filter(project__in=project_list, report_type='NEAR_MISS').count()
    unsafe_act_count = HSEReport.objects.filter(project__in=project_list, report_type='UNSAFE_ACT').count()
    unsafe_condition_count = HSEReport.objects.filter(project__in=project_list, report_type='UNSAFE_CONDITION').count()
    active_manpower = Manpower.objects.filter(project__in=project_list, is_active=True).count()
    week_reports = DailyReport.objects.filter(
        project__in=project_list,
        date__gte=today - datetime.timedelta(days=6),
        date__lte=today,
        status='APPROVED',
    ).order_by('date')
    week_progress_values = [float(report.progress_percentage or 0) for report in week_reports]
    progress_delta_week = max(week_progress_values) - min(week_progress_values) if len(week_progress_values) > 1 else 0.0
    productivity = (progress_delta_week / sum(labor_data)) if sum(labor_data) else 0.0
    budget_used = (total_actual / total_budget * 100) if total_budget > 0 else 0.0

    decision_status = 'ON TRACK'
    if delay_gap > 10 or budget_used > 100 or open_ncr_count > 0:
        decision_status = 'CRITICAL'
    elif delay_gap > 5 or budget_used > (actual_today + 15) or pending_approvals > 0 or low_stock_count > 0:
        decision_status = 'WATCH'

    alerts = []
    if delay_gap > 5 or delay_count > 0:
        alerts.append({
            'severity': 'danger' if delay_gap > 10 or delay_count > 0 else 'warning',
            'title': 'Delay Alert',
            'message': f'Average actual {actual_today:.2f}% vs planned {planned_today:.2f}%. {delay_count} delayed activity across projects.',
            'action': 'Review delayed projects and recovery schedule.',
        })
    if total_budget > 0 and (budget_used > actual_today + 15 or budget_used >= 90):
        alerts.append({
            'severity': 'warning' if budget_used < 100 else 'danger',
            'title': 'Budget vs Actual',
            'message': f'Budget used {budget_used:.2f}% while average progress is {actual_today:.2f}%.',
            'action': 'Review cost performance before approving new payments.',
        })
    if low_stock_count > 0:
        alerts.append({
            'severity': 'warning',
            'title': 'Material Stock',
            'message': f'{low_stock_count} material item is below minimum stock.',
            'action': 'Check material request and purchase request backlog.',
        })
    if pending_approvals > 0:
        alerts.append({
            'severity': 'info',
            'title': 'Pending Approval',
            'message': f'{pending_approvals} approval item is waiting across all projects.',
            'action': "Open Approval System and resolve approval that waiting for.",
        })
    if open_rfi_count > 0 or open_ncr_count > 0:
        alerts.append({
            'severity': 'warning' if open_ncr_count else 'info',
            'title': 'Open Issue',
            'message': f'{open_rfi_count} open RFI and {open_ncr_count} open NCR/issue.',
            'action': 'Prioritize unresolved technical and quality issues.',
        })
    if not alerts:
        alerts.append({
            'severity': 'success',
            'title': 'No Critical Alert',
            'message': 'All project indicators are within expected range.',
            'action': 'Continue monitoring realtime data flow.',
        })

    recommendations = []
    if decision_status == 'CRITICAL':
        recommendations.append('Escalate critical projects to executive review.')
    if delay_gap > 5:
        recommendations.append('Request recovery plan from project managers.')
    if budget_used > actual_today + 15:
        recommendations.append('Hold andn-critical spend until cost variance is explained.')
    if pending_approvals > 0:
        recommendations.append('Clear pending approval queue to avoid execution delay.')
    if low_stock_count > 0:
        recommendations.append('Prioritize procurement for low-stock materials.')
    if not recommendations:
        recommendations.append('Maintain current execution plan and monitor daily updates.')

    kpis = {
        'progress_percent': round(actual_today, 2),
        'planned_progress_percent': round(planned_today, 2),
        'delay_gap_percent': round(delay_gap, 2),
        'delay_count': delay_count,
        'budget_used_percent': round(budget_used, 2),
        'material_usage_count': material_usage,
        'material_pending_count': material_pending,
        'low_stock_count': low_stock_count,
        'productivity': round(productivity, 4),
        'pending_approval_count': pending_approvals,
        'open_rfi_count': open_rfi_count,
        'open_ncr_count': open_ncr_count,
        'incident_count': incident_count,
        'near_miss_count': near_miss_count,
        'unsafe_act_count': unsafe_act_count,
        'unsafe_condition_count': unsafe_condition_count,
        'safety_total_count': incident_count + near_miss_count + unsafe_act_count + unsafe_condition_count,
        'active_manpower': active_manpower,
        'labor_today': labor_data[-1] if labor_data else 0,
        'decision_status': decision_status,
        'recommendations': recommendations,
        'alerts': alerts,
    }

    return {
        'name': 'All Project',
        'progress': {'labels': progress_labels, 'planned': planned_progress, 'actual': actual_progress},
        'labor': {'labels': labor_labels, 'data': labor_data},
        'material': {'labels': material_labels, 'data': material_data},
        'rfi': {'labels': rfi_labels, 'data': rfi_data},
        'cost_curve': {'labels': cost_labels, 'planned': planned_cost, 'actual': actual_cost},
        'cost_category': {'labels': cost_category_labels, 'data': cost_category_data},
        'cost_performance': {
            'budget': round(total_budget, 2),
            'actual': round(total_actual, 2),
            'variance': round(total_budget - total_actual, 2),
            'used_percent': round(budget_used, 2),
        },
        'kpis': kpis,
        'alerts': alerts,
        'recommendations': recommendations,
    }


def ensure_user_authenticated(request):
    if not request.user.is_authenticated:
        director = User.objects.filter(profile__role='HQ_DIRECTOR').first() or User.objects.filter(is_superuser=True).first()
        if director:
            auth_login(request, director)
            return True
        return False
    return True

def switch_role(request):
    if request.method == 'POST':
        role = request.POST.get('role')
        if request.user.is_authenticated:
            if hasattr(request.user, 'profile'):
                profile = request.user.profile
                profile.role = role
                profile.save()
            user = User.objects.filter(profile__role=role).first()
            if user:
                auth_login(request, user)
    return redirect('dashboard')

def _user_role(request):
    if hasattr(request.user, 'profile'):
        return request.user.profile.role
    return 'SITE_ENGINEER'


def _allowed_tabs_for_role(role):
    if role in ALL_ACCESS_ROLES:
        return sorted(ALL_DASHBOARD_TABS)
    return sorted(ROLE_DASHBOARD_TABS.get(role, {'hq-dashboard', 'notifications'}))


def _filter_projects_for_user(user, queryset=None):
    queryset = queryset or Project.objects.all()
    role = getattr(getattr(user, 'profile', None), 'role', None)
    if not user.is_authenticated:
        return queryset.none()
    if user.is_superuser or role in ALL_ACCESS_ROLES:
        return queryset.distinct()
    return queryset.filter(team_members__user=user).distinct()


def _user_can_access_project(user, project):
    if not user.is_authenticated:
        return False
    role = getattr(getattr(user, 'profile', None), 'role', None)
    if user.is_superuser or role in ALL_ACCESS_ROLES:
        return True
    return ProjectTeam.objects.filter(project=project, user=user).exists()


def _reject_project_access(request, project):
    if _user_can_access_project(request.user, project):
        return False
    messages.error(request, "You do not have access to this project.")
    return True


def _get_unread_count(user):
    if user.is_authenticated:
        return Notification.objects.filter(recipient=user, status='UNREAD').count()
    return 0


def _notify_roles(roles, title, message, related_module='', related_id=None, notification_type='INFO', exclude_user=None):
    users = User.objects.filter(profile__role__in=roles).distinct()
    if exclude_user:
        users = users.exclude(id=exclude_user.id)
    notifications = [
        Notification(
            recipient=user,
            notification_type=notification_type,
            title=title,
            message=message,
            related_module=related_module,
            related_id=related_id,
        )
        for user in users
    ]
    if notifications:
        Notification.objects.bulk_create(notifications)


def _notify_user(user, title, message, related_module='', related_id=None, notification_type='INFO'):
    if not user:
        return
    Notification.objects.create(
        recipient=user,
        notification_type=notification_type,
        title=title,
        message=message,
        related_module=related_module,
        related_id=related_id,
    )


def _notify_project_registration(project, actor=None):
    role_labels = {
        'Site Engineer',
        'Finance Site',
        'Safety Officer',
        'Logistics',
        'Director',
        'Admin Site',
        'Document Controller',
    }
    users = User.objects.filter(
        projectteam__project=project,
        projectteam__role_in_project__in=role_labels,
    ).distinct()
    if actor:
        users = users.exclude(id=actor.id)

    notifications = [
        Notification(
            recipient=user,
            notification_type='ALERT',
            title='New project registered',
            message=f"{project.name} has been registered and assigned to your project workflow.",
            related_module='project',
            related_id=project.id,
        )
        for user in users
    ]
    if notifications:
        Notification.objects.bulk_create(notifications)
    return len(notifications)


def _finance_site_roles():
    return ['FINANCE_SITE', 'COST_ENGINEER', 'PROJECT_MANAGER']


def _hq_finance_roles():
    return ['FINANCE_HQ', 'HQ_DIRECTOR']


def _is_category_heading(marker, name, numeric_values=None):
    name_text = str(name or '').strip()
    marker_text = str(marker or '').strip().rstrip('.')
    if not name_text or len(name_text) < 3:
        return False
    if name_text.lower().startswith(('sub total', 'subtotal', 'total', 'grand total')):
        return False
    if not re.match(r'^(?:[ivxlcdm]+|[a-z])$', marker_text, re.IGNORECASE):
        return False
    letters = re.sub(r'[^A-Za-z]+', '', name_text)
    if letters and letters != letters.upper():
        return False
    numeric_values = numeric_values or []
    return all(float(value or 0) == 0 for value in numeric_values)


def _is_item_description_category(name, unit='', quantity=0, rate=0):
    name_text = str(name or '').strip()
    unit_text = str(unit or '').strip()
    if not name_text or len(name_text) < 3:
        return False
    if name_text.lower().startswith(('sub total', 'subtotal', 'total', 'grand total')):
        return False
    letters = re.sub(r'[^A-Za-z]+', '', name_text)
    if not letters or letters != letters.upper():
        return False
    return not unit_text and float(quantity or 0) == 0


def _calculate_project_progress_from_work_items(project):
    items = list(project.work_items.all())
    if not items:
        return 0.0

    weighted_sum = 0.0
    weight_total = 0.0
    progress_sum = 0.0
    progress_count = 0
    for item in items:
        progress = float(item.progress_percent or 0)
        quantity = float(item.boq_quantity or 0)
        progress_sum += progress
        progress_count += 1
        if quantity > 0:
            weighted_sum += quantity * progress
            weight_total += quantity

    if weight_total > 0:
        return weighted_sum / weight_total
    return progress_sum / progress_count if progress_count else 0.0


def _decimal_or_zero(value):
    try:
        parsed = Decimal(str(value or '0'))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal('0')
    return parsed if parsed >= 0 else Decimal('0')


def _unique_andn_empty(values):
    seen = set()
    result = []
    for value in values:
        value_text = str(value or '').strip()
        if value_text and value_text not in seen:
            seen.add(value_text)
            result.append(value_text)
    return result


def _collect_daily_report_photos(request):
    uploaded_photos = list(request.FILES.getlist('progress_photos'))
    legacy_photo = request.FILES.get('progress_photo')
    if legacy_photo:
        uploaded_photos.append(legacy_photo)
    for field_name in ['progress_photo_1', 'progress_photo_2', 'progress_photo_3', 'progress_photo_4']:
        photo = request.FILES.get(field_name)
        if photo:
            uploaded_photos.append(photo)
    return uploaded_photos


def _save_daily_report_material_usages(request, report, project, report_date):
    material_ids = request.POST.getlist('material_item_id')
    quantities = request.POST.getlist('material_quantity')
    notes_list = request.POST.getlist('material_notes')
    summaries = []

    for index, material_id in enumerate(material_ids):
        if not material_id:
            continue
        quantity = _decimal_or_zero(quantities[index] if index < len(quantities) else 0)
        if quantity <= 0:
            continue
        try:
            material = MaterialItem.objects.get(id=material_id, project=project)
        except (MaterialItem.DoesNotExist, ValueError):
            continue

        notes = notes_list[index].strip() if index < len(notes_list) and notes_list[index] else ''
        stock_transaction = StockTransaction.objects.create(
            material_item=material,
            project=project,
            transaction_type='OUT',
            quantity=quantity,
            reference_number=f"DR-{report.id}",
            location=project.location,
            notes=notes or f"Daily report usage: {report.date}",
            transaction_date=report_date,
            recorded_by=request.user,
        )
        DailyReportMaterialUsage.objects.create(
            daily_report=report,
            material_item=material,
            quantity=quantity,
            unit=material.unit,
            notes=notes,
            stock_transaction=stock_transaction,
        )
        summaries.append(f"{material.name}: {quantity} {material.unit}")

    return summaries


def _save_daily_report_manpower_usages(request, report, project, report_date):
    manpower_ids = request.POST.getlist('manpower_id')
    hours_list = request.POST.getlist('manpower_hours')
    notes_list = request.POST.getlist('manpower_notes')
    seen = set()
    summaries = []

    for index, manpower_id in enumerate(manpower_ids):
        if not manpower_id or manpower_id in seen:
            continue
        seen.add(manpower_id)
        try:
            manpower = Manpower.objects.get(id=manpower_id, project=project, is_active=True)
        except (Manpower.DoesNotExist, ValueError):
            continue

        hours = _decimal_or_zero(hours_list[index] if index < len(hours_list) else 8)
        if hours <= 0:
            hours = Decimal('8')
        notes = notes_list[index].strip() if index < len(notes_list) and notes_list[index] else ''
        attendance, _ = Attendance.objects.update_or_create(
            manpower=manpower,
            date=report_date,
            defaults={
                'project': project,
                'status': 'PRESENT',
                'notes': notes or f"Recorded from daily report DR-{report.id}",
                'recorded_by': request.user,
            }
        )
        DailyReportManpowerUsage.objects.create(
            daily_report=report,
            manpower=manpower,
            role_snapshot=manpower.get_role_display(),
            hours_worked=hours,
            notes=notes,
            attendance=attendance,
        )
        summaries.append(f"{manpower.name} ({manpower.get_role_display()}, {hours} jam)")

    return summaries


def _save_daily_report_equipment_usages(request, report, project, report_date):
    equipment_ids = request.POST.getlist('equipment_id')
    hours_list = request.POST.getlist('equipment_hours')
    operator_ids = request.POST.getlist('equipment_operator_id')
    notes_list = request.POST.getlist('equipment_notes')
    summaries = []

    for index, equipment_id in enumerate(equipment_ids):
        if not equipment_id:
            continue
        hours = _decimal_or_zero(hours_list[index] if index < len(hours_list) else 0)
        if hours <= 0:
            continue
        try:
            equipment = Equipment.objects.get(id=equipment_id, project=project, status__in=['ACTIVE', 'RENTED'])
        except (Equipment.DoesNotExist, ValueError):
            continue

        operator = None
        operator_id = operator_ids[index] if index < len(operator_ids) else ''
        if operator_id:
            try:
                operator = Manpower.objects.get(id=operator_id, project=project, is_active=True)
            except (Manpower.DoesNotExist, ValueError):
                operator = None

        notes = notes_list[index].strip() if index < len(notes_list) and notes_list[index] else ''
        equipment_usage = EquipmentUsage.objects.create(
            equipment=equipment,
            project=project,
            usage_date=report_date,
            hours_used=hours,
            activity=report.work_done,
            location=project.location,
            operator=operator,
            notes=notes or f"Recorded from daily report DR-{report.id}",
            recorded_by=request.user,
        )
        DailyReportEquipmentUsage.objects.create(
            daily_report=report,
            equipment=equipment,
            operator=operator,
            hours_used=hours,
            activity=report.work_done,
            location=project.location,
            notes=notes,
            equipment_usage=equipment_usage,
        )
        operator_label = f" - {operator.name}" if operator else ''
        summaries.append(f"{equipment.name}: {hours} jam{operator_label}")

    return summaries



def login_view(request):
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            auth_login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Username/Password sala.')
    return render(request, 'core/login.html')

@login_required
def logout_view(request):
    auth_logout(request)
    return redirect('login')


def dashboard_view(request):
    if not ensure_user_authenticated(request):
        return redirect('login')

    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    role = _user_role(request)
    allowed_tabs = sorted(ALL_DASHBOARD_TABS) if request.user.is_superuser else _allowed_tabs_for_role(role)

    base_projects = Project.objects.select_related('contractor', 'consultant').prefetch_related('team_members__user')
    projects = _filter_projects_for_user(request.user, base_projects)
    project_data_list = []

    total_budget = 0
    total_contract_value = 0
    total_spent = 0
    total_vo_approved = 0

    for p in projects:
        latest_report = p.progress_reports.order_by('-report_date').first()
        overall_progress = float(latest_report.overall_progress) if latest_report else 0.0

        if overall_progress == 0:
            approved_daily = p.daily_reports.filter(status='APPROVED').order_by('-date').first()
            overall_progress = float(approved_daily.progress_percentage) if approved_daily else 0.0

        if overall_progress == 0:
            work_items_avg = p.work_items.aggregate(Avg('progress_percent'))['progress_percent__avg']
            overall_progress = float(work_items_avg) if work_items_avg else 0.0

        actual_spend = float(p.cost_summaries.aggregate(Sum('actual'))['actual__sum'] or 0.0)
        if actual_spend == 0:
            actual_spend = float(p.invoices.filter(status='PAID').aggregate(Sum('amount'))['amount__sum'] or 0.0)

        budget_val = float(p.budget or 0)
        contract_val = float(p.contract_value or 0)

        approved_vo = float(p.variation_orders.filter(status='APPROVED').aggregate(Sum('approved_amount'))['approved_amount__sum'] or 0.0)
        pending_vo = p.variation_orders.filter(status='PENDING').count()

        total_budget += budget_val
        total_contract_value += contract_val
        total_spent += actual_spend
        total_vo_approved += approved_vo

        project_data_list.append({
            'project': p,
            'overall_progress': overall_progress,
            'actual_spend': actual_spend,
            'budget': budget_val,
            'contract_value': contract_val,
            'approved_vo': approved_vo,
            'pending_vo_count': pending_vo,
            'variance': budget_val - actual_spend
        })

    total_projects = projects.count()
    active_projects = projects.filter(status='ACTIVE').count()
    avg_progress = sum(p['overall_progress'] for p in project_data_list) / total_projects if total_projects > 0 else 0
    dashboard_chart_data = _build_dashboard_chart_data(projects)

    cost_summaries = CostSummary.objects.filter(project__in=projects).select_related('project')
    variation_orders = VariationOrder.objects.filter(project__in=projects).select_related('project', 'requested_by')
    invoices = Invoice.objects.filter(project__in=projects).select_related(
        'project', 'submitted_by', 'site_verified_by', 'hq_reviewed_by', 'approved_by'
    ).order_by('-due_date', '-id')
    ipcs = InterimPaymentCertificate.objects.filter(project__in=projects).select_related('project', 'invoice')
    financial_records = FinancialRecord.objects.filter(project__in=projects).select_related(
        'project', 'submitted_by', 'site_verified_by', 'hq_reviewed_by', 'approved_by'
    ).prefetch_related('history').order_by('-transaction_date', '-created_at')

    hse_reports = HSEReport.objects.filter(project__in=projects).select_related('project', 'reporter').order_by('-report_date')
    incident_count = hse_reports.filter(report_type='INCIDENT').count()
    near_miss_count = hse_reports.filter(report_type='NEAR_MISS').count()
    unsafe_act_count = hse_reports.filter(report_type='UNSAFE_ACT').count()
    unsafe_condition_count = hse_reports.filter(report_type='UNSAFE_CONDITION').count()

    qaqc_inspections = QAQCInspection.objects.filter(project__in=projects).select_related('project', 'inspector').order_by('-inspection_date')
    material_tests = MaterialTest.objects.filter(project__in=projects).select_related('project').order_by('-test_date')
    material_requests = MaterialRequest.objects.filter(project__in=projects).select_related(
        'project', 'material_item', 'requested_by', 'approved_by', 'delivered_by', 'received_by', 'stock_transaction'
    ).order_by('-requested_date', '-id')
    purchase_requests = PurchaseRequest.objects.filter(project__in=projects).select_related(
        'project', 'material_request', 'requested_by', 'reviewer_by', 'manager_by', 'consultant_by', 'approved_by'
    ).order_by('-submitted_at')
    material_wastes = MaterialWaste.objects.filter(project__in=projects).select_related(
        'project', 'material_item', 'recorded_by', 'stock_transaction'
    ).order_by('-waste_date', '-created_at')
    logistics_records = LogisticsRecord.objects.filter(project__in=projects).select_related(
        'project', 'material_request', 'material_item', 'stock_transaction', 'handled_by'
    ).order_by('-actual_date', '-created_at')[:120]
    logistics_delivery_requests = material_requests.filter(status__in=['APPROVED', 'DELIVERED'])
    today = timezone.localdate()
    logistics_stats = {
        'pending_delivery': material_requests.filter(status='APPROVED').count(),
        'on_delivery': material_requests.filter(status='DELIVERED').count(),
        'received_today': LogisticsRecord.objects.filter(project__in=projects, record_type='MATERIAL_RECEIVING', actual_date=today).count(),
        'issued_today': LogisticsRecord.objects.filter(project__in=projects, record_type='STOCK_ISSUE', actual_date=today).count(),
        'returned_today': LogisticsRecord.objects.filter(project__in=projects, record_type='STOCK_RETURN', actual_date=today).count(),
    }
    rfis = RFI.objects.filter(project__in=projects).select_related('project', 'raised_by', 'assigned_to').order_by('-raised_date')
    site_instructions = SiteInstruction.objects.filter(project__in=projects).select_related('project', 'issued_by', 'acknowledged_by').order_by('-issued_date')

    inspection_pass = qaqc_inspections.filter(status='PASS').count()
    inspection_total = qaqc_inspections.count()
    qaqc_pass_rate = (inspection_pass / inspection_total * 100) if inspection_total > 0 else 100.0

    daily_report_detail_prefetch = [
        'photos',
        'documents',
        'work_progress_items__work_item',
        'material_usages__material_item',
        'manpower_usages__manpower',
        'equipment_usage_details__equipment',
        'equipment_usage_details__operator',
    ]
    pending_reports = DailyReport.objects.filter(project__in=projects, status='PENDING').select_related(
        'project', 'reporter'
    ).prefetch_related(*daily_report_detail_prefetch).order_by('-date', '-created_at')
    evaluated_reports = DailyReport.objects.filter(project__in=projects, status__in=['VERIFIED', 'APPROVED', 'REJECTED']).select_related(
        'project', 'reporter'
    ).prefetch_related(*daily_report_detail_prefetch).order_by('-updated_at')[:40]
    rejected_reports_for_revision = DailyReport.objects.filter(
        project__in=projects,
        status='REJECTED',
        reporter=request.user,
    ).select_related('project', 'reporter').prefetch_related(
        'photos', 'documents', 'work_progress_items__work_item'
    ).order_by('-updated_at')

    documents = Document.objects.filter(project__in=projects).select_related(
        'project', 'submitted_by', 'dc_reviewed_by', 'consultant_reviewed_by', 'approved_by', 'parent_document'
    ).prefetch_related('revision_history').order_by('-uploaded_at')
    risks = RiskRegister.objects.filter(project__in=projects).select_related('project', 'owner').order_by('-risk_level')
    critical_risks_count = risks.filter(risk_level='CRITICAL').count()

    schedules = Schedule.objects.filter(project__in=projects).select_related('project').order_by('planned_start')
    work_items = WorkItem.objects.filter(project__in=projects).select_related('project').order_by(
        'project_id', 'category', 'item_code', 'item_name'
    )
    contractor_companies = Company.objects.filter(company_type='CONTRACTOR').order_by('company_name')
    consultant_companies = Company.objects.filter(company_type='CONSULTANT').order_by('company_name')
    site_engineer_users = User.objects.filter(profile__role='SITE_ENGINEER').select_related('profile').order_by('first_name', 'username')
    project_manager_users = User.objects.filter(profile__role='PROJECT_MANAGER').select_related('profile').order_by('first_name', 'username')
    supervisor_users = User.objects.filter(profile__role='SUPERVISOR').select_related('profile').order_by('first_name', 'username')
    qs_users = User.objects.filter(profile__role='COST_ENGINEER').select_related('profile').order_by('first_name', 'username')
    finance_site_users = User.objects.filter(profile__role='FINANCE_SITE').select_related('profile').order_by('first_name', 'username')
    safety_officer_users = User.objects.filter(profile__role='HSE_OFFICER').select_related('profile').order_by('first_name', 'username')
    storekeeper_users = User.objects.filter(profile__role='STOREKEEPER').select_related('profile').order_by('first_name', 'username')
    logistics_users = User.objects.filter(profile__role='LOGISTICS').select_related('profile').order_by('first_name', 'username')
    director_users = User.objects.filter(profile__role__in=['PROJECT_DIRECTOR', 'HQ_DIRECTOR']).select_related('profile').order_by('first_name', 'username')
    doc_controller_users = User.objects.filter(profile__role='DOC_CONTROLLER').select_related('profile').order_by('first_name', 'username')
    admin_site_users = User.objects.filter(profile__role='ADMIN_SITE').select_related('profile').order_by('first_name', 'username')
    consultant_users = User.objects.filter(profile__role='CONSULTANT').select_related('profile').order_by('first_name', 'username')
    work_item_categories = []
    seen_work_item_categories = set()
    for item in work_items:
        category_name = (item.category or '').strip() or 'Umum'
        category_key = (item.project_id, category_name.casefold())
        if category_key in seen_work_item_categories:
            continue
        seen_work_item_categories.add(category_key)
        work_item_categories.append({
            'project_id': item.project_id,
            'category': category_name,
        })
    work_item_project_ids = set(work_items.values_list('project_id', flat=True))
    baseline_project_ids = set(schedules.filter(activity_code='BASELINE').values_list('project_id', flat=True))
    project_filter_data = [
        {
            'id': str(project.id),
            'name': project.name,
            'location': project.location or 'No Location',
            'status': project.status,
        }
        for project in projects
    ]
    project_setup_rows = []
    financial_cashflow_rows = []
    for project in projects:
        team_members = list(project.team_members.all())
        team_user_ids = {}
        team_labels = [
            f"{member.role_in_project or 'Team'}: {member.user.get_full_name() or member.user.username}"
            for member in team_members
        ]
        role_field_keys = {
            'Project Manager': 'project_manager',
            'Site Engineer': 'site_engineer',
            'Supervisor': 'supervisor',
            'QS / Cost Engineer': 'qs',
            'Finance Site': 'finance_site',
            'Safety Officer': 'safety_officer',
            'Storekeeper': 'storekeeper',
            'Logistics': 'logistics',
            'Director': 'director',
            'Document Controller': 'doc_controller',
            'Admin Site': 'admin_site',
            'Consultant': 'consultant_user',
        }
        for member in team_members:
            field_key = role_field_keys.get(member.role_in_project or '')
            if field_key and field_key not in team_user_ids:
                team_user_ids[field_key] = member.user_id
        contractor_assigned = bool(project.contractor or project.company)
        consultant_assigned = bool(project.consultant)
        team_assigned = bool(team_members)
        budget_set = bool(project.budget and project.budget > 0)
        timeline_set = bool(project.start_date and project.end_date and project.end_date >= project.start_date)
        baseline_created = project.id in baseline_project_ids
        boq_imported = project.id in work_item_project_ids
        ready = all([
            contractor_assigned,
            consultant_assigned,
            team_assigned,
            budget_set,
            timeline_set,
            baseline_created,
            boq_imported,
        ])
        project_setup_rows.append({
            'project': project,
            'contractor_assigned': contractor_assigned,
            'consultant_assigned': consultant_assigned,
            'team_assigned': team_assigned,
            'budget_set': budget_set,
            'timeline_set': timeline_set,
            'baseline_created': baseline_created,
            'boq_imported': boq_imported,
            'ready': ready,
            'team_labels': team_labels,
            'team_user_ids': team_user_ids,
        })
        cashflow_actual = project.cost_summaries.aggregate(total=Sum('actual'))['total'] or Decimal('0')
        cashflow_committed = project.cost_summaries.aggregate(total=Sum('committed'))['total'] or Decimal('0')
        cashflow_budget = project.budget or Decimal('0')
        budget_used = (cashflow_actual / cashflow_budget * Decimal('100')) if cashflow_budget else Decimal('0')
        financial_cashflow_rows.append({
            'project': project,
            'budget': cashflow_budget,
            'actual': cashflow_actual,
            'committed': cashflow_committed,
            'variance': cashflow_budget - cashflow_actual,
            'budget_used': min(budget_used, Decimal('999.99')),
        })

    bim_models = BIMModel.objects.filter(project__in=projects).select_related('project', 'reviewed_by').order_by('-created_at')
    bim_clashes = BIMClash.objects.filter(project__in=projects).select_related('project', 'bim_model').order_by('-detected_date')
    total_clashes = bim_clashes.filter(status='OPEN').count()

    # Inventory / Stock Management data
    material_items = MaterialItem.objects.filter(project__in=projects).select_related('project').prefetch_related('transactions')
    stock_transactions = StockTransaction.objects.all().select_related(
        'material_item', 'project', 'recorded_by').filter(project__in=projects).order_by('-transaction_date')[:100]
    low_stock_items = [item for item in material_items if item.is_low_stock and item.minimum_stock > 0]
    manpowers = Manpower.objects.filter(project__in=projects).select_related('project')
    today = datetime.date.today()
    attendance_today = Attendance.objects.filter(project__in=projects, date=today).select_related('manpower', 'project', 'recorded_by')
    equipments = Equipment.objects.filter(project__in=projects).select_related('project', 'operator')
    daily_manpowers = manpowers.filter(is_active=True)
    daily_equipments = equipments.filter(status__in=['ACTIVE', 'RENTED'])
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:50]
    selected_item_report_project_id = request.GET.get('item_report_project') or request.GET.get('project_id')
    selected_item_report_project = None
    if selected_item_report_project_id:
        selected_item_report_project = projects.filter(id=selected_item_report_project_id).first()
    if not selected_item_report_project:
        selected_item_report_project = projects.first()
    item_reports = ItemProgressReport.objects.filter(project=selected_item_report_project).prefetch_related('photos').order_by('source_row') if selected_item_report_project else ItemProgressReport.objects.none()
    item_report_count = item_reports.count()
    item_report_completed_count = item_reports.filter(status__iexact='Completed').count()
    item_report_in_progress_count = item_reports.filter(status__icontains='progress').count()
    item_report_progress_total = item_reports.aggregate(total=Sum('progress_percent'))['total'] or Decimal('0')
    item_report_target = Decimal('28.6')
    item_report_rows = []
    item_report_list = list(item_reports)
    group_start_indexes = [
        index for index, item in enumerate(item_report_list)
        if item.item_no is not None
    ]
    if item_report_list and 0 not in group_start_indexes:
        group_start_indexes.insert(0, 0)
    group_spans = {}
    group_items_by_start = {}
    for position, start_index in enumerate(group_start_indexes):
        end_index = group_start_indexes[position + 1] if position + 1 < len(group_start_indexes) else len(item_report_list)
        group_spans[start_index] = end_index - start_index
        group_items_by_start[start_index] = item_report_list[start_index:end_index]
    current_group = None
    current_location = ''
    excel_row_heights = {
        5: Decimal('21'),
        6: Decimal('168.75'),
        8: Decimal('168.75'),
        10: Decimal('84.75'),
        11: Decimal('84.75'),
        13: Decimal('168.75'),
        15: Decimal('72'),
        16: Decimal('46.8'),
        17: Decimal('72'),
        19: Decimal('74.25'),
        20: Decimal('31.2'),
        21: Decimal('74.25'),
        23: Decimal('84.75'),
        24: Decimal('84.75'),
        26: Decimal('84.75'),
        27: Decimal('84.75'),
        29: Decimal('46.8'),
        30: Decimal('31.2'),
        31: Decimal('84.75'),
    }
    previous_source_row = None
    for index, item in enumerate(item_report_list):
        if previous_source_row and item.source_row:
            for blank_source_row in range(previous_source_row + 1, item.source_row):
                item_report_rows.append({
                    'is_blank': True,
                    'source_row': blank_source_row,
                    'excel_height': excel_row_heights.get(blank_source_row, Decimal('18')),
                })
        is_group_start = index in group_spans
        if is_group_start:
            current_group = item
            current_location = item.location or ''
        item_report_rows.append({
            'is_blank': False,
            'source_row': item.source_row,
            'item': item,
            'is_group_start': is_group_start,
            'rowspan': group_spans.get(index, 1),
            'group_item_no': current_group.item_no if current_group else item.item_no,
            'group_location': current_location,
            'group_items': group_items_by_start.get(index, []),
            'excel_height': excel_row_heights.get(item.source_row, Decimal('42')),
        })
        previous_source_row = item.source_row

    meetings = Meeting.objects.filter(project__in=projects).select_related('project', 'chairperson').prefetch_related('actions').order_by('-meeting_date')
    pending_approvals = Approval.objects.filter(
        project__in=projects,
        status__in=['PENDING', 'REVIEWED']
    ).select_related(
        'project', 'submitted_by', 'reviewed_by', 'reviewer_by', 'manager_by', 'consultant_by', 'hq_approved_by'
    ).prefetch_related('step_history').order_by('-submitted_at')
    approval_history = Approval.objects.exclude(
        status__in=['PENDING', 'REVIEWED']
    ).filter(project__in=projects).select_related(
        'project', 'submitted_by', 'approved_by', 'reviewer_by', 'manager_by', 'consultant_by', 'hq_approved_by'
    ).prefetch_related('step_history').order_by('-submitted_at')[:30]

    stats = {
        'total_projects': total_projects,
        'active_projects': active_projects,
        'total_reports': DailyReport.objects.filter(project__in=projects).count(),
        'approved_reports': DailyReport.objects.filter(project__in=projects, status='APPROVED').count(),
        'verified_reports': DailyReport.objects.filter(project__in=projects, status='VERIFIED').count(),
        'pending_reports': pending_reports.count(),
        'total_budget': total_budget,
        'total_contract_value': total_contract_value,
        'total_spent': total_spent,
        'total_vo_approved': total_vo_approved,
        'avg_progress': avg_progress,
        'incident_count': incident_count,
        'near_miss_count': near_miss_count,
        'unsafe_act_count': unsafe_act_count,
        'unsafe_condition_count': unsafe_condition_count,
        'safety_total_count': incident_count + near_miss_count + unsafe_act_count + unsafe_condition_count,
        'qaqc_pass_rate': qaqc_pass_rate,
        'critical_risks_count': critical_risks_count,
        'inspection_total': inspection_total,
        'inspection_fail': qaqc_inspections.filter(status='FAIL').count(),
        'total_clashes': total_clashes,
        'material_requests_count': material_requests.filter(status__in=['SUBMITTED', 'APPROVED', 'DELIVERED']).count(),
        'bim_clashes_resolved': bim_clashes.filter(status='RESOLVED').count(),
        'pending_approvals_count': pending_approvals.count(),
        'low_stock_count': len(low_stock_items),
        'total_stock_items': material_items.count(),
        'open_rfi_count': rfis.filter(status__in=['SUBMITTED', 'IN_REVIEW']).count(),
        'open_ncr_count': NCR.objects.filter(project__in=projects, status__in=['OPEN', 'UNDER_REVIEW', 'CORRECTIVE_ACTION']).count(),
    }

    context = {
        'user_profile': user_profile,
        'allowed_tabs': allowed_tabs,
        'projects': project_data_list,
        'raw_projects': projects,
        'pending_reports': pending_reports,
        'evaluated_reports': evaluated_reports,
        'rejected_reports_for_revision': rejected_reports_for_revision,
        'cost_summaries': cost_summaries,
        'variation_orders': variation_orders,
        'invoices': invoices,
        'ipcs': ipcs,
        'financial_records': financial_records,
        'financial_cashflow_rows': financial_cashflow_rows,
        'hse_reports': hse_reports,
        'qaqc_inspections': qaqc_inspections,
        'material_tests': material_tests,
        'material_requests': material_requests,
        'purchase_requests': purchase_requests,
        'material_wastes': material_wastes,
        'logistics_records': logistics_records,
        'logistics_delivery_requests': logistics_delivery_requests,
        'logistics_stats': logistics_stats,
        'rfis': rfis,
        'site_instructions': site_instructions,
        'documents': documents,
        'risks': risks,
        'schedules': schedules,
        'work_items': work_items,
        'site_engineer_users': site_engineer_users,
        'project_manager_users': project_manager_users,
        'supervisor_users': supervisor_users,
        'qs_users': qs_users,
        'finance_site_users': finance_site_users,
        'safety_officer_users': safety_officer_users,
        'storekeeper_users': storekeeper_users,
        'logistics_users': logistics_users,
        'director_users': director_users,
        'doc_controller_users': doc_controller_users,
        'admin_site_users': admin_site_users,
        'consultant_users': consultant_users,
        'contractor_companies': contractor_companies,
        'consultant_companies': consultant_companies,
        'work_item_categories': work_item_categories,
        'project_setup_rows': project_setup_rows,
        'project_filter_data': project_filter_data,
        'bim_models': bim_models,
        'bim_clashes': bim_clashes,
        'meetings': meetings,
        'pending_approvals': pending_approvals,
        'approval_history': approval_history,
        'stats': stats,
        'dashboard_chart_data': dashboard_chart_data,
        'material_items': material_items,
        'stock_transactions': stock_transactions,
        'low_stock_items': low_stock_items,
        'manpowers': manpowers,
        'daily_manpowers': daily_manpowers,
        'attendance_today': attendance_today,
        'manpower_roles': Manpower.ROLE_CHOICES,
        'attendance_statuses': Attendance.STATUS_CHOICES,
        'today': today,
        'equipments': equipments,
        'daily_equipments': daily_equipments,
        'notifications': notifications,
        'item_reports': item_reports,
        'item_report_projects': projects,
        'selected_item_report_project': selected_item_report_project,
        'item_report_rows': item_report_rows,
        'item_report_stats': {
            'total': item_report_count,
            'completed': item_report_completed_count,
            'in_progress': item_report_in_progress_count,
            'progress_total': item_report_progress_total,
            'target': item_report_target,
            'variance': item_report_progress_total - item_report_target,
        },
        'all_daily_reports': DailyReport.objects.filter(project__in=projects).select_related('project', 'reporter').order_by('-date')[:200],
        'unread_count': _get_unread_count(request.user),
    }
    return render(request, 'core/dashboard.html', context)


def submit_report(request):
    if request.method == 'POST':
        if not ensure_user_authenticated(request):
            messages.error(request, "Please login first.")
            return redirect('dashboard')
        role = _user_role(request)
        if role != 'SITE_ENGINEER':
            messages.error(request, "Only Site Engineer can submit daily report.")
            return redirect('dashboard')

        project_id = request.POST.get('project_id')
        try:
            project = Project.objects.get(id=project_id)
        except (Project.DoesNotExist, ValueError):
            messages.error(request, "Project was not identified.")
            return redirect('dashboard')
        if _reject_project_access(request, project):
            return redirect('dashboard')

        uploaded_photos = _collect_daily_report_photos(request)
        if len(uploaded_photos) < 4:
            messages.error(request, "At least 4 progress photos must be uploaded before submitting the daily report.")
            return redirect('dashboard')

        progress_percentage = None
        work_item = None
        actual_quantity = None
        item_progress_percent = Decimal('0')
        actual_quantity_raw = request.POST.get('actual_quantity')
        work_item_id = request.POST.get('work_item_id')
        if work_item_id and actual_quantity_raw not in (None, ''):
            try:
                work_item = WorkItem.objects.get(id=work_item_id, project=project)
                actual_quantity = Decimal(str(actual_quantity_raw or '0'))
                if actual_quantity < 0:
                    actual_quantity = Decimal('0')
                if not work_item.boq_quantity or work_item.boq_quantity <= 0:
                    messages.error(
                        request,
                        f"Quantity BOQ to item '{work_item.item_name}' sei 0. "
                        "Import/updated quantity BOQ first to progress project can calculated."
                    )
                    return redirect('dashboard')
                progress_decimal = (actual_quantity / work_item.boq_quantity) * Decimal('100')
                progress_decimal = max(Decimal('0'), min(progress_decimal, Decimal('100')))
                work_item.actual_quantity = actual_quantity
                work_item.progress_percent = progress_decimal.quantize(Decimal('0.01'))
                if work_item.boq_amount:
                    work_item.actual_amount = work_item.boq_amount * progress_decimal / Decimal('100')
                work_item.save()
                item_progress_percent = progress_decimal.quantize(Decimal('0.01'))
                progress_percentage = int(round(_calculate_project_progress_from_work_items(project)))
            except (WorkItem.DoesNotExist, ValueError, InvalidOperation, ArithmeticError):
                messages.error(request, "Item work or Quantity Atual invalid.")
                return redirect('dashboard')

        if progress_percentage is None:
            try:
                progress_percentage = int(request.POST.get('progress_percentage') or 0)
            except ValueError:
                progress_percentage = 0

        progress_percentage = max(0, min(progress_percentage, 100))

        raw_date = request.POST.get('date') or datetime.date.today()
        if isinstance(raw_date, str):
            try:
                report_date = datetime.date.fromisoformat(raw_date)
            except ValueError:
                report_date = datetime.date.today()
        else:
            report_date = raw_date

        selected_manpower_ids = _unique_andn_empty(request.POST.getlist('manpower_id'))
        if selected_manpower_ids:
            manpower_count = Manpower.objects.filter(
                id__in=selected_manpower_ids, project=project, is_active=True
            ).count()
        else:
            try:
                manpower_count = int(request.POST.get('manpower_count') or 0)
            except ValueError:
                manpower_count = 0

        with transaction.atomic():
            report = DailyReport.objects.create(
                project=project,
                reporter=request.user,
                date=report_date,
                progress_percentage=progress_percentage,
                manpower_count=manpower_count,
                weather=request.POST.get('weather', 'Sunny') or 'Sunny',
                work_done=request.POST.get('work_done') or (
                    f"Actual quantity updated: {work_item.item_name} = {work_item.actual_quantity} {work_item.unit or ''}"
                    if work_item else ''
                ),
                materials_used=request.POST.get('materials_used') or '',
                equipment_used=request.POST.get('equipment_used') or '',
                issues=request.POST.get('issues') or '',
                status='PENDING'
            )

            material_summaries = _save_daily_report_material_usages(request, report, project, report_date)
            manpower_summaries = _save_daily_report_manpower_usages(request, report, project, report_date)
            equipment_summaries = _save_daily_report_equipment_usages(request, report, project, report_date)
            if work_item and actual_quantity is not None:
                DailyReportWorkProgress.objects.create(
                    daily_report=report,
                    work_item=work_item,
                    actual_quantity=actual_quantity,
                    unit=work_item.unit,
                    item_progress_percent=item_progress_percent,
                    project_progress_percent=Decimal(str(progress_percentage)),
                    notes=f"BOQ {work_item.boq_quantity} {work_item.unit or ''}",
                )

            update_fields = []
            if material_summaries and not report.materials_used:
                report.materials_used = '; '.join(material_summaries)
                update_fields.append('materials_used')
            if equipment_summaries and not report.equipment_used:
                report.equipment_used = '; '.join(equipment_summaries)
                update_fields.append('equipment_used')
            if manpower_summaries and report.manpower_count != len(manpower_summaries):
                report.manpower_count = len(manpower_summaries)
                update_fields.append('manpower_count')
            if update_fields:
                report.save(update_fields=update_fields)

            support_document = request.FILES.get('support_document')
            if support_document:
                DailyReportDocument.objects.create(
                    daily_report=report,
                    file=support_document,
                    document_name=request.POST.get('support_document_name') or support_document.name,
                    uploaded_by=request.user,
                )

            for index, uploaded_photo in enumerate(uploaded_photos, start=1):
                ProgressPhoto.objects.create(
                    daily_report=report,
                    image=uploaded_photo,
                    caption=f"Foto progress {index} - {report.progress_percentage}%"
                )

            if work_item:
                progress_report, _ = ProgressReport.objects.update_or_create(
                    project=project,
                    report_date=report_date,
                    defaults={
                        'report_period': f"Daily actual quantity {report_date.isoformat()}",
                        'overall_progress': progress_percentage,
                        'civil_progress': progress_percentage,
                        'remarks': f"Updated from actual quantity input for {work_item.item_name}.",
                        'prepared_by': request.user,
                        'status': 'SUBMITTED',
                        'approved_by': None,
                        'approved_at': None,
                        'rejection_reason': None,
                    },
                )
                wf.register_progress_submission(progress_report)

        wf.register_daily_report_submission(report)
        _notify_roles(
            ['PROJECT_MANAGER'],
            'Daily report waiting review',
            f"{project.name} - report {report.date} masuk dari {request.user.username}.",
            'daily_report',
            report.id,
            'ALERT',
            exclude_user=request.user,
        )
        messages.success(request, f"Daily report to {project.name} successfully submit to PM review.")

    return redirect('dashboard')


def approve_report(request, report_id):
    if request.method == 'POST':
        if not ensure_user_authenticated(request):
            messages.error(request, "Please login first.")
            return redirect('dashboard')
        role = _user_role(request)
        if role != 'PROJECT_MANAGER':
            messages.error(request, "Only Project Manager can make review and validate report in Phase C.")
            return redirect('dashboard')

        try:
            report = DailyReport.objects.get(id=report_id)
        except DailyReport.DoesNotExist:
            messages.error(request, "Report not found.")
            return redirect('dashboard')
        if _reject_project_access(request, report.project):
            return redirect('dashboard')

        if report.status != 'PENDING':
            messages.error(request, "This report must be resubmitted before the approval process.")
            return redirect('dashboard')

        status = request.POST.get('status')

        if status == 'APPROVED':
            report.status = 'VERIFIED'
            report.rejection_reason = None
            report.save()
            _notify_user(
                report.reporter,
                'Daily report verified',
                f"Daily report {report.project.name} - {report.date} verified  by PM.",
                'daily_report',
                report.id,
                'SUCCESS',
            )
            _notify_roles(
                ['CONSULTANT', 'HQ_DIRECTOR'],
                'Daily report waiting approval',
                f"{report.project.name} - report {report.date} verified  by PM and waiting for approval.",
                'daily_report',
                report.id,
                'ALERT',
                exclude_user=request.user,
            )
            wf.create_or_update_approval(
                report.project,
                'daily_report',
                report.id,
                document_title=f"Daily Report {report.date} — {report.progress_percentage}%",
                submitted_by=report.reporter,
                reviewed_by=request.user,
                status='REVIEWED',
                current_step='CONSULTANT',
                reviewer_by=request.user,
                comments='PM verified  daily report. Pending Approval System Consultant/HQ.',
            )
            messages.success(request, f"Daily report to {report.project.name} verified by PM — now waiting for Approval System.")
        elif status == 'REJECTED':
            report.status = 'REJECTED'
            report.rejection_reason = request.POST.get('rejection_reason') or 'Razão não especificada'
            report.save()
            _notify_user(
                report.reporter,
                'Daily report rejected',
                f"Daily report {report.project.name} - {report.date} rejected: {report.rejection_reason}",
                'daily_report',
                report.id,
                'WARNING',
            )
            wf.create_or_update_approval(
                report.project, 'daily_report', report.id,
                document_title=f"Daily Report {report.date}",
                submitted_by=report.reporter,
                reviewed_by=request.user,
                status='REJECTED',
                comments=report.rejection_reason,
            )
            messages.warning(request, f"Daily report to {report.project.name} REJECTED.")
        else:
            messages.error(request, "Approval status is invalid.")

    return redirect('dashboard')


def resubmit_report(request, report_id):
    if request.method == 'POST':
        if not ensure_user_authenticated(request):
            messages.error(request, "Please login first.")
            return redirect('dashboard')
        role = _user_role(request)
        if role != 'SITE_ENGINEER':
            messages.error(request, "Only Site Engineer can make revision/resubmit report.")
            return redirect('dashboard')

        try:
            report = DailyReport.objects.select_related('project', 'reporter').get(id=report_id)
        except DailyReport.DoesNotExist:
            messages.error(request, "Report not found.")
            return redirect('dashboard')

        if report.status != 'REJECTED':
            messages.error(request, "This report is not rejected.")
            return redirect('dashboard')
        if report.reporter_id != request.user.id:
            messages.error(request, "Ita can resubmit only report that you submitted mak submit.")
            return redirect('dashboard')

        uploaded_photos = _collect_daily_report_photos(request)
        if not report.photos.exists() and not uploaded_photos:
            messages.error(request, "Progress photo is required before resubmitting the report.")
            return redirect('dashboard')

        with transaction.atomic():
            report.work_done = request.POST.get('work_done') or report.work_done
            report.issues = request.POST.get('issues') or ''
            weather = request.POST.get('weather')
            if weather:
                report.weather = weather
            report.status = 'PENDING'
            report.rejection_reason = None
            report.save(update_fields=['work_done', 'issues', 'weather', 'status', 'rejection_reason', 'updated_at'])

            support_document = request.FILES.get('support_document')
            if support_document:
                DailyReportDocument.objects.create(
                    daily_report=report,
                    file=support_document,
                    document_name=request.POST.get('support_document_name') or support_document.name,
                    uploaded_by=request.user,
                )

            remaining_photo_slots = max(4 - report.photos.count(), 0)
            for index, uploaded_photo in enumerate(uploaded_photos[:remaining_photo_slots], start=report.photos.count() + 1):
                ProgressPhoto.objects.create(
                    daily_report=report,
                    image=uploaded_photo,
                    caption=f"Revision photo {index} - {report.progress_percentage}%"
                )

            wf.register_daily_report_submission(report)
            _notify_roles(
                ['PROJECT_MANAGER'],
                'Daily report resubmitted',
                f"{report.project.name} - report {report.date} reviza  and enter fila-fali to review.",
                'daily_report',
                report.id,
                'ALERT',
                exclude_user=request.user,
            )

        messages.success(request, f"Daily report to {report.project.name} successfully resubmit to review.")

    return redirect('dashboard')


def create_project(request):
    if request.method == 'POST':
        if not ensure_user_authenticated(request):
            messages.error(request, "Please login first.")
            return redirect('dashboard')
        role = _user_role(request)
        if role not in ['HQ_DIRECTOR', 'PROJECT_MANAGER', 'PROJECT_DIRECTOR', 'ADMIN_SYSTEM']:
            messages.error(request, "Only Project Manager / Admin can initialized new project.")
            return redirect('dashboard')

        def parse_project_date(value, falltock):
            if isinstance(value, datetime.date):
                return value
            try:
                return datetime.date.fromisoformat(value) if value else falltock
            except ValueError:
                return falltock

        def get_company(company_id, company_type):
            if not company_id:
                return None
            try:
                return Company.objects.get(id=company_id, company_type=company_type)
            except (Company.DoesNotExist, ValueError):
                return None

        name = request.POST.get('name')
        project_code = (request.POST.get('project_code') or '').strip() or None
        location = request.POST.get('location') or ''
        try:
            budget = Decimal(str(request.POST.get('budget') or 0))
        except (ValueError, InvalidOperation):
            budget = Decimal('0')
        contract_value_raw = request.POST.get('contract_value')
        try:
            contract_value = Decimal(str(contract_value_raw)) if contract_value_raw not in (None, '') else budget * Decimal('1.05')
        except (ValueError, InvalidOperation):
            contract_value = budget * Decimal('1.05')

        today = datetime.date.today()
        start_date = parse_project_date(request.POST.get('start_date'), today)
        end_date = parse_project_date(request.POST.get('end_date'), start_date)
        status = request.POST.get('status', 'PLANNING')
        contractor = get_company(request.POST.get('contractor_id'), 'CONTRACTOR')
        consultant = get_company(request.POST.get('consultant_id'), 'CONSULTANT')

        project = Project.objects.create(
            project_code=project_code,
            name=name,
            location=location,
            company=contractor,
            contractor=contractor,
            consultant=consultant,
            client_name=request.POST.get('client_name') or '',
            budget=budget,
            contract_value=contract_value,
            start_date=start_date,
            end_date=end_date,
            status=status
        )

        assigned_count = 0
        project_assignment_notifications = []
        team_fields = [
            ('project_manager_id', 'PROJECT_MANAGER', 'Project Manager'),
            ('site_engineer_id', 'SITE_ENGINEER', 'Site Engineer'),
            ('supervisor_id', 'SUPERVISOR', 'Supervisor'),
            ('qs_id', 'COST_ENGINEER', 'QS / Cost Engineer'),
            ('finance_site_id', 'FINANCE_SITE', 'Finance Site'),
            ('safety_officer_id', 'HSE_OFFICER', 'Safety Officer'),
            ('storekeeper_id', 'STOREKEEPER', 'Storekeeper'),
            ('logistics_id', 'LOGISTICS', 'Logistics'),
            ('director_id', ['PROJECT_DIRECTOR', 'HQ_DIRECTOR'], 'Director'),
            ('doc_controller_id', 'DOC_CONTROLLER', 'Document Controller'),
            ('admin_site_id', 'ADMIN_SITE', 'Admin Site'),
            ('consultant_user_id', 'CONSULTANT', 'Consultant'),
        ]
        for field_name, expected_role, role_label in team_fields:
            user_id = request.POST.get(field_name)
            if not user_id:
                continue
            try:
                if isinstance(expected_role, list):
                    team_user = User.objects.get(id=user_id, profile__role__in=expected_role)
                else:
                    team_user = User.objects.get(id=user_id, profile__role=expected_role)
            except (User.DoesNotExist, ValueError):
                team_user = None
            if team_user:
                ProjectTeam.objects.update_or_create(
                    project=project,
                    user=team_user,
                    defaults={
                        'role_in_project': role_label,
                        'joined_date': datetime.date.today(),
                    },
                )
                assigned_count += 1
                if role_label in [
                    'Site Engineer', 'Finance Site', 'Safety Officer', 'Logistics',
                    'Director', 'Admin Site', 'Document Controller'
                ]:
                    project_assignment_notifications.append((team_user, role_label))

        boq_imported = _import_project_boq_from_url(request.user, project, (request.POST.get('boq_csv_url') or '').strip())
        baseline_created = False
        if request.POST.get('create_baseline') == 'on':
            duration_days = max((end_date - start_date).days, 0)
            Schedule.objects.create(
                project=project,
                activity_code='BASELINE',
                activity_name=request.POST.get('baseline_name') or 'Project Baseline',
                planned_start=start_date,
                planned_finish=end_date,
                duration_planned=duration_days,
                weight=100,
                status='NOT_STARTED',
            )
            baseline_created = True

        readiness = ProjectReadinessChecklist.objects.create(
            project=project,
            contractor_assigned=bool(contractor),
            consultant_assigned=bool(consultant),
            team_assigned=ProjectTeam.objects.filter(project=project).exists(),
            budget_set=budget > 0,
            timeline_set=bool(start_date and end_date and end_date >= start_date),
            baseline_created=baseline_created,
            boq_imported=WorkItem.objects.filter(project=project).exists(),
        )
        readiness.refresh_ready_status()
        readiness.save()

        notification_count = _notify_project_registration(project, request.user)

        readiness_text = " Project Ready." if readiness.ready else " Project belum ready, cek checklist setup."
        if assigned_count:
            suffix = " BOQ Google Sheet mos import ." if boq_imported else ""
            messages.success(request, f"New project '{name}' successfully initialized & published with {assigned_count} team members. {notification_count} notification sent.{suffix}{readiness_text}")
        else:
            suffix = " BOQ Google Sheet mos import ." if boq_imported else ""
            messages.success(request, f"New project '{name}' successfully initialized & published. {notification_count} notification sent.{suffix}{readiness_text}")
        return redirect('dashboard')
    
    return render(request, 'core/create_project.html')


def update_project(request, project_id):
    if request.method != 'POST':
        return redirect('dashboard')
    if not ensure_user_authenticated(request):
        messages.error(request, "Please login first.")
        return redirect('dashboard')
    role = _user_role(request)
    if role not in ['HQ_DIRECTOR', 'PROJECT_MANAGER', 'PROJECT_DIRECTOR', 'ADMIN_SYSTEM']:
        messages.error(request, "Only Project Manager / Admin can edit project.")
        return redirect('dashboard')

    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        messages.error(request, "Project not found.")
        return redirect('dashboard')
    if _reject_project_access(request, project):
        return redirect('dashboard')

    def parse_project_date(value, falltock):
        if isinstance(value, datetime.date):
            return value
        try:
            return datetime.date.fromisoformat(value) if value else falltock
        except ValueError:
            return falltock

    def get_company(company_id, company_type):
        if not company_id:
            return None
        try:
            return Company.objects.get(id=company_id, company_type=company_type)
        except (Company.DoesNotExist, ValueError):
            return None

    project_code = (request.POST.get('project_code') or '').strip() or None
    if project_code and Project.objects.exclude(id=project.id).filter(project_code=project_code).exists():
        messages.error(request, "Code project this is already used by another project.")
        return redirect('dashboard')

    try:
        budget = Decimal(str(request.POST.get('budget') or 0))
    except (ValueError, InvalidOperation):
        budget = Decimal('0')
    contract_value_raw = request.POST.get('contract_value')
    try:
        contract_value = Decimal(str(contract_value_raw)) if contract_value_raw not in (None, '') else budget
    except (ValueError, InvalidOperation):
        contract_value = budget

    contractor = get_company(request.POST.get('contractor_id'), 'CONTRACTOR')
    consultant = get_company(request.POST.get('consultant_id'), 'CONSULTANT')
    project.project_code = project_code
    project.name = request.POST.get('name') or project.name
    project.location = request.POST.get('location') or ''
    project.client_name = request.POST.get('client_name') or ''
    project.company = contractor
    project.contractor = contractor
    project.consultant = consultant
    project.budget = budget
    project.contract_value = contract_value
    project.start_date = parse_project_date(request.POST.get('start_date'), project.start_date)
    project.end_date = parse_project_date(request.POST.get('end_date'), project.end_date)
    project.status = request.POST.get('status', project.status)
    project.save()

    team_fields = [
        ('project_manager_id', 'PROJECT_MANAGER', 'Project Manager'),
        ('site_engineer_id', 'SITE_ENGINEER', 'Site Engineer'),
        ('supervisor_id', 'SUPERVISOR', 'Supervisor'),
        ('qs_id', 'COST_ENGINEER', 'QS / Cost Engineer'),
        ('finance_site_id', 'FINANCE_SITE', 'Finance Site'),
        ('safety_officer_id', 'HSE_OFFICER', 'Safety Officer'),
        ('storekeeper_id', 'STOREKEEPER', 'Storekeeper'),
        ('logistics_id', 'LOGISTICS', 'Logistics'),
        ('director_id', ['PROJECT_DIRECTOR', 'HQ_DIRECTOR'], 'Director'),
        ('doc_controller_id', 'DOC_CONTROLLER', 'Document Controller'),
        ('admin_site_id', 'ADMIN_SITE', 'Admin Site'),
        ('consultant_user_id', 'CONSULTANT', 'Consultant'),
    ]
    assignment_notify_roles = {
        'Site Engineer', 'Finance Site', 'Safety Officer', 'Logistics',
        'Director', 'Admin Site', 'Document Controller'
    }
    notified_user_ids = set()
    for field_name, expected_role, role_label in team_fields:
        user_id = request.POST.get(field_name)
        ProjectTeam.objects.filter(project=project, role_in_project=role_label).exclude(user_id=user_id or None).delete()
        if not user_id:
            continue
        try:
            if isinstance(expected_role, list):
                team_user = User.objects.get(id=user_id, profile__role__in=expected_role)
            else:
                team_user = User.objects.get(id=user_id, profile__role=expected_role)
        except (User.DoesNotExist, ValueError):
            continue
        team_member, created = ProjectTeam.objects.update_or_create(
            project=project,
            user=team_user,
            defaults={
                'role_in_project': role_label,
                'joined_date': datetime.date.today(),
            },
        )
        if created and role_label in assignment_notify_roles and team_user.id not in notified_user_ids:
            notified_user_ids.add(team_user.id)
            _notify_user(
                team_user,
                'Project assignment updated',
                f"You have been assigned as {role_label} for project {project.name}.",
                'project',
                project.id,
                'ALERT',
            )

    if request.POST.get('create_baseline') == 'on':
        duration_days = max((project.end_date - project.start_date).days, 0)
        Schedule.objects.update_or_create(
            project=project,
            activity_code='BASELINE',
            defaults={
                'activity_name': request.POST.get('baseline_name') or 'Project Baseline',
                'planned_start': project.start_date,
                'planned_finish': project.end_date,
                'duration_planned': duration_days,
                'weight': 100,
                'status': 'NOT_STARTED',
            },
        )

    readiness, _ = ProjectReadinessChecklist.objects.get_or_create(project=project)
    readiness.contractor_assigned = bool(project.contractor or project.company)
    readiness.consultant_assigned = bool(project.consultant)
    readiness.team_assigned = ProjectTeam.objects.filter(project=project).exists()
    readiness.budget_set = bool(project.budget and project.budget > 0)
    readiness.timeline_set = bool(project.start_date and project.end_date and project.end_date >= project.start_date)
    readiness.baseline_created = Schedule.objects.filter(project=project, activity_code='BASELINE').exists()
    readiness.boq_imported = WorkItem.objects.filter(project=project).exists()
    readiness.refresh_ready_status()
    readiness.save()

    messages.success(request, f"Project '{project.name}' successfully updated.")
    return redirect('dashboard')


def submit_vo(request):
    if request.method == 'POST':
        if not ensure_user_authenticated(request):
            messages.error(request, "Please login first.")
            return redirect('dashboard')
        role = _user_role(request)
        if role not in ['HQ_DIRECTOR', 'PROJECT_MANAGER', 'COST_ENGINEER', 'ADMIN_SYSTEM']:
            messages.error(request, "Access limited to submit Variation Order (VO).")
            return redirect('dashboard')

        project_id = request.POST.get('project_id')
        try:
            project = Project.objects.get(id=project_id)
        except (Project.DoesNotExist, ValueError):
            messages.error(request, "Project was not identified.")
            return redirect('dashboard')
        if _reject_project_access(request, project):
            return redirect('dashboard')

        project_code = project.project_code or 'UNKNOWN'
        vo_number = f"VO-{project_code}-{datetime.datetime.now().strftime('%M%S')}"
        try:
            requested_amount = float(request.POST.get('requested_amount') or 0)
        except ValueError:
            requested_amount = 0.0

        description = request.POST.get('description') or ''
        justification = request.POST.get('justification') or ''
        try:
            time_impact = int(request.POST.get('time_impact') or 0)
        except ValueError:
            time_impact = 0

        vo = VariationOrder.objects.create(
            project=project,
            vo_number=vo_number,
            description=description,
            requested_by=request.user,
            request_date=datetime.date.today(),
            requested_amount=requested_amount,
            time_impact=time_impact,
            justification=justification,
            status='PENDING'
        )
        wf.register_vo_submission(vo)
        messages.success(request, f"Variation Order {vo_number} successfully submit to approval HQ.")
    return redirect('dashboard')


def approve_vo(request, vo_id):
    if request.method == 'POST':
        if not ensure_user_authenticated(request):
            messages.error(request, "Please login first.")
            return redirect('dashboard')
        role = _user_role(request)
        if role not in ['HQ_DIRECTOR', 'PROJECT_MANAGER', 'PROJECT_DIRECTOR', 'ADMIN_SYSTEM']:
            messages.error(request, "Only HQ Director can approve Variation Order.")
            return redirect('dashboard')

        try:
            vo = VariationOrder.objects.get(id=vo_id)
        except VariationOrder.DoesNotExist:
            messages.error(request, "Variation Order not found.")
            return redirect('dashboard')
        if _reject_project_access(request, vo.project):
            return redirect('dashboard')

        status = request.POST.get('status')

        if status == 'APPROVED':
            vo.status = 'APPROVED'
            vo.approved_amount = vo.requested_amount
            vo.approved_by = request.user
            vo.approved_date = datetime.date.today()
            vo.save()
            wf.propagate_vo_approval(vo, request.user)
            messages.success(request, f"Variation Order {vo.vo_number} APPROVED with amount ${vo.approved_amount:,.2f} — budget & schedule updated.")
        elif status == 'REJECTED':
            vo.status = 'REJECTED'
            vo.save()
            wf.create_or_update_approval(
                vo.project, 'variation_order', vo.id,
                document_title=f"VO {vo.vo_number}",
                submitted_by=vo.requested_by,
                reviewed_by=request.user,
                status='REJECTED',
                comments='VO rejected by HQ Director.',
            )
            messages.warning(request, f"Variation Order {vo.vo_number} REJECTED.")

    return redirect('dashboard')


def submit_hse_incident(request):
    if request.method == 'POST':
        if not ensure_user_authenticated(request):
            messages.error(request, "Please login first.")
            return redirect('dashboard')
        role = _user_role(request)
        if role not in ['HQ_DIRECTOR', 'HSE_OFFICER', 'SITE_ENGINEER', 'ADMIN_SYSTEM']:
            messages.error(request, "Access limited to submit report HSE.")
            return redirect('dashboard')

        project_id = request.POST.get('project_id')
        try:
            project = Project.objects.get(id=project_id)
        except (Project.DoesNotExist, ValueError):
            messages.error(request, "Project was not identified.")
            return redirect('dashboard')
        if _reject_project_access(request, project):
            return redirect('dashboard')

        try:
            persons_involved = int(request.POST.get('persons_involved') or 0)
        except ValueError:
            persons_involved = 0
        report_type = request.POST.get('report_type') or 'INCIDENT'
        if report_type not in dict(HSEReport.REPORT_TYPE):
            report_type = 'INCIDENT'
        severity = request.POST.get('severity') or 'LOW'
        if severity not in dict(HSEReport.SEVERITY):
            severity = 'LOW'
        report_date_raw = request.POST.get('report_date') or datetime.date.today()
        if isinstance(report_date_raw, str):
            try:
                report_date = datetime.date.fromisoformat(report_date_raw)
            except ValueError:
                report_date = datetime.date.today()
        else:
            report_date = report_date_raw

        hse_report = HSEReport.objects.create(
            project=project,
            reporter=request.user,
            report_type=report_type,
            incident_type=request.POST.get('incident_type') or '',
            severity=severity,
            description=request.POST.get('description') or '',
            location=request.POST.get('location') or '',
            persons_involved=persons_involved,
            action_taken=request.POST.get('action_taken') or '',
            report_date=report_date
        )
        hse_title = 'HSE report submitted'
        if severity in ['HIGH', 'CRITICAL']:
            hse_title = 'Critical HSE report submitted'
        _notify_roles(
            ['HSE_OFFICER', 'PROJECT_MANAGER', 'HQ_DIRECTOR'],
            hse_title,
            f"{project.name} - {hse_report.get_report_type_display()} ({hse_report.get_severity_display()}) masuk dari {request.user.username}.",
            'hse_report',
            hse_report.id,
            'ALERT' if severity in ['HIGH', 'CRITICAL'] else 'INFO',
            exclude_user=request.user,
        )
        messages.success(request, "Report HSE / Incident new registered with successfully.")
    return redirect('dashboard')


def submit_material_request(request):
    if request.method == 'POST':
        if not ensure_user_authenticated(request):
            messages.error(request, "Please login first.")
            return redirect('dashboard')
        role = _user_role(request)
        if role not in ['HQ_DIRECTOR', 'SITE_ENGINEER', 'PROJECT_MANAGER', 'STOREKEEPER', 'LOGISTICS', 'ADMIN_SYSTEM']:
            messages.error(request, "Access limited to make Material Request.")
            return redirect('dashboard')

        project_id = request.POST.get('project_id')
        try:
            project = Project.objects.get(id=project_id)
        except (Project.DoesNotExist, ValueError):
            messages.error(request, "Project was not identified.")
            return redirect('dashboard')
        if _reject_project_access(request, project):
            return redirect('dashboard')

        material_item = None
        material_item_id = request.POST.get('material_item_id')
        if material_item_id:
            try:
                material_item = MaterialItem.objects.get(id=material_item_id, project=project)
            except (MaterialItem.DoesNotExist, ValueError):
                material_item = None

        try:
            quantity = Decimal(str(request.POST.get('quantity') or '0'))
        except (InvalidOperation, ValueError):
            quantity = Decimal('0')
        if quantity <= 0:
            messages.error(request, "Quantity pedidu material must greater than 0.")
            return redirect('dashboard')

        material_name = request.POST.get('material_name') or (material_item.name if material_item else '')
        unit = request.POST.get('unit') or (material_item.unit if material_item else '')
        material_request = MaterialRequest.objects.create(
            project=project,
            material_item=material_item,
            request_number=request.POST.get('request_number') or f"MR-{project.project_code or project.id}-{datetime.datetime.now().strftime('%Y%m%d%H%M')}",
            material_name=material_name,
            quantity=quantity,
            unit=unit,
            requested_by=request.user,
            required_date=request.POST.get('required_date') or datetime.date.today(),
            status='SUBMITTED',
            remarks=request.POST.get('remarks') or ''
        )
        wf.register_material_request_submission(material_request)
        _notify_roles(
            ['PROJECT_MANAGER', 'STOREKEEPER', 'LOGISTICS', 'HQ_DIRECTOR'],
            'Material request waiting approval',
            f"{material_request.request_number} - {material_request.material_name} waiting for approval.",
            'material_request',
            material_request.id,
            exclude_user=request.user,
        )
        messages.success(request, "Material Request successfully submitted to Storekeeper & Logistics.")
    return redirect('dashboard')


def submit_purchase_request(request):
    if request.method != 'POST':
        return redirect('dashboard')
    if not ensure_user_authenticated(request):
        messages.error(request, "Please login first.")
        return redirect('dashboard')
    role = _user_role(request)
    if role not in ['SITE_ENGINEER', 'PROJECT_MANAGER', 'PROJECT_DIRECTOR', 'STOREKEEPER', 'LOGISTICS', 'COST_ENGINEER', 'FINANCE_SITE', 'ADMIN_SITE', 'ADMIN_SYSTEM']:
        messages.error(request, "Access limited to make Purchase Request.")
        return redirect('dashboard')

    try:
        project = Project.objects.get(id=request.POST.get('project_id'))
    except (Project.DoesNotExist, ValueError):
        messages.error(request, "Project was not identified.")
        return redirect('dashboard')

    material_request = None
    material_request_id = request.POST.get('material_request_id')
    if material_request_id:
        try:
            material_request = MaterialRequest.objects.get(id=material_request_id, project=project)
        except (MaterialRequest.DoesNotExist, ValueError):
            material_request = None

    try:
        amount = Decimal(str(request.POST.get('amount') or '0'))
    except (InvalidOperation, ValueError):
        amount = Decimal('0')
    if amount < 0:
        amount = Decimal('0')

    purchase_number = request.POST.get('purchase_number') or f"PR-{project.project_code or project.id}-{datetime.datetime.now().strftime('%Y%m%d%H%M')}"
    description = request.POST.get('description') or ''
    if not description:
        messages.error(request, "Description kompra required filled.")
        return redirect('dashboard')

    purchase_request = PurchaseRequest.objects.create(
        project=project,
        material_request=material_request,
        purchase_number=purchase_number,
        description=description,
        supplier_name=request.POST.get('supplier_name') or '',
        amount=amount,
        required_date=request.POST.get('required_date') or None,
        requested_by=request.user,
        status='SUBMITTED',
        attachment=request.FILES.get('attachment') or None,
        remarks=request.POST.get('remarks') or '',
    )
    wf.register_purchase_request_submission(purchase_request)
    _notify_roles(
        ['STOREKEEPER', 'LOGISTICS', 'COST_ENGINEER', 'PROJECT_MANAGER'],
        'Purchase request waiting approval',
        f"{purchase_request.purchase_number or purchase_request.id} waiting for Approval System.",
        'purchase',
        purchase_request.id,
        exclude_user=request.user,
    )
    messages.success(request, f"Request Purchase {purchase_request.purchase_number} successfully submit to Approval System.")
    return redirect('dashboard')


def submit_logistics_record(request):
    if request.method != 'POST':
        return redirect('dashboard')
    if not ensure_user_authenticated(request):
        messages.error(request, "Please login first.")
        return redirect('dashboard')

    role = _user_role(request)
    if role not in LOGISTICS_ROLES:
        messages.error(request, "Access limited to modul Logistics.")
        return redirect('dashboard')

    try:
        project = Project.objects.get(id=request.POST.get('project_id'))
    except (Project.DoesNotExist, ValueError):
        messages.error(request, "Project was not identified.")
        return redirect('dashboard')
    if _reject_project_access(request, project):
        return redirect('dashboard')

    try:
        material_item = MaterialItem.objects.get(id=request.POST.get('material_item_id'), project=project)
    except (MaterialItem.DoesNotExist, ValueError):
        messages.error(request, "Material project invalid to Logistics.")
        return redirect('dashboard')

    record_type = request.POST.get('record_type') or 'STOCK_ISSUE'
    if record_type not in dict(LogisticsRecord.RECORD_TYPE_CHOICES):
        record_type = 'STOCK_ISSUE'

    quantity = _parse_decimal(request.POST.get('quantity'))
    if quantity <= 0:
        messages.error(request, "Quantity lojístior must greater than 0.")
        return redirect('dashboard')

    condition = request.POST.get('condition') or 'GOOD'
    if condition not in dict(LogisticsRecord.CONDITION_CHOICES):
        condition = 'GOOD'

    actual_date = request.POST.get('actual_date') or datetime.date.today()
    stock_transaction = None
    stock_type = _stock_type_for_logistics_type(record_type)
    if stock_type:
        stock_transaction = StockTransaction.objects.create(
            material_item=material_item,
            project=project,
            transaction_type=stock_type,
            quantity=quantity,
            reference_number=request.POST.get('reference_number') or '',
            supplier_name=request.POST.get('supplier_name') or '',
            unit_price=_parse_decimal(request.POST.get('unit_price')) if request.POST.get('unit_price') else None,
            location=request.POST.get('to_location') or request.POST.get('from_location') or project.location,
            notes=request.POST.get('remarks') or f"{dict(LogisticsRecord.RECORD_TYPE_CHOICES).get(record_type)} via Logistics",
            transaction_date=actual_date,
            recorded_by=request.user,
        )

    logistics_record = LogisticsRecord.objects.create(
        project=project,
        material_item=material_item,
        stock_transaction=stock_transaction,
        record_type=record_type,
        status=request.POST.get('status') or _status_for_logistics_type(record_type),
        quantity=quantity,
        unit=material_item.unit,
        reference_number=request.POST.get('reference_number') or '',
        supplier_name=request.POST.get('supplier_name') or '',
        from_location=request.POST.get('from_location') or '',
        to_location=request.POST.get('to_location') or project.location,
        condition=condition,
        scheduled_date=request.POST.get('scheduled_date') or None,
        actual_date=actual_date,
        handled_by=request.user,
        attachment=request.FILES.get('attachment') or None,
        remarks=request.POST.get('remarks') or '',
    )
    _notify_roles(
        ['PROJECT_MANAGER', 'STOREKEEPER', 'LOGISTICS'],
        'Logistics movement recorded',
        f"{logistics_record.get_record_type_display()} - {material_item.name}: {quantity} {material_item.unit}.",
        'logistics',
        logistics_record.id,
        exclude_user=request.user,
    )
    if stock_transaction:
        messages.success(request, "Notes Logistics successfully save and stock updated automátiku.")
    else:
        messages.success(request, "Notes Logistics successfully save.")
    return redirect('dashboard')


def review_material_request(request, request_id):
    if request.method != 'POST':
        return redirect('dashboard')
    if not ensure_user_authenticated(request):
        messages.error(request, "Please login first.")
        return redirect('dashboard')
    role = _user_role(request)
    if role not in ['PROJECT_MANAGER', 'PROJECT_DIRECTOR', 'STOREKEEPER', 'LOGISTICS', 'COST_ENGINEER', 'CONSULTANT', 'HQ_DIRECTOR', 'ADMIN_SYSTEM']:
        messages.error(request, "Access limited to approval material request.")
        return redirect('dashboard')

    try:
        material_request = MaterialRequest.objects.get(id=request_id)
    except MaterialRequest.DoesNotExist:
        messages.error(request, "Material request not found.")
        return redirect('dashboard')

    if material_request.status not in ['SUBMITTED']:
        messages.error(request, "This material request is not in the approval step.")
        return redirect('dashboard')

    action = request.POST.get('status', 'APPROVED')
    comments = request.POST.get('comments') or ''
    approval = Approval.objects.filter(module_type='material', reference_id=material_request.id).first()
    if not approval:
        approval = wf.register_material_request_submission(material_request)
    ok, msg = wf.process_phase_g_approval(
        approval,
        action,
        request.user,
        role,
        comments,
        {'approved_quantity': request.POST.get('approved_quantity') or ''},
    )

    material_request.refresh_from_db()
    if ok and action == 'REJECTED':
        _notify_user(
            material_request.requested_by,
            'Material request rejected',
            f"{material_request.request_number or material_request.id} rejected: {material_request.rejection_reason}",
            'material_request',
            material_request.id,
            'WARNING',
        )
    elif ok and material_request.status == 'APPROVED':
        _notify_roles(
            ['STOREKEEPER', 'LOGISTICS', 'PROJECT_MANAGER'],
            'Material request approved',
            f"{material_request.request_number or material_request.id} approved and ready for delivery.",
            'material_request',
            material_request.id,
            exclude_user=request.user,
        )

    if ok:
        messages.success(request, msg)
    else:
        messages.error(request, msg)
    return redirect('dashboard')


def deliver_material_request(request, request_id):
    if request.method != 'POST':
        return redirect('dashboard')
    if not ensure_user_authenticated(request):
        messages.error(request, "Please login first.")
        return redirect('dashboard')
    role = _user_role(request)
    if role not in ['STOREKEEPER', 'LOGISTICS', 'PROJECT_MANAGER', 'ADMIN_SYSTEM']:
        messages.error(request, "Access limited to material delivery.")
        return redirect('dashboard')

    try:
        material_request = MaterialRequest.objects.get(id=request_id)
    except MaterialRequest.DoesNotExist:
        messages.error(request, "Material request not found.")
        return redirect('dashboard')

    if material_request.status != 'APPROVED':
        messages.error(request, "Material request must be approved before delivery.")
        return redirect('dashboard')

    try:
        delivered_quantity = Decimal(str(request.POST.get('delivered_quantity') or material_request.approved_quantity or material_request.quantity))
    except (InvalidOperation, ValueError):
        delivered_quantity = material_request.approved_quantity or material_request.quantity
    if delivered_quantity <= 0:
        messages.error(request, "Quantity delivery must greater than 0.")
        return redirect('dashboard')

    material_request.status = 'DELIVERED'
    material_request.delivered_quantity = delivered_quantity
    material_request.delivery_reference = request.POST.get('delivery_reference') or material_request.delivery_reference
    material_request.supplier_name = request.POST.get('supplier_name') or material_request.supplier_name
    material_request.delivered_by = request.user
    material_request.delivered_date = datetime.date.today()
    material_request.save(update_fields=[
        'status', 'delivered_quantity', 'delivery_reference', 'supplier_name',
        'delivered_by', 'delivered_date'
    ])
    LogisticsRecord.objects.create(
        project=material_request.project,
        material_request=material_request,
        material_item=material_request.material_item,
        record_type='DELIVERY_TRACKING',
        status='ON_DELIVERY',
        quantity=delivered_quantity,
        unit=material_request.unit,
        reference_number=material_request.delivery_reference or material_request.request_number,
        supplier_name=material_request.supplier_name or '',
        from_location=material_request.supplier_name or 'Supplier',
        to_location=material_request.receiving_location or material_request.project.location,
        scheduled_date=material_request.required_date,
        actual_date=material_request.delivered_date,
        handled_by=request.user,
        remarks=request.POST.get('notes') or f"Delivery for material request {material_request.request_number or material_request.id}",
    )
    _notify_roles(
        ['STOREKEEPER', 'LOGISTICS', 'SITE_ENGINEER', 'PROJECT_MANAGER'],
        'Material delivered, waiting for receiving',
        f"{material_request.request_number or material_request.id} delivery  and waiting for receive.",
        'material_request',
        material_request.id,
        exclude_user=request.user,
    )
    messages.success(request, f"Material request {material_request.request_number or material_request.id} delivered.")
    return redirect('dashboard')


def receive_material_request(request, request_id):
    if request.method != 'POST':
        return redirect('dashboard')
    if not ensure_user_authenticated(request):
        messages.error(request, "Please login first.")
        return redirect('dashboard')
    role = _user_role(request)
    if role not in ['STOREKEEPER', 'LOGISTICS', 'SITE_ENGINEER', 'PROJECT_MANAGER', 'ADMIN_SYSTEM']:
        messages.error(request, "Access limited to material receiving.")
        return redirect('dashboard')

    try:
        material_request = MaterialRequest.objects.get(id=request_id)
    except MaterialRequest.DoesNotExist:
        messages.error(request, "Material request not found.")
        return redirect('dashboard')

    if material_request.status != 'DELIVERED':
        messages.error(request, "Material request must be delivered before receiving.")
        return redirect('dashboard')

    try:
        received_quantity = Decimal(str(request.POST.get('received_quantity') or material_request.delivered_quantity or material_request.quantity))
    except (InvalidOperation, ValueError):
        received_quantity = material_request.delivered_quantity or material_request.quantity
    if received_quantity <= 0:
        messages.error(request, "Quantity receive must greater than 0.")
        return redirect('dashboard')

    material_item = material_request.material_item
    if not material_item:
        item_code = f"MR-{material_request.id}"
        material_item, _ = MaterialItem.objects.get_or_create(
            project=material_request.project,
            item_code=item_code,
            defaults={
                'name': material_request.material_name,
                'unit': material_request.unit or 'unit',
                'category': 'LAIN',
                'minimum_stock': 0,
                'description': f"Auto-created from material request {material_request.request_number or material_request.id}",
            },
        )
        material_request.material_item = material_item

    stock_transaction = StockTransaction.objects.create(
        material_item=material_item,
        project=material_request.project,
        transaction_type='IN',
        quantity=received_quantity,
        reference_number=material_request.delivery_reference or material_request.request_number,
        supplier_name=material_request.supplier_name or '',
        location=request.POST.get('receiving_location') or material_request.receiving_location or material_request.project.location,
        notes=request.POST.get('notes') or f"Receiving from material request {material_request.request_number or material_request.id}",
        transaction_date=request.POST.get('received_date') or datetime.date.today(),
        recorded_by=request.user,
    )
    condition = request.POST.get('condition') or 'GOOD'
    if condition not in dict(LogisticsRecord.CONDITION_CHOICES):
        condition = 'GOOD'
    LogisticsRecord.objects.create(
        project=material_request.project,
        material_request=material_request,
        material_item=material_item,
        stock_transaction=stock_transaction,
        record_type='MATERIAL_RECEIVING',
        status='RECEIVED' if condition in ['GOOD', 'PARTIAL'] else 'DAMAGED',
        quantity=received_quantity,
        unit=material_request.unit or material_item.unit,
        reference_number=material_request.delivery_reference or material_request.request_number,
        supplier_name=material_request.supplier_name or '',
        from_location=material_request.supplier_name or 'Supplier',
        to_location=request.POST.get('receiving_location') or material_request.receiving_location or material_request.project.location,
        condition=condition,
        scheduled_date=material_request.required_date,
        actual_date=stock_transaction.transaction_date,
        handled_by=request.user,
        attachment=request.FILES.get('attachment') or None,
        remarks=request.POST.get('notes') or f"Receiving from material request {material_request.request_number or material_request.id}",
    )

    material_request.status = 'RECEIVED'
    material_request.received_quantity = received_quantity
    material_request.receiving_location = request.POST.get('receiving_location') or material_request.receiving_location
    material_request.received_by = request.user
    material_request.received_date = datetime.date.today()
    material_request.stock_transaction = stock_transaction
    material_request.save(update_fields=[
        'material_item', 'status', 'received_quantity', 'receiving_location',
        'received_by', 'received_date', 'stock_transaction'
    ])
    _notify_user(
        material_request.requested_by,
        'Material received',
        f"{material_request.request_number or material_request.id} received and stock updated.",
        'material_request',
        material_request.id,
        'SUCCESS',
    )
    messages.success(request, f"Material request {material_request.request_number or material_request.id} received and stock updated.")
    return redirect('dashboard')


def submit_bim_clash(request):
    if request.method == 'POST':
        if not ensure_user_authenticated(request):
            messages.error(request, "Please login first.")
            return redirect('dashboard')
        role = _user_role(request)
        if role not in ['HQ_DIRECTOR', 'QA_QC', 'PROJECT_MANAGER', 'ADMIN_SYSTEM']:
            messages.error(request, "Access limited to register BIM Clash.")
            return redirect('dashboard')

        project_id = request.POST.get('project_id')
        try:
            project = Project.objects.get(id=project_id)
        except (Project.DoesNotExist, ValueError):
            messages.error(request, "Project was not identified.")
            return redirect('dashboard')

        BIMClash.objects.create(
            project=project,
            clash_type=request.POST.get('clash_type', 'HARD'),
            description=request.POST.get('description') or '',
            discipline_a=request.POST.get('discipline_a') or '',
            discipline_b=request.POST.get('discipline_b') or '',
            severity=request.POST.get('severity', 'MEDIUM'),
            status='OPEN',
            detected_date=datetime.date.today()
        )
        messages.success(request, "BIM Clash new registered with successfully to discipline coordination.")
    return redirect('dashboard')


def import_boq_excel(request):
    if request.method == 'POST':
        if not ensure_user_authenticated(request):
            messages.error(request, "Please login first.")
            return redirect('dashboard')
        role = _user_role(request)
        if role not in ['HQ_DIRECTOR', 'PROJECT_MANAGER', 'PROJECT_DIRECTOR', 'COST_ENGINEER', 'SITE_ENGINEER', 'ADMIN_SYSTEM']:
            messages.error(request, "Access limited to import file BOQ.")
            return redirect('dashboard')

        project_id = request.POST.get('project_id')
        if not project_id:
            messages.error(request, "Please selesi project one.")
            return redirect('dashboard')

        if project_id == '__all__':
            target_projects = list(Project.objects.all())
        else:
            try:
                target_projects = [Project.objects.get(id=project_id)]
            except (Project.DoesNotExist, ValueError):
                messages.error(request, "Project was not identified.")
                return redirect('dashboard')
        if not target_projects:
            messages.error(request, "La in project to import BOQ.")
            return redirect('dashboard')

        uploaded_file = request.FILES.get('boq_file')
        boq_csv_url = (request.POST.get('boq_csv_url') or '').strip()
        if not uploaded_file and not boq_csv_url:
            messages.error(request, "Please hili file Excel/CSV one or haenter URL Google Sheet CSV.")
            return redirect('dashboard')

        overwrite = request.POST.get('overwrite') == 'on'

        if boq_csv_url:
            if not boq_csv_url.lower().startswith(('http://', 'https://')):
                messages.error(request, "URL Google Sheet CSV must start with http:// or https://.")
                return redirect('dashboard')
            try:
                req = urllib.request.Request(boq_csv_url, headers={'User-Agent': 'CCMS/1.0'})
                with urllib.request.urlopen(req, timeout=20) as response:
                    uploaded_file = io.BytesIO(response.read())
                uploaded_file.name = 'google_sheet_boq.csv'
            except Exception as e:
                messages.error(request, f"La konsege lee BOQ CSV by URL: {str(e)}")
                return redirect('dashboard')

        file_name = uploaded_file.name.lower()

        HEADER_KEYWORDS = [
            'no', 'item', 'code', 'kode', 'usavean', 'deskripsi', 'description',
            'pekerjaan', 'unit', 'stoan', 'qty', 'quantity', 'volume', 'harga',
            'rate', 'price', 'jumlah', 'amount', 'total', 'sat', 'ket'
        ]

        def andrmalize_boq_col(value):
            return re.sub(r'\s+', ' ', str(value or '').strip().lower())

        try:
            if file_name.endswith('.csv'):
                uploaded_file.seek(0)
                csv_bytes = uploaded_file.read()
                try:
                    csv_text = csv_bytes.decode('utf-8-sig')
                except UnicodeDecodeError:
                    csv_text = csv_bytes.decode('latin-1')
                try:
                    dialect = csv.Sniffer().sniff(csv_text[:4096]) if csv_text.strip() else csv.excel
                except csv.Error:
                    dialect = csv.excel
                raw_rows = list(csv.reader(io.StringIO(csv_text), dialect=dialect))
                header_row_idx = 0
                best_score = 0
                for i, raw_row in enumerate(raw_rows[:25]):
                    row_vals = [str(v).strip().lower() for v in raw_row]
                    score = sum(1 for kw in HEADER_KEYWORDS if any(kw in cell for cell in row_vals))
                    if score > best_score:
                        best_score = score
                        header_row_idx = i
                if best_score == 0:
                    messages.error(request, "Header BOQ CSV not found.")
                    return redirect('dashboard')

                df_columns = []
                seen_cols = {}
                for index, header in enumerate(raw_rows[header_row_idx]):
                    col_name = andrmalize_boq_col(header) or f"column_{index + 1}"
                    count = seen_cols.get(col_name, 0)
                    seen_cols[col_name] = count + 1
                    if count:
                        col_name = f"{col_name}_{count + 1}"
                    df_columns.append(col_name)

                boq_rows = []
                for raw_row in raw_rows[header_row_idx + 1:]:
                    padded_row = raw_row + [''] * max(0, len(df_columns) - len(raw_row))
                    boq_rows.append(dict(zip(df_columns, padded_row[:len(df_columns)])))
            elif file_name.endswith(('.xlsx', '.xls')):
                import pandas as pd

                raw_df = pd.read_excel(uploaded_file, header=None, dtype=str)
                header_row_idx = 0
                best_score = 0
                max_scan = min(25, len(raw_df))
                for i in range(max_scan):
                    row_vals = [str(v).strip().lower() for v in raw_df.iloc[i].fillna('')]
                    score = sum(1 for kw in HEADER_KEYWORDS if any(kw in cell for cell in row_vals))
                    if score > best_score:
                        best_score = score
                        header_row_idx = i

                uploaded_file.seek(0)
                df = pd.read_excel(uploaded_file, header=header_row_idx, dtype=str)
                df.columns = [andrmalize_boq_col(c) for c in df.columns]
                df_columns = df.columns.tolist()
                boq_rows = [
                    {col: row.get(col, '') for col in df_columns}
                    for _, row in df.fillna('').iterrows()
                ]
            else:
                messages.error(request, "Invalid file format. Use .xlsx, .xls, or .csv.")
                return redirect('dashboard')
        except Exception as e:
            messages.error(request, f"Erro toinhira lee file: {str(e)}")
            return redirect('dashboard')

        COLUMN_RULES = {
            'code': [
                ('exact', ['no', 'item code', 'kode item', 'item and', 'kode']),
                ('contains', ['item code', 'kode item', 'kode', 'code']),
            ],
            'name': [
                ('exact', ['usavean pekerjaan', 'deskripsi pekerjaan', 'description of work',
                           'item description', 'item name', 'usavean', 'deskripsi', 'pekerjaan',
                           'description', 'nama pekerjaan']),
                ('contains', ['usavean pekerjaan', 'deskripsi pekerjaan', 'usavean', 'pekerjaan',
                              'deskripsi', 'description', 'item name']),
            ],
            'category': [
                ('exact', ['ortegori', 'category', 'kelompok', 'group', 'divisi']),
                ('contains', ['ortegori', 'category', 'divisi']),
            ],
            'sub_category': [
                ('exact', ['sub ortegori', 'sub category', 'sub-ortegori']),
                ('contains', ['sub ortegori', 'sub category']),
            ],
            'unit': [
                ('exact', ['stoan', 'unit', 'sat.', 'sat']),
                ('contains', ['stoan', 'unit']),
            ],
            'qty': [
                ('exact', ['volume', 'qty', 'quantity', 'jumlah', 'boq qty', 'boq quantity',
                           'kuantitas', 'koantonede']),
                ('contains', ['volume', 'qty', 'quantity', 'jumlah', 'kuantitas']),
            ],
            'rate': [
                ('exact', ['harga stoan', 'unit rate', 'unit price', 'harga/unit',
                           'rate', 'harga', 'price']),
                ('contains', ['harga stoan', 'unit rate', 'unit price', 'harga']),
            ],
        }

        def find_col(field, df_cols):
            rules = COLUMN_RULES.get(field, [])
            for match_type, keywords in rules:
                for kw in keywords:
                    for col in df_cols:
                        if match_type == 'exact' and col == kw:
                            return col
                        elif match_type == 'contains' and kw in col:
                            return col
            return None

        code_col = find_col('code', df_columns)
        name_col = find_col('name', df_columns)
        category_col = find_col('category', df_columns)
        sub_col = find_col('sub_category', df_columns)
        unit_col = find_col('unit', df_columns)
        qty_col = find_col('qty', df_columns)
        rate_col = find_col('rate', df_columns)

        if not name_col:
            top_cols = ', '.join([f"'{c}'" for c in df_columns[:12]])
            messages.error(request, f"Column description/name work not found. "
                           f"Kolom yang tertoca: [{top_cols}]. "
                           f"Ensure the Excel header has a 'Work Description' or 'Description' column.")
            return redirect('dashboard')

        if overwrite:
            WorkItem.objects.filter(project__in=target_projects).delete()

        def safe_float(val):
            if val is None:
                return 0.0
            s = str(val).strip().replace(',', '').replace('\xa0', '').replace(' ', '')
            s = re.sub(r'[^\d.\-]', '', s)
            try:
                return float(s) if s else 0.0
            except ValueError:
                return 0.0

        def clean_str(val):
            if val is None:
                return ''
            if str(val).strip().lower() in ('nan', 'none', ''):
                return ''
            s = str(val).strip()
            if re.match(r'^\d+\.0$', s):
                s = s[:-2]
            return s

        SKIP_NAME_RE = re.compile(
            r'^(\d+\.?|[A-Z]\.?|[IVX]+\.?)$|'
            r'^(total|sub.?total|grand.?total|jumlah|nan|none|#)',
            re.IGNORECASE
        )

        success_count = 0
        skipped_count = 0
        category_count = 0
        current_category = ''

        for row in boq_rows:
            raw_name = row.get(name_col, '') if name_col else ''
            name_str = clean_str(raw_name)

            if not name_str or len(name_str) < 3:
                skipped_count += 1
                continue
            if SKIP_NAME_RE.match(name_str.strip()):
                skipped_count += 1
                continue

            try:
                code_val = clean_str(row.get(code_col, ''))[:100] if code_col else ''
                sub_val = clean_str(row.get(sub_col, ''))[:100] if sub_col else ''
                unit_val = clean_str(row.get(unit_col, ''))[:50] if unit_col else ''
                qty_val = safe_float(row.get(qty_col) if qty_col else None)
                rate_val = safe_float(row.get(rate_col) if rate_col else None)
                if _is_category_heading(code_val, name_str, [qty_val, rate_val]) or _is_item_description_category(
                    name_str, unit_val, qty_val, rate_val
                ):
                    current_category = name_str[:100]
                    category_count += 1
                    skipped_count += 1
                    continue
                if not unit_val:
                    unit_val = 'Ls'
                if qty_val <= 0 and unit_val.lower() in ('ls', 'l/s', 'lump sum') and rate_val > 0:
                    qty_val = 1.0

                category_val = (
                    clean_str(row.get(category_col, '')) if category_col else ''
                )
                category_val = (category_val or current_category or 'Umum')[:100]
                boq_amount_val = round(qty_val * rate_val, 2)

                for target_project in target_projects:
                    existing_item = None
                    if not overwrite and code_val:
                        existing_item = WorkItem.objects.filter(
                            project=target_project,
                            item_code=code_val,
                            category=category_val,
                        ).first()
                    if not overwrite and not existing_item:
                        existing_item = WorkItem.objects.filter(
                            project=target_project,
                            item_name__iexact=name_str[:255],
                            category=category_val,
                        ).first()

                    if existing_item:
                        existing_item.item_code = code_val
                        existing_item.item_name = name_str[:255]
                        existing_item.category = category_val
                        existing_item.sub_category = sub_val
                        existing_item.unit = unit_val
                        existing_item.boq_quantity = qty_val
                        existing_item.unit_rate = rate_val
                        existing_item.boq_amount = boq_amount_val
                        existing_item.save()
                    else:
                        WorkItem.objects.create(
                            project=target_project,
                            item_code=code_val,
                            item_name=name_str[:255],
                            category=category_val,
                            sub_category=sub_val,
                            unit=unit_val,
                            boq_quantity=qty_val,
                            unit_rate=rate_val,
                            boq_amount=boq_amount_val,
                            actual_quantity=0,
                            actual_amount=0,
                            progress_percent=0
                        )
                    success_count += 1
            except Exception:
                skipped_count += 1

        if success_count > 0:
            messages.success(request, (
                f"Import BOQ successfully! {success_count} item work save to datatose "
                f"for {len(target_projects)} projects "
                f"(header terdeteksi di toris ke-{header_row_idx + 1}). "
                f"{category_count} ortegori terdeteksi. "
                f"{skipped_count} toris dilewati (header/total/kosong/ortegori)."
            ))
        else:
            detected = f"name='{name_col}', qty='{qty_col}', rate='{rate_col}', unit='{unit_col}'"
            messages.warning(request, (
                f"No items were imported successfully. "
                f"Kolom terdeteksi: [{detected}]. "
                f"Verifior formto file Excel and asegura column loos ."
            ))

    return redirect('dashboard')


def _item_report_group_rows(item_report):
    next_group = ItemProgressReport.objects.filter(
        project=item_report.project,
        source_row__gt=item_report.source_row,
        item_no__isnull=False,
    ).order_by('source_row').first()
    queryset = ItemProgressReport.objects.filter(
        project=item_report.project,
        source_row__gte=item_report.source_row,
    )
    if next_group:
        queryset = queryset.filter(source_row__lt=next_group.source_row)
    return list(queryset.order_by('source_row'))


def _parse_item_report_detail_rows(request):
    activities = request.POST.getlist('activity[]') or [request.POST.get('activity') or '']
    descriptions = request.POST.getlist('description[]') or [request.POST.get('description') or '']
    progress_values = request.POST.getlist('progress_percent[]') or [request.POST.get('progress_percent') or 0]
    statuses = request.POST.getlist('status[]') or [request.POST.get('status') or '']
    detail_rows = []
    max_length = max(len(activities), len(descriptions), len(progress_values), len(statuses), 1)
    for index in range(max_length):
        row_activity = (activities[index] if index < len(activities) else '').strip()
        row_description = (descriptions[index] if index < len(descriptions) else '').strip()
        row_progress = progress_values[index] if index < len(progress_values) else 0
        row_status = (statuses[index] if index < len(statuses) else '').strip()
        if not row_activity and not row_description:
            continue
        try:
            row_progress = Decimal(str(row_progress or 0))
        except Exception:
            row_progress = Decimal('0')
        detail_rows.append({
            'activity': row_activity,
            'description': row_description,
            'progress_percent': row_progress,
            'status': row_status,
        })
    return detail_rows


def submit_item_progress_report(request):
    if request.method == 'POST':
        project_id = request.POST.get('project_id')
        project = _filter_projects_for_user(request.user).filter(id=project_id).first()
        if not project:
            messages.error(request, 'Please select a valid project for this item report.')
            return redirect('dashboard')

        location = request.POST.get('location')

        # Get up to 4 selected photo IDs
        photo_ids = request.POST.getlist('photo_ids[]')[:4]

        detail_rows = _parse_item_report_detail_rows(request)

        if not detail_rows:
            messages.error(request, 'Please add at least one activity row.')
            return redirect(f"{reverse('dashboard')}?item_report_project={project.id}#report-per-item")

        max_row = ItemProgressReport.objects.filter(project=project).aggregate(max_row=Max('source_row'))['max_row']
        next_row = (max_row or 0) + 1

        max_item = ItemProgressReport.objects.filter(project=project).aggregate(max_item=Max('item_no'))['max_item']
        next_item_no = (max_item or 0) + 1

        valid_photos = ProgressPhoto.objects.none()
        if photo_ids:
            valid_photos = ProgressPhoto.objects.filter(id__in=photo_ids, daily_report__project=project)

        created_reports = []
        for index, row in enumerate(detail_rows):
            item_report = ItemProgressReport.objects.create(
                project=project,
                source_name='Manual Input',
                source_sheet='Form Input',
                source_row=next_row + index,
                item_no=next_item_no if index == 0 else None,
                activity=row['activity'],
                location=location if index == 0 else '',
                description=row['description'],
                progress_percent=row['progress_percent'],
                status=row['status'],
            )
            if index == 0 and valid_photos:
                item_report.photos.set(valid_photos)
            created_reports.append(item_report)

        messages.success(request, f'Item Progress Report saved successfully ({len(created_reports)} row(s)).')

        return redirect(f"{reverse('dashboard')}?item_report_project={project.id}#report-per-item")

    return redirect('dashboard')


def update_item_progress_report(request, item_id):
    if request.method != 'POST':
        return redirect('dashboard')

    item_report = ItemProgressReport.objects.select_related('project').filter(id=item_id).first()
    if not item_report or not item_report.project or not _user_can_access_project(request.user, item_report.project):
        messages.error(request, 'You do not have access to this item report.')
        return redirect('dashboard')

    detail_rows = _parse_item_report_detail_rows(request)
    if not detail_rows:
        messages.error(request, 'Please add at least one activity row.')
        return redirect(f"{reverse('dashboard')}?item_report_project={item_report.project.id}#report-per-item")

    location = request.POST.get('location') or ''
    photo_ids = request.POST.getlist('photo_ids[]')[:4]
    has_photo_selection = bool(photo_ids)

    with transaction.atomic():
        group_rows = _item_report_group_rows(item_report)
        if not group_rows:
            messages.error(request, 'Item report group not found.')
            return redirect(f"{reverse('dashboard')}?item_report_project={item_report.project.id}#report-per-item")

        first_row = group_rows[0]
        start_row = first_row.source_row
        old_count = len(group_rows)
        new_count = len(detail_rows)
        delta = new_count - old_count

        if delta > 0:
            rows_to_shift = ItemProgressReport.objects.filter(
                project=item_report.project,
                source_row__gte=start_row + old_count,
            ).order_by('-source_row')
            for row in rows_to_shift:
                row.source_row += delta
                row.save(update_fields=['source_row'])
        elif delta < 0:
            for row in group_rows[new_count:]:
                row.delete()
            rows_to_shift = ItemProgressReport.objects.filter(
                project=item_report.project,
                source_row__gte=start_row + old_count,
            ).order_by('source_row')
            for row in rows_to_shift:
                row.source_row += delta
                row.save(update_fields=['source_row'])

        valid_photos = ProgressPhoto.objects.none()
        if has_photo_selection:
            valid_photos = ProgressPhoto.objects.filter(id__in=photo_ids, daily_report__project=item_report.project)

        existing_rows = _item_report_group_rows(first_row)
        for index, row_data in enumerate(detail_rows):
            if index < len(existing_rows):
                row = existing_rows[index]
            else:
                row = ItemProgressReport(
                    project=item_report.project,
                    source_name=first_row.source_name,
                    source_sheet=first_row.source_sheet,
                )
            row.source_row = start_row + index
            row.item_no = first_row.item_no if index == 0 else None
            row.location = location if index == 0 else ''
            row.activity = row_data['activity']
            row.description = row_data['description']
            row.progress_percent = row_data['progress_percent']
            row.status = row_data['status']
            row.save()
            if index == 0 and has_photo_selection:
                row.photos.set(valid_photos)

    messages.success(request, 'Item Progress Report updated successfully.')
    return redirect(f"{reverse('dashboard')}?item_report_project={item_report.project.id}#report-per-item")


def delete_item_progress_report(request, item_id):
    if request.method != 'POST':
        return redirect('dashboard')

    item_report = ItemProgressReport.objects.select_related('project').filter(id=item_id).first()
    if not item_report or not item_report.project or not _user_can_access_project(request.user, item_report.project):
        messages.error(request, 'You do not have access to this item report.')
        return redirect('dashboard')

    project_id = item_report.project.id
    with transaction.atomic():
        group_rows = _item_report_group_rows(item_report)
        if not group_rows:
            messages.error(request, 'Item report group not found.')
            return redirect(f"{reverse('dashboard')}?item_report_project={project_id}#report-per-item")
        start_row = group_rows[0].source_row
        row_count = len(group_rows)
        next_source_row = start_row + row_count
        for row in group_rows:
            row.delete()
        rows_to_shift = ItemProgressReport.objects.filter(
            project_id=project_id,
            source_row__gte=next_source_row,
        ).order_by('source_row')
        for row in rows_to_shift:
            row.source_row -= row_count
            row.save(update_fields=['source_row'])

    messages.success(request, 'Item Progress Report deleted successfully.')
    return redirect(f"{reverse('dashboard')}?item_report_project={project_id}#report-per-item")


def get_daily_report_photos(request):
    """AJAX endpoint: return list of photos for a given daily report."""
    from django.http import JsonResponse
    daily_report_id = request.GET.get('daily_report_id')
    if not daily_report_id:
        return JsonResponse({'photos': []})
    photos = ProgressPhoto.objects.filter(daily_report_id=daily_report_id)
    data = []
    for p in photos:
        url = ''
        if p.image and hasattr(p.image, 'url'):
            try:
                url = p.image.url
            except Exception:
                url = p.image_url or ''
        else:
            url = p.image_url or ''
        data.append({'id': p.id, 'url': url, 'caption': p.caption or ''})
    return JsonResponse({'photos': data})


def import_progress_csv(request):
    if request.method != 'POST':
        return redirect('dashboard')
    if not ensure_user_authenticated(request):
        messages.error(request, "Please login first.")
        return redirect('dashboard')

    role = _user_role(request)
    if role not in ['HQ_DIRECTOR', 'PROJECT_MANAGER', 'COST_ENGINEER', 'SITE_ENGINEER', 'ADMIN_SYSTEM']:
        messages.error(request, "Access limited to import progress CSV.")
        return redirect('dashboard')

    selected_project = None
    project_id = request.POST.get('project_id')
    if project_id:
        try:
            selected_project = Project.objects.get(id=project_id)
        except (Project.DoesNotExist, ValueError):
            messages.error(request, "Project was not identified.")
            return redirect('dashboard')

    csv_text = ''
    csv_url = (request.POST.get('progress_csv_url') or '').strip()
    uploaded_file = request.FILES.get('progress_csv_file')

    if csv_url:
        if not csv_url.lower().startswith(('http://', 'https://')):
            messages.error(request, "URL Google Sheet CSV must start with http:// or https://.")
            return redirect('dashboard')
        try:
            req = urllib.request.Request(csv_url, headers={'User-Agent': 'CCMS/1.0'})
            with urllib.request.urlopen(req, timeout=20) as response:
                csv_bytes = response.read()
            csv_text = csv_bytes.decode('utf-8-sig')
        except UnicodeDecodeError:
            csv_text = csv_bytes.decode('latin-1')
        except Exception as e:
            messages.error(request, f"La konsege lee CSV by URL: {str(e)}")
            return redirect('dashboard')
    elif uploaded_file:
        try:
            csv_bytes = uploaded_file.read()
            try:
                csv_text = csv_bytes.decode('utf-8-sig')
            except UnicodeDecodeError:
                csv_text = csv_bytes.decode('latin-1')
        except Exception as e:
            messages.error(request, f"La konsege lee file CSV: {str(e)}")
            return redirect('dashboard')
    else:
        messages.error(request, "Please haenter URL Google Sheet CSV or upload file CSV.")
        return redirect('dashboard')

    def andrmalize_header(value):
        return re.sub(r'[^a-z0-9]+', '_', str(value or '').strip().lower()).strip('_')

    def clean_str(value):
        text = str(value or '').strip()
        if text.lower() in ('nan', 'none', 'null'):
            return ''
        if re.match(r'^\d+\.0$', text):
            return text[:-2]
        return text

    def parse_number(value, default=0.0):
        text = clean_str(value)
        if not text:
            return default
        text = text.replace('%', '').replace('\xa0', '').replace(' ', '')
        if ',' in text and '.' not in text:
            text = text.replace(',', '.')
        else:
            text = text.replace(',', '')
        text = re.sub(r'[^\d.\-]', '', text)
        try:
            return float(text) if text else default
        except ValueError:
            return default

    def clamp_progress(value):
        return max(0.0, min(parse_number(value), 100.0))

    def parse_date(value):
        text = clean_str(value)
        if not text:
            return datetime.date.today()
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y'):
            try:
                return datetime.datetime.strptime(text, fmt).date()
            except ValueError:
                pass
        try:
            return datetime.date.fromisoformat(text[:10])
        except ValueError:
            return datetime.date.today()

    aliases = {
        'project_code': ['project_code', 'kode_project', 'kode_proyek', 'project', 'proyek_code', 'proyek'],
        'item_code': ['item_code', 'item_code', 'code', 'kode', 'wbs', 'work_code', 'no', 'no_item'],
        'item_name': ['item_name', 'nama_item', 'work_item', 'pekerjaan', 'usavean_pekerjaan', 'description', 'deskripsi'],
        'boq_quantity': ['boq_quantity', 'boq_qty', 'quantity', 'qty', 'volume', 'target_qty', 'area'],
        'actual_quantity': ['actual_quantity', 'actual_qty', 'qty_actual', 'realisasi', 'volume_actual', 'progress_qty', 'actual_volume'],
        'unit': ['unit', 'stoan'],
        'weight': ['weight', 'weight_percent', 'bobot', 'bobot_percent', 'bobot_%'],
        'progress_percent': ['progress_percent', 'progress', 'progress_%', 'percent', 'persen', 'persentase'],
        'report_date': ['report_date', 'tanggal', 'date', 'periode'],
    }

    try:
        sample = csv_text[:4096]
        dialect = csv.Sniffer().sniff(sample) if sample.strip() else csv.excel
    except csv.Error:
        dialect = csv.excel

    csv_rows = list(csv.reader(io.StringIO(csv_text), dialect=dialect))
    if not csv_rows:
        messages.error(request, "CSV has no header. Please use the first row as column names.")
        return redirect('dashboard')

    alias_lookup = {andrmalize_header(alias) for values in aliases.values() for alias in values}
    header_row_idx = None
    best_score = 0
    max_scan = min(30, len(csv_rows))
    for idx in range(max_scan):
        andrmalized_cells = [andrmalize_header(cell) for cell in csv_rows[idx]]
        score = sum(1 for cell in andrmalized_cells if cell in alias_lookup)
        if score > best_score:
            best_score = score
            header_row_idx = idx

    if header_row_idx is None or best_score < 2:
        messages.error(request, "Header CSV not found. Ensure ortak in column Description/Item and Quantity/Volume.")
        return redirect('dashboard')

    raw_headers = csv_rows[header_row_idx]
    fieldnames = []
    seen_headers = {}
    for index, header in enumerate(raw_headers):
        andrmalized = andrmalize_header(header) or f"column_{index + 1}"
        count = seen_headers.get(andrmalized, 0)
        seen_headers[andrmalized] = count + 1
        if count:
            andrmalized = f"{andrmalized}_{count + 1}"
        fieldnames.append(andrmalized)

    reader_rows = []
    for raw_row in csv_rows[header_row_idx + 1:]:
        padded_row = raw_row + [''] * max(0, len(fieldnames) - len(raw_row))
        reader_rows.append(dict(zip(fieldnames, padded_row[:len(fieldnames)])))

    andrmalized_to_original = {name: name for name in fieldnames}

    def get_col(field):
        for alias in aliases[field]:
            andrmalized = andrmalize_header(alias)
            if andrmalized in andrmalized_to_original:
                return andrmalized_to_original[andrmalized]
        return None

    cols = {field: get_col(field) for field in aliases}
    if not selected_project and not cols['project_code']:
        messages.error(request, "Please hili project, or filled column project_code in CSV.")
        return redirect('dashboard')
    if not cols['item_code'] and not cols['item_name']:
        messages.error(request, "CSV presiza column item_code/item_code or item_name/work.")
        return redirect('dashboard')

    has_progress_source = bool(cols['progress_percent'] or cols['actual_quantity'])
    project_totals = {}
    success_count = 0
    skipped_count = 0
    created_count = 0
    updated_count = 0
    category_count = 0
    current_categories = {}

    for row in reader_rows:
        try:
            project = selected_project
            if not project:
                project_code = clean_str(row.get(cols['project_code']))
                project = Project.objects.filter(project_code=project_code).first()
                if not project:
                    skipped_count += 1
                    continue

            item_code = clean_str(row.get(cols['item_code'])) if cols['item_code'] else ''
            item_name = clean_str(row.get(cols['item_name'])) if cols['item_name'] else ''
            if not item_code and not item_name:
                skipped_count += 1
                continue
            if item_name.lower().startswith(('sub total', 'subtotal', 'total', 'grand total')):
                skipped_count += 1
                continue

            boq_quantity = parse_number(row.get(cols['boq_quantity'])) if cols['boq_quantity'] else 0.0
            actual_quantity = parse_number(row.get(cols['actual_quantity'])) if cols['actual_quantity'] else 0.0
            if _is_category_heading(item_code, item_name, [boq_quantity, actual_quantity]):
                current_categories[project.id] = item_name[:100]
                category_count += 1
                skipped_count += 1
                continue

            if cols['progress_percent']:
                progress = clamp_progress(row.get(cols['progress_percent']))
            elif boq_quantity > 0:
                progress = max(0.0, min((actual_quantity / boq_quantity) * 100.0, 100.0))
            else:
                progress = 0.0

            weight = parse_number(row.get(cols['weight']), default=0.0) if cols['weight'] else 0.0
            if weight <= 0 and boq_quantity > 0:
                weight = boq_quantity
            report_date = parse_date(row.get(cols['report_date'])) if cols['report_date'] else datetime.date.today()

            item = None
            if item_code:
                item = WorkItem.objects.filter(project=project, item_code=item_code).first()
            if not item and item_name:
                item = WorkItem.objects.filter(project=project, item_name__iexact=item_name).first()

            defaults = {}
            if boq_quantity > 0:
                defaults['boq_quantity'] = boq_quantity
            if has_progress_source:
                defaults['progress_percent'] = progress
                defaults['actual_quantity'] = actual_quantity
            if cols['unit']:
                unit_value = clean_str(row.get(cols['unit']))
                if unit_value:
                    defaults['unit'] = unit_value[:50]
            current_category = current_categories.get(project.id, '')

            if item:
                for field, value in defaults.items():
                    setattr(item, field, value)
                if current_category and (not item.category or item.category == 'Google Sheet Progress'):
                    item.category = current_category
                if has_progress_source and item.boq_amount and progress:
                    item.actual_amount = item.boq_amount * Decimal(str(progress)) / Decimal('100')
                item.save()
                updated_count += 1
            else:
                item = WorkItem.objects.create(
                    project=project,
                    item_code=item_code[:100],
                    item_name=(item_name or item_code)[:255],
                    category=current_category or 'Google Sheet Progress',
                    unit=clean_str(row.get(cols['unit']))[:50] if cols['unit'] else '',
                    boq_quantity=boq_quantity,
                    actual_quantity=actual_quantity,
                    progress_percent=progress,
                )
                created_count += 1

            if has_progress_source:
                total = project_totals.setdefault(project.id, {
                    'project': project,
                    'weighted_sum': 0.0,
                    'weight_total': 0.0,
                    'progress_sum': 0.0,
                    'row_count': 0,
                    'report_date': report_date,
                })
                total['progress_sum'] += progress
                total['row_count'] += 1
                total['report_date'] = max(total['report_date'], report_date)
                if weight > 0:
                    total['weighted_sum'] += weight * progress
                    total['weight_total'] += weight
            success_count += 1
        except Exception:
            skipped_count += 1

    for total in project_totals.values():
        if total['weight_total'] > 0:
            overall_progress = total['weighted_sum'] / total['weight_total']
        elif total['row_count'] > 0:
            overall_progress = total['progress_sum'] / total['row_count']
        else:
            continue

        ProgressReport.objects.update_or_create(
            project=total['project'],
            report_date=total['report_date'],
            defaults={
                'report_period': f"Google Sheet CSV {total['report_date'].isoformat()}",
                'overall_progress': round(overall_progress, 2),
                'civil_progress': round(overall_progress, 2),
                'remarks': f"Imported from Google Sheet CSV. {success_count} rows processed.",
                'prepared_by': request.user,
            },
        )

    if success_count:
        messages.success(request, (
            f"Import progress CSV successfully: {success_count} rows prosesu , "
            f"{created_count} item dibuat, {updated_count} item diupdate, "
            f"{category_count} ortegori terdeteksi, "
            f"{len(project_totals)} project progress totals calculated "
            f"(header toris ke-{header_row_idx + 1}). {skipped_count} toris dilewati."
        ))
    else:
        messages.warning(request, (
            "La in progress that successfully import. Ensure column project_code/item_code/progress_percent "
            "or actual_quantity + boq_quantity loos ."
        ))

    return redirect('dashboard')


def process_approval(request, approval_id):
    """Central approval handler for all module types."""
    if request.method != 'POST':
        return redirect('dashboard')
    if not ensure_user_authenticated(request):
        messages.error(request, "Please login first.")
        return redirect('dashboard')

    role = _user_role(request)
    allowed = [
        'PROJECT_MANAGER', 'PROJECT_DIRECTOR', 'HQ_DIRECTOR',
        'FINANCE_HQ', 'FINANCE_SITE', 'COST_ENGINEER',
        'CONSULTANT', 'DOC_CONTROLLER', 'STOREKEEPER', 'QA_QC',
        'ADMIN_SYSTEM',
    ]
    if role not in allowed:
        messages.error(request, "Access limited to prosesu approval central.")
        return redirect('dashboard')

    try:
        approval = Approval.objects.get(id=approval_id)
    except Approval.DoesNotExist:
        messages.error(request, "Record approval not found.")
        return redirect('dashboard')

    action = request.POST.get('status', 'APPROVED')
    comments = request.POST.get('comments', '')

    if approval.module_type == 'daily_report':
        if role not in ['CONSULTANT', 'HQ_DIRECTOR']:
            messages.error(request, "Daily Report that verified must enter to Consultant/HQ in Approval System.")
            return redirect('dashboard')
        if approval.status != 'REVIEWED':
            messages.error(request, "Daily Report must be verified by Project Manager before entering the Approval System.")
            return redirect('dashboard')
        if action == 'REJECTED':
            ok, msg = wf.process_central_approval(approval, 'REJECTED', request.user, comments)
        elif role == 'CONSULTANT':
            approval.reviewed_by = request.user
            approval.consultant_by = request.user
            approval.consultant_at = timezone.now()
            approval.current_step = 'HQ_APPROVAL'
            approval.comments = (comments or 'Consultant reviewed. Waiting HQ approval.')
            approval.save(update_fields=['reviewed_by', 'consultant_by', 'consultant_at', 'current_step', 'comments'])
            wf.record_approval_step(approval, 'CONSULTANT', 'HQ_APPROVAL', 'Approved', comments, request.user)
            ok, msg = True, 'Daily report reviewed by Consultant. Waiting HQ approval.'
        elif role == 'HQ_DIRECTOR':
            ok, msg = wf.process_central_approval(approval, 'APPROVED', request.user, comments)
        else:
            ok, msg = False, 'This role is not authorized for final daily report approval.'
    elif approval.module_type == 'document':
        try:
            doc = Document.objects.get(id=approval.reference_id)
        except Document.DoesNotExist:
            ok, msg = False, 'Document not found.'
        else:
            reject_roles_by_stage = {
                'SUBMITTED': ['DOC_CONTROLLER', 'ADMIN_SYSTEM'],
                'DC_REVIEW': ['CONSULTANT', 'ADMIN_SYSTEM'],
                'CONSULTANT_REVIEW': ['PROJECT_MANAGER', 'HQ_DIRECTOR', 'ADMIN_SYSTEM'],
            }
            if action == 'REJECTED':
                if role not in reject_roles_by_stage.get(doc.status, []):
                    ok, msg = False, 'Role not autwithrized to reject this document stage.'
                else:
                    _reject_document_for_revision(doc, request.user, comments)
                    ok, msg = True, f'Document {doc.document_number} needs revision.'
            elif doc.status == 'SUBMITTED':
                if role not in ['DOC_CONTROLLER', 'ADMIN_SYSTEM']:
                    ok, msg = False, 'Document must hetan review by Document Controller first.'
                else:
                    from_status = doc.status
                    doc.status = 'DC_REVIEW'
                    doc.dc_reviewed_by = request.user
                    doc.dc_reviewed_at = timezone.now()
                    doc.rejection_reason = None
                    doc.save(update_fields=['status', 'dc_reviewed_by', 'dc_reviewed_at', 'rejection_reason'])
                    _record_document_history(doc, request.user, from_status, doc.status, 'Document Controller Review', comments)
                    _sync_document_approval(
                        doc,
                        status='PENDING',
                        reviewed_by=request.user,
                        comments=comments or 'Document Controller reviewed. Waiting Consultant review.',
                    )
                    ok, msg = True, f'Document {doc.document_number} reviewed by Document Controller.'
            elif doc.status == 'DC_REVIEW':
                if role not in ['CONSULTANT', 'ADMIN_SYSTEM']:
                    ok, msg = False, 'Document must be reviewed by Consultant before final approval.'
                else:
                    from_status = doc.status
                    doc.status = 'CONSULTANT_REVIEW'
                    doc.consultant_reviewed_by = request.user
                    doc.consultant_reviewed_at = timezone.now()
                    doc.rejection_reason = None
                    doc.save(update_fields=['status', 'consultant_reviewed_by', 'consultant_reviewed_at', 'rejection_reason'])
                    _record_document_history(doc, request.user, from_status, doc.status, 'Consultant Review', comments)
                    _sync_document_approval(
                        doc,
                        status='REVIEWED',
                        reviewed_by=request.user,
                        comments=comments or 'Consultant reviewed. Waiting final approval.',
                    )
                    ok, msg = True, f'Document {doc.document_number} reviewed by Consultant.'
            elif doc.status == 'CONSULTANT_REVIEW':
                if role not in ['PROJECT_MANAGER', 'HQ_DIRECTOR', 'ADMIN_SYSTEM']:
                    ok, msg = False, 'Deit Project Manager or Director HQ can make final approval to document this.'
                else:
                    wf.propagate_document_approval(doc, request.user, approved=True, comments=comments)
                    ok, msg = True, f'Document {doc.document_number} approved.'
            else:
                ok, msg = False, 'Document is not in a processable review stage.'
    elif approval.module_type == 'invoice':
        try:
            invoice = Invoice.objects.get(id=approval.reference_id)
        except Invoice.DoesNotExist:
            ok, msg = False, 'Invoice not found.'
        else:
            if action == 'REJECTED':
                invoice.status = 'REJECTED'
                invoice.rejection_reason = comments or 'Rejected.'
                invoice.save(update_fields=['status', 'rejection_reason'])
                approval.status = 'REJECTED'
                approval.comments = invoice.rejection_reason
                approval.reviewed_by = request.user
                approval.save(update_fields=['status', 'comments', 'reviewed_by'])
                _notify_user(invoice.submitted_by, 'Invoice rejected', f"Invoice {invoice.invoice_number} rejected: {invoice.rejection_reason}", 'invoice', invoice.id, 'WARNING')
                ok, msg = True, f"Invoice {invoice.invoice_number} rejected."
            elif invoice.status == 'SUBMITTED':
                if role not in ['FINANCE_SITE', 'COST_ENGINEER', 'PROJECT_MANAGER', 'ADMIN_SYSTEM']:
                    ok, msg = False, 'Invoice must be verified by Finance Site / Cost Engineer first.'
                else:
                    wf.propagate_invoice_site_verifiedtion(invoice, request.user, comments)
                    _notify_roles(_hq_finance_roles(), 'Invoice waiting for Review Finance HQ', f"Invoice {invoice.invoice_number} verified  by Finance Site.", 'invoice', invoice.id, exclude_user=request.user)
                    ok, msg = True, f"Invoice {invoice.invoice_number} verified by Finance Site."
            elif invoice.status == 'SITE_VERIFIED':
                if role not in ['FINANCE_HQ', 'HQ_DIRECTOR', 'ADMIN_SYSTEM']:
                    ok, msg = False, 'Invoice must be reviewed by HQ Finance.'
                else:
                    wf.propagate_invoice_hq_review(invoice, request.user, comments)
                    _notify_roles(['HQ_DIRECTOR'], 'Invoice waiting for final approval', f"Invoice {invoice.invoice_number} reviewed by HQ Finance.", 'invoice', invoice.id, exclude_user=request.user)
                    ok, msg = True, f"Invoice {invoice.invoice_number} reviewed by HQ Finance."
            elif invoice.status in ['HQ_REVIEWED', 'VERIFIED']:
                if role not in ['HQ_DIRECTOR', 'ADMIN_SYSTEM']:
                    ok, msg = False, 'Only HQ Director can final approve invoice.'
                else:
                    deduction = float(request.POST.get('deduction') or 0)
                    wf.propagate_invoice_certification(invoice, request.user, deduction=deduction)
                    _notify_user(invoice.submitted_by, 'Invoice approved', f"Invoice {invoice.invoice_number} approved and IPC kria .", 'invoice', invoice.id, 'SUCCESS')
                    ok, msg = True, f"Invoice {invoice.invoice_number} approved and IPC generated."
            else:
                ok, msg = False, 'Invoice is not in a processable financial stage.'
    elif approval.module_type == 'financial_record':
        try:
            record = FinancialRecord.objects.get(id=approval.reference_id)
        except FinancialRecord.DoesNotExist:
            ok, msg = False, 'Financial record not found.'
        else:
            if action == 'REJECTED':
                wf.reject_financial_record(record, request.user, comments)
                _notify_user(record.submitted_by, 'Financial record rejected', f"{record.get_record_type_display()} {record.reference_number or record.id} rejected: {record.rejection_reason}", 'financial_record', record.id, 'WARNING')
                ok, msg = True, f"{record.get_record_type_display()} rejected."
            elif record.status == 'SUBMITTED':
                if role not in ['FINANCE_SITE', 'COST_ENGINEER', 'PROJECT_MANAGER', 'ADMIN_SYSTEM']:
                    ok, msg = False, 'Financial record must be verified by Finance Site / Cost Engineer first.'
                else:
                    wf.propagate_financial_record_site_verifiedtion(record, request.user, comments)
                    _notify_roles(_hq_finance_roles(), 'Financial record waiting for Review Finance HQ', f"{record.get_record_type_display()} {record.reference_number or record.id} verified  by Finance Site.", 'financial_record', record.id, exclude_user=request.user)
                    ok, msg = True, f"{record.get_record_type_display()} verified by Finance Site."
            elif record.status == 'SITE_VERIFIED':
                if role not in ['FINANCE_HQ', 'HQ_DIRECTOR', 'ADMIN_SYSTEM']:
                    ok, msg = False, 'Financial record must be reviewed by HQ Finance.'
                else:
                    wf.propagate_financial_record_hq_review(record, request.user, comments)
                    _notify_roles(['HQ_DIRECTOR'], 'Financial record waiting for final approval', f"{record.get_record_type_display()} {record.reference_number or record.id} reviewed by HQ Finance.", 'financial_record', record.id, exclude_user=request.user)
                    ok, msg = True, f"{record.get_record_type_display()} reviewed by HQ Finance."
            elif record.status == 'HQ_REVIEWED':
                if role not in ['HQ_DIRECTOR', 'ADMIN_SYSTEM']:
                    ok, msg = False, 'Only HQ Director can final approve financial record.'
                else:
                    wf.propagate_financial_record_approval(record, request.user, comments)
                    _notify_user(record.submitted_by, 'Financial record approved', f"{record.get_record_type_display()} {record.reference_number or record.id} approved and cashflow updated.", 'financial_record', record.id, 'SUCCESS')
                    ok, msg = True, f"{record.get_record_type_display()} approved and synced to cashflow."
            else:
                ok, msg = False, 'Financial record is not in a processable stage.'
    elif approval.module_type in ['material', 'purchase', 'progress']:
        metadata = {
            'approved_quantity': request.POST.get('approved_quantity') or '',
        }
        ok, msg = wf.process_phase_g_approval(approval, action, request.user, role, comments, metadata)
        if ok and approval.module_type == 'material' and approval.status == 'APPROVED':
            _notify_roles(
                ['STOREKEEPER', 'PROJECT_MANAGER'],
                'Material request approved',
                f"{approval.document_title or 'Material request'} approved and ready for delivery.",
                'material_request',
                approval.reference_id,
                exclude_user=request.user,
            )
    elif action == 'REJECTED':
        ok, msg = wf.process_central_approval(approval, 'REJECTED', request.user, comments)
    elif role in ['PROJECT_MANAGER', 'HQ_DIRECTOR', 'FINANCE_HQ', 'CONSULTANT']:
        ok, msg = wf.process_central_approval(approval, 'APPROVED', request.user, comments)
    else:
        ok, msg = False, 'This role is not authorized to approve this item.'

    if ok:
        messages.success(request, msg)
    else:
        messages.error(request, msg)
    return redirect('dashboard')


def submit_invoice(request):
    if request.method != 'POST':
        return redirect('dashboard')
    if not ensure_user_authenticated(request):
        messages.error(request, "Please login first.")
        return redirect('dashboard')
    role = _user_role(request)
    if role not in ['SITE_ENGINEER', 'PROJECT_MANAGER', 'FINANCE_SITE', 'COST_ENGINEER', 'ADMIN_SITE', 'ADMIN_SYSTEM']:
        messages.error(request, "Access limited to submit invoice.")
        return redirect('dashboard')

    project_id = request.POST.get('project_id')
    try:
        project = Project.objects.get(id=project_id)
    except (Project.DoesNotExist, ValueError):
        messages.error(request, "Project was not identified.")
        return redirect('dashboard')

    try:
        amount = float(request.POST.get('amount') or 0)
        retention = float(request.POST.get('retention') or 0)
    except ValueError:
        amount = retention = 0.0

    inv_type = request.POST.get('invoice_type', 'PROGRESS')
    claim_period = request.POST.get('claim_period') or ''
    inv_number = request.POST.get('invoice_number') or f"INV-{project.project_code or project.id}-{datetime.datetime.now().strftime('%Y%m%d%H%M')}"
    net_amount = amount - retention

    invoice = Invoice.objects.create(
        project=project,
        invoice_number=inv_number,
        invoice_type=inv_type,
        claim_period=claim_period,
        amount=amount,
        retention=retention,
        net_amount=net_amount,
        status='SUBMITTED',
        due_date=request.POST.get('due_date') or None,
        submitted_by=request.user,
        attachment=request.FILES.get('attachment') or None,
    )
    wf.register_invoice_submission(invoice)
    _notify_roles(_finance_site_roles(), 'Invoice waiting for Verifiorsaun Finance Site', f"Invoice {invoice.invoice_number} waiting for Verifiorsaun Finance Site.", 'invoice', invoice.id, exclude_user=request.user)
    messages.success(request, f"Invoice {inv_number} submit — waiting for verifiedtion & sertifiorsaun.")
    return redirect('dashboard')


def review_invoice(request, invoice_id):
    if request.method != 'POST':
        return redirect('dashboard')
    if not ensure_user_authenticated(request):
        messages.error(request, "Please login first.")
        return redirect('dashboard')
    role = _user_role(request)
    try:
        invoice = Invoice.objects.get(id=invoice_id)
    except Invoice.DoesNotExist:
        messages.error(request, "Invoice not found.")
        return redirect('dashboard')

    action = request.POST.get('status', 'APPROVED')
    comments = request.POST.get('comments') or ''
    if action == 'REJECTED':
        allowed_reject = {
            'SUBMITTED': ['FINANCE_SITE', 'COST_ENGINEER', 'PROJECT_MANAGER', 'ADMIN_SYSTEM'],
            'SITE_VERIFIED': ['FINANCE_HQ', 'HQ_DIRECTOR', 'ADMIN_SYSTEM'],
            'HQ_REVIEWED': ['HQ_DIRECTOR', 'ADMIN_SYSTEM'],
        }
        if role not in allowed_reject.get(invoice.status, []):
            messages.error(request, "This role is not authorized to reject the invoice at this step.")
            return redirect('dashboard')
        invoice.status = 'REJECTED'
        invoice.rejection_reason = comments or 'Rejected.'
        invoice.save(update_fields=['status', 'rejection_reason'])
        approval = Approval.objects.filter(module_type='invoice', reference_id=invoice.id).first()
        if approval:
            approval.status = 'REJECTED'
            approval.comments = invoice.rejection_reason
            approval.reviewed_by = request.user
            approval.save(update_fields=['status', 'comments', 'reviewed_by'])
        _notify_user(invoice.submitted_by, 'Invoice rejected', f"Invoice {invoice.invoice_number} rejected: {invoice.rejection_reason}", 'invoice', invoice.id, 'WARNING')
        messages.warning(request, f"Invoice {invoice.invoice_number} rejected.")
    elif invoice.status == 'SUBMITTED':
        if role not in ['FINANCE_SITE', 'COST_ENGINEER', 'PROJECT_MANAGER', 'ADMIN_SYSTEM']:
            messages.error(request, "Invoice must Finance Site / Cost Engineer verify first.")
            return redirect('dashboard')
        wf.propagate_invoice_site_verifiedtion(invoice, request.user, comments)
        _notify_roles(_hq_finance_roles(), 'Invoice waiting for Review Finance HQ', f"Invoice {invoice.invoice_number} verified  by Finance Site.", 'invoice', invoice.id, exclude_user=request.user)
        messages.success(request, f"Invoice {invoice.invoice_number} verified by Finance Site.")
    elif invoice.status == 'SITE_VERIFIED':
        if role not in ['FINANCE_HQ', 'HQ_DIRECTOR', 'ADMIN_SYSTEM']:
            messages.error(request, "Invoice must HQ Finance review first.")
            return redirect('dashboard')
        wf.propagate_invoice_hq_review(invoice, request.user, comments)
        _notify_roles(['HQ_DIRECTOR'], 'Invoice waiting for final approval', f"Invoice {invoice.invoice_number} reviewed by HQ Finance.", 'invoice', invoice.id, exclude_user=request.user)
        messages.success(request, f"Invoice {invoice.invoice_number} reviewed by HQ Finance.")
    elif invoice.status in ['HQ_REVIEWED', 'VERIFIED']:
        if role not in ['HQ_DIRECTOR', 'ADMIN_SYSTEM']:
            messages.error(request, "Final approval invoice only to HQ Director.")
            return redirect('dashboard')
        try:
            deduction = Decimal(str(request.POST.get('deduction') or '0'))
        except (InvalidOperation, ValueError):
            deduction = Decimal('0')
        wf.propagate_invoice_certification(invoice, request.user, deduction=deduction)
        _notify_user(invoice.submitted_by, 'Invoice approved', f"Invoice {invoice.invoice_number} approved and IPC kria .", 'invoice', invoice.id, 'SUCCESS')
        messages.success(request, f"Invoice {invoice.invoice_number} approved and IPC generated.")
    else:
        messages.error(request, "Invoice cannot be processed in step this.")
    return redirect('dashboard')


def submit_financial_record(request):
    if request.method != 'POST':
        return redirect('dashboard')
    if not ensure_user_authenticated(request):
        messages.error(request, "Please login first.")
        return redirect('dashboard')
    role = _user_role(request)
    if role not in ['SITE_ENGINEER', 'PROJECT_MANAGER', 'FINANCE_SITE', 'COST_ENGINEER', 'ADMIN_SITE', 'ADMIN_SYSTEM']:
        messages.error(request, "Access limited to input financial record.")
        return redirect('dashboard')

    try:
        project = Project.objects.get(id=request.POST.get('project_id'))
    except (Project.DoesNotExist, ValueError):
        messages.error(request, "Project was not identified.")
        return redirect('dashboard')

    try:
        amount = Decimal(str(request.POST.get('amount') or '0'))
    except (InvalidOperation, ValueError):
        amount = Decimal('0')
    if amount <= 0:
        messages.error(request, "Amount must greater than 0.")
        return redirect('dashboard')

    record = FinancialRecord.objects.create(
        project=project,
        record_type=request.POST.get('record_type') or 'EXPENSE',
        reference_number=request.POST.get('reference_number') or f"FIN-{project.project_code or project.id}-{datetime.datetime.now().strftime('%Y%m%d%H%M')}",
        category=request.POST.get('category') or 'General',
        description=request.POST.get('description') or '',
        amount=amount,
        transaction_date=request.POST.get('transaction_date') or datetime.date.today(),
        due_date=request.POST.get('due_date') or None,
        payment_method=request.POST.get('payment_method') or '',
        attachment=request.FILES.get('attachment') or None,
        status='SUBMITTED',
        submitted_by=request.user,
    )
    wf.register_financial_record_submission(record)
    _notify_roles(_finance_site_roles(), 'Financial record waiting Finance Site Verify', f"{record.get_record_type_display()} {record.reference_number or record.id} waiting for Verifiorsaun Finance Site.", 'financial_record', record.id, exclude_user=request.user)
    messages.success(request, f"{record.get_record_type_display()} {record.reference_number} submit - waiting for Finance Site verify.")
    return redirect('dashboard')


def review_financial_record(request, record_id):
    if request.method != 'POST':
        return redirect('dashboard')
    if not ensure_user_authenticated(request):
        messages.error(request, "Please login first.")
        return redirect('dashboard')
    role = _user_role(request)
    try:
        record = FinancialRecord.objects.get(id=record_id)
    except FinancialRecord.DoesNotExist:
        messages.error(request, "Financial record not found.")
        return redirect('dashboard')

    action = request.POST.get('status', 'APPROVED')
    comments = request.POST.get('comments') or ''
    if action == 'REJECTED':
        allowed_reject = {
            'SUBMITTED': ['FINANCE_SITE', 'COST_ENGINEER', 'PROJECT_MANAGER', 'ADMIN_SYSTEM'],
            'SITE_VERIFIED': ['FINANCE_HQ', 'HQ_DIRECTOR', 'ADMIN_SYSTEM'],
            'HQ_REVIEWED': ['HQ_DIRECTOR', 'ADMIN_SYSTEM'],
        }
        if role not in allowed_reject.get(record.status, []):
            messages.error(request, "This role is not authorized to reject the financial record at this step.")
            return redirect('dashboard')
        wf.reject_financial_record(record, request.user, comments)
        _notify_user(record.submitted_by, 'Financial record rejected', f"{record.get_record_type_display()} {record.reference_number or record.id} rejected: {record.rejection_reason}", 'financial_record', record.id, 'WARNING')
        messages.warning(request, f"{record.get_record_type_display()} rejected.")
    elif record.status == 'SUBMITTED':
        if role not in ['FINANCE_SITE', 'COST_ENGINEER', 'PROJECT_MANAGER', 'ADMIN_SYSTEM']:
            messages.error(request, "Financial record must Finance Site / Cost Engineer verify first.")
            return redirect('dashboard')
        wf.propagate_financial_record_site_verifiedtion(record, request.user, comments)
        _notify_roles(_hq_finance_roles(), 'Financial record waiting for Review Finance HQ', f"{record.get_record_type_display()} {record.reference_number or record.id} verified  by Finance Site.", 'financial_record', record.id, exclude_user=request.user)
        messages.success(request, f"{record.get_record_type_display()} verified by Finance Site.")
    elif record.status == 'SITE_VERIFIED':
        if role not in ['FINANCE_HQ', 'HQ_DIRECTOR', 'ADMIN_SYSTEM']:
            messages.error(request, "Financial record must HQ Finance review first.")
            return redirect('dashboard')
        wf.propagate_financial_record_hq_review(record, request.user, comments)
        _notify_roles(['HQ_DIRECTOR'], 'Financial record waiting for final approval', f"{record.get_record_type_display()} {record.reference_number or record.id} reviewed by HQ Finance.", 'financial_record', record.id, exclude_user=request.user)
        messages.success(request, f"{record.get_record_type_display()} reviewed by HQ Finance.")
    elif record.status == 'HQ_REVIEWED':
        if role not in ['HQ_DIRECTOR', 'ADMIN_SYSTEM']:
            messages.error(request, "Final approval financial only to HQ Director.")
            return redirect('dashboard')
        wf.propagate_financial_record_approval(record, request.user, comments)
        _notify_user(record.submitted_by, 'Financial record approved', f"{record.get_record_type_display()} {record.reference_number or record.id} approved and cashflow updated.", 'financial_record', record.id, 'SUCCESS')
        messages.success(request, f"{record.get_record_type_display()} approved and cashflow updated.")
    else:
        messages.error(request, "Financial record cannot be processed in step this.")
    return redirect('dashboard')


def mark_invoice_paid(request, invoice_id):
    if request.method != 'POST':
        return redirect('dashboard')
    if not ensure_user_authenticated(request):
        messages.error(request, "Please login first.")
        return redirect('dashboard')
    role = _user_role(request)
    if role not in ['FINANCE_HQ', 'HQ_DIRECTOR', 'ADMIN_SYSTEM']:
        messages.error(request, "Only Finance HQ / HQ Director can mark invoice paid.")
        return redirect('dashboard')
    try:
        invoice = Invoice.objects.get(id=invoice_id)
    except Invoice.DoesNotExist:
        messages.error(request, "Invoice not found.")
        return redirect('dashboard')
    if invoice.status != 'APPROVED':
        messages.error(request, "Invoice must be approved before marking it paid.")
        return redirect('dashboard')
    paid_date = request.POST.get('paid_date') or datetime.date.today()
    invoice.status = 'PAID'
    invoice.paid_date = paid_date
    invoice.save(update_fields=['status', 'paid_date'])
    _notify_user(invoice.submitted_by, 'Invoice paid', f"Invoice {invoice.invoice_number} marked as paid.", 'invoice', invoice.id, 'SUCCESS')
    messages.success(request, f"Invoice {invoice.invoice_number} marked as paid.")
    return redirect('dashboard')


def mark_financial_record_paid(request, record_id):
    if request.method != 'POST':
        return redirect('dashboard')
    if not ensure_user_authenticated(request):
        messages.error(request, "Please login first.")
        return redirect('dashboard')
    role = _user_role(request)
    if role not in ['FINANCE_HQ', 'HQ_DIRECTOR', 'ADMIN_SYSTEM']:
        messages.error(request, "Only Finance HQ / HQ Director can mark payment paid.")
        return redirect('dashboard')
    try:
        record = FinancialRecord.objects.get(id=record_id)
    except FinancialRecord.DoesNotExist:
        messages.error(request, "Financial record not found.")
        return redirect('dashboard')
    if record.status != 'APPROVED':
        messages.error(request, "Financial record must be approved before marking it paid.")
        return redirect('dashboard')
    from_status = record.status
    record.status = 'PAID'
    record.save(update_fields=['status', 'updated_at'])
    FinancialRecordHistory.objects.create(
        financial_record=record,
        action='Paid',
        from_status=from_status,
        to_status=record.status,
        comments='Marked as paid.',
        action_by=request.user,
    )
    _notify_user(record.submitted_by, 'Financial record paid', f"{record.get_record_type_display()} {record.reference_number or record.id} marked as paid.", 'financial_record', record.id, 'SUCCESS')
    messages.success(request, f"{record.get_record_type_display()} marked as paid.")
    return redirect('dashboard')


def _document_display_title(document):
    number = document.document_number or f"DOC-{document.id}"
    title = document.document_title or 'Untitled Document'
    return f"{number} - {title}"


def _record_document_history(document, action_by, from_status, to_status, action, comments=''):
    DocumentRevisionHistory.objects.create(
        document=document,
        action=action,
        from_status=from_status,
        to_status=to_status,
        revision=document.revision,
        comments=comments,
        action_by=action_by,
    )


def _sync_document_approval(document, *, status='PENDING', reviewed_by=None, approved_by=None, comments='', current_step=None):
    if current_step is None:
        current_step = {
            'SUBMITTED': 'REVIEWER',
            'DC_REVIEW': 'CONSULTANT',
            'CONSULTANT_REVIEW': 'HQ_APPROVAL',
            'APPROVED': 'COMPLETED',
            'REVISION_REQUIRED': 'REVIEWER',
            'REJECTED': 'REVIEWER',
        }.get(document.status, 'REVIEWER')
    return wf.create_or_update_approval(
        document.project,
        'document',
        document.id,
        document_title=_document_display_title(document),
        submitted_by=document.submitted_by,
        reviewed_by=reviewed_by,
        approved_by=approved_by,
        reviewer_by=document.dc_reviewed_by,
        consultant_by=document.consultant_reviewed_by,
        hq_approved_by=document.approved_by if status == 'APPROVED' else None,
        current_step=current_step,
        status=status,
        comments=comments,
    )


def _reject_document_for_revision(document, user, comments):
    from_status = document.status
    document.status = 'REVISION_REQUIRED'
    document.rejection_reason = comments or 'Document rejected. Revision required.'
    document.save(update_fields=['status', 'rejection_reason'])
    _record_document_history(
        document,
        user,
        from_status,
        document.status,
        'Revision Required',
        document.rejection_reason,
    )
    _sync_document_approval(
        document,
        status='REJECTED',
        reviewed_by=user,
        comments=document.rejection_reason,
    )


def submit_document(request):
    if request.method != 'POST':
        return redirect('dashboard')
    if not ensure_user_authenticated(request):
        messages.error(request, "Please login first.")
        return redirect('dashboard')
    role = _user_role(request)
    if role not in ['SITE_ENGINEER', 'PROJECT_MANAGER', 'DOC_CONTROLLER', 'ADMIN_SYSTEM']:
        messages.error(request, "Access limited to submit document.")
        return redirect('dashboard')

    document_file = request.FILES.get('document_file') or request.FILES.get('file')
    if not document_file:
        messages.error(request, "File document required upload to Jestaun Document.")
        return redirect('dashboard')

    parent_doc = None
    parent_doc_id = request.POST.get('parent_document_id')
    if parent_doc_id:
        try:
            parent_doc = Document.objects.get(id=parent_doc_id)
        except (Document.DoesNotExist, ValueError):
            messages.error(request, "Original revision document not found.")
            return redirect('dashboard')

    if parent_doc:
        project = parent_doc.project
    else:
        project_id = request.POST.get('project_id')
        try:
            project = Project.objects.get(id=project_id)
        except (Project.DoesNotExist, ValueError):
            messages.error(request, "Project was not identified.")
            return redirect('dashboard')
    if _reject_project_access(request, project):
        return redirect('dashboard')

    doc = Document.objects.create(
        project=project,
        document_type=request.POST.get('document_type') or (parent_doc.document_type if parent_doc else 'SHOP_DRAWING'),
        document_number=request.POST.get('document_number') or (parent_doc.document_number if parent_doc else f"DOC-{datetime.datetime.now().strftime('%M%S')}"),
        document_title=request.POST.get('document_title') or (parent_doc.document_title if parent_doc else ''),
        revision=request.POST.get('revision') or (parent_doc.revision if parent_doc else 'A'),
        category=request.POST.get('category') or (parent_doc.category if parent_doc else 'General'),
        description=request.POST.get('description') or '',
        file=document_file,
        status='SUBMITTED',
        submitted_by=request.user,
        parent_document=parent_doc,
    )

    if parent_doc:
        parent_from_status = parent_doc.status
        parent_doc.status = 'SUPERSEDED'
        parent_doc.save(update_fields=['status'])
        _record_document_history(
            parent_doc,
            request.user,
            parent_from_status,
            parent_doc.status,
            'Resubmitted as New Revision',
            f"Replaced by revision {doc.revision or '-'} ({doc.document_number}).",
        )

    wf.register_document_submission(doc)
    messages.success(request, f"Document {doc.document_number} submit to Document Controller Review.")
    return redirect('dashboard')


def review_document(request, doc_id):
    if request.method != 'POST':
        return redirect('dashboard')
    if not ensure_user_authenticated(request):
        messages.error(request, "Please login first.")
        return redirect('dashboard')
    role = _user_role(request)

    try:
        doc = Document.objects.get(id=doc_id)
    except Document.DoesNotExist:
        messages.error(request, "Document not found.")
        return redirect('dashboard')

    status = request.POST.get('status')
    comments = request.POST.get('comments') or request.POST.get('rejection_reason') or ''

    reject_roles_by_stage = {
        'SUBMITTED': ['DOC_CONTROLLER', 'ADMIN_SYSTEM'],
        'DC_REVIEW': ['CONSULTANT', 'ADMIN_SYSTEM'],
        'CONSULTANT_REVIEW': ['PROJECT_MANAGER', 'HQ_DIRECTOR', 'ADMIN_SYSTEM'],
    }
    if status == 'REJECTED':
        if role not in reject_roles_by_stage.get(doc.status, []):
            messages.error(request, "This role is not authorized to reject the document at this step.")
            return redirect('dashboard')
        _reject_document_for_revision(doc, request.user, comments)
        messages.warning(request, f"Document {doc.document_number} precisa revisi.")
        return redirect('dashboard')

    if doc.status == 'SUBMITTED':
        if role not in ['DOC_CONTROLLER', 'ADMIN_SYSTEM']:
            messages.error(request, "Document must review first by Document Controller.")
            return redirect('dashboard')
        from_status = doc.status
        doc.status = 'DC_REVIEW'
        doc.dc_reviewed_by = request.user
        doc.dc_reviewed_at = timezone.now()
        doc.rejection_reason = None
        doc.save(update_fields=['status', 'dc_reviewed_by', 'dc_reviewed_at', 'rejection_reason'])
        _record_document_history(doc, request.user, from_status, doc.status, 'Document Controller Review', comments)
        _sync_document_approval(
            doc,
            status='PENDING',
            reviewed_by=request.user,
            comments=comments or 'Document Controller reviewed. Waiting Consultant review.',
        )
        messages.success(request, f"Document {doc.document_number} reviewed by Document Controller.")
    elif doc.status == 'DC_REVIEW':
        if role not in ['CONSULTANT', 'ADMIN_SYSTEM']:
            messages.error(request, "Document must be reviewed by Consultant before final approval.")
            return redirect('dashboard')
        from_status = doc.status
        doc.status = 'CONSULTANT_REVIEW'
        doc.consultant_reviewed_by = request.user
        doc.consultant_reviewed_at = timezone.now()
        doc.rejection_reason = None
        doc.save(update_fields=['status', 'consultant_reviewed_by', 'consultant_reviewed_at', 'rejection_reason'])
        _record_document_history(doc, request.user, from_status, doc.status, 'Consultant Review', comments)
        _sync_document_approval(
            doc,
            status='REVIEWED',
            reviewed_by=request.user,
            comments=comments or 'Consultant reviewed. Waiting final approval.',
        )
        messages.success(request, f"Document {doc.document_number} reviewed by Consultant.")
    elif doc.status == 'CONSULTANT_REVIEW':
        if role not in ['PROJECT_MANAGER', 'HQ_DIRECTOR', 'ADMIN_SYSTEM']:
            messages.error(request, "Final approval document only to Project Manager / HQ Director.")
            return redirect('dashboard')
        wf.propagate_document_approval(doc, request.user, approved=True, comments=comments)
        messages.success(request, f"Document {doc.document_number} APPROVED.")
    else:
        messages.error(request, "Document status cannot be processed at this step.")
    return redirect('dashboard')


def approve_document(request, doc_id):
    return review_document(request, doc_id)


def submit_meeting(request):
    if request.method != 'POST':
        return redirect('dashboard')
    if not ensure_user_authenticated(request):
        messages.error(request, "Please login first.")
        return redirect('dashboard')
    role = _user_role(request)
    if role not in ['PROJECT_MANAGER', 'SITE_ENGINEER', 'ADMIN_SYSTEM']:
        messages.error(request, "Access limited to rejistu meeting.")
        return redirect('dashboard')

    project_id = request.POST.get('project_id')
    try:
        project = Project.objects.get(id=project_id)
    except (Project.DoesNotExist, ValueError):
        messages.error(request, "Project was not identified.")
        return redirect('dashboard')

    meeting = Meeting.objects.create(
        project=project,
        meeting_type=request.POST.get('meeting_type', 'SITE'),
        meeting_title=request.POST.get('meeting_title') or 'Site Coordination Meeting',
        meeting_date=request.POST.get('meeting_date') or datetime.date.today(),
        location=request.POST.get('location') or '',
        chairperson=request.user,
        minutes=request.POST.get('minutes') or '',
    )

    action_text = request.POST.get('action_item', '').strip()
    if action_text:
        meeting_action = MeetingAction.objects.create(
            meeting=meeting,
            action_item=action_text,
            responsible_name=request.POST.get('responsible_name') or '',
            due_date=request.POST.get('action_due_date') or None,
            priority=request.POST.get('priority', 'MEDIUM'),
            status='OPEN',
        )
        _notify_roles(
            ['PROJECT_MANAGER', 'SITE_ENGINEER'],
            'Meeting action item created',
            f"{project.name} - action toru: {meeting_action.action_item[:90]}",
            'meeting_action',
            meeting_action.id,
            'ALERT',
            exclude_user=request.user,
        )

    wf.register_meeting_submission(meeting)
    _notify_roles(
        ['PROJECT_MANAGER', 'SITE_ENGINEER', 'HQ_DIRECTOR'],
        'Meeting submitted',
        f"{project.name} - meeting '{meeting.meeting_title}' masuk dari {request.user.username}.",
        'meeting',
        meeting.id,
        'INFO',
        exclude_user=request.user,
    )
    messages.success(request, f"Meeting '{meeting.meeting_title}' registered — waiting for acknowledgment.")
    return redirect('dashboard')


# ============================================================
# INVENTORY / STOCK MANAGEMENT VIEWS
# ============================================================

def add_material_item(request):
    """Add new material to the project inventory catalog."""
    if not ensure_user_authenticated(request):
        return redirect('login')
    role = _user_role(request)
    if role not in ['SITE_ENGINEER', 'PROJECT_MANAGER', 'STOREKEEPER', 'LOGISTICS', 'ADMIN_SYSTEM']:
        messages.error(request, "You do not have permission to add material.")
        return redirect('dashboard')

    if request.method == 'POST':
        project_id = request.POST.get('project_id')
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            messages.error(request, "Project not found.")
            return redirect('dashboard')

        item_code = request.POST.get('item_code', '').strip()
        name = request.POST.get('item_name', '').strip()
        unit = request.POST.get('unit', 'unit')
        category = request.POST.get('category', 'LAIN')
        minimum_stock = request.POST.get('minimum_stock', 0) or 0
        description = request.POST.get('description', '')

        if not item_code or not name:
            messages.error(request, "Code Item and Material Name required filled.")
            return redirect('dashboard')

        item, created = MaterialItem.objects.get_or_create(
            project=project,
            item_code=item_code,
            defaults={
                'name': name,
                'unit': unit,
                'category': category,
                'minimum_stock': minimum_stock,
                'description': description,
            }
        )
        if created:
            messages.success(request, f"Material '{name}' successfully added to inventory.")
        else:
            messages.warning(request, f"Code item '{item_code}' in  to project this.")

    return redirect('dashboard')


def record_stock_transaction(request):
    """Record incoming/outgoing material stock transactions."""
    if not ensure_user_authenticated(request):
        return redirect('login')
    role = _user_role(request)
    if role not in ['SITE_ENGINEER', 'PROJECT_MANAGER', 'ADMIN_SYSTEM', 'ADMIN_SYSTEM']:
        messages.error(request, "You do not have permission to record stock transactions.")
        return redirect('dashboard')

    if request.method == 'POST':
        material_item_id = request.POST.get('material_item_id')
        try:
            material_item = MaterialItem.objects.get(id=material_item_id)
        except MaterialItem.DoesNotExist:
            messages.error(request, "Material not found.")
            return redirect('dashboard')

        transaction_type = request.POST.get('transaction_type', 'IN')
        quantity_str = request.POST.get('quantity', '0')
        unit_price_str = request.POST.get('unit_price', '')
        transaction_date = request.POST.get('transaction_date') or datetime.date.today()

        try:
            quantity = float(quantity_str)
            if quantity <= 0:
                raise ValueError("Quantity must greater than 0.")
        except (ValueError, TypeError):
            messages.error(request, "Total (quantity) invalid.")
            return redirect('dashboard')

        unit_price = None
        if unit_price_str:
            try:
                unit_price = float(unit_price_str)
            except ValueError:
                pass

        stock_transaction = StockTransaction.objects.create(
            material_item=material_item,
            project=material_item.project,
            transaction_type=transaction_type,
            quantity=quantity,
            unit_price=unit_price,
            reference_number=request.POST.get('reference_number', ''),
            supplier_name=request.POST.get('supplier_name', ''),
            location=request.POST.get('location', ''),
            notes=request.POST.get('notes', ''),
            transaction_date=transaction_date,
            recorded_by=request.user,
        )
        logistics_type = {
            'IN': 'MATERIAL_RECEIVING',
            'OUT': 'STOCK_ISSUE',
            'RETURN': 'STOCK_RETURN',
            'ADJUST': 'STOCK_ISSUE',
        }.get(transaction_type, 'STOCK_ISSUE')
        LogisticsRecord.objects.create(
            project=material_item.project,
            material_item=material_item,
            stock_transaction=stock_transaction,
            record_type=logistics_type,
            status=_status_for_logistics_type(logistics_type),
            quantity=stock_transaction.quantity,
            unit=material_item.unit,
            reference_number=stock_transaction.reference_number,
            supplier_name=stock_transaction.supplier_name,
            from_location=stock_transaction.supplier_name or stock_transaction.location,
            to_location=stock_transaction.location,
            actual_date=stock_transaction.transaction_date,
            handled_by=request.user,
            remarks=stock_transaction.notes,
        )

        type_label = dict(StockTransaction.TRANSACTION_TYPE).get(transaction_type, transaction_type)
        messages.success(request, f"Transasaun '{type_label}' — {quantity} {material_item.unit} '{material_item.name}' successfully register.")

    return redirect('dashboard')


def record_material_waste(request):
    if request.method != 'POST':
        return redirect('dashboard')
    if not ensure_user_authenticated(request):
        return redirect('login')
    role = _user_role(request)
    if role not in ['SITE_ENGINEER', 'STOREKEEPER', 'LOGISTICS', 'PROJECT_MANAGER', 'ADMIN_SYSTEM']:
        messages.error(request, "You do not have permission to record material waste.")
        return redirect('dashboard')

    try:
        material_item = MaterialItem.objects.get(id=request.POST.get('material_item_id'))
    except (MaterialItem.DoesNotExist, ValueError):
        messages.error(request, "Material not found.")
        return redirect('dashboard')

    try:
        quantity = Decimal(str(request.POST.get('quantity') or '0'))
    except (InvalidOperation, ValueError):
        quantity = Decimal('0')
    if quantity <= 0:
        messages.error(request, "Quantity waste must greater than 0.")
        return redirect('dashboard')

    waste_date = request.POST.get('waste_date') or datetime.date.today()
    stock_transaction = StockTransaction.objects.create(
        material_item=material_item,
        project=material_item.project,
        transaction_type='OUT',
        quantity=quantity,
        reference_number=request.POST.get('reference_number') or f"WASTE-{datetime.datetime.now().strftime('%Y%m%d%H%M')}",
        location=request.POST.get('location') or material_item.project.location,
        notes=request.POST.get('notes') or 'Material waste analysis',
        transaction_date=waste_date,
        recorded_by=request.user,
    )
    waste = MaterialWaste.objects.create(
        project=material_item.project,
        material_item=material_item,
        quantity=quantity,
        reason=request.POST.get('reason') or 'OTHER',
        location=request.POST.get('location') or '',
        notes=request.POST.get('notes') or '',
        waste_date=waste_date,
        recorded_by=request.user,
        stock_transaction=stock_transaction,
    )
    LogisticsRecord.objects.create(
        project=material_item.project,
        material_item=material_item,
        stock_transaction=stock_transaction,
        record_type='STOCK_ISSUE',
        status='DAMAGED',
        quantity=quantity,
        unit=material_item.unit,
        reference_number=stock_transaction.reference_number,
        from_location=request.POST.get('location') or material_item.project.location,
        to_location='Waste / damaged material',
        condition='DAMAGED',
        actual_date=waste_date,
        handled_by=request.user,
        remarks=request.POST.get('notes') or 'Material waste analysis',
    )
    _notify_roles(
        ['PROJECT_MANAGER', 'STOREKEEPER', 'LOGISTICS'],
        'Material waste recorded',
        f"Waste {material_item.name}: {quantity} {material_item.unit} tercatat.",
        'material_waste',
        waste.id,
        exclude_user=request.user,
    )
    messages.success(request, f"Material waste {material_item.name} successfully register and stock updated.")
    return redirect('dashboard')


# ============================================================
# MANPOWER & ATTENDANCE VIEWS
# ============================================================
def manpower_view(request):
    if not ensure_user_authenticated(request):
        return redirect('login')
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    manpowers = Manpower.objects.select_related('project').all()
    projects = Project.objects.all()
    
    # Hitung statistik manpower
    total_staff = manpowers.count()
    active_staff = manpowers.filter(is_active=True).count()
    by_role = {}
    for role, _ in Manpower.ROLE_CHOICES:
        by_role[role] = manpowers.filter(role=role).count()
    
    context = {
        'user_profile': user_profile,
        'manpowers': manpowers,
        'projects': projects,
        'total_staff': total_staff,
        'active_staff': active_staff,
        'by_role': by_role,
        'unread_count': _get_unread_count(request.user),
    }
    return render(request, 'core/manpower.html', context)


def add_manpower(request):
    if request.method != 'POST':
        return redirect('manpower')
    next_url = request.POST.get('next') or reverse('manpower')
    if not next_url.startswith('/') or next_url.startswith('//'):
        next_url = reverse('manpower')
    if not ensure_user_authenticated(request):
        messages.error(request, "Please login first.")
        return redirect(next_url)
    
    project_id = request.POST.get('project_id')
    try:
        project = Project.objects.get(id=project_id)
    except (Project.DoesNotExist, ValueError):
        messages.error(request, "Project was not identified.")
        return redirect(next_url)
    
    nik = (request.POST.get('nik') or '').strip()
    name = (request.POST.get('name') or '').strip()
    if not nik or not name:
        messages.error(request, "NIK with name staff must complete.")
        return redirect(next_url)
    if Manpower.objects.filter(nik=nik).exists():
        messages.error(request, "NIK staff nee existe .")
        return redirect(next_url)

    Manpower.objects.create(
        project=project,
        nik=nik,
        name=name,
        role=request.POST.get('role', 'WORKER'),
        phone=request.POST.get('phone', ''),
    )
    messages.success(request, "Staff new successfully aumenta!")
    return redirect(next_url)


def attendance_view(request):
    if not ensure_user_authenticated(request):
        return redirect('login')
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    selected_date = request.GET.get('date') or datetime.date.today().isoformat()
    if isinstance(selected_date, str):
        selected_date = datetime.date.fromisoformat(selected_date)
    
    attendances = Attendance.objects.filter(date=selected_date).select_related('manpower', 'project')
    projects = Project.objects.all()
    manpowers = Manpower.objects.filter(is_active=True)
    
    # Hitung statistik kehadiran
    present = attendances.filter(status='PRESENT').count()
    absent = attendances.filter(status='ABSENT').count()
    sick = attendances.filter(status='SICK').count()
    leave = attendances.filter(status='LEAVE').count()
    late = attendances.filter(status='LATE').count()
    
    context = {
        'user_profile': user_profile,
        'attendances': attendances,
        'projects': projects,
        'manpowers': manpowers,
        'selected_date': selected_date,
        'present': present,
        'absent': absent,
        'sick': sick,
        'leave': leave,
        'late': late,
        'unread_count': _get_unread_count(request.user),
    }
    return render(request, 'core/attendance.html', context)


def record_attendance(request):
    if request.method != 'POST':
        return redirect('attendance')
    next_url = request.POST.get('next')
    if next_url and (not next_url.startswith('/') or next_url.startswith('//')):
        next_url = None
    if not ensure_user_authenticated(request):
        messages.error(request, "Please login first.")
        return redirect('attendance')
    
    manpower_id = request.POST.get('manpower_id')
    project_id = request.POST.get('project_id')
    date_str = request.POST.get('date')
    
    try:
        manpower = Manpower.objects.get(id=manpower_id, project_id=project_id)
        project = Project.objects.get(id=project_id)
        date = datetime.date.fromisoformat(date_str)
    except (Manpower.DoesNotExist, Project.DoesNotExist, ValueError):
        messages.error(request, "Date invalid.")
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
        return redirect('attendance')
    
    check_in = request.POST.get('check_in')
    check_out = request.POST.get('check_out')
    
    attendance, created = Attendance.objects.update_or_create(
        manpower=manpower,
        date=date,
        defaults={
            'project': project,
            'check_in': check_in or None,
            'check_out': check_out or None,
            'status': request.POST.get('status', 'PRESENT'),
            'notes': request.POST.get('notes', ''),
            'recorded_by': request.user,
        }
    )
    
    if created:
        messages.success(request, "Absensi dicatat!")
    else:
        messages.success(request, "Absensi dipertorui!")
    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    return redirect(f"{reverse('attendance')}?date={date_str}")


# ============================================================
# EQUIPMENT MANAGEMENT VIEWS
# ============================================================
def equipment_view(request):
    if not ensure_user_authenticated(request):
        return redirect('login')
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    equipments = Equipment.objects.select_related('project', 'operator').all()
    projects = Project.objects.all()
    manpowers = Manpower.objects.filter(is_active=True)
    
    # Hitung statistik equipment
    total_equipment = equipments.count()
    active_equipment = equipments.filter(status='ACTIVE').count()
    maintenance_equipment = equipments.filter(status='MAINTENANCE').count()
    
    context = {
        'user_profile': user_profile,
        'equipments': equipments,
        'projects': projects,
        'manpowers': manpowers,
        'total_equipment': total_equipment,
        'active_equipment': active_equipment,
        'maintenance_equipment': maintenance_equipment,
        'unread_count': _get_unread_count(request.user),
    }
    return render(request, 'core/equipment.html', context)


def add_equipment(request):
    if request.method != 'POST':
        return redirect('equipment')
    if not ensure_user_authenticated(request):
        messages.error(request, "Please login first.")
        return redirect('equipment')
    
    project_id = request.POST.get('project_id')
    try:
        project = Project.objects.get(id=project_id)
    except (Project.DoesNotExist, ValueError):
        messages.error(request, "Project was not identified.")
        return redirect('equipment')
    
    operator_id = request.POST.get('operator_id')
    operator = None
    if operator_id:
        try:
            operator = Manpower.objects.get(id=operator_id)
        except Manpower.DoesNotExist:
            pass
    
    Equipment.objects.create(
        project=project,
        equipment_code=request.POST.get('equipment_code'),
        name=request.POST.get('name'),
        category=request.POST.get('category', 'OTHER'),
        brand=request.POST.get('brand', ''),
        model=request.POST.get('model', ''),
        serial_number=request.POST.get('serial_number', ''),
        year=request.POST.get('year') or None,
        purchase_date=request.POST.get('purchase_date') or None,
        purchase_value=request.POST.get('purchase_value') or 0,
        status=request.POST.get('status', 'ACTIVE'),
        location=request.POST.get('location', ''),
        operator=operator,
    )
    messages.success(request, "Equipment new successfully aumenta!")
    return redirect('equipment')


def record_equipment_usage(request):
    if request.method != 'POST':
        return redirect('equipment')
    if not ensure_user_authenticated(request):
        messages.error(request, "Please login first.")
        return redirect('equipment')
    
    equipment_id = request.POST.get('equipment_id')
    project_id = request.POST.get('project_id')
    
    try:
        equipment = Equipment.objects.get(id=equipment_id)
        project = Project.objects.get(id=project_id)
    except (Equipment.DoesNotExist, Project.DoesNotExist, ValueError):
        messages.error(request, "Date invalid.")
        return redirect('equipment')
    
    operator_id = request.POST.get('operator_id')
    operator = None
    if operator_id:
        try:
            operator = Manpower.objects.get(id=operator_id)
        except Manpower.DoesNotExist:
            pass
    
    EquipmentUsage.objects.create(
        equipment=equipment,
        project=project,
        usage_date=request.POST.get('usage_date') or datetime.date.today(),
        start_time=request.POST.get('start_time') or None,
        end_time=request.POST.get('end_time') or None,
        hours_used=request.POST.get('hours_used') or 0,
        activity=request.POST.get('activity', ''),
        location=request.POST.get('location', ''),
        operator=operator,
        fuel_used=request.POST.get('fuel_used') or None,
        notes=request.POST.get('notes', ''),
        recorded_by=request.user,
    )
    messages.success(request, "Equipment usage recorded!")
    return redirect('equipment')


def record_equipment_maintenance(request):
    if request.method != 'POST':
        return redirect('equipment')
    if not ensure_user_authenticated(request):
        messages.error(request, "Please login first.")
        return redirect('equipment')
    
    equipment_id = request.POST.get('equipment_id')
    
    try:
        equipment = Equipment.objects.get(id=equipment_id)
    except (Equipment.DoesNotExist, ValueError):
        messages.error(request, "Equipment invalid.")
        return redirect('equipment')
    
    EquipmentMaintenance.objects.create(
        equipment=equipment,
        maintenance_type=request.POST.get('maintenance_type', 'SCHEDULED'),
        maintenance_date=request.POST.get('maintenance_date') or datetime.date.today(),
        description=request.POST.get('description', ''),
        cost=request.POST.get('cost') or 0,
        vendor=request.POST.get('vendor', ''),
        status=request.POST.get('status', 'PENDING'),
        next_maintenance_date=request.POST.get('next_maintenance_date') or None,
        notes=request.POST.get('notes', ''),
        recorded_by=request.user,
    )
    messages.success(request, "Maintenance equipment dicatat!")
    return redirect('equipment')


# ============================================================
# EXPORTING FUNCTIONALITY
# ============================================================
import csv
from django.http import HttpResponse


REPORT_TYPE_LABELS = {
    'daily': 'Daily Report',
    'weekly': 'Weekly Report',
    'monthly': 'Monthly Report',
    'progress': 'Progress Report',
    'financial': 'Financial Report',
}


def _parse_date_filter(value, falltock=None):
    if not value:
        return falltock
    try:
        return datetime.date.fromisoformat(value)
    except (TypeError, ValueError):
        return falltock


def _reporting_filters(request, report_type=None):
    today = datetime.date.today()
    selected_type = report_type or request.GET.get('report_type') or 'daily'
    if selected_type not in REPORT_TYPE_LABELS:
        selected_type = 'daily'

    if selected_type == 'weekly':
        default_start = today - datetime.timedelta(days=6)
        default_end = today
    elif selected_type == 'monthly':
        default_start = today.replace(day=1)
        default_end = today
    else:
        default_start = today - datetime.timedelta(days=30)
        default_end = today

    start_date = _parse_date_filter(request.GET.get('start_date'), default_start)
    end_date = _parse_date_filter(request.GET.get('end_date'), default_end)
    if start_date and end_date and start_date > end_date:
        start_date, end_date = end_date, start_date

    project_id = request.GET.get('project_id') or ''
    return selected_type, project_id, start_date, end_date


def _filter_project(qs, project_id):
    if project_id:
        return qs.filter(project_id=project_id)
    return qs


def _period_label(start_date, end_date):
    if start_date == end_date:
        return start_date.strftime('%Y-%m-%d')
    return f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"


def _build_reporting_dataset(report_type, project_id, start_date, end_date):
    title = REPORT_TYPE_LABELS.get(report_type, 'Report')
    project = None
    if project_id:
        project = Project.objects.filter(id=project_id).first()
    project_label = project.name if project else 'All Project'
    period = _period_label(start_date, end_date)

    dataset = {
        'report_type': report_type,
        'title': title,
        'project_label': project_label,
        'period': period,
        'headers': [],
        'rows': [],
        'summary': {},
    }

    if report_type in ['daily', 'weekly', 'monthly']:
        reports = DailyReport.objects.select_related('project', 'reporter').filter(
            date__gte=start_date,
            date__lte=end_date,
        ).order_by('date', 'project__name')
        reports = _filter_project(reports, project_id)
        dataset['headers'] = [
            'Date', 'Project', 'Reporter', 'Weather', 'Work Completed',
            'Progress %', 'Manpower', 'Material', 'Equipment', 'Status'
        ]
        for report in reports:
            dataset['rows'].append([
                report.date.strftime('%Y-%m-%d'),
                report.project.name,
                report.reporter.username if report.reporter else '',
                report.weather,
                report.work_done,
                f"{report.progress_percentage}%",
                report.manpower_count,
                report.materials_used or '',
                report.equipment_used or '',
                report.get_status_display(),
            ])
        dataset['summary'] = {
            'Total Reports': reports.count(),
            'Approved Reports': reports.filter(status='APPROVED').count(),
            'Pending Reports': reports.filter(status='PENDING').count(),
            'Average Progress': f"{(reports.aggregate(avg=Avg('progress_percentage'))['avg'] or 0):.2f}%",
            'Total Manpower': reports.aggregate(total=Sum('manpower_count'))['total'] or 0,
        }
        return dataset

    if report_type == 'progress':
        progress_reports = ProgressReport.objects.select_related('project', 'prepared_by').filter(
            report_date__gte=start_date,
            report_date__lte=end_date,
        ).order_by('report_date', 'project__name')
        progress_reports = _filter_project(progress_reports, project_id)
        work_items = WorkItem.objects.select_related('project').all()
        work_items = _filter_project(work_items, project_id)
        dataset['headers'] = [
            'Date Report', 'Project', 'Period', 'Total %',
            'Civil %', 'Architectural %', 'MEP %', 'Prepared By', 'Status', 'Notes'
        ]
        for progress in progress_reports:
            dataset['rows'].append([
                progress.report_date.strftime('%Y-%m-%d'),
                progress.project.name,
                progress.report_period or '',
                f"{progress.overall_progress}%",
                f"{progress.civil_progress}%",
                f"{progress.architectural_progress}%",
                f"{progress.mep_progress}%",
                progress.prepared_by.username if progress.prepared_by else '',
                progress.get_status_display(),
                progress.remarks or '',
            ])
        dataset['summary'] = {
            'Progress Records': progress_reports.count(),
            'Average Progress Total': f"{(progress_reports.aggregate(avg=Avg('overall_progress'))['avg'] or 0):.2f}%",
            'BOQ Work Items': work_items.count(),
            'Completed Items': work_items.filter(progress_percent__gte=100).count(),
            'Average BOQ Progress': f"{(work_items.aggregate(avg=Avg('progress_percent'))['avg'] or 0):.2f}%",
        }
        return dataset

    if report_type == 'financial':
        records = FinancialRecord.objects.select_related(
            'project', 'submitted_by', 'approved_by'
        ).filter(
            transaction_date__gte=start_date,
            transaction_date__lte=end_date,
        ).order_by('transaction_date', 'project__name')
        records = _filter_project(records, project_id)
        invoices = Invoice.objects.select_related('project', 'submitted_by', 'approved_by').filter(
            due_date__gte=start_date,
            due_date__lte=end_date,
        ).order_by('due_date', 'project__name')
        invoices = _filter_project(invoices, project_id)
        summaries = CostSummary.objects.select_related('project').all()
        summaries = _filter_project(summaries, project_id)

        dataset['headers'] = [
            'Source', 'Date', 'Project', 'Reference', 'Category/Type',
            'Description', 'Amount', 'Status', 'Submitted By', 'Approved By'
        ]
        for record in records:
            dataset['rows'].append([
                'Financial Record',
                record.transaction_date.strftime('%Y-%m-%d') if record.transaction_date else '',
                record.project.name,
                record.reference_number or '',
                record.get_record_type_display(),
                record.description or record.category or '',
                record.amount,
                record.get_status_display(),
                record.submitted_by.username if record.submitted_by else '',
                record.approved_by.username if record.approved_by else '',
            ])
        for invoice in invoices:
            dataset['rows'].append([
                'Invoice',
                invoice.due_date.strftime('%Y-%m-%d') if invoice.due_date else '',
                invoice.project.name,
                invoice.invoice_number,
                invoice.get_invoice_type_display(),
                invoice.claim_period or '',
                invoice.net_amount,
                invoice.get_status_display(),
                invoice.submitted_by.username if invoice.submitted_by else '',
                invoice.approved_by.username if invoice.approved_by else '',
            ])
        dataset['summary'] = {
            'Financial Records': records.count(),
            'Invoices': invoices.count(),
            'Total Record Amount': records.aggregate(total=Sum('amount'))['total'] or Decimal('0'),
            'Total Invoice Net': invoices.aggregate(total=Sum('net_amount'))['total'] or Decimal('0'),
            'Budget': summaries.aggregate(total=Sum('budget'))['total'] or Decimal('0'),
            'Actual Cost': summaries.aggregate(total=Sum('actual'))['total'] or Decimal('0'),
            'Committed Cost': summaries.aggregate(total=Sum('committed'))['total'] or Decimal('0'),
        }
        return dataset

    return dataset


def print_report(request):
    if not ensure_user_authenticated(request):
        return redirect('login')
    report_type, project_id, start_date, end_date = _reporting_filters(request)
    dataset = _build_reporting_dataset(report_type, project_id, start_date, end_date)
    context = {
        'dataset': dataset,
        'format': request.GET.get('format') or 'print',
        'auto_print': request.GET.get('format') in ['print', 'pdf'],
        'generated_at': timezone.now(),
    }
    return render(request, 'core/report_print.html', context)


def export_report_excel(request):
    if not ensure_user_authenticated(request):
        return redirect('login')
    report_type, project_id, start_date, end_date = _reporting_filters(request)
    dataset = _build_reporting_dataset(report_type, project_id, start_date, end_date)

    safe_project = (dataset['project_label'] or 'all_project').replace(' ', '_').lower()
    filename = f"{report_type}_report_{safe_project}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow([dataset['title']])
    writer.writerow(['Project', dataset['project_label']])
    writer.writerow(['Period', dataset['period']])
    writer.writerow([])
    writer.writerow(['Summary'])
    for key, value in dataset['summary'].items():
        writer.writerow([key, value])
    writer.writerow([])
    writer.writerow(dataset['headers'])
    for row in dataset['rows']:
        writer.writerow(row)
    return response


def export_manpower(request):
    if not ensure_user_authenticated(request):
        return redirect('login')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="manpower.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['NIK', 'Name', 'Role', 'Project', 'Phone Number', 'Active Status', 'Join Date'])
    
    manpowers = Manpower.objects.select_related('project').all()
    for m in manpowers:
        writer.writerow([
            m.nik,
            m.name,
            m.get_role_display(),
            m.project.name,
            m.phone or '',
            'Active' if m.is_active else 'Inactive',
            m.join_date.strftime('%Y-%m-%d')
        ])
    
    return response


def export_attendance(request):
    if not ensure_user_authenticated(request):
        return redirect('login')
    
    selected_date = request.GET.get('date') or datetime.date.today().isoformat()
    if isinstance(selected_date, str):
        try:
            selected_date = datetime.date.fromisoformat(selected_date)
        except ValueError:
            selected_date = datetime.date.today()
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="attendance_{selected_date.strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['NIK', 'Name', 'Project', 'Date', 'Check In', 'Check Out', 'Status', 'Notes'])
    
    attendances = Attendance.objects.filter(date=selected_date).select_related('manpower', 'project')
    for a in attendances:
        writer.writerow([
            a.manpower.nik,
            a.manpower.name,
            a.project.name,
            a.date.strftime('%Y-%m-%d'),
            a.check_in or '',
            a.check_out or '',
            a.get_status_display(),
            a.notes or ''
        ])
    
    return response


def export_equipment(request):
    if not ensure_user_authenticated(request):
        return redirect('login')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="equipment.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Code', 'Name', 'Category', 'Brand', 'Model', 'Serial Number', 'Year', 'Project', 'Status', 'Location', 'Operator', 'Purchase Date', 'Purchase Value'])
    
    equipments = Equipment.objects.select_related('project', 'operator').all()
    for e in equipments:
        writer.writerow([
            e.equipment_code,
            e.name,
            e.get_category_display(),
            e.brand or '',
            e.model or '',
            e.serial_number or '',
            e.year or '',
            e.project.name,
            e.get_status_display(),
            e.location or '',
            e.operator.name if e.operator else '',
            e.purchase_date.strftime('%Y-%m-%d') if e.purchase_date else '',
            e.purchase_value
        ])
    
    return response


def export_daily_reports(request):
    if not ensure_user_authenticated(request):
        return redirect('login')
    
    project_id = request.GET.get('project_id')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    response = HttpResponse(content_type='text/csv')
    filename = 'daily_reports.csv'
    if project_id:
        filename = f'daily_reports_project_{project_id}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Project', 'Date', 'Reporter', 'Weather', 'Work Completed',
        'Issues', 'Progress Percentage', 'Total Manpower', 'Status'
    ])
    
    reports = DailyReport.objects.select_related('project', 'reporter').all()
    if project_id:
        reports = reports.filter(project_id=project_id)
    if start_date:
        try:
            start = datetime.date.fromisoformat(start_date)
            reports = reports.filter(date__gte=start)
        except ValueError:
            pass
    if end_date:
        try:
            end = datetime.date.fromisoformat(end_date)
            reports = reports.filter(date__lte=end)
        except ValueError:
            pass
    
    for r in reports:
        writer.writerow([
            r.project.name,
            r.date.strftime('%Y-%m-%d'),
            r.reporter.username,
            r.weather,
            r.work_done,
            r.issues or '',
            r.progress_percentage,
            r.manpower_count,
            r.get_status_display()
        ])
    
    return response


def export_cost_summaries(request):
    if not ensure_user_authenticated(request):
        return redirect('login')
    
    project_id = request.GET.get('project_id')
    
    response = HttpResponse(content_type='text/csv')
    filename = 'cost_summaries.csv'
    if project_id:
        filename = f'cost_summaries_project_{project_id}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Project', 'Category', 'Sub Category', 'Budget', 'Actual',
        'Committed', 'Forecast', 'Variance', 'Date Report'
    ])
    
    summaries = CostSummary.objects.select_related('project').all()
    if project_id:
        summaries = summaries.filter(project_id=project_id)
    
    for s in summaries:
        writer.writerow([
            s.project.name,
            s.category,
            s.sub_category or '',
            s.budget,
            s.actual,
            s.committed,
            s.forecast,
            s.variance(),
            s.report_date.strftime('%Y-%m-%d') if s.report_date else ''
        ])
    
    return response


def export_financial_records(request):
    if not ensure_user_authenticated(request):
        return redirect('login')

    project_id = request.GET.get('project_id')

    response = HttpResponse(content_type='text/csv')
    filename = 'financial_records.csv'
    if project_id:
        filename = f'financial_records_project_{project_id}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        'Project', 'Type', 'Numeru Reference', 'Category', 'Description',
        'Amount', 'Transaction Date', 'Due Date', 'Payment Method', 'Status',
        'Submitted By', 'Finance Site Verified By', 'HQ Finance Reviewed By', 'Approved By'
    ])

    records = FinancialRecord.objects.select_related(
        'project', 'submitted_by', 'site_verified_by', 'hq_reviewed_by', 'approved_by'
    ).all()
    if project_id:
        records = records.filter(project_id=project_id)

    for record in records:
        writer.writerow([
            record.project.name,
            record.get_record_type_display(),
            record.reference_number or '',
            record.category or '',
            record.description or '',
            record.amount,
            record.transaction_date.strftime('%Y-%m-%d') if record.transaction_date else '',
            record.due_date.strftime('%Y-%m-%d') if record.due_date else '',
            record.payment_method or '',
            record.get_status_display(),
            record.submitted_by.username if record.submitted_by else '',
            record.site_verified_by.username if record.site_verified_by else '',
            record.hq_reviewed_by.username if record.hq_reviewed_by else '',
            record.approved_by.username if record.approved_by else '',
        ])

    return response


def export_material_items(request):
    if not ensure_user_authenticated(request):
        return redirect('login')
    
    project_id = request.GET.get('project_id')
    
    response = HttpResponse(content_type='text/csv')
    filename = 'material_items.csv'
    if project_id:
        filename = f'material_items_project_{project_id}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Code Item', 'Material Name', 'Category', 'Unit', 'Minimum Stock',
        'Current Stock', 'Project', 'Description'
    ])
    
    items = MaterialItem.objects.select_related('project').all()
    if project_id:
        items = items.filter(project_id=project_id)
    
    for i in items:
        writer.writerow([
            i.item_code,
            i.name,
            i.get_category_display(),
            i.unit,
            i.minimum_stock,
            i.current_stock,
            i.project.name,
            i.description or ''
        ])
    
    return response


def export_material_control(request):
    if not ensure_user_authenticated(request):
        return redirect('login')

    project_id = request.GET.get('project_id')
    response = HttpResponse(content_type='text/csv')
    filename = 'material_control.csv'
    if project_id:
        filename = f'material_control_project_{project_id}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(['SECTION', 'Project', 'Reference', 'Material', 'Quantity', 'Unit', 'Status/Type', 'Date', 'User', 'Notes'])

    requests = MaterialRequest.objects.select_related('project', 'requested_by').all()
    transactions = StockTransaction.objects.select_related('project', 'material_item', 'recorded_by').all()
    wastes = MaterialWaste.objects.select_related('project', 'material_item', 'recorded_by').all()
    if project_id:
        requests = requests.filter(project_id=project_id)
        transactions = transactions.filter(project_id=project_id)
        wastes = wastes.filter(project_id=project_id)

    for mr in requests:
        writer.writerow([
            'MATERIAL REQUEST',
            mr.project.name,
            mr.request_number or mr.id,
            mr.material_name,
            mr.quantity,
            mr.unit,
            mr.get_status_display(),
            mr.requested_date.strftime('%Y-%m-%d') if mr.requested_date else '',
            mr.requested_by.username if mr.requested_by else '',
            mr.remarks or mr.rejection_reason or '',
        ])

    for tx in transactions:
        writer.writerow([
            'STOCK TRANSACTION',
            tx.project.name,
            tx.reference_number or '',
            tx.material_item.name,
            tx.quantity,
            tx.material_item.unit,
            tx.get_transaction_type_display(),
            tx.transaction_date.strftime('%Y-%m-%d') if tx.transaction_date else '',
            tx.recorded_by.username if tx.recorded_by else '',
            tx.notes or '',
        ])

    for waste in wastes:
        writer.writerow([
            'WASTE ANALYSIS',
            waste.project.name,
            waste.stock_transaction.reference_number if waste.stock_transaction else '',
            waste.material_item.name,
            waste.quantity,
            waste.material_item.unit,
            waste.get_reason_display(),
            waste.waste_date.strftime('%Y-%m-%d') if waste.waste_date else '',
            waste.recorded_by.username if waste.recorded_by else '',
            waste.notes or '',
        ])

    return response


def export_logistics_records(request):
    if not ensure_user_authenticated(request):
        return redirect('login')

    project_id = request.GET.get('project_id')
    response = HttpResponse(content_type='text/csv')
    filename = 'logistics_records.csv'
    if project_id:
        filename = f'logistics_records_project_{project_id}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        'Date', 'Project', 'Type', 'Status', 'Material', 'Quantity', 'Unit',
        'Reference', 'Supplier', 'From Location', 'To Location', 'Condition',
        'Handled By', 'Notes'
    ])

    records = LogisticsRecord.objects.select_related(
        'project', 'material_item', 'material_request', 'handled_by'
    ).all()
    if project_id:
        records = records.filter(project_id=project_id)

    for record in records:
        material_name = ''
        if record.material_item:
            material_name = record.material_item.name
        elif record.material_request:
            material_name = record.material_request.material_name
        writer.writerow([
            record.actual_date.strftime('%Y-%m-%d') if record.actual_date else '',
            record.project.name,
            record.get_record_type_display(),
            record.get_status_display(),
            material_name,
            record.quantity,
            record.unit or '',
            record.reference_number or '',
            record.supplier_name or '',
            record.from_location or '',
            record.to_location or '',
            record.get_condition_display(),
            record.handled_by.username if record.handled_by else '',
            record.remarks or '',
        ])

    return response


# ============================================================
# NOTIFICATIONS
# ============================================================
def notifications_view(request):
    if not ensure_user_authenticated(request):
        return redirect('login')
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    
    # Hitung jumlah notifications belum ditoca
    unread_count = notifications.filter(status='UNREAD').count()
    
    context = {
        'user_profile': user_profile,
        'notifications': notifications,
        'unread_count': unread_count,
    }
    return render(request, 'core/notifications.html', context)


def mark_notification_read(request, notification_id):
    if not ensure_user_authenticated(request):
        return redirect('login')
    try:
        notification = Notification.objects.get(id=notification_id, recipient=request.user)
        notification.status = 'READ'
        notification.save()
        messages.success(request, "Notification marked as read!")
    except Notification.DoesNotExist:
        messages.error(request, "Notifications not found!")
    return redirect('notifications')


# ============================================================
# SCHEDULE & GANTT CHART MANAGEMENT
# ============================================================
def schedule_view(request):
    """Show halaman schedule dengan Gantt Chart."""
    if not ensure_user_authenticated(request):
        return redirect('login')
    
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    projects = Project.objects.all()
    selected_project_id = request.GET.get('project_id')
    
    schedules = Schedule.objects.select_related('project', 'parent').all()
    if selected_project_id:
        schedules = schedules.filter(project_id=selected_project_id)
    
    # Siaporn data untuk Gantt Chart (JSON)
    import json
    gantt_data = []
    for s in schedules:
        gantt_data.append({
            'id': s.id,
            'text': s.activity_name,
            'start_date': s.planned_start.strftime('%Y-%m-%d') if s.planned_start else None,
            'end_date': s.planned_finish.strftime('%Y-%m-%d') if s.planned_finish else None,
            'progress': float(s.progress),
            'status': s.status,
            'project_id': s.project.id
        })
    
    context = {
        'user_profile': user_profile,
        'projects': projects,
        'schedules': schedules,
        'selected_project_id': selected_project_id,
        'gantt_data_json': json.dumps(gantt_data),
        'unread_count': _get_unread_count(request.user),
    }
    return render(request, 'core/schedule.html', context)


def add_schedule(request):
    """Add a new schedule."""
    if request.method != 'POST':
        return redirect('schedule')
    if not ensure_user_authenticated(request):
        messages.error(request, "Please login first.")
        return redirect('schedule')
    
    project_id = request.POST.get('project_id')
    try:
        project = Project.objects.get(id=project_id)
    except (Project.DoesNotExist, ValueError):
        messages.error(request, "Project not found.")
        return redirect('schedule')
    
    Schedule.objects.create(
        project=project,
        activity_code=request.POST.get('activity_code', ''),
        activity_name=request.POST.get('activity_name', ''),
        planned_start=request.POST.get('planned_start') or None,
        planned_finish=request.POST.get('planned_finish') or None,
        duration_planned=request.POST.get('duration_planned') or 0,
        progress=request.POST.get('progress') or 0,
        status=request.POST.get('status', 'NOT_STARTED'),
    )
    
    messages.success(request, "Schedule new successfully aumenta!")
    return redirect('schedule')


def update_schedule_progress(request, schedule_id):
    """Update progress schedule."""
    if request.method != 'POST':
        return redirect('schedule')
    if not ensure_user_authenticated(request):
        messages.error(request, "Please login first.")
        return redirect('schedule')
    
    try:
        schedule = Schedule.objects.get(id=schedule_id)
    except Schedule.DoesNotExist:
        messages.error(request, "Schedule not found.")
        return redirect('schedule')
    
    progress = request.POST.get('progress')
    if progress is not None:
        try:
            schedule.progress = float(progress)
            schedule.status = request.POST.get('status', schedule.status)
            schedule.save()
            messages.success(request, "Progress schedule dipertorui!")
        except ValueError:
            messages.error(request, "Progress invalid.")
    
    return redirect('schedule')


# ============================================================
# INTERNAL CHAT SYSTEM
# ============================================================
def chat_view(request):
    """Show halaman chat."""
    if not ensure_user_authenticated(request):
        return redirect('login')
    
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    projects = Project.objects.all()
    
    # Dapatorn chat rooms yang diikuti user
    chat_rooms = ChatRoom.objects.filter(
        Q(project__team_members__user=request.user) |
        Q(participants=request.user) |
        Q(is_public=True)
    ).distinct().prefetch_related('messages', 'participants')
    
    context = {
        'user_profile': user_profile,
        'projects': projects,
        'chat_rooms': chat_rooms,
        'unread_count': _get_unread_count(request.user),
    }
    return render(request, 'core/chat.html', context)


def create_chat_room(request):
    """Create sala chat new."""
    if request.method != 'POST':
        return redirect('chat')
    if not ensure_user_authenticated(request):
        messages.error(request, "Please login first.")
        return redirect('chat')
    
    project_id = request.POST.get('project_id')
    try:
        project = Project.objects.get(id=project_id)
    except (Project.DoesNotExist, ValueError):
        messages.error(request, "Project not found.")
        return redirect('chat')
    
    room = ChatRoom.objects.create(
        project=project,
        name=request.POST.get('name', f"Chat {project.name}"),
        is_public=request.POST.get('is_public') == 'on',
        created_by=request.user,
    )
    room.participants.add(request.user)
    
    messages.success(request, "Chat room toru dibuat!")
    return redirect('chat')




@login_required
def daily_report_detail_view(request, report_id):
    import json
    from django.shortcuts import get_object_or_404
    
    report = get_object_or_404(DailyReport, id=report_id)
    
    # 1. Progress Data
    progress_percentage = float(report.progress_percentage) if report.progress_percentage else 0.0
    
    # 2. Work Progress Data
    work_items = report.work_progress.all()
    work_labels = []
    work_target = []
    work_actual = []
    for w in work_items:
        work_labels.append(w.item_description or "Unknown")
        work_target.append(float(w.target_volume) if w.target_volume else 0.0)
        work_actual.append(float(w.actual_volume) if w.actual_volume else 0.0)
        
    # 3. Manpower Data
    manpower_items = report.manpower_usages.all()
    mp_roles = []
    mp_counts = []
    for m in manpower_items:
        mp_roles.append(m.role or "Unknown")
        mp_counts.append(int(m.count) if m.count else 0)
        
    # 4. Equipment Data
    equipment_items = report.equipment_usages.all()
    eq_names = []
    eq_hours = []
    for e in equipment_items:
        eq_names.append(e.equipment_name or "Unknown")
        eq_hours.append(float(e.hours_used) if e.hours_used else 0.0)
        
    chart_data = {
        'progress': progress_percentage,
        'work': {
            'labels': work_labels,
            'target': work_target,
            'actual': work_actual,
        },
        'manpower': {
            'labels': mp_roles,
            'data': mp_counts,
        },
        'equipment': {
            'labels': eq_names,
            'data': eq_hours,
        }
    }
    
    context = {
        'report': report,
        'chart_data': json.dumps(chart_data)
    }
    return render(request, 'core/daily_report_detail.html', context)

