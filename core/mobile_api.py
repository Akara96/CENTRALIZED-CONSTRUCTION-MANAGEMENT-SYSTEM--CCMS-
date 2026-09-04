import json
from decimal import Decimal, InvalidOperation

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    Approval,
    DailyReport,
    DailyReportDocument,
    DailyReportEquipmentUsage,
    DailyReportMaterialUsage,
    DailyReportWorkProgress,
    Equipment,
    EquipmentUsage,
    Manpower,
    MaterialItem,
    Notification,
    ProgressPhoto,
    Project,
    ProjectTeam,
    RoleReport,
    StockTransaction,
    WorkItem,
)
from .services import workflow as wf


PRIVILEGED_ROLES = {"HQ_DIRECTOR", "PROJECT_DIRECTOR", "ADMIN_SYSTEM"}


def _user_role(user):
    profile = getattr(user, "profile", None)
    return profile.role if profile else None


def _user_can_access_project(user, project):
    role = _user_role(user)
    if user.is_superuser or role in PRIVILEGED_ROLES:
        return True
    return ProjectTeam.objects.filter(project=project, user=user).exists()


def _assigned_projects_for_user(user):
    role = _user_role(user)
    if user.is_superuser or role in PRIVILEGED_ROLES:
        return Project.objects.all()
    project_ids = ProjectTeam.objects.filter(user=user).values_list("project_id", flat=True)
    return Project.objects.filter(Q(id__in=project_ids) | Q(team_members__user=user)).distinct()


def _project_payload(project):
    return {
        "id": project.id,
        "project_code": project.project_code,
        "name": project.name,
        "location": project.location,
        "client_name": project.client_name,
        "status": project.status,
        "start_date": project.start_date.isoformat() if project.start_date else None,
        "end_date": project.end_date.isoformat() if project.end_date else None,
        "progress": float(project.get_latest_progress() or 0),
    }


