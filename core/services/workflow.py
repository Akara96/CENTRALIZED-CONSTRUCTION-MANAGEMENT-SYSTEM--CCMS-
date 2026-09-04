"""
Central workflow engine for CCMS module chains.

Site Activity → Progress Report → Schedule → Cost Impact → Invoice → Approval
"""
import datetime
from decimal import Decimal

from django.db.models import Avg
from django.utils import timezone

from core.models import (
    Approval,
    ApprovalStepHistory,
    CostSummary,
    DailyReport,
    Document,
    DocumentRevisionHistory,
    FinancialRecord,
    FinancialRecordHistory,
    InterimPaymentCertificate,
    Invoice,
    MaterialRequest,
    Meeting,
    MeetingAction,
    ProgressReport,
    PurchaseRequest,
    Schedule,
    SiteActivity,
    VariationOrder,
    WorkItem,
)


def _decimal(value):
    if value is None:
        return Decimal('0')
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _default_step_for_status(status):
    if status == 'APPROVED':
        return 'COMPLETED'
    return 'REVIEWER'


def record_approval_step(approval, from_step, to_step, action, comments='', action_by=None):
    return ApprovalStepHistory.objects.create(
        approval=approval,
        from_step=from_step,
        to_step=to_step,
        action=action,
        comments=comments,
        action_by=action_by,
    )


def get_previous_project_progress(project, before_date=None):
    """Latest overall progress before a given date."""
    qs = project.progress_reports.order_by('-report_date')
    if before_date:
        qs = qs.filter(report_date__lt=before_date)
    latest = qs.first()
    if latest:
        return float(latest.overall_progress)

    daily_qs = project.daily_reports.filter(status='APPROVED')
    if before_date:
        daily_qs = daily_qs.filter(date__lt=before_date)
    approved = daily_qs.order_by('-date').first()
    if approved:
        return float(approved.progress_percentage)

    avg = project.work_items.aggregate(Avg('progress_percent'))['progress_percent__avg']
    return float(avg or 0)


def create_or_update_approval(
    project,
    module_type,
    reference_id,
    *,
    document_title='',
    submitted_by=None,
    reviewed_by=None,
    approved_by=None,
    reviewer_by=None,
    manager_by=None,
    consultant_by=None,
    hq_approved_by=None,
    current_step=None,
    status='PENDING',
    comments='',
    rejection_reason='',
):
    approval, created = Approval.objects.get_or_create(
        project=project,
        module_type=module_type,
        reference_id=reference_id,
        defaults={
            'document_title': document_title,
            'submitted_by': submitted_by,
            'reviewed_by': reviewed_by,
            'approved_by': approved_by,
            'reviewer_by': reviewer_by,
            'manager_by': manager_by,
            'consultant_by': consultant_by,
            'hq_approved_by': hq_approved_by,
            'current_step': current_step or _default_step_for_status(status),
            'status': status,
            'comments': comments,
            'rejection_reason': rejection_reason,
            'approved_at': timezone.now() if status == 'APPROVED' else None,
        },
    )
    if not created:
        approval.document_title = document_title
        approval.submitted_by = submitted_by
        approval.reviewed_by = reviewed_by
        approval.approved_by = approved_by
        approval.status = status
        approval.comments = comments
        approval.rejection_reason = rejection_reason
        if reviewer_by is not None:
            approval.reviewer_by = reviewer_by
        if manager_by is not None:
            approval.manager_by = manager_by
        if consultant_by is not None:
            approval.consultant_by = consultant_by
        if hq_approved_by is not None:
            approval.hq_approved_by = hq_approved_by
        if current_step is not None:
            approval.current_step = current_step
        elif status == 'APPROVED':
            approval.current_step = 'COMPLETED'
        if status == 'APPROVED' and not approval.approved_at:
            approval.approved_at = timezone.now()
        approval.save()
    return approval


def register_daily_report_submission(report):
    """Queue daily report for PM/Director review."""
    if report.status == 'APPROVED':
        return None
    return create_or_update_approval(
        report.project,
        'daily_report',
        report.id,
        document_title=f"Daily Report {report.date} — {report.progress_percentage}%",
        submitted_by=report.reporter,
        status='PENDING',
        current_step='REVIEWER',
    )


