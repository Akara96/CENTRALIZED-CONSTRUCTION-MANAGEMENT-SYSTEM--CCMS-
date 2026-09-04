from django.db import models
from django.contrib.auth.models import User

# ============================================================
# USER & ROLE MANAGEMENT
# ============================================================

class UserProfile(models.Model):
    ROLE_CHOICES = [
        # â”€â”€ HEAD OFFICE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        ('HQ_DIRECTOR', 'HQ Director'),            # Monitoring & Final Approval
        ('PROJECT_DIRECTOR', 'Project Director'),  # NEW: Oversight per project (Head Office)
        ('FINANCE_HQ', 'Finance HQ'),              # Invoice & cost verifiedtion
        ('FINANCE_SITE', 'Finance Site'),          # Site expense/payment verifiedtion
        ('DOC_CONTROLLER', 'Document Controller'), # Document management
        ('ADMIN_SYSTEM', 'Admin System'),          # System admin & user management
        # â”€â”€ SITE / LAPANGAN â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        ('PROJECT_MANAGER', 'Project Manager'),    # Full site management
        ('SITE_ENGINEER', 'Site Engineer'),        # Daily reports & progress
        ('SUPERVISOR', 'Supervisor'),              # NEW: Field supervision & daily ops
        ('COST_ENGINEER', 'Cost Engineer / QS'),   # UPDATED: was Cost Engineer, now includes QS
        ('HSE_OFFICER', 'Safety Officer (HSE)'),   # UPDATED: renamed to match diagram
        ('STOREKEEPER', 'Storekeeper'),            # NEW: Inventory & stock management
        ('LOGISTICS', 'Logistics Officer'),        # Material delivery, receiving & stock movement
        ('ADMIN_SITE', 'Admin Site'),              # NEW: Site-level administration
        # â”€â”€ QA / BIM / SPECIALIST â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        ('QA_QC', 'QA/QC Engineer'),
        ('BIM_MANAGER', 'BIM Manager'),
        ('ENV_SPECIALIST', 'Environmental Specialist'),
        # â”€â”€ EXTERNAL â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        ('CONSULTANT', 'Consultant'),              # Review & advisory
        ('CLIENT', 'Client / Owner'),              # NEW: Read-only project monitoring
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    employee_id = models.CharField(max_length=50, blank=True, null=True, unique=True)
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='SITE_ENGINEER')
    phone = models.CharField(max_length=50, blank=True, null=True)
    position = models.CharField(max_length=100, blank=True, null=True)
    division = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=30, blank=True, null=True, default='Active')

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


# ============================================================
# COMPANY & PROJECT
# ============================================================

class Company(models.Model):
    COMPANY_TYPE = [
        ('CONTRACTOR', 'Kontraktor'),
        ('CONSULTANT', 'Konsultan'),
        ('CLIENT', 'Klien'),
        ('VENDOR', 'Vendor'),
        ('SUBCONTRACTOR', 'Subkontraktor'),
    ]
    company_name = models.CharField(max_length=255)
    company_type = models.CharField(max_length=20, choices=COMPANY_TYPE)
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True)
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.company_name


class Vendor(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='vendors', limit_choices_to={'company_type': 'VENDOR'})
    vendor_code = models.CharField(max_length=100, unique=True)
    material_types = models.TextField(blank=True, null=True, help_text='Jenis material yang disediakan')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.vendor_code} - {self.company.company_name}"


class Subcontractor(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='subcontractors', limit_choices_to={'company_type': 'SUBCONTRACTOR'})
    subcontractor_code = models.CharField(max_length=100, unique=True)
    specialization = models.TextField(blank=True, null=True, help_text='Spesialisasi pekerjaan')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subcontractor_code} - {self.company.company_name}"


class Project(models.Model):
    STATUS_CHOICES = [
        ('PLANNING', 'Planning'),
        ('ONGOING', 'Ongoing'),
        ('HOLD', 'Hold'),
        ('COMPLETED', 'Completed'),
        ('ACTIVE', 'Active'),
    ]
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='projects')
    contractor = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='contractor_projects')
    consultant = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='consultant_projects')
    project_code = models.CharField(max_length=100, unique=True, blank=True, null=True)
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)
    client_name = models.CharField(max_length=255, blank=True, null=True)
    contract_value = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    budget = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PLANNING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def get_latest_progress(self):
        report = self.progress_reports.order_by('-report_date').first()
        return report.overall_progress if report else 0

    def get_cost_actual(self):
        total = self.cost_summaries.aggregate(models.Sum('actual'))['actual__sum']
        return total or 0

    def get_pending_vo_count(self):
        return self.variation_orders.filter(status='PENDING').count()


class ProjectTeam(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='team_members')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role_in_project = models.CharField(max_length=100, blank=True)
    joined_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.project.name} - {self.user.username}"


class ProjectReadinessChecklist(models.Model):
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='readiness')
    contractor_assigned = models.BooleanField(default=False)
    consultant_assigned = models.BooleanField(default=False)
    team_assigned = models.BooleanField(default=False)
    budget_set = models.BooleanField(default=False)
    timeline_set = models.BooleanField(default=False)
    baseline_created = models.BooleanField(default=False)
    boq_imported = models.BooleanField(default=False)
    ready = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def refresh_ready_status(self):
        self.ready = all([
            self.contractor_assigned,
            self.consultant_assigned,
            self.team_assigned,
            self.budget_set,
            self.timeline_set,
            self.baseline_created,
            self.boq_imported,
        ])
        return self.ready

    def __str__(self):
        return f"{self.project.name} readiness: {'Ready' if self.ready else 'Not Ready'}"


