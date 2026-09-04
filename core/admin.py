from django.contrib import admin
from .models import (
    UserProfile, Company, Project, ProjectReadinessChecklist, DailyReport, ProgressPhoto, DailyReportDocument,
    DailyReportWorkProgress, DailyReportMaterialUsage, DailyReportManpowerUsage, DailyReportEquipmentUsage,
    Document, DocumentRevisionHistory, FinancialRecord, FinancialRecordHistory,
    Approval, ApprovalStepHistory, MaterialRequest, PurchaseRequest, MaterialItem, MaterialWaste, StockTransaction, LogisticsRecord, RFI, NCR, SiteInstruction,
    Manpower, Attendance, Equipment, EquipmentUsage,
    EquipmentMaintenance, Notification, Vendor, Subcontractor,
    ChatRoom, ChatMessage, RoleReport, ItemProgressReport
)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'user', 'role', 'position', 'division', 'phone', 'status')
    list_filter = ('role', 'division', 'status')
    search_fields = ('employee_id', 'user__username', 'user__first_name', 'user__last_name', 'position', 'phone')

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'status', 'contractor', 'consultant', 'budget', 'start_date', 'end_date')
    list_filter = ('status', 'contractor', 'consultant')
    search_fields = ('name', 'location', 'contractor__company_name', 'consultant__company_name')

@admin.register(ProjectReadinessChecklist)
class ProjectReadinessChecklistAdmin(admin.ModelAdmin):
    list_display = (
        'project', 'contractor_assigned', 'consultant_assigned', 'team_assigned',
        'budget_set', 'timeline_set', 'baseline_created', 'boq_imported', 'ready'
    )
    list_filter = ('ready', 'contractor_assigned', 'consultant_assigned', 'team_assigned', 'boq_imported')

@admin.register(DailyReport)
class DailyReportAdmin(admin.ModelAdmin):
    list_display = ('project', 'reporter', 'date', 'weather', 'progress_percentage', 'status')
    list_filter = ('status', 'weather', 'project')
    search_fields = ('work_done', 'issues')

@admin.register(ProgressPhoto)
class ProgressPhotoAdmin(admin.ModelAdmin):
    list_display = ('daily_report', 'caption')


@admin.register(DailyReportDocument)
class DailyReportDocumentAdmin(admin.ModelAdmin):
    list_display = ('daily_report', 'document_name', 'uploaded_by', 'uploaded_at')
    search_fields = ('document_name', 'daily_report__project__name')


@admin.register(DailyReportWorkProgress)
class DailyReportWorkProgressAdmin(admin.ModelAdmin):
    list_display = (
        'daily_report', 'work_item', 'actual_quantity', 'unit',
        'item_progress_percent', 'project_progress_percent', 'created_at'
    )
    list_filter = ('daily_report__project', 'work_item__category')
    search_fields = ('work_item__item_name', 'work_item__item_code', 'daily_report__project__name')


@admin.register(DailyReportMaterialUsage)
class DailyReportMaterialUsageAdmin(admin.ModelAdmin):
    list_display = ('daily_report', 'material_item', 'quantity', 'unit', 'stock_transaction', 'created_at')
    list_filter = ('daily_report__project', 'material_item__category')
    search_fields = ('material_item__name', 'daily_report__project__name', 'notes')


@admin.register(DailyReportManpowerUsage)
class DailyReportManpowerUsageAdmin(admin.ModelAdmin):
    list_display = ('daily_report', 'manpower', 'role_snapshot', 'hours_worked', 'attendance', 'created_at')
    list_filter = ('daily_report__project', 'manpower__role')
    search_fields = ('manpower__name', 'manpower__nik', 'daily_report__project__name', 'notes')


@admin.register(DailyReportEquipmentUsage)
class DailyReportEquipmentUsageAdmin(admin.ModelAdmin):
    list_display = ('daily_report', 'equipment', 'operator', 'hours_used', 'equipment_usage', 'created_at')
    list_filter = ('daily_report__project', 'equipment__category')
    search_fields = ('equipment__name', 'equipment__equipment_code', 'daily_report__project__name', 'notes')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        'document_number', 'document_title', 'project', 'document_type', 'revision',
        'status', 'submitted_by', 'dc_reviewed_by', 'consultant_reviewed_by', 'approved_by'
    )
    list_filter = ('status', 'document_type', 'project')
    search_fields = ('document_number', 'document_title', 'project__name')


