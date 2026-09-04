from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    UserProfile, Company, Project, ProjectTeam, ProgressReport, DailyReport,
    ProgressPhoto, DailyReportDocument, SiteActivity, WorkItem, CostSummary, VariationOrder,
    Invoice, FinancialRecord, FinancialRecordHistory, Schedule, QAQCInspection, HSEReport, Meeting, MeetingAction,
    Document, Approval, ApprovalStepHistory, RiskRegister, MaterialTest, MaterialRequest,
    PurchaseRequest,
    MaterialWaste, BIMModel, BIMClash, InterimPaymentCertificate, MaterialItem,
    LogisticsRecord,
    StockTransaction, RFI, NCR, SiteInstruction, Manpower, Attendance,
    Equipment, EquipmentUsage, EquipmentMaintenance, Notification, Vendor,
    Subcontractor, ChatRoom, ChatMessage
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = UserProfile
        fields = '__all__'


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'


class VendorSerializer(serializers.ModelSerializer):
    company = CompanySerializer(read_only=True)

    class Meta:
        model = Vendor
        fields = '__all__'


class SubcontractorSerializer(serializers.ModelSerializer):
    company = CompanySerializer(read_only=True)

    class Meta:
        model = Subcontractor
        fields = '__all__'


class ProjectSerializer(serializers.ModelSerializer):
    company = CompanySerializer(read_only=True)

    class Meta:
        model = Project
        fields = '__all__'


class ProjectTeamSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)
    user = UserSerializer(read_only=True)

    class Meta:
        model = ProjectTeam
        fields = '__all__'


class ProgressReportSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)
    prepared_by = UserSerializer(read_only=True)

    class Meta:
        model = ProgressReport
        fields = '__all__'


class DailyReportSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)
    reporter = UserSerializer(read_only=True)

    class Meta:
        model = DailyReport
        fields = '__all__'


class ProgressPhotoSerializer(serializers.ModelSerializer):
    daily_report = DailyReportSerializer(read_only=True)

    class Meta:
        model = ProgressPhoto
        fields = '__all__'


class DailyReportDocumentSerializer(serializers.ModelSerializer):
    daily_report = DailyReportSerializer(read_only=True)

    class Meta:
        model = DailyReportDocument
        fields = '__all__'


class SiteActivitySerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)

    class Meta:
        model = SiteActivity
        fields = '__all__'


class WorkItemSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)

    class Meta:
        model = WorkItem
        fields = '__all__'


class CostSummarySerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)

    class Meta:
        model = CostSummary
        fields = '__all__'


class VariationOrderSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)
    requested_by = UserSerializer(read_only=True)
    approved_by = UserSerializer(read_only=True)

    class Meta:
        model = VariationOrder
        fields = '__all__'


class InvoiceSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)
    submitted_by = UserSerializer(read_only=True)

    class Meta:
        model = Invoice
        fields = '__all__'


class FinancialRecordSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)
    submitted_by = UserSerializer(read_only=True)
    site_verified_by = UserSerializer(read_only=True)
    hq_reviewed_by = UserSerializer(read_only=True)
    approved_by = UserSerializer(read_only=True)

    class Meta:
        model = FinancialRecord
        fields = '__all__'


class FinancialRecordHistorySerializer(serializers.ModelSerializer):
    financial_record = FinancialRecordSerializer(read_only=True)
    action_by = UserSerializer(read_only=True)

    class Meta:
        model = FinancialRecordHistory
        fields = '__all__'


class ScheduleSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)

    class Meta:
        model = Schedule
        fields = '__all__'


class QAQCInspectionSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)
    inspector = UserSerializer(read_only=True)

    class Meta:
        model = QAQCInspection
        fields = '__all__'


class HSEReportSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)
    reporter = UserSerializer(read_only=True)

    class Meta:
        model = HSEReport
        fields = '__all__'


class MeetingSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)
    chairperson = UserSerializer(read_only=True)

    class Meta:
        model = Meeting
        fields = '__all__'


class MeetingActionSerializer(serializers.ModelSerializer):
    meeting = MeetingSerializer(read_only=True)
    responsible_user = UserSerializer(read_only=True)

    class Meta:
        model = MeetingAction
        fields = '__all__'


class DocumentSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)
    submitted_by = UserSerializer(read_only=True)
    approved_by = UserSerializer(read_only=True)

    class Meta:
        model = Document
        fields = '__all__'


class ApprovalSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)
    submitted_by = UserSerializer(read_only=True)
    reviewed_by = UserSerializer(read_only=True)
    approved_by = UserSerializer(read_only=True)
    reviewer_by = UserSerializer(read_only=True)
    manager_by = UserSerializer(read_only=True)
    consultant_by = UserSerializer(read_only=True)
    hq_approved_by = UserSerializer(read_only=True)

    class Meta:
        model = Approval
        fields = '__all__'