# ============================================================
# PROGRESS & SITE REPORTS
# ============================================================

class ProgressReport(models.Model):
    STATUS_CHOICES = [
        ('SUBMITTED', 'Submitted'),
        ('REVIEWER_REVIEWED', 'Reviewer Reviewed'),
        ('MANAGER_REVIEWED', 'Manager Reviewed'),
        ('CONSULTANT_REVIEWED', 'Consultant Reviewed'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='progress_reports')
    report_date = models.DateField()
    report_period = models.CharField(max_length=100, blank=True, null=True)
    overall_progress = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    civil_progress = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    architectural_progress = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    mep_progress = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    remarks = models.TextField(blank=True, null=True)
    prepared_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='SUBMITTED')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_progress_reports')
    approved_at = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-report_date']

    def __str__(self):
        return f"{self.project.name} - {self.report_date}"


class DailyReport(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('VERIFIED', 'Verified'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='daily_reports')
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submitted_reports')
    date = models.DateField()
    weather = models.CharField(max_length=50)
    work_done = models.TextField()
    issues = models.TextField(blank=True, null=True)
    progress_percentage = models.IntegerField(default=0)
    manpower_count = models.IntegerField(default=0)
    equipment_used = models.TextField(blank=True, null=True)
    materials_used = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.project.name} - {self.date}"