def propagate_daily_report_approval(report, approver):
    """
    On daily report approval:
    - Sync ProgressReport
    - Update active Schedule activities
    - Update WorkItem progress & actuals
    - Apply cost impact to CostSummary
    - Log SiteActivity
    - Close Approval record
    """
    project = report.project
    progress = float(report.progress_percentage)
    prev_progress = get_previous_project_progress(project, before_date=report.date)
    progress_delta = max(progress - prev_progress, 0)

    progress_report, _ = ProgressReport.objects.update_or_create(
        project=project,
        report_date=report.date,
        defaults={
            'report_period': f"Week of {report.date.strftime('%Y-%m-%d')}",
            'overall_progress': progress,
            'civil_progress': progress,
            'remarks': f"Synced from approved daily report #{report.id}",
            'prepared_by': report.reporter,
            'status': 'APPROVED',
            'approved_by': approver,
            'approved_at': timezone.now(),
            'rejection_reason': None,
        },
    )
    create_or_update_approval(
        project,
        'progress',
        progress_report.id,
        document_title=f"Progress {progress_report.report_date} - {progress_report.overall_progress}%",
        submitted_by=report.reporter,
        reviewed_by=approver,
        approved_by=approver,
        status='APPROVED',
        current_step='COMPLETED',
        hq_approved_by=approver,
        comments='Progress approved together with final Daily Report approval.',
    )

    for sched in project.schedules.filter(status__in=['IN_PROGRESS', 'NOT_STARTED']):
        new_progress = max(float(sched.progress), progress)
        sched.progress = min(new_progress, 100)
        if sched.status == 'NOT_STARTED' and sched.progress > 0:
            sched.status = 'IN_PROGRESS'
            if not sched.actual_start:
                sched.actual_start = report.date
        if sched.progress >= 100:
            sched.status = 'COMPLETED'
            sched.actual_finish = report.date
        elif sched.planned_finish and report.date > sched.planned_finish:
            sched.status = 'DELAYED'
        sched.save()

    if not project.work_items.filter(actual_quantity__gt=0).exists():
        for item in project.work_items.filter(progress_percent__lt=progress):
            item.progress_percent = progress
            ratio = _decimal(progress) / Decimal('100')
            item.actual_quantity = item.boq_quantity * ratio
            item.actual_amount = item.boq_amount * ratio
            item.save()

    budget = _decimal(project.budget)
    if progress_delta > 0 and budget > 0:
        cost_delta = budget * _decimal(progress_delta) / Decimal('100')
        summary, _ = CostSummary.objects.get_or_create(
            project=project,
            category='Construction Progress',
            defaults={
                'sub_category': 'Physical Works',
                'budget': budget * Decimal('0.85'),
                'actual': Decimal('0'),
                'committed': Decimal('0'),
                'forecast': budget,
            },
        )
        summary.actual = _decimal(summary.actual) + cost_delta
        summary.forecast = max(_decimal(summary.forecast), _decimal(summary.actual))
        summary.report_date = report.date
        summary.save()

    SiteActivity.objects.create(
        project=project,
        activity_name=f"Approved daily progress {progress}%",
        location=project.location or '',
        activity_date=report.date,
        status='DONE',
        manpower=report.manpower_count,
        notes=(report.work_done or '')[:500],
    )

    return create_or_update_approval(
        project,
        'daily_report',
        report.id,
        document_title=f"Daily Report {report.date} — {progress}%",
        submitted_by=report.reporter,
        reviewed_by=approver,
        approved_by=approver,
        status='APPROVED',
        current_step='COMPLETED',
        hq_approved_by=approver,
        comments='Progress synced to schedule, BOQ, and cost summary.',
    )


def register_vo_submission(vo):
    return create_or_update_approval(
        vo.project,
        'variation_order',
        vo.id,
        document_title=f"VO {vo.vo_number} — ${_decimal(vo.requested_amount):,.2f}",
        submitted_by=vo.requested_by,
        status='PENDING',
        current_step='HQ_APPROVAL',
    )


def propagate_vo_approval(vo, approver):
    """
    On VO approval:
    - Increase project budget & contract value
    - Extend schedule if time impact
    - Record VO cost line
    - Close Approval
    """
    project = vo.project
    amount = _decimal(vo.approved_amount or vo.requested_amount)

    vo_line, _ = CostSummary.objects.get_or_create(
        project=project,
        category='Variation Orders',
        defaults={
            'sub_category': 'Approved VO',
            'budget': Decimal('0'),
            'actual': Decimal('0'),
            'committed': Decimal('0'),
            'forecast': Decimal('0'),
        },
    )
    vo_line.committed = _decimal(vo_line.committed) + amount
    vo_line.forecast = _decimal(vo_line.forecast) + amount
    vo_line.report_date = vo.approved_date or datetime.date.today()
    vo_line.save()

    project.budget = _decimal(project.budget) + amount
    project.contract_value = _decimal(project.contract_value) + amount
    if vo.time_impact and vo.time_impact > 0:
        project.end_date = project.end_date + datetime.timedelta(days=vo.time_impact)
        for sched in project.schedules.filter(status__in=['IN_PROGRESS', 'NOT_STARTED']):
            if sched.planned_finish:
                sched.planned_finish = sched.planned_finish + datetime.timedelta(days=vo.time_impact)
                sched.status = 'DELAYED'
                sched.save()
    project.save()

    return create_or_update_approval(
        project,
        'variation_order',
        vo.id,
        document_title=f"VO {vo.vo_number}",
        submitted_by=vo.requested_by,
        approved_by=approver,
        status='APPROVED',
        current_step='COMPLETED',
        hq_approved_by=approver,
        comments=f"VO approved — budget increased by ${amount:,.2f}.",
    )