def _daily_report_payload(report):
    return {
        "id": report.id,
        "project": _project_payload(report.project),
        "date": report.date.isoformat(),
        "weather": report.weather,
        "work_done": report.work_done,
        "issues": report.issues,
        "progress_percentage": report.progress_percentage,
        "manpower_count": report.manpower_count,
        "status": report.status,
        "rejection_reason": report.rejection_reason,
        "photo_count": report.photos.count(),
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


def _role_report_payload(report):
    return {
        "id": report.id,
        "project": _project_payload(report.project),
        "reporter": report.reporter.username if report.reporter else None,
        "reporter_role": report.reporter_role,
        "report_type": report.report_type,
        "title": report.title,
        "description": report.description,
        "location": report.location,
        "priority": report.priority,
        "status": report.status,
        "report_date": report.report_date.isoformat() if report.report_date else None,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


def _decimal_or_none(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _decimal_or_zero(value):
    parsed = _decimal_or_none(value)
    if parsed is None or parsed < 0:
        return Decimal("0")
    return parsed


def _calculate_project_progress_from_work_items(project):
    items = list(project.work_items.all())
    if not items:
        return 0

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

    progress = weighted_sum / weight_total if weight_total > 0 else progress_sum / progress_count
    return max(0, min(100, int(round(progress))))


def _json_rows(request, key):
    raw_value = request.data.get(key)
    if not raw_value:
        return []
    try:
        rows = json.loads(raw_value)
    except (TypeError, ValueError):
        return []
    return rows if isinstance(rows, list) else []


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mobile_me(request):
    profile = getattr(request.user, "profile", None)
    role = profile.role if profile else None
    return Response(
        {
            "id": request.user.id,
            "username": request.user.username,
            "email": request.user.email,
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "role": role,
            "role_display": profile.get_role_display() if profile else None,
            "permissions": {
                "can_submit_daily_report": role == "SITE_ENGINEER",
                "can_view_all_projects": request.user.is_superuser or role in PRIVILEGED_ROLES,
            },
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mobile_projects(request):
    projects = _assigned_projects_for_user(request.user).order_by("name")
    return Response({"results": [_project_payload(project) for project in projects]})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mobile_project_resources(request, project_id):
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)
    if not _user_can_access_project(request.user, project):
        return Response({"detail": "You do not have access to this project."}, status=status.HTTP_403_FORBIDDEN)
    return Response(
        {
            "project": _project_payload(project),
            "work_items": [
                {
                    "id": item.id,
                    "item_code": item.item_code,
                    "item_name": item.item_name,
                    "category": item.category,
                    "unit": item.unit,
                    "boq_quantity": float(item.boq_quantity or 0),
                    "actual_quantity": float(item.actual_quantity or 0),
                    "progress_percent": float(item.progress_percent or 0),
                }
                for item in project.work_items.order_by("category", "item_code", "item_name")[:300]
            ],
            "materials": [
                {
                    "id": item.id,
                    "item_code": item.item_code,
                    "name": item.name,
                    "unit": item.unit,
                    "category": item.category,
                    "current_stock": float(item.current_stock or 0),
                }
                for item in MaterialItem.objects.filter(project=project).order_by("name")[:300]
            ],
            "manpower": [
                {
                    "id": person.id,
                    "nik": person.nik,
                    "name": person.name,
                    "role": person.role,
                    "role_display": person.get_role_display(),
                    "phone": person.phone,
                }
                for person in Manpower.objects.filter(project=project, is_active=True).order_by("name")[:300]
            ],
            "equipment": [
                {
                    "id": equipment.id,
                    "equipment_code": equipment.equipment_code,
                    "name": equipment.name,
                    "category": equipment.category,
                    "status": equipment.status,
                    "location": equipment.location,
                }
                for equipment in Equipment.objects.filter(project=project, status__in=["ACTIVE", "RENTED"]).order_by("name")[:300]
            ],
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mobile_daily_reports(request):
    project_id = request.query_params.get("project_id")
    role = _user_role(request.user)
    allowed_projects = _assigned_projects_for_user(request.user)
    reports = DailyReport.objects.select_related("project", "reporter").filter(project__in=allowed_projects)
    if role == "SITE_ENGINEER":
        reports = reports.filter(reporter=request.user)
    if project_id:
        reports = reports.filter(project_id=project_id)
    return Response({"results": [_daily_report_payload(report) for report in reports.order_by("-date", "-created_at")[:100]]})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mobile_role_reports(request):
    project_id = request.query_params.get("project_id")
    role = _user_role(request.user)
    allowed_projects = _assigned_projects_for_user(request.user)
    reports = RoleReport.objects.select_related("project", "reporter").filter(project__in=allowed_projects)
    if role not in PRIVILEGED_ROLES and role not in {"PROJECT_MANAGER", "CONSULTANT"}:
        reports = reports.filter(reporter=request.user)
    if project_id:
        reports = reports.filter(project_id=project_id)
    return Response({"results": [_role_report_payload(report) for report in reports.order_by("-report_date", "-created_at")[:100]]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mobile_submit_role_report(request):
    project_id = request.data.get("project_id")
    if not project_id:
        return Response({"detail": "project_id is required."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)
    if not _user_can_access_project(request.user, project):
        return Response({"detail": "You do not have access to this project."}, status=status.HTTP_403_FORBIDDEN)

    title = (request.data.get("title") or "").strip()
    description = (request.data.get("description") or "").strip()
    if not title:
        return Response({"detail": "title is required."}, status=status.HTTP_400_BAD_REQUEST)
    if not description:
        return Response({"detail": "description is required."}, status=status.HTTP_400_BAD_REQUEST)

    report_date_raw = request.data.get("report_date") or timezone.localdate().isoformat()
    try:
        report_date = timezone.datetime.fromisoformat(report_date_raw).date()
    except ValueError:
        return Response({"detail": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

    role = _user_role(request.user) or ""
    priority = request.data.get("priority") or "MEDIUM"
    if priority not in dict(RoleReport.PRIORITY_CHOICES):
        priority = "MEDIUM"
    report_type = (request.data.get("report_type") or role or "GENERAL").strip()

    role_report = RoleReport.objects.create(
        project=project,
        reporter=request.user,
        reporter_role=role,
        report_type=report_type,
        title=title,
        description=description,
        location=(request.data.get("location") or "").strip(),
        priority=priority,
        report_date=report_date,
    )

    recipients = User.objects.filter(
        Q(profile__role__in=["PROJECT_MANAGER", "PROJECT_DIRECTOR", "HQ_DIRECTOR", "ADMIN_SYSTEM"]) |
        Q(projectteam__project=project, projectteam__role_in_project__in=["Project Manager", "Director"])
    ).exclude(id=request.user.id).distinct()
    Notification.objects.bulk_create([
        Notification(
            recipient=user,
            notification_type="ALERT" if priority in ["HIGH", "CRITICAL"] else "INFO",
            title=f"{role_report.report_type} report submitted",
            message=f"{request.user.username} submitted {role_report.title} for {project.name}.",
            related_module="role_report",
            related_id=role_report.id,
        )
        for user in recipients
    ])

    return Response({"report": _role_report_payload(role_report)}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def mobile_submit_daily_report(request):
    project_id = request.data.get("project_id")
    if not project_id:
        return Response({"detail": "project_id is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)
    if _user_role(request.user) != "SITE_ENGINEER":
        return Response({"detail": "Only Site Engineer can submit daily report."}, status=status.HTTP_403_FORBIDDEN)
    if not _user_can_access_project(request.user, project):
        return Response({"detail": "You do not have access to this project."}, status=status.HTTP_403_FORBIDDEN)

    report_date_raw = request.data.get("date") or timezone.localdate().isoformat()
    try:
        report_date = timezone.datetime.fromisoformat(report_date_raw).date()
    except ValueError:
        return Response({"detail": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

    work_done = (request.data.get("work_done") or "").strip()
    if not work_done:
        return Response({"detail": "work_done is required."}, status=status.HTTP_400_BAD_REQUEST)

    manpower_raw = request.data.get("manpower_count") or 0
    try:
        manpower_count = max(0, int(float(manpower_raw)))
    except (TypeError, ValueError):
        return Response({"detail": "Total staff site must be a number."}, status=status.HTTP_400_BAD_REQUEST)

    photos = request.FILES.getlist("photos") or request.FILES.getlist("progress_photos")
    if len(photos) < 4:
        return Response({"detail": "At least 4 progress photos are required."}, status=status.HTTP_400_BAD_REQUEST)

    work_item = None
    actual_quantity = _decimal_or_none(request.data.get("actual_quantity"))
    work_item_id = request.data.get("work_item_id")
    progress_percentage = 0
    item_progress = Decimal("0")
    if work_item_id and actual_quantity is not None:
        try:
            work_item = WorkItem.objects.get(id=work_item_id, project=project)
        except WorkItem.DoesNotExist:
            return Response({"detail": "Work item not found for this project."}, status=status.HTTP_400_BAD_REQUEST)
        if actual_quantity < 0:
            actual_quantity = Decimal("0")
        boq_quantity = work_item.boq_quantity or Decimal("0")
        if boq_quantity <= 0:
            return Response({"detail": "BOQ quantity for selected work item is 0."}, status=status.HTTP_400_BAD_REQUEST)
        item_progress = max(Decimal("0"), min(Decimal("100"), (actual_quantity / boq_quantity) * Decimal("100")))
        work_item.actual_quantity = actual_quantity
        work_item.progress_percent = item_progress.quantize(Decimal("0.01"))
        if work_item.boq_amount:
            work_item.actual_amount = work_item.boq_amount * item_progress / Decimal("100")
        elif work_item.unit_rate:
            work_item.actual_amount = actual_quantity * work_item.unit_rate
        work_item.save(update_fields=["actual_quantity", "progress_percent", "actual_amount"])
        progress_percentage = _calculate_project_progress_from_work_items(project)
    else:
        progress_raw = request.data.get("progress_percentage") or 0
        try:
            progress_percentage = max(0, min(100, int(float(progress_raw))))
        except (TypeError, ValueError):
            return Response({"detail": "Progress must be a number."}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        report = DailyReport.objects.create(
            project=project,
            reporter=request.user,
            date=report_date,
            weather=request.data.get("weather") or "Sunny",
            work_done=work_done,
            issues=request.data.get("issues") or "",
            progress_percentage=progress_percentage,
            manpower_count=manpower_count,
            equipment_used=request.data.get("equipment_used") or "",
            materials_used=request.data.get("materials_used") or "",
            status="PENDING",
        )

        if work_item and actual_quantity is not None:
            DailyReportWorkProgress.objects.create(
                daily_report=report,
                work_item=work_item,
                actual_quantity=actual_quantity,
                unit=work_item.unit,
                item_progress_percent=item_progress.quantize(Decimal("0.01")),
                project_progress_percent=Decimal(str(progress_percentage)),
                notes=f"BOQ {work_item.boq_quantity} {work_item.unit or ''}",
            )

        material_summaries = []
        for row in _json_rows(request, "material_items_json"):
            if not isinstance(row, dict) or not row.get("id"):
                continue
            quantity = _decimal_or_zero(row.get("quantity"))
            if quantity <= 0:
                continue
            try:
                material = MaterialItem.objects.get(id=row.get("id"), project=project)
            except (MaterialItem.DoesNotExist, ValueError):
                continue
            notes = str(row.get("notes") or "").strip()
            stock_transaction = StockTransaction.objects.create(
                material_item=material,
                project=project,
                transaction_type="OUT",
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
            material_summaries.append(f"{material.name}: {quantity} {material.unit}")

        equipment_summaries = []
        for row in _json_rows(request, "equipment_items_json")[:3]:
            if not isinstance(row, dict) or not row.get("id"):
                continue
            hours = _decimal_or_zero(row.get("hours"))
            if hours <= 0:
                continue
            try:
                equipment = Equipment.objects.get(id=row.get("id"), project=project, status__in=["ACTIVE", "RENTED"])
            except (Equipment.DoesNotExist, ValueError):
                continue
            operator = None
            operator_id = row.get("operator_id")
            if operator_id:
                try:
                    operator = Manpower.objects.get(id=operator_id, project=project, is_active=True)
                except (Manpower.DoesNotExist, ValueError):
                    operator = None
            notes = str(row.get("notes") or "").strip()
            equipment_usage = EquipmentUsage.objects.create(
                equipment=equipment,
                project=project,
                usage_date=report_date,
                hours_used=hours,
                activity=report.work_done,
                location=project.location,
                operator=operator,
                notes=notes or f"Recorded from mobile daily report DR-{report.id}",
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
            operator_label = f" - {operator.name}" if operator else ""
            equipment_summaries.append(f"{equipment.name}: {hours} jam{operator_label}")

        update_fields = []
        if material_summaries and not report.materials_used:
            report.materials_used = "; ".join(material_summaries)
            update_fields.append("materials_used")
        if equipment_summaries and not report.equipment_used:
            report.equipment_used = "; ".join(equipment_summaries)
            update_fields.append("equipment_used")
        if update_fields:
            report.save(update_fields=update_fields)

        support_document = request.FILES.get("support_document")
        if support_document:
            DailyReportDocument.objects.create(
                daily_report=report,
                file=support_document,
                document_name=request.data.get("support_document_name") or support_document.name,
                uploaded_by=request.user,
            )

        for index, image in enumerate(photos, start=1):
            ProgressPhoto.objects.create(daily_report=report, image=image, caption=f"Mobile photo {index}")

        approval = wf.register_daily_report_submission(report)
        pm_users = ProjectTeam.objects.filter(
            project=project, role_in_project__icontains="Project Manager"
        ).select_related("user")
        for member in pm_users:
            Notification.objects.create(
                recipient=member.user,
                notification_type="INFO",
                title="Daily report submitted",
                message=f"{request.user.username} submitted a daily report for {project.name} on {report.date}.",
                related_module="daily_report",
                related_id=report.id,
            )

    return Response(
        {
            "report": _daily_report_payload(report),
            "approval_id": approval.id if approval else None,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mobile_notifications(request):
    notifications = Notification.objects.filter(recipient=request.user).order_by("-created_at")[:100]
    return Response(
        {
            "unread_count": Notification.objects.filter(recipient=request.user, status="UNREAD").count(),
            "results": [
                {
                    "id": item.id,
                    "type": item.notification_type,
                    "title": item.title,
                    "message": item.message,
                    "status": item.status,
                    "related_module": item.related_module,
                    "related_id": item.related_id,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                }
                for item in notifications
            ]
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mobile_mark_notification_read(request, notification_id):
    try:
        notification = Notification.objects.get(id=notification_id, recipient=request.user)
    except Notification.DoesNotExist:
        return Response({"detail": "Notification not found."}, status=status.HTTP_404_NOT_FOUND)

    notification.status = "READ"
    notification.save(update_fields=["status"])
    return Response(
        {
            "id": notification.id,
            "status": notification.status,
            "unread_count": Notification.objects.filter(recipient=request.user, status="UNREAD").count(),
        }
    )