class ProgressPhoto(models.Model):
    daily_report = models.ForeignKey(DailyReport, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='progress_photos/%Y/%m/', blank=True, null=True)
    image_url = models.CharField(max_length=500, blank=True, null=True)
    caption = models.CharField(max_length=255, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo for {self.daily_report.project.name} on {self.daily_report.date}"


class DailyReportDocument(models.Model):
    daily_report = models.ForeignKey(DailyReport, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(upload_to='daily_report_documents/%Y/%m/')
    document_name = models.CharField(max_length=255, blank=True, null=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.document_name or f"Document for {self.daily_report.project.name} on {self.daily_report.date}"


class DailyReportWorkProgress(models.Model):
    daily_report = models.ForeignKey(DailyReport, on_delete=models.CASCADE, related_name='work_progress_items')
    work_item = models.ForeignKey('WorkItem', on_delete=models.PROTECT, related_name='daily_report_progress_items')
    actual_quantity = models.DecimalField(max_digits=15, decimal_places=4)
    unit = models.CharField(max_length=50, blank=True, null=True)
    item_progress_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    project_progress_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.daily_report} - {self.work_item.item_name} ({self.actual_quantity} {self.unit or ''})"


class DailyReportMaterialUsage(models.Model):
    daily_report = models.ForeignKey(DailyReport, on_delete=models.CASCADE, related_name='material_usages')
    material_item = models.ForeignKey('MaterialItem', on_delete=models.PROTECT, related_name='daily_report_usages')
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit = models.CharField(max_length=20, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    stock_transaction = models.ForeignKey(
        'StockTransaction', on_delete=models.SET_NULL, blank=True, null=True, related_name='daily_report_usages'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.daily_report} - {self.material_item.name} ({self.quantity} {self.unit or ''})"


class DailyReportManpowerUsage(models.Model):
    daily_report = models.ForeignKey(DailyReport, on_delete=models.CASCADE, related_name='manpower_usages')
    manpower = models.ForeignKey('Manpower', on_delete=models.PROTECT, related_name='daily_report_usages')
    role_snapshot = models.CharField(max_length=100, blank=True, null=True)
    hours_worked = models.DecimalField(max_digits=5, decimal_places=2, default=8)
    notes = models.TextField(blank=True, null=True)
    attendance = models.ForeignKey(
        'Attendance', on_delete=models.SET_NULL, blank=True, null=True, related_name='daily_report_usages'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.daily_report} - {self.manpower.name}"


class DailyReportEquipmentUsage(models.Model):
    daily_report = models.ForeignKey(DailyReport, on_delete=models.CASCADE, related_name='equipment_usage_details')
    equipment = models.ForeignKey('Equipment', on_delete=models.PROTECT, related_name='daily_report_usages')
    operator = models.ForeignKey(
        'Manpower', on_delete=models.SET_NULL, blank=True, null=True, related_name='daily_report_equipment_usages'
    )
    hours_used = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    activity = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    equipment_usage = models.ForeignKey(
        'EquipmentUsage', on_delete=models.SET_NULL, blank=True, null=True, related_name='daily_report_details'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.daily_report} - {self.equipment.name}"


class SiteActivity(models.Model):
    STATUS_CHOICES = [
        ('PLANNED', 'Planned'),
        ('IN_PROGRESS', 'In Progress'),
        ('DONE', 'Done'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='site_activities')
    activity_name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True, null=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    unit = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PLANNED')
    activity_date = models.DateField(blank=True, null=True)
    manpower = models.IntegerField(default=0)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.project.name} - {self.activity_name}"


# ============================================================
# WORK ITEMS (Work Items)
# ============================================================

class WorkItem(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='work_items')
    item_code = models.CharField(max_length=100, blank=True, null=True)
    item_name = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True, null=True)
    sub_category = models.CharField(max_length=100, blank=True, null=True)
    unit = models.CharField(max_length=50, blank=True, null=True)
    boq_quantity = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    unit_rate = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    boq_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    actual_quantity = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    actual_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    progress_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.project.name} - {self.item_name}"

    @property
    def description(self):
        return self.item_name

    @property
    def quantity(self):
        return self.boq_quantity

    @property
    def total_amount(self):
        return self.boq_amount



# ============================================================
# COST CONTROL MODULE
# ============================================================

class CostSummary(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='cost_summaries')
    category = models.CharField(max_length=100)
    sub_category = models.CharField(max_length=100, blank=True, null=True)
    budget = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    actual = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    committed = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    forecast = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    report_date = models.DateField(blank=True, null=True)

    def variance(self):
        return self.budget - self.actual

    def __str__(self):
        return f"{self.project.name} - {self.category}"


class VariationOrder(models.Model):
    STATUS_CHOICES = [
        ('SUBMITTED', 'Submitted'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('PENDING', 'Pending'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='variation_orders')
    vo_number = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='vo_requests')
    request_date = models.DateField(blank=True, null=True)
    requested_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    approved_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    time_impact = models.IntegerField(default=0, help_text='Days')
    justification = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='vo_approvals')
    approved_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"VO-{self.vo_number} | {self.project.name}"


class Invoice(models.Model):
    INVOICE_TYPE = [
        ('PROGRESS', 'Progress'),
        ('FINAL', 'Final'),
        ('ADVANCE', 'Advance'),
    ]
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('SITE_VERIFIED', 'Finance Site Verified'),
        ('HQ_REVIEWED', 'HQ Finance Reviewed'),
        ('APPROVED', 'Approved'),
        ('VERIFIED', 'Verified'),
        ('PAID', 'Paid'),
        ('REJECTED', 'Rejected'),
        ('OVERDUE', 'Overdue'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=100, unique=True)
    invoice_type = models.CharField(max_length=20, choices=INVOICE_TYPE, default='PROGRESS')
    claim_period = models.CharField(max_length=100, blank=True, null=True)
    amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    retention = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    due_date = models.DateField(blank=True, null=True)
    paid_date = models.DateField(blank=True, null=True)
    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    site_verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='site_verified_invoices')
    hq_reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='hq_reviewed_invoices')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_invoices')
    site_verified_at = models.DateTimeField(blank=True, null=True)
    hq_reviewed_at = models.DateTimeField(blank=True, null=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    attachment = models.FileField(upload_to='financial_documents/%Y/%m/', blank=True, null=True)

    def __str__(self):
        return f"{self.invoice_number} - {self.project.name}"


class FinancialRecord(models.Model):
    RECORD_TYPE_CHOICES = [
        ('EXPENSE', 'Expense'),
        ('PROGRESS_PAYMENT', 'Progress Payment'),
        ('SUBCONTRACTOR_PAYMENT', 'Subcontractor Payment'),
        ('PAYMENT', 'Payment'),
        ('BUDGET_REALISATION', 'Budget Realisation'),
    ]
    STATUS_CHOICES = [
        ('SUBMITTED', 'Submitted'),
        ('SITE_VERIFIED', 'Finance Site Verified'),
        ('HQ_REVIEWED', 'HQ Finance Reviewed'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('PAID', 'Paid'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='financial_records')
    record_type = models.CharField(max_length=30, choices=RECORD_TYPE_CHOICES, default='EXPENSE')
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    transaction_date = models.DateField(blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)
    payment_method = models.CharField(max_length=100, blank=True, null=True)
    attachment = models.FileField(upload_to='financial_documents/%Y/%m/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SUBMITTED')
    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='submitted_financial_records')
    site_verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='site_verified_financial_records')
    hq_reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='hq_reviewed_financial_records')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_financial_records')
    site_verified_at = models.DateTimeField(blank=True, null=True)
    hq_reviewed_at = models.DateTimeField(blank=True, null=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-transaction_date', '-created_at']

    def __str__(self):
        return f"{self.project.name} - {self.get_record_type_display()} - {self.amount}"


class FinancialRecordHistory(models.Model):
    financial_record = models.ForeignKey(FinancialRecord, on_delete=models.CASCADE, related_name='history')
    action = models.CharField(max_length=100, blank=True, null=True)
    from_status = models.CharField(max_length=30, blank=True, null=True)
    to_status = models.CharField(max_length=30, blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    action_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.financial_record} - {self.action or self.to_status}"


# ============================================================
# SCHEDULE
# ============================================================

class Schedule(models.Model):
    STATUS_CHOICES = [
        ('NOT_STARTED', 'Not Started'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('DELAYED', 'Delayed'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='schedules')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    activity_code = models.CharField(max_length=100, blank=True, null=True)
    activity_name = models.CharField(max_length=255)
    planned_start = models.DateField(blank=True, null=True)
    planned_finish = models.DateField(blank=True, null=True)
    actual_start = models.DateField(blank=True, null=True)
    actual_finish = models.DateField(blank=True, null=True)
    duration_planned = models.IntegerField(default=0)
    progress = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NOT_STARTED')

    def __str__(self):
        return f"{self.project.name} - {self.activity_name}"


# ============================================================
# QA/QC MODULE
# ============================================================

class QAQCInspection(models.Model):
    STATUS_CHOICES = [
        ('PASS', 'Pass'),
        ('FAIL', 'Fail'),
        ('HOLD', 'Hold'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='qaqc_inspections')
    inspector = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    inspection_type = models.CharField(max_length=100, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    item = models.CharField(max_length=255, blank=True, null=True)
    standard_reference = models.CharField(max_length=255, blank=True, null=True)
    result_value = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='HOLD')
    remarks = models.TextField(blank=True, null=True)
    inspection_date = models.DateField(blank=True, null=True)
    corrective_action = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.project.name} - {self.item} ({self.status})"


# ============================================================
# HSE MODULE
# ============================================================

class HSEReport(models.Model):
    REPORT_TYPE = [
        ('DAILY', 'Daily'),
        ('INCIDENT', 'Incident'),
        ('NEAR_MISS', 'Near Miss'),
        ('UNSAFE_ACT', 'Unsafe Act'),
        ('UNSAFE_CONDITION', 'Unsafe Condition'),
        ('AUDIT', 'Audit'),
    ]
    SEVERITY = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='hse_reports')
    reporter = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE, default='DAILY')
    incident_type = models.CharField(max_length=255, blank=True, null=True)
    severity = models.CharField(max_length=10, choices=SEVERITY, default='LOW')
    description = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    persons_involved = models.IntegerField(default=0)
    action_taken = models.TextField(blank=True, null=True)
    report_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.project.name} - HSE {self.report_type} ({self.report_date})"