def register_invoice_submission(invoice):
    return create_or_update_approval(
        invoice.project,
        'invoice',
        invoice.id,
        document_title=f"Invoice {invoice.invoice_number} — ${invoice.net_amount:,.2f}",
        submitted_by=invoice.submitted_by,
        status='PENDING',
        current_step='REVIEWER',
    )


def propagate_invoice_verification(invoice, reviewer):
    """PM/Cost Engineer verifies claim amount."""
    invoice.status = 'VERIFIED'
    invoice.save(update_fields=['status'])
    return create_or_update_approval(
        invoice.project,
        'invoice',
        invoice.id,
        document_title=f"Invoice {invoice.invoice_number}",
        submitted_by=invoice.submitted_by,
        reviewed_by=reviewer,
        status='REVIEWED',
        comments='Invoice verified — awaiting HQ certification.',
    )


def propagate_invoice_site_verification(invoice, reviewer, comments=''):
    """Finance site verifies expense/invoice/payment claim data."""
    invoice.status = 'SITE_VERIFIED'
    invoice.site_verified_by = reviewer
    invoice.site_verified_at = timezone.now()
    invoice.rejection_reason = None
    invoice.save(update_fields=['status', 'site_verified_by', 'site_verified_at', 'rejection_reason'])
    return create_or_update_approval(
        invoice.project,
        'invoice',
        invoice.id,
        document_title=f"Invoice {invoice.invoice_number}",
        submitted_by=invoice.submitted_by,
        reviewed_by=reviewer,
        status='PENDING',
        current_step='MANAGER',
        reviewer_by=reviewer,
        comments=comments or 'Finance Site verified invoice. Waiting HQ Finance review.',
    )


def propagate_invoice_hq_review(invoice, reviewer, comments=''):
    """HQ Finance reviews verified claim before final approval."""
    invoice.status = 'HQ_REVIEWED'
    invoice.hq_reviewed_by = reviewer
    invoice.hq_reviewed_at = timezone.now()
    invoice.rejection_reason = None
    invoice.save(update_fields=['status', 'hq_reviewed_by', 'hq_reviewed_at', 'rejection_reason'])
    return create_or_update_approval(
        invoice.project,
        'invoice',
        invoice.id,
        document_title=f"Invoice {invoice.invoice_number}",
        submitted_by=invoice.submitted_by,
        reviewed_by=reviewer,
        status='REVIEWED',
        current_step='HQ_APPROVAL',
        manager_by=reviewer,
        comments=comments or 'HQ Finance reviewed invoice. Waiting final approval.',
    )


def propagate_invoice_verification(invoice, reviewer):
    """Backward-compatible alias for the site finance verification step."""
    return propagate_invoice_site_verification(invoice, reviewer)


def propagate_invoice_certification(invoice, certifier, deduction=0):
    """
    Director certifies invoice → creates IPC and updates cost actuals.
    """
    deduction = _decimal(deduction)
    verified = _decimal(invoice.net_amount)
    certified = verified - deduction

    ipc_number = f"IPC-{invoice.invoice_number}"
    ipc, _ = InterimPaymentCertificate.objects.update_or_create(
        project=invoice.project,
        invoice=invoice,
        defaults={
            'ipc_number': ipc_number,
            'claimed_amount': _decimal(invoice.amount),
            'verified_amount': verified,
            'deduction': deduction,
            'certified_amount': certified,
            'status': 'CERTIFIED',
            'certified_by': certifier,
            'certified_date': datetime.date.today(),
            'remarks': f"Certified from invoice {invoice.invoice_number}",
        },
    )

    summary, _ = CostSummary.objects.get_or_create(
        project=invoice.project,
        category='Payment Claims',
        defaults={
            'sub_category': 'Invoiced Works',
            'budget': _decimal(invoice.project.budget),
            'actual': Decimal('0'),
            'committed': Decimal('0'),
            'forecast': _decimal(invoice.project.budget),
        },
    )
    summary.actual = _decimal(summary.actual) + certified
    summary.report_date = datetime.date.today()
    summary.save()

    invoice.status = 'APPROVED'
    invoice.approved_by = certifier
    invoice.approved_at = timezone.now()
    invoice.rejection_reason = None
    invoice.save(update_fields=['status', 'approved_by', 'approved_at', 'rejection_reason'])

    create_or_update_approval(
        invoice.project,
        'invoice',
        invoice.id,
        document_title=f"Invoice {invoice.invoice_number}",
        submitted_by=invoice.submitted_by,
        reviewed_by=certifier,
        approved_by=certifier,
        status='APPROVED',
        current_step='COMPLETED',
        hq_approved_by=certifier,
        comments=f"IPC {ipc.ipc_number} certified — ${certified:,.2f}.",
    )
    return ipc


