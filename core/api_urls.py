from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .api_views import (
    UserProfileViewSet, CompanyViewSet, ProjectViewSet, ProjectTeamViewSet,
    ProgressReportViewSet, DailyReportViewSet, ProgressPhotoViewSet,
    SiteActivityViewSet, WorkItemViewSet, CostSummaryViewSet,
    VariationOrderViewSet, InvoiceViewSet, FinancialRecordViewSet,
    FinancialRecordHistoryViewSet, ScheduleViewSet,
    QAQCInspectionViewSet, HSEReportViewSet, MeetingViewSet,
    MeetingActionViewSet, DocumentViewSet, ApprovalViewSet, ApprovalStepHistoryViewSet,
    RiskRegisterViewSet, MaterialTestViewSet, MaterialRequestViewSet, PurchaseRequestViewSet,
    MaterialWasteViewSet, BIMModelViewSet, BIMClashViewSet, InterimPaymentCertificateViewSet,
    MaterialItemViewSet, StockTransactionViewSet, LogisticsRecordViewSet, RFIViewSet,
    NCRViewSet, SiteInstructionViewSet, ManpowerViewSet,
    AttendanceViewSet, EquipmentViewSet, EquipmentUsageViewSet,
    EquipmentMaintenanceViewSet, NotificationViewSet, VendorViewSet,
    SubcontractorViewSet, ChatRoomViewSet, ChatMessageViewSet,
    DailyDashboardAPIView
)
from . import mobile_api

router = DefaultRouter()
router.register(r'user-profiles', UserProfileViewSet)
router.register(r'companies', CompanyViewSet)
router.register(r'vendors', VendorViewSet)
router.register(r'subcontractors', SubcontractorViewSet)
router.register(r'projects', ProjectViewSet)
router.register(r'project-teams', ProjectTeamViewSet)
router.register(r'progress-reports', ProgressReportViewSet)
router.register(r'daily-reports', DailyReportViewSet)
router.register(r'progress-photos', ProgressPhotoViewSet)
router.register(r'site-activities', SiteActivityViewSet)
router.register(r'work-items', WorkItemViewSet)
router.register(r'cost-summaries', CostSummaryViewSet)
router.register(r'variation-orders', VariationOrderViewSet)
router.register(r'invoices', InvoiceViewSet)
router.register(r'financial-records', FinancialRecordViewSet)
router.register(r'financial-record-history', FinancialRecordHistoryViewSet)
router.register(r'schedules', ScheduleViewSet)
router.register(r'qaqc-inspections', QAQCInspectionViewSet)
router.register(r'hse-reports', HSEReportViewSet)
router.register(r'meetings', MeetingViewSet)
router.register(r'meeting-actions', MeetingActionViewSet)
router.register(r'documents', DocumentViewSet)
router.register(r'approvals', ApprovalViewSet)
router.register(r'approval-step-history', ApprovalStepHistoryViewSet)
router.register(r'risk-registers', RiskRegisterViewSet)
router.register(r'material-tests', MaterialTestViewSet)
router.register(r'material-requests', MaterialRequestViewSet)
router.register(r'purchase-requests', PurchaseRequestViewSet)
router.register(r'material-wastes', MaterialWasteViewSet)
router.register(r'bim-models', BIMModelViewSet)
router.register(r'bim-clashes', BIMClashViewSet)
router.register(r'ipcs', InterimPaymentCertificateViewSet)
router.register(r'material-items', MaterialItemViewSet)
router.register(r'stock-transactions', StockTransactionViewSet)
router.register(r'logistics-records', LogisticsRecordViewSet)
router.register(r'rfis', RFIViewSet)
router.register(r'ncrs', NCRViewSet)
router.register(r'site-instructions', SiteInstructionViewSet)
router.register(r'manpower', ManpowerViewSet)
router.register(r'attendance', AttendanceViewSet)
router.register(r'equipment', EquipmentViewSet)
router.register(r'equipment-usages', EquipmentUsageViewSet)
router.register(r'equipment-maintenances', EquipmentMaintenanceViewSet)
router.register(r'notifications', NotificationViewSet)
router.register(r'chat-rooms', ChatRoomViewSet)
router.register(r'chat-messages', ChatMessageViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard-summary/', DailyDashboardAPIView.as_view(), name='dashboard-summary'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('mobile/me/', mobile_api.mobile_me, name='mobile_me'),
    path('mobile/projects/', mobile_api.mobile_projects, name='mobile_projects'),
    path('mobile/projects/<int:project_id>/resources/', mobile_api.mobile_project_resources, name='mobile_project_resources'),
    path('mobile/daily-reports/', mobile_api.mobile_daily_reports, name='mobile_daily_reports'),
    path('mobile/daily-reports/submit/', mobile_api.mobile_submit_daily_report, name='mobile_submit_daily_report'),
    path('mobile/role-reports/', mobile_api.mobile_role_reports, name='mobile_role_reports'),
    path('mobile/role-reports/submit/', mobile_api.mobile_submit_role_report, name='mobile_submit_role_report'),
    path('mobile/notifications/', mobile_api.mobile_notifications, name='mobile_notifications'),
    path('mobile/notifications/<int:notification_id>/read/', mobile_api.mobile_mark_notification_read, name='mobile_mark_notification_read'),
]