@admin.register(DocumentRevisionHistory)
class DocumentRevisionHistoryAdmin(admin.ModelAdmin):
    list_display = ('document', 'revision', 'action', 'from_status', 'to_status', 'action_by', 'created_at')
    list_filter = ('to_status', 'action')
    search_fields = ('document__document_number', 'document__document_title', 'comments')


@admin.register(FinancialRecord)
class FinancialRecordAdmin(admin.ModelAdmin):
    list_display = (
        'project', 'record_type', 'reference_number', 'category', 'amount', 'status',
        'submitted_by', 'site_verified_by', 'hq_reviewed_by', 'approved_by'
    )
    list_filter = ('status', 'record_type', 'project', 'category')
    search_fields = ('reference_number', 'description', 'project__name')


@admin.register(FinancialRecordHistory)
class FinancialRecordHistoryAdmin(admin.ModelAdmin):
    list_display = ('financial_record', 'action', 'from_status', 'to_status', 'action_by', 'created_at')
    list_filter = ('action', 'to_status')
    search_fields = ('financial_record__reference_number', 'financial_record__description', 'comments')


@admin.register(Approval)
class ApprovalAdmin(admin.ModelAdmin):
    list_display = (
        'project', 'module_type', 'document_title', 'current_step',
        'status', 'submitted_by', 'reviewer_by', 'manager_by',
        'consultant_by', 'hq_approved_by'
    )
    list_filter = ('module_type', 'current_step', 'status', 'project')
    search_fields = ('document_title', 'comments', 'rejection_reason')


@admin.register(ApprovalStepHistory)
class ApprovalStepHistoryAdmin(admin.ModelAdmin):
    list_display = ('approval', 'from_step', 'to_step', 'action', 'action_by', 'created_at')
    list_filter = ('action', 'from_step', 'to_step')
    search_fields = ('approval__document_title', 'comments')


@admin.register(MaterialItem)
class MaterialItemAdmin(admin.ModelAdmin):
    list_display = ('item_code', 'name', 'project', 'unit', 'category', 'minimum_stock', 'current_stock_display')
    list_filter = ('category', 'project')
    search_fields = ('item_code', 'name')

    def current_stock_display(self, obj):
        stock = obj.current_stock
        return f"{stock} {obj.unit}"
    current_stock_display.short_description = 'Stok Saat Ini'


@admin.register(MaterialRequest)
class MaterialRequestAdmin(admin.ModelAdmin):
    list_display = (
        'request_number', 'project', 'material_name', 'quantity', 'unit', 'status',
        'requested_by', 'approved_by', 'delivered_by', 'received_by'
    )
    list_filter = ('status', 'project', 'required_date')
    search_fields = ('request_number', 'material_name', 'remarks')


@admin.register(PurchaseRequest)
class PurchaseRequestAdmin(admin.ModelAdmin):
    list_display = (
        'purchase_number', 'project', 'supplier_name', 'amount', 'status',
        'requested_by', 'reviewer_by', 'manager_by', 'consultant_by', 'approved_by'
    )
    list_filter = ('status', 'project', 'submitted_at')
    search_fields = ('purchase_number', 'description', 'supplier_name', 'remarks')


@admin.register(MaterialWaste)
class MaterialWasteAdmin(admin.ModelAdmin):
    list_display = ('waste_date', 'project', 'material_item', 'quantity', 'reason', 'recorded_by')
    list_filter = ('reason', 'project', 'waste_date')
    search_fields = ('material_item__name', 'notes', 'location')


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_date', 'material_item', 'project', 'transaction_type',
                    'quantity', 'reference_number', 'supplier_name', 'recorded_by')
    list_filter = ('transaction_type', 'project', 'transaction_date')
    search_fields = ('material_item__name', 'reference_number', 'supplier_name')
    date_hierarchy = 'transaction_date'


@admin.register(LogisticsRecord)
class LogisticsRecordAdmin(admin.ModelAdmin):
    list_display = (
        'actual_date', 'project', 'record_type', 'status', 'material_item',
        'quantity', 'unit', 'reference_number', 'condition', 'handled_by'
    )
    list_filter = ('record_type', 'status', 'condition', 'project', 'actual_date')
    search_fields = ('reference_number', 'supplier_name', 'remarks', 'material_item__name', 'material_request__material_name')
    date_hierarchy = 'actual_date'


@admin.register(RFI)
class RFIAdmin(admin.ModelAdmin):
    list_display = ('rfi_number', 'subject', 'project', 'raised_by', 'status', 'raised_date')
    list_filter = ('status', 'project')
    search_fields = ('rfi_number', 'subject', 'description')
    date_hierarchy = 'raised_date'