def register_financial_record_submission(record):
    FinancialRecordHistory.objects.create(
        financial_record=record,
        action='Submitted',
        from_status='DRAFT',
        to_status=record.status,
        comments='Financial record submitted for Finance Site verification.',
        action_by=record.submitted_by,
    )
    return create_or_update_approval(
        record.project,
        'financial_record',
        record.id,
        document_title=f"{record.get_record_type_display()} {record.reference_number or record.id} - ${record.amount:,.2f}",
        submitted_by=record.submitted_by,
        status='PENDING',
        current_step='REVIEWER',
    )


def sync_financial_record_cost(record):
    category = record.category or record.get_record_type_display()
    summary, _ = CostSummary.objects.get_or_create(
        project=record.project,
        category=category,
        defaults={
            'sub_category': record.get_record_type_display(),
            'budget': _decimal(record.project.budget),
            'actual': Decimal('0'),
            'committed': Decimal('0'),
            'forecast': _decimal(record.project.budget),
        },
    )
    summary.actual = _decimal(summary.actual) + _decimal(record.amount)
    summary.report_date = record.transaction_date or datetime.date.today()
    summary.save()
    return summary


def propagate_financial_record_site_verification(record, reviewer, comments=''):
    from_status = record.status
    record.status = 'SITE_VERIFIED'
    record.site_verified_by = reviewer
    record.site_verified_at = timezone.now()
    record.rejection_reason = None
    record.save(update_fields=['status', 'site_verified_by', 'site_verified_at', 'rejection_reason', 'updated_at'])
    FinancialRecordHistory.objects.create(
        financial_record=record,
        action='Finance Site Verify',
        from_status=from_status,
        to_status=record.status,
        comments=comments,
        action_by=reviewer,
    )
    return create_or_update_approval(
        record.project,
        'financial_record',
        record.id,
        document_title=f"{record.get_record_type_display()} {record.reference_number or record.id} - ${record.amount:,.2f}",
        submitted_by=record.submitted_by,
        reviewed_by=reviewer,
        status='PENDING',
        current_step='MANAGER',
        reviewer_by=reviewer,
        comments=comments or 'Finance Site verified. Waiting HQ Finance review.',
    )


def propagate_financial_record_hq_review(record, reviewer, comments=''):
    from_status = record.status
    record.status = 'HQ_REVIEWED'
    record.hq_reviewed_by = reviewer
    record.hq_reviewed_at = timezone.now()
    record.rejection_reason = None
    record.save(update_fields=['status', 'hq_reviewed_by', 'hq_reviewed_at', 'rejection_reason', 'updated_at'])
    FinancialRecordHistory.objects.create(
        financial_record=record,
        action='HQ Finance Review',
        from_status=from_status,
        to_status=record.status,
        comments=comments,
        action_by=reviewer,
    )
    return create_or_update_approval(
        record.project,
        'financial_record',
        record.id,
        document_title=f"{record.get_record_type_display()} {record.reference_number or record.id} - ${record.amount:,.2f}",
        submitted_by=record.submitted_by,
        reviewed_by=reviewer,
        status='REVIEWED',
        current_step='HQ_APPROVAL',
        manager_by=reviewer,
        comments=comments or 'HQ Finance reviewed. Waiting final approval.',
    )