# ============================================================
# MEETING MODULE
# ============================================================

class Meeting(models.Model):
    MEETING_TYPE = [
        ('SITE', 'Site Meeting'),
        ('MANAGEMENT', 'Management Meeting'),
        ('DESIGN', 'Design Meeting'),
        ('EMERGENCY', 'Emergency Meeting'),
        ('COORDINATION', 'Coordination Meeting'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='meetings')
    meeting_type = models.CharField(max_length=20, choices=MEETING_TYPE, default='SITE')
    meeting_title = models.CharField(max_length=255)
    meeting_date = models.DateField(blank=True, null=True)
    time_start = models.TimeField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    chairperson = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    minutes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.project.name} - {self.meeting_title}"


class MeetingAction(models.Model):
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('CLOSED', 'Closed'),
    ]
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='actions')
    action_item = models.TextField()
    responsible_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    responsible_name = models.CharField(max_length=255, blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)
    priority = models.CharField(max_length=10, default='MEDIUM')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Action: {self.action_item[:50]}"


# ============================================================
# DOCUMENT CONTROL
# ============================================================

class Document(models.Model):
    DOCUMENT_TYPE_CHOICES = [
        ('SHOP_DRAWING', 'Shop Drawing'),
        ('METHOD_STATEMENT', 'Method Statement'),
        ('RFI', 'RFI'),
        ('NCR', 'NCR'),
        ('MIR', 'MIR'),
        ('LETTER', 'Letter / Surat Proyek'),
        ('OTHER', 'Other'),
    ]
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('DC_REVIEW', 'Document Controller Reviewed'),
        ('CONSULTANT_REVIEW', 'Consultant Reviewed'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('REVISION_REQUIRED', 'Revision Required'),
        ('SUPERSEDED', 'Superseded'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=100, choices=DOCUMENT_TYPE_CHOICES, blank=True, null=True)
    document_number = models.CharField(max_length=100, blank=True, null=True)
    document_title = models.CharField(max_length=255, blank=True, null=True)
    revision = models.CharField(max_length=50, blank=True, null=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to='project_documents/%Y/%m/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='submitted_docs')
    dc_reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='dc_reviewed_docs')
    consultant_reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='consultant_reviewed_docs')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_docs')
    dc_reviewed_at = models.DateTimeField(blank=True, null=True)
    consultant_reviewed_at = models.DateTimeField(blank=True, null=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    parent_document = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='revision_documents')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document_number} - {self.document_title}"


class DocumentRevisionHistory(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='revision_history')
    action = models.CharField(max_length=100, blank=True, null=True)
    from_status = models.CharField(max_length=30, blank=True, null=True)
    to_status = models.CharField(max_length=30, blank=True, null=True)
    revision = models.CharField(max_length=50, blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    action_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.document.document_number} rev {self.revision or '-'}: {self.action or self.to_status}"


# ============================================================
# APPROVAL WORKFLOW
# ============================================================

class Approval(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('REVIEWED', 'Reviewed'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    STEP_CHOICES = [
        ('REVIEWER', 'Reviewer'),
        ('MANAGER', 'Manager'),
        ('CONSULTANT', 'Consultant'),
        ('HQ_APPROVAL', 'HQ Approval'),
        ('COMPLETED', 'Completed'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='approvals')
    module_type = models.CharField(max_length=100, help_text='e.g. daily_report, invoice, vo, document')
    reference_id = models.IntegerField()
    document_title = models.CharField(max_length=255, blank=True, null=True)
    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='submitted_approvals')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_approvals')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='final_approvals')
    reviewer_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewer_stage_approvals')
    manager_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='manager_stage_approvals')
    consultant_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='consultant_stage_approvals')
    hq_approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='hq_stage_approvals')
    current_step = models.CharField(max_length=30, choices=STEP_CHOICES, default='REVIEWER')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    comments = models.TextField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewer_at = models.DateTimeField(blank=True, null=True)
    manager_at = models.DateTimeField(blank=True, null=True)
    consultant_at = models.DateTimeField(blank=True, null=True)
    hq_approved_at = models.DateTimeField(blank=True, null=True)
    approved_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Approval: {self.module_type} #{self.reference_id} ({self.status})"


