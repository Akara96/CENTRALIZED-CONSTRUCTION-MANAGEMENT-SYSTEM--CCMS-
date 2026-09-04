from rest_framework import viewsets, permissions
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .models import (
    UserProfile, Company, Project, ProjectTeam, ProgressReport, DailyReport,
    ProgressPhoto, SiteActivity, WorkItem, CostSummary, VariationOrder,
    Invoice, FinancialRecord, FinancialRecordHistory, Schedule, QAQCInspection, HSEReport, Meeting, MeetingAction,
    Document, Approval, ApprovalStepHistory, RiskRegister, MaterialTest, MaterialRequest,
    PurchaseRequest,
    MaterialWaste, BIMModel, BIMClash, InterimPaymentCertificate, MaterialItem,
    LogisticsRecord,
    StockTransaction, RFI, NCR, SiteInstruction, Manpower, Attendance,
    Equipment, EquipmentUsage, EquipmentMaintenance, Notification, Vendor,
    Subcontractor, ChatRoom, ChatMessage, DailyReportManpowerUsage, DailyReportEquipmentUsage
)
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum, Count
from datetime import date, timedelta
from .serializers import (
    UserProfileSerializer, CompanySerializer, ProjectSerializer,
    ProjectTeamSerializer, ProgressReportSerializer, DailyReportSerializer,
    ProgressPhotoSerializer, SiteActivitySerializer, WorkItemSerializer,
    CostSummarySerializer, VariationOrderSerializer, InvoiceSerializer,
    FinancialRecordSerializer, FinancialRecordHistorySerializer,
    ScheduleSerializer, QAQCInspectionSerializer, HSEReportSerializer,
    MeetingSerializer, MeetingActionSerializer, DocumentSerializer,
    ApprovalSerializer, ApprovalStepHistorySerializer, RiskRegisterSerializer, MaterialTestSerializer,
    MaterialRequestSerializer, PurchaseRequestSerializer, MaterialWasteSerializer, BIMModelSerializer, BIMClashSerializer,
    InterimPaymentCertificateSerializer, MaterialItemSerializer,
    LogisticsRecordSerializer,
    StockTransactionSerializer, RFISerializer, NCRSerializer,
    SiteInstructionSerializer, ManpowerSerializer, AttendanceSerializer,
    EquipmentSerializer, EquipmentUsageSerializer, EquipmentMaintenanceSerializer,
    NotificationSerializer, VendorSerializer, SubcontractorSerializer,
    ChatRoomSerializer, ChatMessageSerializer
)


class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]


class VendorViewSet(viewsets.ModelViewSet):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    permission_classes = [permissions.IsAuthenticated]


class SubcontractorViewSet(viewsets.ModelViewSet):
    queryset = Subcontractor.objects.all()
    serializer_class = SubcontractorSerializer
    permission_classes = [permissions.IsAuthenticated]


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]


class ProjectTeamViewSet(viewsets.ModelViewSet):
    queryset = ProjectTeam.objects.all()
    serializer_class = ProjectTeamSerializer
    permission_classes = [permissions.IsAuthenticated]


class ProgressReportViewSet(viewsets.ModelViewSet):
    queryset = ProgressReport.objects.all()
    serializer_class = ProgressReportSerializer
    permission_classes = [permissions.IsAuthenticated]


class DailyReportViewSet(viewsets.ModelViewSet):
    queryset = DailyReport.objects.all()
    serializer_class = DailyReportSerializer
    permission_classes = [permissions.IsAuthenticated]


class ProgressPhotoViewSet(viewsets.ModelViewSet):
    queryset = ProgressPhoto.objects.all()
    serializer_class = ProgressPhotoSerializer
    permission_classes = [permissions.IsAuthenticated]


class SiteActivityViewSet(viewsets.ModelViewSet):
    queryset = SiteActivity.objects.all()
    serializer_class = SiteActivitySerializer
    permission_classes = [permissions.IsAuthenticated]