def propagate_financial_record_approval(record, approver, comments=''):
    from_status = record.status
    record.status = 'APPROVED'
    record.approved_by = approver
    record.approved_at = timezone.now()
    record.rejection_reason = None
    record.save(update_fields=['status', 'approved_by', 'approved_at', 'rejection_reason', 'updated_at'])
    sync_financial_record_cost(record)
    FinancialRecordHistory.objects.create(
        financial_record=record,
        action='Approved',
        from_status=from_status,
        to_status=record.status,
        comments=comments or 'Approved and synced to cashflow.',
        action_by=approver,
    )
    return create_or_update_approval(
        record.project,
        'financial_record',
        record.id,
        document_title=f"{record.get_record_type_display()} {record.reference_number or record.id} - ${record.amount:,.2f}",
        submitted_by=record.submitted_by,
        approved_by=approver,
        status='APPROVED',
        current_step='COMPLETED',
        hq_approved_by=approver,
        comments=comments or 'Financial record approved and synced to cashflow.',
    )


def reject_financial_record(record, reviewer, comments=''):
    from_status = record.status
    record.status = 'REJECTED'
    record.rejection_reason = comments or 'Rejected.'
    record.save(update_fields=['status', 'rejection_reason', 'updated_at'])
    FinancialRecordHistory.objects.create(
        financial_record=record,
        action='Rejected',
        from_status=from_status,
        to_status=record.status,
        comments=record.rejection_reason,
        action_by=reviewer,
    )
    return create_or_update_approval(
        record.project,
        'financial_record',
        record.id,
        document_title=f"{record.get_record_type_display()} {record.reference_number or record.id} - ${record.amount:,.2f}",
        submitted_by=record.submitted_by,
        reviewed_by=reviewer,
        status='REJECTED',
        comments=record.rejection_reason,
        rejection_reason=record.rejection_reason,
    )


def register_document_submission(document):
    DocumentRevisionHistory.objects.create(
        document=document,
        action='Submitted',
        from_status='DRAFT',
        to_status=document.status,
        revision=document.revision,
        comments='Document submitted for Document Controller review.',
        action_by=document.submitted_by,
    )
    return create_or_update_approval(
        document.project,
        'document',
        document.id,
        document_title=f"{document.document_number} — {document.document_title}",
        submitted_by=document.submitted_by,
        status='PENDING',
        current_step='REVIEWER',
    )


def propagate_document_approval(document, approver, approved=True, comments=''):
    from_status = document.status
    if approved:
        document.status = 'APPROVED'
        document.approved_by = approver
        document.approved_at = timezone.now()
        document.rejection_reason = None
        approval_status = 'APPROVED'
    else:
        document.status = 'REVISION_REQUIRED'
        document.rejection_reason = comments or 'Document rejected. Revision required.'
        approval_status = 'REJECTED'
    document.save()

    DocumentRevisionHistory.objects.create(
        document=document,
        action='Final Approval' if approved else 'Revision Required',
        from_status=from_status,
        to_status=document.status,
        revision=document.revision,
        comments=comments or ('Document approved.' if approved else 'Document rejected. Revision required.'),
        action_by=approver,
    )

    return create_or_update_approval(
        document.project,
        'document',
        document.id,
        document_title=f"{document.document_number} — {document.document_title}",
        submitted_by=document.submitted_by,
        approved_by=approver if approved else None,
        status=approval_status,
        current_step='COMPLETED' if approved else 'REVIEWER',
        hq_approved_by=approver if approved else None,
        comments=comments or ('Document approved.' if approved else 'Document rejected. Revision required.'),
        rejection_reason='' if approved else (comments or 'Document rejected. Revision required.'),
    )


def register_meeting_submission(meeting):
    return create_or_update_approval(
        meeting.project,
        'meeting',
        meeting.id,
        document_title=f"Meeting: {meeting.meeting_title}",
        submitted_by=meeting.chairperson,
        status='PENDING',
        current_step='MANAGER',
        comments='Meeting minutes submitted for acknowledgment.',
    )


def propagate_meeting_acknowledgment(meeting, approver):
    return create_or_update_approval(
        meeting.project,
        'meeting',
        meeting.id,
        document_title=f"Meeting: {meeting.meeting_title}",
        submitted_by=meeting.chairperson,
        approved_by=approver,
        status='APPROVED',
        current_step='COMPLETED',
        comments='Meeting minutes acknowledged.',
    )


PHASE_G_MODULES = {'material', 'purchase', 'progress'}
PHASE_G_NEXT_STEP = {
    'REVIEWER': 'MANAGER',
    'MANAGER': 'CONSULTANT',
    'CONSULTANT': 'HQ_APPROVAL',
    'HQ_APPROVAL': 'COMPLETED',
}
PHASE_G_STAGE_STATUS = {
    'REVIEWER': 'REVIEWER_REVIEWED',
    'MANAGER': 'MANAGER_REVIEWED',
    'CONSULTANT': 'CONSULTANT_REVIEWED',
    'HQ_APPROVAL': 'APPROVED',
}