class ApprovalStepHistory(models.Model):
    approval = models.ForeignKey(Approval, on_delete=models.CASCADE, related_name='step_history')
    from_step = models.CharField(max_length=30, blank=True, null=True)
    to_step = models.CharField(max_length=30, blank=True, null=True)
    action = models.CharField(max_length=50)
    comments = models.TextField(blank=True, null=True)
    action_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.approval} - {self.action}: {self.from_step} -> {self.to_step}"


# ============================================================
# RISK REGISTER
# ============================================================

class RiskRegister(models.Model):
    PROBABILITY = [('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High')]
    IMPACT = [('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High')]
    STATUS = [('OPEN', 'Open'), ('MITIGATED', 'Mitigated'), ('CLOSED', 'Closed')]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='risks')
    risk_code = models.CharField(max_length=50, blank=True, null=True)
    risk_description = models.TextField()
    category = models.CharField(max_length=100, blank=True, null=True)
    probability = models.CharField(max_length=10, choices=PROBABILITY, default='MEDIUM')
    impact = models.CharField(max_length=10, choices=IMPACT, default='MEDIUM')
    risk_level = models.CharField(max_length=10, default='MEDIUM')
    mitigation_plan = models.TextField(blank=True, null=True)
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS, default='OPEN')
    identified_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.project.name} - {self.risk_code}: {self.risk_description[:50]}"


# ============================================================
# NEW WORKFLOW ALIGNMENTS (MATERIAL, BIM, IPC)
# ============================================================

class MaterialTest(models.Model):
    STATUS_CHOICES = [
        ('PASS', 'Pass'),
        ('FAIL', 'Fail'),
        ('PENDING', 'Pending'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='material_tests')
    material_name = models.CharField(max_length=255)
    test_type = models.CharField(max_length=100)
    sample_location = models.CharField(max_length=255, blank=True, null=True)
    test_date = models.DateField(blank=True, null=True)
    lab_name = models.CharField(max_length=255, blank=True, null=True)
    result_value = models.CharField(max_length=100, blank=True, null=True)
    standard_value = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.project.name} - Test: {self.material_name} ({self.status})"


class MaterialRequest(models.Model):
    STATUS_CHOICES = [
        ('SUBMITTED', 'Submitted'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('DELIVERED', 'Delivered'),
        ('RECEIVED', 'Received'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='material_requests')
    material_item = models.ForeignKey(
        'MaterialItem', on_delete=models.SET_NULL, null=True, blank=True, related_name='material_requests'
    )
    request_number = models.CharField(max_length=100, blank=True, null=True)
    material_name = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit = models.CharField(max_length=50)
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='requested_materials')
    requested_date = models.DateField(auto_now_add=True)
    required_date = models.DateField(blank=True, null=True)
    approved_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    delivered_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    received_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_material_requests')
    delivered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='delivered_material_requests')
    received_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_material_requests')
    approved_date = models.DateField(blank=True, null=True)
    delivered_date = models.DateField(blank=True, null=True)
    received_date = models.DateField(blank=True, null=True)
    delivery_reference = models.CharField(max_length=100, blank=True, null=True)
    supplier_name = models.CharField(max_length=255, blank=True, null=True)
    receiving_location = models.CharField(max_length=100, blank=True, null=True)
    stock_transaction = models.ForeignKey(
        'StockTransaction', on_delete=models.SET_NULL, null=True, blank=True, related_name='material_request_receipts'
    )
    rejection_reason = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SUBMITTED')
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Req: {self.material_name} x {self.quantity} {self.unit} ({self.status})"


class PurchaseRequest(models.Model):
    STATUS_CHOICES = [
        ('SUBMITTED', 'Submitted'),
        ('REVIEWER_REVIEWED', 'Reviewer Reviewed'),
        ('MANAGER_REVIEWED', 'Manager Reviewed'),
        ('CONSULTANT_REVIEWED', 'Consultant Reviewed'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='purchase_requests')
    material_request = models.ForeignKey(MaterialRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchase_requests')
    purchase_number = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField()
    supplier_name = models.CharField(max_length=255, blank=True, null=True)
    amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    required_date = models.DateField(blank=True, null=True)
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='requested_purchases')
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewer_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_purchase_requests')
    manager_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_purchase_requests')
    consultant_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='consulted_purchase_requests')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_purchase_requests')
    reviewer_at = models.DateTimeField(blank=True, null=True)
    manager_at = models.DateTimeField(blank=True, null=True)
    consultant_at = models.DateTimeField(blank=True, null=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='SUBMITTED')
    rejection_reason = models.TextField(blank=True, null=True)
    attachment = models.FileField(upload_to='purchase_documents/%Y/%m/', blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.purchase_number or self.id} - {self.project.name} ({self.status})"