class WorkItemViewSet(viewsets.ModelViewSet):
    queryset = WorkItem.objects.all()
    serializer_class = WorkItemSerializer
    permission_classes = [permissions.IsAuthenticated]


class CostSummaryViewSet(viewsets.ModelViewSet):
    queryset = CostSummary.objects.all()
    serializer_class = CostSummarySerializer
    permission_classes = [permissions.IsAuthenticated]


class VariationOrderViewSet(viewsets.ModelViewSet):
    queryset = VariationOrder.objects.all()
    serializer_class = VariationOrderSerializer
    permission_classes = [permissions.IsAuthenticated]


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]


class FinancialRecordViewSet(viewsets.ModelViewSet):
    queryset = FinancialRecord.objects.all()
    serializer_class = FinancialRecordSerializer
    permission_classes = [permissions.IsAuthenticated]


class FinancialRecordHistoryViewSet(viewsets.ModelViewSet):
    queryset = FinancialRecordHistory.objects.all()
    serializer_class = FinancialRecordHistorySerializer
    permission_classes = [permissions.IsAuthenticated]


class ScheduleViewSet(viewsets.ModelViewSet):
    queryset = Schedule.objects.all()
    serializer_class = ScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]


class QAQCInspectionViewSet(viewsets.ModelViewSet):
    queryset = QAQCInspection.objects.all()
    serializer_class = QAQCInspectionSerializer
    permission_classes = [permissions.IsAuthenticated]


class HSEReportViewSet(viewsets.ModelViewSet):
    queryset = HSEReport.objects.all()
    serializer_class = HSEReportSerializer
    permission_classes = [permissions.IsAuthenticated]


class MeetingViewSet(viewsets.ModelViewSet):
    queryset = Meeting.objects.all()
    serializer_class = MeetingSerializer
    permission_classes = [permissions.IsAuthenticated]


class MeetingActionViewSet(viewsets.ModelViewSet):
    queryset = MeetingAction.objects.all()
    serializer_class = MeetingActionSerializer
    permission_classes = [permissions.IsAuthenticated]


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]


class ApprovalViewSet(viewsets.ModelViewSet):
    queryset = Approval.objects.all()
    serializer_class = ApprovalSerializer
    permission_classes = [permissions.IsAuthenticated]


class ApprovalStepHistoryViewSet(viewsets.ModelViewSet):
    queryset = ApprovalStepHistory.objects.all()
    serializer_class = ApprovalStepHistorySerializer
    permission_classes = [permissions.IsAuthenticated]


class RiskRegisterViewSet(viewsets.ModelViewSet):
    queryset = RiskRegister.objects.all()
    serializer_class = RiskRegisterSerializer
    permission_classes = [permissions.IsAuthenticated]


class MaterialTestViewSet(viewsets.ModelViewSet):
    queryset = MaterialTest.objects.all()
    serializer_class = MaterialTestSerializer
    permission_classes = [permissions.IsAuthenticated]


class MaterialRequestViewSet(viewsets.ModelViewSet):
    queryset = MaterialRequest.objects.all()
    serializer_class = MaterialRequestSerializer
    permission_classes = [permissions.IsAuthenticated]


class PurchaseRequestViewSet(viewsets.ModelViewSet):
    queryset = PurchaseRequest.objects.all()
    serializer_class = PurchaseRequestSerializer
    permission_classes = [permissions.IsAuthenticated]


class MaterialWasteViewSet(viewsets.ModelViewSet):
    queryset = MaterialWaste.objects.all()
    serializer_class = MaterialWasteSerializer
    permission_classes = [permissions.IsAuthenticated]


class BIMModelViewSet(viewsets.ModelViewSet):
    queryset = BIMModel.objects.all()
    serializer_class = BIMModelSerializer
    permission_classes = [permissions.IsAuthenticated]


class BIMClashViewSet(viewsets.ModelViewSet):
    queryset = BIMClash.objects.all()
    serializer_class = BIMClashSerializer
    permission_classes = [permissions.IsAuthenticated]