def register_material_request_submission(material_request):
    return create_or_update_approval(
        material_request.project,
        'material',
        material_request.id,
        document_title=f"Material {material_request.request_number or material_request.id} - {material_request.material_name}",
        submitted_by=material_request.requested_by,
        status='PENDING',
        current_step='REVIEWER',
        comments='Material request submitted. Waiting reviewer.',
    )


def register_purchase_request_submission(purchase_request):
    return create_or_update_approval(
        purchase_request.project,
        'purchase',
        purchase_request.id,
        document_title=f"Purchase {purchase_request.purchase_number or purchase_request.id} - ${purchase_request.amount:,.2f}",
        submitted_by=purchase_request.requested_by,
        status='PENDING',
        current_step='REVIEWER',
        comments='Purchase request submitted. Waiting reviewer.',
    )


def register_progress_submission(progress_report):
    return create_or_update_approval(
        progress_report.project,
        'progress',
        progress_report.id,
        document_title=f"Progress {progress_report.report_date} - {progress_report.overall_progress}%",
        submitted_by=progress_report.prepared_by,
        status='PENDING',
        current_step='REVIEWER',
        comments='Progress update submitted. Waiting reviewer.',
    )


def _phase_g_allowed_roles(module, step):
    role_map = {
        'REVIEWER': {
            'PROJECT_MANAGER', 'PROJECT_DIRECTOR', 'STOREKEEPER',
            'COST_ENGINEER', 'FINANCE_SITE', 'DOC_CONTROLLER', 'QA_QC',
        },
        'MANAGER': {'PROJECT_MANAGER', 'PROJECT_DIRECTOR'},
        'CONSULTANT': {'CONSULTANT'},
        'HQ_APPROVAL': {'HQ_DIRECTOR', 'PROJECT_DIRECTOR'},
    }
    module_first_step = {
        'material': {'STOREKEEPER', 'COST_ENGINEER', 'PROJECT_MANAGER', 'PROJECT_DIRECTOR'},
        'purchase': {'STOREKEEPER', 'COST_ENGINEER', 'FINANCE_SITE', 'PROJECT_MANAGER', 'PROJECT_DIRECTOR'},
        'progress': {'PROJECT_MANAGER', 'PROJECT_DIRECTOR', 'QA_QC'},
    }
    if step == 'REVIEWER':
        return module_first_step.get(module, role_map[step])
    return role_map.get(step, set())


def _can_process_phase_g_step(module, step, role):
    if role == 'ADMIN_SYSTEM':
        return True
    return role in _phase_g_allowed_roles(module, step)


def _sync_phase_g_linked_record(approval, completed_step, user, metadata=None):
    metadata = metadata or {}
    now = timezone.now()
    module = approval.module_type
    stage_status = PHASE_G_STAGE_STATUS.get(completed_step)

    if module == 'material':
        try:
            material_request = MaterialRequest.objects.get(id=approval.reference_id)
        except MaterialRequest.DoesNotExist:
            return
        if completed_step == 'HQ_APPROVAL':
            approved_quantity = _decimal(
                metadata.get('approved_quantity') or material_request.approved_quantity or material_request.quantity
            )
            if approved_quantity <= 0:
                approved_quantity = material_request.quantity
            material_request.status = 'APPROVED'
            material_request.approved_quantity = approved_quantity
            material_request.approved_by = user
            material_request.approved_date = datetime.date.today()
            material_request.rejection_reason = None
            material_request.save(update_fields=[
                'status', 'approved_quantity', 'approved_by', 'approved_date', 'rejection_reason'
            ])
        return

    if module == 'purchase':
        try:
            purchase_request = PurchaseRequest.objects.get(id=approval.reference_id)
        except PurchaseRequest.DoesNotExist:
            return
        if completed_step == 'REVIEWER':
            purchase_request.status = stage_status
            purchase_request.reviewer_by = user
            purchase_request.reviewer_at = now
            fields = ['status', 'reviewer_by', 'reviewer_at']
        elif completed_step == 'MANAGER':
            purchase_request.status = stage_status
            purchase_request.manager_by = user
            purchase_request.manager_at = now
            fields = ['status', 'manager_by', 'manager_at']
        elif completed_step == 'CONSULTANT':
            purchase_request.status = stage_status
            purchase_request.consultant_by = user
            purchase_request.consultant_at = now
            fields = ['status', 'consultant_by', 'consultant_at']
        else:
            purchase_request.status = 'APPROVED'
            purchase_request.approved_by = user
            purchase_request.approved_at = now
            purchase_request.rejection_reason = None
            fields = ['status', 'approved_by', 'approved_at', 'rejection_reason']
        purchase_request.save(update_fields=fields)
        return

    if module == 'progress':
        try:
            progress_report = ProgressReport.objects.get(id=approval.reference_id)
        except ProgressReport.DoesNotExist:
            return
        if completed_step == 'HQ_APPROVAL':
            progress_report.status = 'APPROVED'
            progress_report.approved_by = user
            progress_report.approved_at = now
            progress_report.rejection_reason = None
            progress_report.save(update_fields=['status', 'approved_by', 'approved_at', 'rejection_reason'])
        elif stage_status:
            progress_report.status = stage_status
            progress_report.save(update_fields=['status'])