class MaterialWaste(models.Model):
    REASON_CHOICES = [
        ('DAMAGE', 'Damage'),
        ('CUTTING_LOSS', 'Cutting Loss'),
        ('OVERUSE', 'Overuse'),
        ('QUALITY_REJECT', 'Quality Reject'),
        ('EXPIRED', 'Expired'),
        ('OTHER', 'Other'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='material_wastes')
    material_item = models.ForeignKey('MaterialItem', on_delete=models.CASCADE, related_name='waste_records')
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=30, choices=REASON_CHOICES, default='OTHER')
    location = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    waste_date = models.DateField(blank=True, null=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    stock_transaction = models.ForeignKey(
        'StockTransaction', on_delete=models.SET_NULL, null=True, blank=True, related_name='waste_records'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-waste_date', '-created_at']

    def __str__(self):
        return f"Waste: {self.material_item.name} - {self.quantity} {self.material_item.unit}"


class BIMModel(models.Model):
    DISCIPLINE_CHOICES = [
        ('ARCH', 'Architectural'),
        ('STRUCT', 'Structural'),
        ('MEP', 'MEP'),
        ('INFRA', 'Infrastructure'),
        ('LANDSCAPE', 'Landscape'),
    ]
    STATUS_CHOICES = [
        ('WIP', 'Work In Progress'),
        ('REVIEW', 'In Review'),
        ('APPROVED', 'Approved'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='bim_models')
    model_name = models.CharField(max_length=255)
    discipline = models.CharField(max_length=20, choices=DISCIPLINE_CHOICES)
    lod_level = models.CharField(max_length=50, default='LOD 300')
    version = models.CharField(max_length=50, default='v1.0')
    file_path = models.CharField(max_length=500, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='WIP')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.model_name} ({self.discipline})"


class BIMClash(models.Model):
    SEVERITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
    ]
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('IN_REVIEW', 'In Review'),
        ('RESOLVED', 'Resolved'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='bim_clashes')
    bim_model = models.ForeignKey(BIMModel, on_delete=models.CASCADE, related_name='clashes', blank=True, null=True)
    clash_type = models.CharField(max_length=50, default='HARD')
    description = models.TextField()
    discipline_a = models.CharField(max_length=50)
    discipline_b = models.CharField(max_length=50)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='MEDIUM')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    detected_date = models.DateField(blank=True, null=True)
    resolved_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"Clash: {self.discipline_a} vs {self.discipline_b} ({self.status})"


class InterimPaymentCertificate(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Certificate'),
        ('CERTIFIED', 'Certified'),
        ('REJECTED', 'Rejected'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='ipcs')
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='ipcs', blank=True, null=True)
    ipc_number = models.CharField(max_length=100)
    claimed_amount = models.DecimalField(max_digits=20, decimal_places=2)
    verified_amount = models.DecimalField(max_digits=20, decimal_places=2)
    deduction = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    certified_amount = models.DecimalField(max_digits=20, decimal_places=2)
    remarks = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    certified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    certified_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"IPC: {self.ipc_number} - {self.status}"


# ============================================================
# INVENTORY / STOCK MANAGEMENT  (Phase F - Material Control)
# ============================================================

class MaterialItem(models.Model):
    """Katalog master material/barang yang tersedia."""
    UNIT_CHOICES = [
        ('m', 'Meter (m)'), ('m2', 'Square Meter (m2)'), ('m3', 'Cubic Meter (m3)'),
        ('kg', 'Kilogram (kg)'), ('ton', 'Ton'), ('unit', 'Unit'), ('pcs', 'Pieces'),
        ('ltr', 'Liter (ltr)'), ('sak', 'Sak'), ('roll', 'Roll'), ('ls', 'Lump Sum'),
    ]
    CATEGORY_CHOICES = [
        ('STRUKTUR', 'Structure'),
        ('FINISHING', 'Finishing'),
        ('MEP', 'MEP'),
        ('ALAT', 'Tools & Equipment'),
        ('LAIN', 'Other'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='material_items')
    item_code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default='unit')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='LAIN')
    minimum_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                        help_text="Minimum stock threshold before notification")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('project', 'item_code')
        ordering = ['category', 'name']

    def __str__(self):
        return f"[{self.item_code}] {self.name}"

    @property
    def current_stock(self):
        """Calculate current stock balance from all transactions."""
        from django.db.models import Sum
        masuk = self.transactions.filter(transaction_type='IN').aggregate(
            total=Sum('quantity'))['total'] or 0
        keluar = self.transactions.filter(transaction_type='OUT').aggregate(
            total=Sum('quantity'))['total'] or 0
        return masuk - keluar

    @property
    def is_low_stock(self):
        return self.current_stock <= self.minimum_stock


class StockTransaction(models.Model):
    """Every material stock in/out transaction."""
    TRANSACTION_TYPE = [
        ('IN', 'Material In (Delivery)'),
        ('OUT', 'Material Out (Usage)'),
        ('ADJUST', 'Stock Adjustment'),
        ('RETURN', 'Return to Supplier'),
    ]
    material_item = models.ForeignKey(MaterialItem, on_delete=models.CASCADE, related_name='transactions')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='stock_transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    reference_number = models.CharField(max_length=100, blank=True, null=True,
                                         help_text="Delivery Note / DO / PO No.")
    supplier_name = models.CharField(max_length=255, blank=True, null=True)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True,
                                 help_text="Usage location / warehouse")
    notes = models.TextField(blank=True, null=True)
    transaction_date = models.DateField()
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-transaction_date', '-created_at']

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.material_item.name} ({self.quantity})"

    @property
    def total_value(self):
        if self.unit_price:
            return self.quantity * self.unit_price
        return None