class InterimPaymentCertificateViewSet(viewsets.ModelViewSet):
    queryset = InterimPaymentCertificate.objects.all()
    serializer_class = InterimPaymentCertificateSerializer
    permission_classes = [permissions.IsAuthenticated]


class MaterialItemViewSet(viewsets.ModelViewSet):
    queryset = MaterialItem.objects.all()
    serializer_class = MaterialItemSerializer
    permission_classes = [permissions.IsAuthenticated]


class StockTransactionViewSet(viewsets.ModelViewSet):
    queryset = StockTransaction.objects.all()
    serializer_class = StockTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]


class LogisticsRecordViewSet(viewsets.ModelViewSet):
    queryset = LogisticsRecord.objects.all()
    serializer_class = LogisticsRecordSerializer
    permission_classes = [permissions.IsAuthenticated]


class RFIViewSet(viewsets.ModelViewSet):
    queryset = RFI.objects.all()
    serializer_class = RFISerializer
    permission_classes = [permissions.IsAuthenticated]


class NCRViewSet(viewsets.ModelViewSet):
    queryset = NCR.objects.all()
    serializer_class = NCRSerializer
    permission_classes = [permissions.IsAuthenticated]


class SiteInstructionViewSet(viewsets.ModelViewSet):
    queryset = SiteInstruction.objects.all()
    serializer_class = SiteInstructionSerializer
    permission_classes = [permissions.IsAuthenticated]


class ManpowerViewSet(viewsets.ModelViewSet):
    queryset = Manpower.objects.all()
    serializer_class = ManpowerSerializer
    permission_classes = [permissions.IsAuthenticated]


class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]


class EquipmentViewSet(viewsets.ModelViewSet):
    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer
    permission_classes = [permissions.IsAuthenticated]


class EquipmentUsageViewSet(viewsets.ModelViewSet):
    queryset = EquipmentUsage.objects.all()
    serializer_class = EquipmentUsageSerializer
    permission_classes = [permissions.IsAuthenticated]


class EquipmentMaintenanceViewSet(viewsets.ModelViewSet):
    queryset = EquipmentMaintenance.objects.all()
    serializer_class = EquipmentMaintenanceSerializer
    permission_classes = [permissions.IsAuthenticated]


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]


class ChatRoomViewSet(viewsets.ModelViewSet):
    queryset = ChatRoom.objects.all()
    serializer_class = ChatRoomSerializer
    permission_classes = [permissions.IsAuthenticated]


class ChatMessageViewSet(viewsets.ModelViewSet):
    queryset = ChatMessage.objects.all()
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]


class DailyDashboardAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        today = date.today()
        # Get list of last 7 dates
        last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]

        # 1. Manpower Data (Total per day for the last 7 days)
        # Using Attendance model or DailyReportManpowerUsage. Let's use Attendance as it tracks daily presence.
        manpower_data = []
        for d in last_7_days:
            attendances = Attendance.objects.filter(date=d)
            # Assuming we want to group by Role of Manpower
            worker = attendances.filter(manpower__role='WORKER').count()
            operator = attendances.filter(manpower__role='OPERATOR').count()
            foreman = attendances.filter(manpower__role='FOREMAN').count()
            
            manpower_data.append({
                'date': d.strftime('%d %b'), # Format: 01 Oct
                'worker': worker,
                'operator': operator,
                'foreman': foreman
            })

        # 2. Equipment Data (Current Status of all Equipment)
        equipment = Equipment.objects.all()
        active = equipment.filter(status='ACTIVE').count()
        maintenance = equipment.filter(status='MAINTENANCE').count()
        repair = equipment.filter(status='REPAIR').count()
        rented = equipment.filter(status='RENTED').count()

        return Response({
            'manpower_chart_data': manpower_data,
            'equipment_status': {
                'active': active,
                'maintenance': maintenance,
                'repair': repair,
                'rented': rented
            }
        })