def process_phase_g_approval(approval, action, user, role, comments='', metadata=None):
    if approval.module_type not in PHASE_G_MODULES:
        return False, f'Unknown Phase G module: {approval.module_type}'
    if approval.status not in ('PENDING', 'REVIEWED'):
        return False, 'Approval already finalized.'

    current_step = approval.current_step or 'REVIEWER'
    if current_step == 'COMPLETED':
        return False, 'Approval already completed.'
    if not _can_process_phase_g_step(approval.module_type, current_step, role):
        return False, f'Role {role} not authorized for {approval.get_current_step_display()} step.'

    if action == 'REJECTED':
        approval.status = 'REJECTED'
        approval.rejection_reason = comments or 'Rejected.'
        approval.comments = approval.rejection_reason
        approval.reviewed_by = user
        approval.save()
        record_approval_step(approval, current_step, current_step, 'Rejected', approval.rejection_reason, user)
        _reject_linked_record(approval.module_type, approval.reference_id, approval.rejection_reason)
        return True, f'{approval.document_title or approval.module_type} rejected.'

    next_step = PHASE_G_NEXT_STEP[current_step]
    now = timezone.now()
    update_fields = ['current_step', 'status', 'comments']
    approval.comments = comments or f'{approval.get_current_step_display()} completed.'

    if current_step == 'REVIEWER':
        approval.reviewer_by = user
        approval.reviewer_at = now
        approval.reviewed_by = user
        approval.status = 'PENDING'
        update_fields += ['reviewer_by', 'reviewer_at', 'reviewed_by']
    elif current_step == 'MANAGER':
        approval.manager_by = user
        approval.manager_at = now
        approval.status = 'PENDING'
        update_fields += ['manager_by', 'manager_at']
    elif current_step == 'CONSULTANT':
        approval.consultant_by = user
        approval.consultant_at = now
        approval.status = 'REVIEWED'
        update_fields += ['consultant_by', 'consultant_at']
    elif current_step == 'HQ_APPROVAL':
        approval.hq_approved_by = user
        approval.hq_approved_at = now
        approval.approved_by = user
        approval.approved_at = now
        approval.status = 'APPROVED'
        update_fields += ['hq_approved_by', 'hq_approved_at', 'approved_by', 'approved_at']

    approval.current_step = next_step
    approval.save(update_fields=update_fields)
    record_approval_step(approval, current_step, next_step, 'Approved', comments, user)
    _sync_phase_g_linked_record(approval, current_step, user, metadata)

    if next_step == 'COMPLETED':
        return True, f'{approval.document_title or approval.module_type} approved by HQ.'
    return True, f'{approval.document_title or approval.module_type} moved to {approval.get_current_step_display()}.'