class LogisticsRecord(models.Model):
    """Logistics records for delivery, receiving, issue, return, and material transfer."""
    RECORD_TYPE_CHOICES = [
        ('DELIVERY_TRACKING', 'Delivery Tracking'),
        ('MATERIAL_RECEIVING', 'Material Receiving'),
        ('STOCK_ISSUE', 'Stock Issue to Site'),
        ('STOCK_RETURN', 'Return to Supplier'),
        ('STOCK_TRANSFER', 'Transfer Material'),
    ]
    STATUS_CHOICES = [
        ('PLANNED', 'Planned'),
        ('ON_DELIVERY', 'On Delivery'),
        ('RECEIVED', 'Received'),
        ('ISSUED', 'Issued'),
        ('RETURNED', 'Returned'),
        ('TRANSFERRED', 'Transferred'),
        ('DAMAGED', 'Damaged / Rejected'),
        ('CANCELLED', 'Cancelled'),
    ]
    CONDITION_CHOICES = [
        ('GOOD', 'Good'),
        ('PARTIAL', 'Partial'),
        ('DAMAGED', 'Damaged'),
        ('REJECTED', 'Rejected'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='logistics_records')
    material_request = models.ForeignKey(
        MaterialRequest, on_delete=models.SET_NULL, blank=True, null=True, related_name='logistics_records'
    )
    material_item = models.ForeignKey(
        MaterialItem, on_delete=models.SET_NULL, blank=True, null=True, related_name='logistics_records'
    )
    stock_transaction = models.ForeignKey(
        StockTransaction, on_delete=models.SET_NULL, blank=True, null=True, related_name='logistics_records'
    )
    record_type = models.CharField(max_length=30, choices=RECORD_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PLANNED')
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit = models.CharField(max_length=50, blank=True, null=True)
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    supplier_name = models.CharField(max_length=255, blank=True, null=True)
    from_location = models.CharField(max_length=150, blank=True, null=True)
    to_location = models.CharField(max_length=150, blank=True, null=True)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='GOOD')
    scheduled_date = models.DateField(blank=True, null=True)
    actual_date = models.DateField(blank=True, null=True)
    handled_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='logistics_records')
    attachment = models.FileField(upload_to='logistics_documents/%Y/%m/', blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-actual_date', '-created_at']

    def __str__(self):
        material_name = self.material_item.name if self.material_item else self.material_request.material_name if self.material_request else 'Material'
        return f"{self.get_record_type_display()} - {material_name} ({self.quantity} {self.unit or ''})"


# =====================================
# RFI (Request for Information)
# =====================================
class RFI(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('IN_REVIEW', 'In Review'),
        ('RESPONDED', 'Responded'),
        ('CLOSED', 'Closed'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='rfis')
    rfi_number = models.CharField(max_length=100, unique=True)
    subject = models.CharField(max_length=255)
    description = models.TextField()
    raised_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='rfis_raised')
    raised_date = models.DateField(auto_now_add=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='rfis_assigned')
    response = models.TextField(blank=True, null=True)
    response_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.rfi_number} - {self.subject}"


# =====================================
# NCR (Non-Conformance Report)
# =====================================
class NCR(models.Model):
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('UNDER_REVIEW', 'Under Review'),
        ('CORRECTIVE_ACTION', 'Corrective Action'),
        ('VERIFIED', 'Verified'),
        ('CLOSED', 'Closed'),
    ]
    SEVERITY_CHOICES = [
        ('MINOR', 'Minor'),
        ('MAJOR', 'Major'),
        ('CRITICAL', 'Critical'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='ncrs')
    ncr_number = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    location = models.CharField(max_length=255, blank=True, null=True)
    reported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='ncrs_reported')
    reported_date = models.DateField(auto_now_add=True)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='MAJOR')
    root_cause = models.TextField(blank=True, null=True)
    corrective_action = models.TextField(blank=True, null=True)
    corrective_action_date = models.DateField(blank=True, null=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='ncrs_verified')
    verified_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')

    def __str__(self):
        return f"{self.ncr_number} - {self.status}"


# =====================================
# Site Instruction
# =====================================
class SiteInstruction(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('ISSUED', 'Issued'),
        ('ACKNOWLEDGED', 'Acknowledged'),
        ('IMPLEMENTED', 'Implemented'),
        ('CLOSED', 'Closed'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='site_instructions')
    si_number = models.CharField(max_length=100, unique=True)
    subject = models.CharField(max_length=255)
    instruction = models.TextField()
    issued_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='si_issued')
    issued_date = models.DateField(auto_now_add=True)
    issued_to = models.CharField(max_length=255)
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='si_acknowledged')
    acknowledged_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.si_number} - {self.subject}"


# =====================================
# Manpower & Staff
# =====================================
class Manpower(models.Model):
    ROLE_CHOICES = [
        ('WORKER', 'Field Worker'),
        ('FOREMAN', 'Foreman'),
        ('OPERATOR', 'Equipment Operator'),
        ('TECHNICIAN', 'Technician'),
        ('ADMIN', 'Site Admin'),
        ('OTHER', 'Other'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='manpowers')
    nik = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='WORKER')
    phone = models.CharField(max_length=50, blank=True, null=True)
    join_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    photo = models.ImageField(upload_to='manpower_photos/', blank=True, null=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.nik} - {self.name}"


# =====================================
# Attendance / Absensi
# =====================================
class Attendance(models.Model):
    STATUS_CHOICES = [
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
        ('SICK', 'Sick'),
        ('LEAVE', 'Leave'),
        ('LATE', 'Late'),
    ]
    manpower = models.ForeignKey(Manpower, on_delete=models.CASCADE, related_name='attendances')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    check_in = models.TimeField(blank=True, null=True)
    check_out = models.TimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PRESENT')
    notes = models.TextField(blank=True, null=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='recorded_attendances')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['manpower', 'date']
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.manpower.name} - {self.date} ({self.get_status_display()})"