class ApprovalStepHistorySerializer(serializers.ModelSerializer):
    approval = ApprovalSerializer(read_only=True)
    action_by = UserSerializer(read_only=True)

    class Meta:
        model = ApprovalStepHistory
        fields = '__all__'


class RiskRegisterSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)
    owner = UserSerializer(read_only=True)

    class Meta:
        model = RiskRegister
        fields = '__all__'


class MaterialTestSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)

    class Meta:
        model = MaterialTest
        fields = '__all__'


class MaterialRequestSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)
    material_item = serializers.StringRelatedField(read_only=True)
    requested_by = UserSerializer(read_only=True)
    approved_by = UserSerializer(read_only=True)
    delivered_by = UserSerializer(read_only=True)
    received_by = UserSerializer(read_only=True)

    class Meta:
        model = MaterialRequest
        fields = '__all__'


class PurchaseRequestSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)
    material_request = serializers.StringRelatedField(read_only=True)
    requested_by = UserSerializer(read_only=True)
    reviewer_by = UserSerializer(read_only=True)
    manager_by = UserSerializer(read_only=True)
    consultant_by = UserSerializer(read_only=True)
    approved_by = UserSerializer(read_only=True)

    class Meta:
        model = PurchaseRequest
        fields = '__all__'


class MaterialWasteSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)
    material_item = serializers.StringRelatedField(read_only=True)
    recorded_by = UserSerializer(read_only=True)

    class Meta:
        model = MaterialWaste
        fields = '__all__'


class BIMModelSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)
    reviewed_by = UserSerializer(read_only=True)

    class Meta:
        model = BIMModel
        fields = '__all__'


class BIMClashSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)
    bim_model = BIMModelSerializer(read_only=True)

    class Meta:
        model = BIMClash
        fields = '__all__'


class InterimPaymentCertificateSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)
    invoice = InvoiceSerializer(read_only=True)
    certified_by = UserSerializer(read_only=True)

    class Meta:
        model = InterimPaymentCertificate
        fields = '__all__'


class MaterialItemSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)
    current_stock = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = MaterialItem
        fields = '__all__'


class StockTransactionSerializer(serializers.ModelSerializer):
    material_item = MaterialItemSerializer(read_only=True)
    project = ProjectSerializer(read_only=True)
    recorded_by = UserSerializer(read_only=True)
    total_value = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)

    class Meta:
        model = StockTransaction
        fields = '__all__'


class LogisticsRecordSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)
    material_request = serializers.StringRelatedField(read_only=True)
    material_item = MaterialItemSerializer(read_only=True)
    stock_transaction = StockTransactionSerializer(read_only=True)
    handled_by = UserSerializer(read_only=True)

    class Meta:
        model = LogisticsRecord
        fields = '__all__'


class RFISerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)
    raised_by = UserSerializer(read_only=True)
    assigned_to = UserSerializer(read_only=True)

    class Meta:
        model = RFI
        fields = '__all__'


class NCRSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)
    reported_by = UserSerializer(read_only=True)
    verified_by = UserSerializer(read_only=True)

    class Meta:
        model = NCR
        fields = '__all__'


class SiteInstructionSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)
    issued_by = UserSerializer(read_only=True)
    acknowledged_by = UserSerializer(read_only=True)

    class Meta:
        model = SiteInstruction
        fields = '__all__'


class ManpowerSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)

    class Meta:
        model = Manpower
        fields = '__all__'


class AttendanceSerializer(serializers.ModelSerializer):
    manpower = ManpowerSerializer(read_only=True)
    project = ProjectSerializer(read_only=True)
    recorded_by = UserSerializer(read_only=True)

    class Meta:
        model = Attendance
        fields = '__all__'


class EquipmentSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)
    operator = ManpowerSerializer(read_only=True)

    class Meta:
        model = Equipment
        fields = '__all__'


class EquipmentUsageSerializer(serializers.ModelSerializer):
    equipment = EquipmentSerializer(read_only=True)
    project = ProjectSerializer(read_only=True)
    operator = ManpowerSerializer(read_only=True)
    recorded_by = UserSerializer(read_only=True)

    class Meta:
        model = EquipmentUsage
        fields = '__all__'


class EquipmentMaintenanceSerializer(serializers.ModelSerializer):
    equipment = EquipmentSerializer(read_only=True)
    recorded_by = UserSerializer(read_only=True)

    class Meta:
        model = EquipmentMaintenance
        fields = '__all__'


class NotificationSerializer(serializers.ModelSerializer):
    recipient = UserSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = '__all__'


class ChatMessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)

    class Meta:
        model = ChatMessage
        fields = '__all__'


class ChatRoomSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True)
    messages = ChatMessageSerializer(many=True, read_only=True)
    project = ProjectSerializer(read_only=True)

    class Meta:
        model = ChatRoom
        fields = '__all__'