@admin.register(NCR)
class NCRAdmin(admin.ModelAdmin):
    list_display = ('ncr_number', 'project', 'severity', 'status', 'reported_by', 'reported_date')
    list_filter = ('status', 'severity', 'project')
    search_fields = ('ncr_number', 'description')
    date_hierarchy = 'reported_date'


@admin.register(SiteInstruction)
class SiteInstructionAdmin(admin.ModelAdmin):
    list_display = ('si_number', 'subject', 'project', 'issued_by', 'status', 'issued_date')
    list_filter = ('status', 'project')
    search_fields = ('si_number', 'subject', 'instruction')
    date_hierarchy = 'issued_date'


@admin.register(Manpower)
class ManpowerAdmin(admin.ModelAdmin):
    list_display = ('nik', 'name', 'role', 'project', 'phone', 'is_active', 'join_date')
    list_filter = ('role', 'is_active', 'project')
    search_fields = ('nik', 'name', 'phone')
    date_hierarchy = 'join_date'


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('manpower', 'project', 'date', 'check_in', 'check_out', 'status', 'recorded_by', 'created_at')
    list_filter = ('status', 'date', 'project')
    search_fields = ('manpower__name', 'manpower__nik', 'notes')
    date_hierarchy = 'date'
    readonly_fields = ('created_at',)


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('equipment_code', 'name', 'category', 'project', 'status', 'operator', 'created_at')
    list_filter = ('category', 'status', 'project')
    search_fields = ('equipment_code', 'name', 'brand', 'model', 'serial_number')
    date_hierarchy = 'created_at'


@admin.register(EquipmentUsage)
class EquipmentUsageAdmin(admin.ModelAdmin):
    list_display = ('equipment', 'project', 'usage_date', 'hours_used', 'operator', 'recorded_by', 'created_at')
    list_filter = ('equipment', 'project', 'usage_date')
    search_fields = ('equipment__name', 'activity', 'notes')
    date_hierarchy = 'usage_date'
    readonly_fields = ('created_at',)


@admin.register(EquipmentMaintenance)
class EquipmentMaintenanceAdmin(admin.ModelAdmin):
    list_display = ('equipment', 'maintenance_type', 'maintenance_date', 'status', 'cost', 'recorded_by', 'created_at')
    list_filter = ('maintenance_type', 'status', 'equipment')
    search_fields = ('equipment__name', 'description', 'vendor', 'notes')
    date_hierarchy = 'maintenance_date'
    readonly_fields = ('created_at',)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'company_type', 'contact_person', 'phone', 'email', 'created_at')
    list_filter = ('company_type',)
    search_fields = ('company_name', 'contact_person', 'email', 'phone')
    date_hierarchy = 'created_at'


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ('vendor_code', 'company', 'material_types', 'is_active', 'created_at')
    list_filter = ('is_active', 'company')
    search_fields = ('vendor_code', 'company__company_name', 'material_types')
    date_hierarchy = 'created_at'


@admin.register(Subcontractor)
class SubcontractorAdmin(admin.ModelAdmin):
    list_display = ('subcontractor_code', 'company', 'specialization', 'is_active', 'created_at')
    list_filter = ('is_active', 'company')
    search_fields = ('subcontractor_code', 'company__company_name', 'specialization')
    date_hierarchy = 'created_at'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'notification_type', 'title', 'status', 'created_at')
    list_filter = ('notification_type', 'status', 'recipient')
    search_fields = ('title', 'message')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)


@admin.register(RoleReport)
class RoleReportAdmin(admin.ModelAdmin):
    list_display = ('report_date', 'project', 'report_type', 'title', 'reporter', 'reporter_role', 'priority', 'status')
    list_filter = ('report_type', 'reporter_role', 'priority', 'status', 'project')
    search_fields = ('title', 'description', 'location', 'project__name', 'reporter__username')
    date_hierarchy = 'report_date'
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ItemProgressReport)
class ItemProgressReportAdmin(admin.ModelAdmin):
    list_display = ('item_no', 'project', 'activity', 'location', 'progress_percent', 'status', 'source_row')
    list_filter = ('status', 'source_sheet', 'project')
    search_fields = ('activity', 'location', 'description', 'source_name', 'project__name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'project', 'is_public', 'created_by', 'created_at', 'updated_at')
    list_filter = ('type', 'project', 'is_public')
    search_fields = ('name',)
    filter_horizontal = ('participants',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('room', 'sender', 'content', 'is_read', 'created_at')
    list_filter = ('is_read', 'room', 'sender')
    search_fields = ('content',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)