# =====================================
# Equipment / Alat
# =====================================
class Equipment(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('MAINTENANCE', 'Under Maintenance'),
        ('REPAIR', 'Under Repair'),
        ('RENTED', 'Rented'),
    ]
    CATEGORY_CHOICES = [
        ('EXCAVATOR', 'Excavator'),
        ('BULLDOZER', 'Bulldozer'),
        ('CRANE', 'Crane'),
        ('CONCRETE_MIXER', 'Concrete Mixer'),
        ('COMPACTOR', 'Compactor'),
        ('TRUCK', 'Truck'),
        ('GENERATOR', 'Generator'),
        ('WELDING', 'Welding Machine'),
        ('OTHER', 'Other'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='equipments')
    equipment_code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='OTHER')
    brand = models.CharField(max_length=255, blank=True, null=True)
    model = models.CharField(max_length=255, blank=True, null=True)
    serial_number = models.CharField(max_length=255, blank=True, null=True)
    year = models.IntegerField(blank=True, null=True)
    purchase_date = models.DateField(blank=True, null=True)
    purchase_value = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    location = models.CharField(max_length=255, blank=True, null=True)
    operator = models.ForeignKey(Manpower, on_delete=models.SET_NULL, null=True, blank=True, related_name='operated_equipments')
    photo = models.ImageField(upload_to='equipment_photos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"[{self.equipment_code}] {self.name}"


class EquipmentUsage(models.Model):
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='usages')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='equipment_usages')
    usage_date = models.DateField()
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    hours_used = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    activity = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    operator = models.ForeignKey(Manpower, on_delete=models.SET_NULL, null=True, blank=True)
    fuel_used = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-usage_date', '-created_at']

    def __str__(self):
        return f"{self.equipment.name} - {self.usage_date}"


class EquipmentMaintenance(models.Model):
    TYPE_CHOICES = [
        ('SCHEDULED', 'Scheduled Maintenance'),
        ('UNSCHEDULED', 'Unscheduled Maintenance'),
        ('REPAIR', 'Repair'),
        ('OVERHAUL', 'Overhaul'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
    ]
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='maintenances')
    maintenance_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='SCHEDULED')
    maintenance_date = models.DateField()
    description = models.TextField()
    cost = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    vendor = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    next_maintenance_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-maintenance_date', '-created_at']

    def __str__(self):
        return f"Maintenance {self.equipment.name} - {self.maintenance_date}"


# =====================================
# Notifications / Notifikasi
# =====================================
class RoleReport(models.Model):
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    STATUS_CHOICES = [
        ('SUBMITTED', 'Submitted'),
        ('REVIEWED', 'Reviewed'),
        ('CLOSED', 'Closed'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='role_reports')
    reporter = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='role_reports')
    reporter_role = models.CharField(max_length=30, blank=True, null=True)
    report_type = models.CharField(max_length=100)
    title = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=255, blank=True, null=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SUBMITTED')
    report_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-report_date', '-created_at']

    def __str__(self):
        return f"{self.project.name} - {self.report_type}: {self.title}"


class ItemProgressReport(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='item_progress_reports', blank=True, null=True)
    source_name = models.CharField(max_length=255, default='Progress Report Church Iliomar Versi 1.xlsx')
    source_sheet = models.CharField(max_length=255, default='Construction Progress Report')
    source_row = models.PositiveIntegerField()
    item_no = models.PositiveIntegerField(blank=True, null=True)
    activity = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    progress_percent = models.DecimalField(max_digits=7, decimal_places=3, default=0)
    status = models.CharField(max_length=50, blank=True, null=True)
    photo_note = models.TextField(blank=True, null=True)
    photos = models.ManyToManyField('ProgressPhoto', blank=True, related_name='item_reports')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('project', 'source_name', 'source_sheet', 'source_row')
        ordering = ['source_row']

    def __str__(self):
        number = f"{self.item_no}. " if self.item_no else ''
        project_name = f"{self.project.name} - " if self.project else ''
        return f"{project_name}{number}{self.activity} - {self.progress_percent}%"


class Notification(models.Model):
    TYPE_CHOICES = [
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('SUCCESS', 'Success'),
        ('ALERT', 'Important Alert'),
    ]
    STATUS_CHOICES = [
        ('UNREAD', 'Unread'),
        ('READ', 'Read'),
    ]
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='INFO')
    title = models.CharField(max_length=255)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UNREAD')
    related_module = models.CharField(max_length=100, blank=True, null=True)  # e.g., 'daily_report', 'invoice'
    related_id = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.title[:50]}"


# =====================================
# Internal Chat System
# =====================================
class ChatRoom(models.Model):
    TYPE_CHOICES = [
        ('DIRECT', 'Direct Message'),
        ('GROUP', 'Group Chat'),
        ('PROJECT', 'Project Chat'),
    ]
    name = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='DIRECT')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, blank=True, null=True, related_name='chat_rooms')
    participants = models.ManyToManyField(User, related_name='chat_rooms')
    is_public = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_chat_rooms')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        if self.type == 'PROJECT' and self.project:
            return f"Chat Proyek: {self.project.name}"
        if self.name:
            return f"Chat: {self.name}"
        participants_list = ", ".join([u.username for u in self.participants.all()[:3]])
        return f"Chat: {participants_list}"


class ChatMessage(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_messages')
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Pesan dari {self.sender.username}: {self.content[:50]}"