def process_central_approval(approval, action, user, comments='', role=None, metadata=None):
    """
    Route a pending Approval record through the correct propagation handler.
    Returns (success: bool, message: str).
    """
    if approval.status not in ('PENDING', 'REVIEWED'):
        return False, 'Approval already finalized.'

    module = approval.module_type
    ref_id = approval.reference_id

    if module in PHASE_G_MODULES:
        user_role = role
        if user_role is None and hasattr(user, 'profile'):
            user_role = user.profile.role
        return process_phase_g_approval(approval, action, user, user_role or '', comments, metadata)

    if action == 'REJECTED':
        approval.status = 'REJECTED'
        approval.comments = comments or 'Rejected.'
        approval.reviewed_by = user
        approval.save()
        _reject_linked_record(module, ref_id, comments)
        return True, f'{module} rejected.'

    if module == 'daily_report':
        try:
            report = DailyReport.objects.get(id=ref_id)
        except DailyReport.DoesNotExist:
            return False, 'Daily report not found.'
        report.status = 'APPROVED'
        report.rejection_reason = None
        report.save()
        propagate_daily_report_approval(report, user)
        return True, f'Daily report for {report.project.name} approved and synced.'

    if module == 'variation_order':
        try:
            vo = VariationOrder.objects.get(id=ref_id)
        except VariationOrder.DoesNotExist:
            return False, 'Variation order not found.'
        vo.status = 'APPROVED'
        vo.approved_amount = vo.requested_amount
        vo.approved_by = user
        vo.approved_date = datetime.date.today()
        vo.save()
        propagate_vo_approval(vo, user)
        return True, f'VO {vo.vo_number} approved.'

    if module == 'invoice':
        try:
            invoice = Invoice.objects.get(id=ref_id)
        except Invoice.DoesNotExist:
            return False, 'Invoice not found.'
        if invoice.status == 'SUBMITTED':
            propagate_invoice_site_verification(invoice, user, comments)
            return True, f'Invoice {invoice.invoice_number} verified by Finance Site.'
        if invoice.status == 'SITE_VERIFIED':
            propagate_invoice_hq_review(invoice, user, comments)
            return True, f'Invoice {invoice.invoice_number} reviewed by HQ Finance.'
        if invoice.status in ['HQ_REVIEWED', 'VERIFIED']:
            propagate_invoice_certification(invoice, user)
            return True, f'Invoice {invoice.invoice_number} certified with IPC.'
        if approval.status == 'PENDING':
            propagate_invoice_site_verification(invoice, user, comments)
            return True, f'Invoice {invoice.invoice_number} verified by Finance Site.'
        propagate_invoice_certification(invoice, user)
        return True, f'Invoice {invoice.invoice_number} certified with IPC.'

    if module == 'financial_record':
        try:
            record = FinancialRecord.objects.get(id=ref_id)
        except FinancialRecord.DoesNotExist:
            return False, 'Financial record not found.'
        if record.status == 'SUBMITTED':
            propagate_financial_record_site_verification(record, user, comments)
            return True, f'{record.get_record_type_display()} verified by Finance Site.'
        if record.status == 'SITE_VERIFIED':
            propagate_financial_record_hq_review(record, user, comments)
            return True, f'{record.get_record_type_display()} reviewed by HQ Finance.'
        if record.status == 'HQ_REVIEWED':
            propagate_financial_record_approval(record, user, comments)
            return True, f'{record.get_record_type_display()} approved and synced to cashflow.'
        return False, 'Financial record is not in a processable review stage.'

    if module == 'document':
        try:
            doc = Document.objects.get(id=ref_id)
        except Document.DoesNotExist:
            return False, 'Document not found.'
        propagate_document_approval(doc, user, approved=True, comments=comments)
        return True, f'Document {doc.document_number} approved.'

    if module == 'meeting':
        try:
            meeting = Meeting.objects.get(id=ref_id)
        except Meeting.DoesNotExist:
            return False, 'Meeting not found.'
        propagate_meeting_acknowledgment(meeting, user)
        return True, f'Meeting "{meeting.meeting_title}" acknowledged.'

    return False, f'Unknown module type: {module}'


def _reject_linked_record(module_type, reference_id, comments=''):
    if module_type == 'daily_report':
        DailyReport.objects.filter(id=reference_id).update(
            status='REJECTED',
            rejection_reason=comments or 'Rejected via approval workflow.',
        )
    elif module_type == 'variation_order':
        VariationOrder.objects.filter(id=reference_id).update(status='REJECTED')
    elif module_type == 'invoice':
        Invoice.objects.filter(id=reference_id).update(status='REJECTED', rejection_reason=comments or 'Rejected via approval workflow.')
    elif module_type == 'financial_record':
        try:
            record = FinancialRecord.objects.get(id=reference_id)
            reject_financial_record(record, None, comments or 'Rejected via approval workflow.')
        except FinancialRecord.DoesNotExist:
            pass
    elif module_type == 'document':
        Document.objects.filter(id=reference_id).update(
            status='REVISION_REQUIRED',
            rejection_reason=comments or 'Rejected via approval workflow.',
        )
    elif module_type == 'material':
        MaterialRequest.objects.filter(id=reference_id).update(
            status='REJECTED',
            rejection_reason=comments or 'Rejected via approval workflow.',
        )
    elif module_type == 'purchase':
        PurchaseRequest.objects.filter(id=reference_id).update(
            status='REJECTED',
            rejection_reason=comments or 'Rejected via approval workflow.',
        )
    elif module_type == 'progress':
        ProgressReport.objects.filter(id=reference_id).update(
            status='REJECTED',
            rejection_reason=comments or 'Rejected via approval workflow.',
        )
