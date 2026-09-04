from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch
import tempfile
import shutil
from core.models import (
    UserProfile, Company, Project, ProjectTeam, DailyReport, ProgressReport,
    WorkItem, VariationOrder, HSEReport, MaterialRequest, MaterialWaste, BIMModel, BIMClash,
    Approval, ApprovalStepHistory, CostSummary, Schedule, Invoice, FinancialRecord, FinancialRecordHistory,
    Document, DocumentRevisionHistory, Meeting, InterimPaymentCertificate,
    ProgressPhoto, DailyReportDocument, DailyReportWorkProgress, DailyReportMaterialUsage, DailyReportManpowerUsage,
    DailyReportEquipmentUsage, ProjectReadinessChecklist, MaterialItem, StockTransaction,
    Manpower, Attendance, Equipment, EquipmentUsage, Notification, PurchaseRequest, LogisticsRecord
)
from core.services import workflow as wf
import datetime


TEST_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class CCMSViewTestCase(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = Client()
        # Create all role users for role switching
        self.users = {}
        self.profiles = {}
        for role, username in [
            ('HQ_DIRECTOR', 'director'),
            ('PROJECT_MANAGER', 'projectmanager'),
            ('FINANCE_HQ', 'financehq'),
            ('FINANCE_SITE', 'financesite'),
            ('SITE_ENGINEER', 'siteengineer'),
            ('SUPERVISOR', 'supervisor'),
            ('COST_ENGINEER', 'costengineer'),
            ('QA_QC', 'qaqc'),
            ('HSE_OFFICER', 'hse'),
            ('STOREKEEPER', 'storekeeper'),
            ('LOGISTICS', 'logistics'),
            ('DOC_CONTROLLER', 'doccontroller'),
            ('ADMIN_SITE', 'adminsite'),
            ('CONSULTANT', 'consultant')
        ]:
            u = User.objects.create_user(username=username, password='password123')
            p = UserProfile.objects.create(user=u, role=role)
            self.users[username] = u
            self.profiles[username] = p
            
        self.user = self.users['director']
        self.profile = self.profiles['director']
        
        # Create a contractor company
        self.company = Company.objects.create(
            company_name='Test Contractor',
            company_type='CONTRACTOR'
        )
        self.consultant_company = Company.objects.create(
            company_name='Test Consultant',
            company_type='CONSULTANT'
        )
        
        # Create a project
        self.project = Project.objects.create(
            company=self.company,
            project_code='PRJ001',
            name='Test Project',
            location='Dili',
            client_name='Client A',
            contract_value=100000.00,
            budget=90000.00,
            start_date=datetime.date.today(),
            end_date=datetime.date.today() + datetime.timedelta(days=30),
            status='ACTIVE'
        )

    def test_dashboard_view_anonymous(self):
        # Anonymous users should automatically login as 'director' if it exists
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Project')

    def test_dashboard_view_authenticated(self):
        self.client.login(username='director', password='password123')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Project')

    def test_daily_report_categories_are_grouped_by_project_boq(self):
        self.client.login(username='director', password='password123')
        other_project = Project.objects.create(
            company=self.company,
            project_code='PRJ002',
            name='Other Project',
            location='Baucau',
            client_name='Client B',
            contract_value=50000.00,
            budget=45000.00,
            start_date=datetime.date.today(),
            end_date=datetime.date.today() + datetime.timedelta(days=30),
            status='ACTIVE'
        )
        WorkItem.objects.create(
            project=self.project,
            item_code='A001',
            item_name='Mobilization',
            category='PRELIMINARIES WORKS',
            boq_quantity=1,
            unit='Ls',
        )
        WorkItem.objects.create(
            project=self.project,
            item_code='A002',
            item_name='Uncategorized item',
            category='',
            boq_quantity=5,
            unit='m',
        )
        WorkItem.objects.create(
            project=other_project,
            item_code='B001',
            item_name='Demolition wall',
            category='DEMOLITION WORKS',
            boq_quantity=2,
            unit='m2',
        )

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        categories = response.context['work_item_categories']
        self.assertIn({'project_id': self.project.id, 'category': 'PRELIMINARIES WORKS'}, categories)
        self.assertIn({'project_id': self.project.id, 'category': 'Umum'}, categories)
        self.assertIn({'project_id': other_project.id, 'category': 'DEMOLITION WORKS'}, categories)
        self.assertContains(response, f'data-project="{self.project.id}" data-category="PRELIMINARIES WORKS"')
        self.assertContains(response, f'data-project="{other_project.id}" data-category="DEMOLITION WORKS"')

    def test_progress_monitoring_uses_project_dropdown(self):
        self.client.login(username='director', password='password123')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="boq-project-select"')
        self.assertContains(response, 'onchange="filterBOQ(this.value)"')
        self.assertNotContains(response, 'boq-filter-btn')

    def test_switch_role(self):
        self.client.login(username='director', password='password123')
        # Test valid role
        response = self.client.post(reverse('switch_role'), {'role': 'PROJECT_MANAGER'})
        self.assertEqual(response.status_code, 302)
        # Verify the new user role in profile is correct
        pm_profile = UserProfile.objects.get(user__username='projectmanager')
        self.assertEqual(pm_profile.role, 'PROJECT_MANAGER')

        # Test invalid role - shouldn't affect anything
        response = self.client.post(reverse('switch_role'), {'role': 'INVALID_ROLE'})
        self.assertEqual(response.status_code, 302)

    def test_submit_report_valid(self):
        self.client.login(username='siteengineer', password='password123')
        data = {
            'project_id': self.project.id,
            'progress_percentage': '50',
            'manpower_count': '10',
            'weather': 'Rainy',
            'work_done': 'Foundation works done',
            'materials_used': 'Cement, Sand',
            'equipment_used': 'Excavator',
            'issues': 'None',
            'date': str(datetime.date.today()),
            'progress_photo_1': SimpleUploadedFile('report-photo.jpg', b'photo', content_type='image/jpeg'),
            'progress_photo_2': SimpleUploadedFile('report-photo-2.jpg', b'photo2', content_type='image/jpeg'),
            'progress_photo_3': SimpleUploadedFile('report-photo-3.jpg', b'photo3', content_type='image/jpeg'),
            'progress_photo_4': SimpleUploadedFile('report-photo-4.jpg', b'photo4', content_type='image/jpeg'),
        }
        response = self.client.post(reverse('submit_report'), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(DailyReport.objects.count(), 1)
        report = DailyReport.objects.first()
        self.assertEqual(report.progress_percentage, 50)
        self.assertEqual(report.manpower_count, 10)
        self.assertEqual(report.photos.count(), 4)

    def test_submit_report_saves_master_based_daily_operation_details(self):
        self.client.login(username='siteengineer', password='password123')
        material = MaterialItem.objects.create(
            project=self.project,
            item_code='MAT-001',
            name='Cement',
            unit='sak',
            category='STRUKTUR',
        )
        worker = Manpower.objects.create(
            project=self.project,
            nik='MP-001',
            name='Jose Worker',
            role='WORKER',
        )
        operator = Manpower.objects.create(
            project=self.project,
            nik='MP-002',
            name='Maria Operator',
            role='OPERATOR',
        )
        equipment = Equipment.objects.create(
            project=self.project,
            equipment_code='EQ-001',
            name='Excavator',
            category='EXCAVATOR',
            status='ACTIVE',
            operator=operator,
        )

        data = {
            'project_id': self.project.id,
            'progress_percentage': '35',
            'weather': 'Loro / Sunny',
            'work_done': 'Ground work operation',
            'date': str(datetime.date.today()),
            'material_item_id': [str(material.id)],
            'material_quantity': ['12.50'],
            'material_notes': ['Zone A'],
            'manpower_id': [str(worker.id), str(operator.id)],
            'manpower_hours': ['8', '7.5'],
            'manpower_notes': ['General work', 'Operate excavator'],
            'equipment_id': [str(equipment.id)],
            'equipment_hours': ['6.5'],
            'equipment_operator_id': [str(operator.id)],
            'equipment_notes': ['Earthmoving'],
            'progress_photo_1': SimpleUploadedFile('site-photo.jpg', b'photo', content_type='image/jpeg'),
            'progress_photo_2': SimpleUploadedFile('site-photo-2.jpg', b'photo2', content_type='image/jpeg'),
            'progress_photo_3': SimpleUploadedFile('site-photo-3.jpg', b'photo3', content_type='image/jpeg'),
            'progress_photo_4': SimpleUploadedFile('site-photo-4.jpg', b'photo4', content_type='image/jpeg'),
        }

        response = self.client.post(reverse('submit_report'), data)

        self.assertEqual(response.status_code, 302)
        report = DailyReport.objects.latest('id')
        self.assertEqual(report.manpower_count, 2)
        self.assertIn('Cement: 12.50 sak', report.materials_used)
        self.assertIn('Excavator: 6.5 jam', report.equipment_used)
        self.assertEqual(DailyReportMaterialUsage.objects.filter(daily_report=report).count(), 1)
        self.assertEqual(DailyReportManpowerUsage.objects.filter(daily_report=report).count(), 2)
        self.assertEqual(DailyReportEquipmentUsage.objects.filter(daily_report=report).count(), 1)
        self.assertEqual(StockTransaction.objects.filter(material_item=material, transaction_type='OUT').count(), 1)
        self.assertEqual(Attendance.objects.filter(project=self.project, date=datetime.date.today()).count(), 2)
        self.assertEqual(EquipmentUsage.objects.filter(equipment=equipment, usage_date=datetime.date.today()).count(), 1)

    def test_submit_report_requires_at_least_four_photos(self):
        self.client.login(username='siteengineer', password='password123')
        data = {
            'project_id': self.project.id,
            'progress_percentage': '25',
            'manpower_count': '6',
            'weather': 'Loro / Sunny',
            'work_done': 'Missing photo evidence',
            'date': str(datetime.date.today()),
        }

        response = self.client.post(reverse('submit_report'), data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(DailyReport.objects.count(), 0)
        self.assertEqual(ProgressPhoto.objects.count(), 0)

    def test_submit_report_accepts_document_and_four_photos(self):
        self.client.login(username='siteengineer', password='password123')
        data = {
            'project_id': self.project.id,
            'progress_percentage': '25',
            'manpower_count': '6',
            'weather': 'Loro / Sunny',
            'work_done': 'Detailed progress with attachments',
            'date': str(datetime.date.today()),
            'support_document': SimpleUploadedFile(
                'daily-report.pdf',
                b'%PDF-1.4 daily report',
                content_type='application/pdf',
            ),
            'progress_photo_1': SimpleUploadedFile('photo-1.jpg', b'photo1', content_type='image/jpeg'),
            'progress_photo_2': SimpleUploadedFile('photo-2.jpg', b'photo2', content_type='image/jpeg'),
            'progress_photo_3': SimpleUploadedFile('photo-3.jpg', b'photo3', content_type='image/jpeg'),
            'progress_photo_4': SimpleUploadedFile('photo-4.jpg', b'photo4', content_type='image/jpeg'),
        }

        response = self.client.post(reverse('submit_report'), data)

        self.assertEqual(response.status_code, 302)
        report = DailyReport.objects.latest('id')
        self.assertEqual(report.documents.count(), 1)
        self.assertEqual(report.photos.count(), 4)
        self.assertEqual(DailyReportDocument.objects.first().document_name, 'daily-report.pdf')
        self.assertEqual(ProgressPhoto.objects.filter(daily_report=report).count(), 4)

    def test_submit_report_actual_quantity_updates_work_item_progress(self):
        self.client.login(username='siteengineer', password='password123')
        work_item = WorkItem.objects.create(
            project=self.project,
            item_code='W001',
            item_name='Foundation',
            boq_quantity=100,
            boq_amount=1000,
            unit='m3',
            progress_percent=0,
        )
        data = {
            'project_id': self.project.id,
            'work_item_id': work_item.id,
            'actual_quantity': '40',
            'manpower_count': '8',
            'weather': 'Sunny',
            'work_done': 'Foundation quantity update',
            'date': str(datetime.date.today()),
            'progress_photo_1': SimpleUploadedFile('quantity-photo.jpg', b'photo', content_type='image/jpeg'),
            'progress_photo_2': SimpleUploadedFile('quantity-photo-2.jpg', b'photo2', content_type='image/jpeg'),
            'progress_photo_3': SimpleUploadedFile('quantity-photo-3.jpg', b'photo3', content_type='image/jpeg'),
            'progress_photo_4': SimpleUploadedFile('quantity-photo-4.jpg', b'photo4', content_type='image/jpeg'),
        }

        response = self.client.post(reverse('submit_report'), data)

        self.assertEqual(response.status_code, 302)
        work_item.refresh_from_db()
        report = DailyReport.objects.first()
        self.assertEqual(float(work_item.actual_quantity), 40.0)
        self.assertEqual(float(work_item.progress_percent), 40.0)
        self.assertEqual(float(work_item.actual_amount), 400.0)
        self.assertEqual(report.progress_percentage, 40)
        work_progress = DailyReportWorkProgress.objects.get(daily_report=report)
        self.assertEqual(work_progress.work_item, work_item)
        self.assertEqual(float(work_progress.actual_quantity), 40.0)
        self.assertEqual(float(work_progress.item_progress_percent), 40.0)
        progress_report = ProgressReport.objects.get(project=self.project, report_date=datetime.date.today())
        self.assertEqual(float(progress_report.overall_progress), 40.0)

    def test_submit_report_actual_quantity_requires_boq_quantity(self):
        self.client.login(username='siteengineer', password='password123')
        work_item = WorkItem.objects.create(
            project=self.project,
            item_code='W000',
            item_name='Unmeasured item',
            boq_quantity=0,
            unit='Ls',
            progress_percent=0,
        )

        response = self.client.post(reverse('submit_report'), {
            'project_id': self.project.id,
            'work_item_id': work_item.id,
            'actual_quantity': '5',
            'manpower_count': '8',
            'weather': 'Sunny',
            'date': str(datetime.date.today())
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(DailyReport.objects.count(), 0)
        self.assertEqual(ProgressReport.objects.filter(project=self.project).count(), 0)

    def test_submit_report_invalid_data(self):
        self.client.login(username='director', password='password123')
        # Test with invalid project ID, empty/non-numeric integers
        data = {
            'project_id': '9999',
            'progress_percentage': 'abc',
            'manpower_count': '',
            'weather': '',
            'work_done': '',
            'date': ''
        }
        response = self.client.post(reverse('submit_report'), data)
        self.assertEqual(response.status_code, 302)
        # Should redirect cleanly without crashing (500)
        self.assertEqual(DailyReport.objects.count(), 0)

    def test_approve_report(self):
        self.client.login(username='projectmanager', password='password123')
        report = DailyReport.objects.create(
            project=self.project,
            reporter=self.users['siteengineer'],
            date=datetime.date.today(),
            weather='Sunny',
            work_done='Brick laying',
            progress_percentage=20,
            manpower_count=5,
            status='PENDING'
        )
        # Approve report
        response = self.client.post(reverse('approve_report', args=[report.id]), {'status': 'APPROVED'})
        self.assertEqual(response.status_code, 302)
        report.refresh_from_db()
        self.assertEqual(report.status, 'VERIFIED')
        self.assertTrue(Approval.objects.filter(
            module_type='daily_report',
            reference_id=report.id,
            status='REVIEWED',
            reviewed_by=self.users['projectmanager'],
        ).exists())

        rejected_report = DailyReport.objects.create(
            project=self.project,
            reporter=self.users['siteengineer'],
            date=datetime.date.today(),
            weather='Sunny',
            work_done='Needs checking',
            progress_percentage=15,
            manpower_count=3,
            status='PENDING'
        )
        response = self.client.post(reverse('approve_report', args=[rejected_report.id]), {
            'status': 'REJECTED',
            'rejection_reason': 'Incomplete photos'
        })
        self.assertEqual(response.status_code, 302)
        rejected_report.refresh_from_db()
        self.assertEqual(rejected_report.status, 'REJECTED')
        self.assertEqual(rejected_report.rejection_reason, 'Incomplete photos')

        response = self.client.post(reverse('approve_report', args=[report.id]), {
            'status': 'REJECTED',
            'rejection_reason': 'Should not change verified report'
        })
        self.assertEqual(response.status_code, 302)
        report.refresh_from_db()
        self.assertEqual(report.status, 'VERIFIED')

    def test_resubmit_rejected_report_returns_to_pending_review(self):
        self.client.login(username='siteengineer', password='password123')
        report = DailyReport.objects.create(
            project=self.project,
            reporter=self.users['siteengineer'],
            date=datetime.date.today(),
            weather='Loro / Sunny',
            work_done='Original rejected work',
            progress_percentage=20,
            manpower_count=4,
            status='REJECTED',
            rejection_reason='Need clearer notes'
        )
        ProgressPhoto.objects.create(
            daily_report=report,
            image=SimpleUploadedFile('existing.jpg', b'photo', content_type='image/jpeg'),
            caption='Existing photo'
        )

        response = self.client.post(reverse('resubmit_report', args=[report.id]), {
            'weather': 'Kalohan / Cloudy',
            'work_done': 'Revised work done notes',
            'issues': 'Issue clarified',
        })

        self.assertEqual(response.status_code, 302)
        report.refresh_from_db()
        self.assertEqual(report.status, 'PENDING')
        self.assertIsNone(report.rejection_reason)
        self.assertEqual(report.weather, 'Kalohan / Cloudy')
        self.assertEqual(report.work_done, 'Revised work done notes')
        self.assertTrue(Approval.objects.filter(
            project=self.project,
            module_type='daily_report',
            reference_id=report.id,
            status='PENDING',
        ).exists())

    def test_create_project(self):
        self.client.login(username='director', password='password123')
        engineer = self.users['siteengineer']
        data = {
            'name': 'New Project B',
            'location': 'Baucau',
            'budget': '150000',
            'start_date': str(datetime.date.today()),
            'end_date': str(datetime.date.today() + datetime.timedelta(days=60)),
            'status': 'ONGOING',
            'site_engineer_id': engineer.id,
        }
        response = self.client.post(reverse('create_project'), data)
        self.assertEqual(response.status_code, 302)
        project = Project.objects.get(name='New Project B')
        self.assertTrue(ProjectTeam.objects.filter(project=project, user=engineer, role_in_project='Site Engineer').exists())

    def test_create_project_full_setup_creates_team_baseline_and_readiness(self):
        self.client.login(username='director', password='password123')

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self):
                return (
                    "NO,ITEM DESCRIPTION,UNIT,QUANTITY,UNIT PRICE,AMOUNT\n"
                    "I,PRELIMINARIES WORKS,,,,\n"
                    "1,Mobilization,Ls,1,1000,1000\n"
                ).encode("utf-8")

        data = {
            'project_code': 'PRJ-FULL',
            'name': 'Full Setup Project',
            'location': 'Dili',
            'client_name': 'Client Full',
            'budget': '150000',
            'contract_value': '175000',
            'start_date': str(datetime.date.today()),
            'end_date': str(datetime.date.today() + datetime.timedelta(days=60)),
            'status': 'ACTIVE',
            'contractor_id': self.company.id,
            'consultant_id': self.consultant_company.id,
            'project_manager_id': self.users['projectmanager'].id,
            'site_engineer_id': self.users['siteengineer'].id,
            'supervisor_id': self.users['supervisor'].id,
            'qs_id': self.users['costengineer'].id,
            'safety_officer_id': self.users['hse'].id,
            'storekeeper_id': self.users['storekeeper'].id,
            'doc_controller_id': self.users['doccontroller'].id,
            'admin_site_id': self.users['adminsite'].id,
            'consultant_user_id': self.users['consultant'].id,
            'boq_csv_url': 'https://docs.google.com/full-setup.csv',
            'baseline_name': 'Full Project Baseline',
            'create_baseline': 'on',
        }

        with patch('core.views.urllib.request.urlopen', return_value=FakeResponse()):
            response = self.client.post(reverse('create_project'), data)

        self.assertEqual(response.status_code, 302)
        project = Project.objects.get(project_code='PRJ-FULL')
        self.assertEqual(project.contractor, self.company)
        self.assertEqual(project.consultant, self.consultant_company)
        self.assertEqual(project.client_name, 'Client Full')
        self.assertEqual(float(project.contract_value), 175000.0)
        self.assertEqual(ProjectTeam.objects.filter(project=project).count(), 9)
        self.assertTrue(Schedule.objects.filter(project=project, activity_code='BASELINE', activity_name='Full Project Baseline').exists())
        self.assertTrue(WorkItem.objects.filter(project=project, item_name='Mobilization', category='PRELIMINARIES WORKS').exists())
        readiness = ProjectReadinessChecklist.objects.get(project=project)
        self.assertTrue(readiness.ready)

    def test_create_project_can_import_boq_from_google_sheet_url(self):
        self.client.login(username='director', password='password123')

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self):
                return (
                    "NO,ITEM DESCRIPTION,UNIT,QUANTITY,UNIT PRICE,AMOUNT\n"
                    "I,PRELIMINARIES WORKS,,,,\n"
                    "1,Water for the works,Ls,-,600,0\n"
                ).encode("utf-8")

        with patch('core.views.urllib.request.urlopen', return_value=FakeResponse()):
            response = self.client.post(reverse('create_project'), {
                'name': 'Project With BOQ',
                'location': 'Dili',
                'budget': '150000',
                'start_date': str(datetime.date.today()),
                'end_date': str(datetime.date.today() + datetime.timedelta(days=60)),
                'status': 'ACTIVE',
                'site_engineer_id': self.users['siteengineer'].id,
                'boq_csv_url': 'https://docs.google.com/test.csv',
            })

        self.assertEqual(response.status_code, 302)
        project = Project.objects.get(name='Project With BOQ')
        item = WorkItem.objects.get(project=project, item_name='Water for the works')
        self.assertEqual(item.category, 'PRELIMINARIES WORKS')
        self.assertEqual(float(item.boq_quantity), 1.0)

    def test_create_project_invalid(self):
        self.client.login(username='director', password='password123')
        data = {
            'name': 'Invalid Budget Project',
            'location': 'Viqueque',
            'budget': 'invalid_num',
            'start_date': '',
            'end_date': '',
            'status': 'PLANNING'
        }
        response = self.client.post(reverse('create_project'), data)
        self.assertEqual(response.status_code, 302)
        # Should create project with default 0.0 budget and default today dates cleanly
        proj = Project.objects.get(name='Invalid Budget Project')
        self.assertEqual(proj.budget, 0.0)

    def test_submit_vo(self):
        self.client.login(username='director', password='password123')
        data = {
            'project_id': self.project.id,
            'requested_amount': '15000.50',
            'description': 'Additional drainage works',
            'justification': 'Heavy rain washouts',
            'time_impact': '10'
        }
        response = self.client.post(reverse('submit_vo'), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(VariationOrder.objects.count(), 1)
        vo = VariationOrder.objects.first()
        self.assertEqual(vo.requested_amount, 15000.50)
        self.assertEqual(vo.time_impact, 10)

    def test_approve_vo(self):
        self.client.login(username='director', password='password123')
        vo = VariationOrder.objects.create(
            project=self.project,
            vo_number='VO-TEST-1',
            description='Test VO',
            requested_by=self.user,
            request_date=datetime.date.today(),
            requested_amount=5000,
            status='PENDING'
        )
        response = self.client.post(reverse('approve_vo', args=[vo.id]), {'status': 'APPROVED'})
        self.assertEqual(response.status_code, 302)
        vo.refresh_from_db()
        self.assertEqual(vo.status, 'APPROVED')
        self.assertEqual(vo.approved_amount, 5000)

    def test_submit_hse_incident(self):
        self.client.login(username='director', password='password123')
        report_date = datetime.date.today() - datetime.timedelta(days=1)
        data = {
            'project_id': self.project.id,
            'report_type': 'INCIDENT',
            'severity': 'HIGH',
            'incident_type': 'Trip hazard',
            'description': 'Minor trip injury on site',
            'location': 'Sector C',
            'persons_involved': '1',
            'action_taken': 'First aid administered',
            'report_date': str(report_date),
        }
        response = self.client.post(reverse('submit_hse_incident'), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(HSEReport.objects.count(), 1)
        report = HSEReport.objects.first()
        self.assertEqual(report.persons_involved, 1)
        self.assertEqual(report.incident_type, 'Trip hazard')
        self.assertEqual(report.report_date, report_date)

    def test_hse_officer_can_submit_unsafe_act(self):
        self.client.login(username='hse', password='password123')
        response = self.client.post(reverse('submit_hse_incident'), {
            'project_id': self.project.id,
            'report_type': 'UNSAFE_ACT',
            'severity': 'MEDIUM',
            'incident_type': 'PPE violation',
            'description': 'Worker entered area without safety harness',
            'location': 'Roof work area',
            'persons_involved': '1',
            'action_taken': 'Stopped work and briefed worker',
            'report_date': str(datetime.date.today()),
        })
        self.assertEqual(response.status_code, 302)
        report = HSEReport.objects.get(report_type='UNSAFE_ACT')
        self.assertEqual(report.reporter, self.users['hse'])
        self.assertEqual(report.severity, 'MEDIUM')
        self.assertEqual(report.action_taken, 'Stopped work and briefed worker')

    def test_submit_material_request(self):
        self.client.login(username='director', password='password123')
        data = {
            'project_id': self.project.id,
            'material_name': 'Reinforcement Bars',
            'quantity': '25.5',
            'unit': 'Tons',
            'required_date': str(datetime.date.today() + datetime.timedelta(days=5)),
            'remarks': 'Urgent requirement'
        }
        response = self.client.post(reverse('submit_material_request'), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(MaterialRequest.objects.count(), 1)
        req = MaterialRequest.objects.first()
        self.assertEqual(req.quantity, 25.5)

    def test_material_control_workflow_delivery_receiving_and_waste(self):
        material = MaterialItem.objects.create(
            project=self.project,
            item_code='MAT-F-001',
            name='Reinforcement Bars',
            unit='ton',
            category='STRUKTUR',
            minimum_stock=1,
        )

        self.client.login(username='siteengineer', password='password123')
        response = self.client.post(reverse('submit_material_request'), {
            'project_id': self.project.id,
            'material_item_id': material.id,
            'request_number': 'MR-F-001',
            'quantity': '10',
            'required_date': str(datetime.date.today() + datetime.timedelta(days=3)),
            'remarks': 'For slab reinforcement',
        })
        self.assertEqual(response.status_code, 302)
        req = MaterialRequest.objects.get(request_number='MR-F-001')
        self.assertEqual(req.status, 'SUBMITTED')
        self.assertEqual(req.material_item, material)
        self.assertTrue(Notification.objects.filter(recipient=self.users['storekeeper'], related_module='material_request').exists())
        approval = Approval.objects.get(module_type='material', reference_id=req.id)
        self.assertEqual(approval.current_step, 'REVIEWER')

        self.client.login(username='storekeeper', password='password123')
        self.client.post(reverse('review_material_request', args=[req.id]), {
            'status': 'APPROVED',
            'comments': 'Storekeeper checked request',
        })
        req.refresh_from_db()
        approval.refresh_from_db()
        self.assertEqual(req.status, 'SUBMITTED')
        self.assertEqual(approval.current_step, 'MANAGER')

        self.client.login(username='projectmanager', password='password123')
        self.client.post(reverse('review_material_request', args=[req.id]), {
            'status': 'APPROVED',
            'comments': 'Manager validated need',
        })
        approval.refresh_from_db()
        self.assertEqual(approval.current_step, 'CONSULTANT')

        self.client.login(username='consultant', password='password123')
        self.client.post(reverse('review_material_request', args=[req.id]), {
            'status': 'APPROVED',
            'comments': 'Consultant reviewed material',
        })
        approval.refresh_from_db()
        self.assertEqual(approval.current_step, 'HQ_APPROVAL')

        self.client.login(username='director', password='password123')
        self.client.post(reverse('review_material_request', args=[req.id]), {
            'status': 'APPROVED',
            'approved_quantity': '9',
            'comments': 'HQ final material approval',
        })
        req.refresh_from_db()
        approval.refresh_from_db()
        self.assertEqual(req.status, 'APPROVED')
        self.assertEqual(float(req.approved_quantity), 9.0)
        self.assertEqual(approval.status, 'APPROVED')
        self.assertEqual(approval.current_step, 'COMPLETED')
        self.assertEqual(ApprovalStepHistory.objects.filter(approval=approval).count(), 4)

        self.client.login(username='storekeeper', password='password123')
        self.client.post(reverse('deliver_material_request', args=[req.id]), {
            'delivered_quantity': '9',
            'delivery_reference': 'DO-001',
            'supplier_name': 'Steel Supplier',
        })
        req.refresh_from_db()
        self.assertEqual(req.status, 'DELIVERED')
        self.assertEqual(float(req.delivered_quantity), 9.0)
        self.assertTrue(LogisticsRecord.objects.filter(
            material_request=req,
            record_type='DELIVERY_TRACKING',
            status='ON_DELIVERY',
            reference_number='DO-001',
        ).exists())

        self.client.login(username='siteengineer', password='password123')
        self.client.post(reverse('receive_material_request', args=[req.id]), {
            'received_quantity': '8.5',
            'receiving_location': 'Main Warehouse',
            'condition': 'GOOD',
        })
        req.refresh_from_db()
        self.assertEqual(req.status, 'RECEIVED')
        self.assertEqual(float(req.received_quantity), 8.5)
        self.assertTrue(StockTransaction.objects.filter(material_item=material, transaction_type='IN', reference_number='DO-001').exists())
        self.assertTrue(LogisticsRecord.objects.filter(
            material_request=req,
            record_type='MATERIAL_RECEIVING',
            status='RECEIVED',
            condition='GOOD',
        ).exists())

        self.client.login(username='storekeeper', password='password123')
        self.client.post(reverse('record_material_waste'), {
            'material_item_id': material.id,
            'quantity': '0.5',
            'reason': 'CUTTING_LOSS',
            'location': 'Cutting Yard',
            'notes': 'Bar cutting waste',
        })
        self.assertTrue(MaterialWaste.objects.filter(material_item=material, quantity='0.5').exists())
        self.assertTrue(StockTransaction.objects.filter(material_item=material, transaction_type='OUT', notes='Bar cutting waste').exists())
        self.assertTrue(LogisticsRecord.objects.filter(material_item=material, status='DAMAGED', condition='DAMAGED').exists())

        response = self.client.get(reverse('export_material_control'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'MR-F-001', response.content)

    def test_logistics_manual_stock_issue_and_export(self):
        material = MaterialItem.objects.create(
            project=self.project,
            item_code='MAT-L-001',
            name='Cement',
            unit='sak',
            category='STRUKTUR',
            minimum_stock=5,
        )
        StockTransaction.objects.create(
            material_item=material,
            project=self.project,
            transaction_type='IN',
            quantity='20',
            reference_number='OPENING',
            transaction_date=datetime.date.today(),
            recorded_by=self.users['storekeeper'],
        )

        self.client.login(username='logistics', password='password123')
        response = self.client.post(reverse('submit_logistics_record'), {
            'project_id': self.project.id,
            'material_item_id': material.id,
            'record_type': 'STOCK_ISSUE',
            'quantity': '3',
            'reference_number': 'ISS-001',
            'from_location': 'Main Warehouse',
            'to_location': 'Zone A',
            'condition': 'GOOD',
            'actual_date': str(datetime.date.today()),
            'remarks': 'Issued to masonry team',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(StockTransaction.objects.filter(material_item=material, transaction_type='OUT', reference_number='ISS-001').exists())
        record = LogisticsRecord.objects.get(reference_number='ISS-001')
        self.assertEqual(record.record_type, 'STOCK_ISSUE')
        self.assertEqual(record.status, 'ISSUED')
        self.assertEqual(record.handled_by, self.users['logistics'])

        response = self.client.get(reverse('export_logistics_records'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'ISS-001', response.content)

    def test_submit_bim_clash(self):
        self.client.login(username='director', password='password123')
        data = {
            'project_id': self.project.id,
            'clash_type': 'HARD',
            'description': 'Structure column clashing with MEP pipe',
            'discipline_a': 'Structural',
            'discipline_b': 'MEP',
            'severity': 'HIGH'
        }
        response = self.client.post(reverse('submit_bim_clash'), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(BIMClash.objects.count(), 1)
        clash = BIMClash.objects.first()
        self.assertEqual(clash.clash_type, 'HARD')

    def test_import_boq_excel_empty(self):
        self.client.login(username='director', password='password123')
        # Empty POST should redirect with error
        response = self.client.post(reverse('import_boq_excel'))
        self.assertEqual(response.status_code, 302)

    def test_import_boq_excel_anonymous(self):
        # Without logging in, call import_boq_excel POST
        response = self.client.post(reverse('import_boq_excel'))
        self.assertEqual(response.status_code, 302)

    def test_import_boq_csv_uses_item_description_headings_as_categories(self):
        self.client.login(username='director', password='password123')
        csv_content = (
            ",,,,,\n"
            "NO,ITEM DESCRIPTION,UNIT,QUANTITY,UNIT PRICE,AMOUNT\n"
            "I,PRELIMINARIES WORKS,,,,\n"
            "1,Mobilization & Demobilization,Ls,1,1000,1000\n"
            "2,Temporary site buildings,Ls,1,500,500\n"
            "II,DEMOLITION WORKS,,,,\n"
            "1,Remove existing wall,m2,25,10,250\n"
        )
        upload = SimpleUploadedFile(
            "boq.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        response = self.client.post(reverse('import_boq_excel'), {
            'project_id': self.project.id,
            'boq_file': upload,
            'overwrite': 'on',
        })

        self.assertEqual(response.status_code, 302)
        self.assertFalse(WorkItem.objects.filter(project=self.project, item_name='PRELIMINARIES WORKS').exists())
        mobilization = WorkItem.objects.get(project=self.project, item_name='Mobilization & Demobilization')
        temporary = WorkItem.objects.get(project=self.project, item_name='Temporary site buildings')
        demolition = WorkItem.objects.get(project=self.project, item_name='Remove existing wall')
        self.assertEqual(mobilization.category, 'PRELIMINARIES WORKS')
        self.assertEqual(temporary.category, 'PRELIMINARIES WORKS')
        self.assertEqual(demolition.category, 'DEMOLITION WORKS')

    def test_import_boq_csv_can_apply_to_all_projects(self):
        self.client.login(username='director', password='password123')
        other_project = Project.objects.create(
            company=self.company,
            project_code='PRJ002',
            name='Other Project',
            location='Dili',
            client_name='Client B',
            contract_value=50000.00,
            budget=45000.00,
            start_date=datetime.date.today(),
            end_date=datetime.date.today() + datetime.timedelta(days=30),
            status='ACTIVE'
        )
        csv_content = (
            "NO,ITEM DESCRIPTION,UNIT,QUANTITY,UNIT PRICE,AMOUNT\n"
            "I,PRELIMINARIES WORKS,,,,\n"
            "1,Mobilization & Demobilization,Ls,1,1000,1000\n"
        )
        upload = SimpleUploadedFile(
            "boq_all.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        response = self.client.post(reverse('import_boq_excel'), {
            'project_id': '__all__',
            'boq_file': upload,
            'overwrite': 'on',
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(WorkItem.objects.filter(
            project=self.project,
            item_name='Mobilization & Demobilization',
            category='PRELIMINARIES WORKS',
        ).exists())
        self.assertTrue(WorkItem.objects.filter(
            project=other_project,
            item_name='Mobilization & Demobilization',
            category='PRELIMINARIES WORKS',
        ).exists())

    def test_import_boq_csv_uses_item_description_uppercase_rows_as_categories(self):
        self.client.login(username='director', password='password123')
        csv_content = (
            "Project ID,BOQ ID,WBS Code,Item Description,Unit,Quantity,Unit Rate,Amount\n"
            "DL-PRJ-2026-001,A-GER,A-GER,GENERAL REQUIREMENT,,,,4000\n"
            "DL-PRJ-2026-001,A-GER-001,A-GER,Contractor's Mobilization,Ls,1,1750,1750\n"
            "DL-PRJ-2026-001,A-GER-002,A-GER,Direksi Keet,Ls,1,1250,1250\n"
            "DL-PRJ-2026-001,A-GER-SUT,A-GER-SUT,Sub-Total,,,,4000\n"
            "DL-PRJ-2026-001,A-EAR-WO,A-EAR-WO,EARTHWORKS,,,,8098.67\n"
            "DL-PRJ-2026-001,A-EAR-WO-003,A-EAR-WO,Foundation Excavation,m3,1268.15,5.14,6515.75\n"
        )
        upload = SimpleUploadedFile(
            "boq_item_description.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        response = self.client.post(reverse('import_boq_excel'), {
            'project_id': self.project.id,
            'boq_file': upload,
            'overwrite': 'on',
        })

        self.assertEqual(response.status_code, 302)
        self.assertFalse(WorkItem.objects.filter(project=self.project, item_name='GENERAL REQUIREMENT').exists())
        mobilization = WorkItem.objects.get(project=self.project, item_name="Contractor's Mobilization")
        direksi = WorkItem.objects.get(project=self.project, item_name='Direksi Keet')
        excavation = WorkItem.objects.get(project=self.project, item_name='Foundation Excavation')
        self.assertEqual(mobilization.category, 'GENERAL REQUIREMENT')
        self.assertEqual(direksi.category, 'GENERAL REQUIREMENT')
        self.assertEqual(excavation.category, 'EARTHWORKS')

    def test_import_boq_csv_defaults_lump_sum_blank_quantity_to_one(self):
        self.client.login(username='director', password='password123')
        csv_content = (
            "NO,ITEM DESCRIPTION,UNIT,QUANTITY,UNIT PRICE,AMOUNT\n"
            "I,PRELIMINARIES WORKS,,,,\n"
            "1,Water for the works,Ls,-,600,0\n"
        )
        upload = SimpleUploadedFile(
            "boq_lumpsum.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        response = self.client.post(reverse('import_boq_excel'), {
            'project_id': self.project.id,
            'boq_file': upload,
            'overwrite': 'on',
        })

        self.assertEqual(response.status_code, 302)
        item = WorkItem.objects.get(project=self.project, item_name='Water for the works')
        self.assertEqual(float(item.boq_quantity), 1.0)
        self.assertEqual(float(item.boq_amount), 600.0)

    def test_import_progress_csv_upload_updates_work_items_and_progress_report(self):
        self.client.login(username='director', password='password123')
        WorkItem.objects.create(
            project=self.project,
            item_code='W001',
            item_name='Foundation',
            boq_quantity=100,
            unit='m3',
            progress_percent=0,
        )
        csv_content = (
            "item_code,item_name,boq_quantity,actual_quantity,weight,progress_percent,report_date\n"
            "W001,Foundation,100,50,20,50,2026-07-08\n"
            "W002,Structure,200,160,30,80,2026-07-08\n"
        )
        upload = SimpleUploadedFile(
            "progress.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        response = self.client.post(reverse('import_progress_csv'), {
            'project_id': self.project.id,
            'progress_csv_file': upload,
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(WorkItem.objects.filter(project=self.project).count(), 2)
        item = WorkItem.objects.get(project=self.project, item_code='W001')
        self.assertEqual(float(item.progress_percent), 50.0)
        self.assertEqual(float(item.actual_quantity), 50.0)
        self.assertTrue(ProgressReport.objects.filter(
            project=self.project,
            report_date=datetime.date(2026, 7, 8),
            overall_progress=68,
        ).exists())

    def test_import_progress_csv_detects_shifted_quantity_sheet_header(self):
        self.client.login(username='director', password='password123')
        csv_content = (
            ",,,,,,,,,,\n"
            ",,,,,,,,,,\n"
            "No,Description,Unit,Depth,Width,Height,Tickness,Length,Area,Volume\n"
            "1,Excavate for foundation footing,m3,1,2,3,, , ,6\n"
        )
        upload = SimpleUploadedFile(
            "quantity.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        response = self.client.post(reverse('import_progress_csv'), {
            'project_id': self.project.id,
            'progress_csv_file': upload,
        })

        self.assertEqual(response.status_code, 302)
        item = WorkItem.objects.get(project=self.project, item_name='Excavate for foundation footing')
        self.assertEqual(item.item_code, '1')
        self.assertEqual(float(item.boq_quantity), 6.0)
        self.assertEqual(ProgressReport.objects.filter(project=self.project).count(), 0)

    def test_import_progress_csv_uses_roman_headings_as_categories(self):
        self.client.login(username='director', password='password123')
        csv_content = (
            ",,,,,\n"
            "No,Description,Unit,Volume,Actual Quantity,Report Date\n"
            "I,PRELIMINARIES WORKS,,,,\n"
            "1,Mobilization,Ls,10,5,2026-07-08\n"
            "II,DEMOLITION WORKS,,,,\n"
            "2,Remove wall,m2,20,10,2026-07-08\n"
        )
        upload = SimpleUploadedFile(
            "categorized_quantity.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        response = self.client.post(reverse('import_progress_csv'), {
            'project_id': self.project.id,
            'progress_csv_file': upload,
        })

        self.assertEqual(response.status_code, 302)
        self.assertFalse(WorkItem.objects.filter(project=self.project, item_name='PRELIMINARIES WORKS').exists())
        mobilization = WorkItem.objects.get(project=self.project, item_name='Mobilization')
        remove_wall = WorkItem.objects.get(project=self.project, item_name='Remove wall')
        self.assertEqual(mobilization.category, 'PRELIMINARIES WORKS')
        self.assertEqual(remove_wall.category, 'DEMOLITION WORKS')

    def test_import_progress_csv_calculates_project_progress_from_actual_quantity_and_volume(self):
        self.client.login(username='director', password='password123')
        csv_content = (
            ",,,,,\n"
            "No,Description,Unit,Volume,Actual Quantity,Report Date\n"
            "1,Foundation,m3,100,50,2026-07-08\n"
            "2,Structure,m3,200,160,2026-07-08\n"
        )
        upload = SimpleUploadedFile(
            "quantity_progress.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        response = self.client.post(reverse('import_progress_csv'), {
            'project_id': self.project.id,
            'progress_csv_file': upload,
        })

        self.assertEqual(response.status_code, 302)
        foundation = WorkItem.objects.get(project=self.project, item_name='Foundation')
        structure = WorkItem.objects.get(project=self.project, item_name='Structure')
        self.assertEqual(float(foundation.progress_percent), 50.0)
        self.assertEqual(float(structure.progress_percent), 80.0)
        self.assertTrue(ProgressReport.objects.filter(
            project=self.project,
            report_date=datetime.date(2026, 7, 8),
            overall_progress=70,
        ).exists())

    def test_submit_report_anonymous(self):
        response = self.client.post(reverse('submit_report'), {'project_id': self.project.id})
        self.assertEqual(response.status_code, 302)

    def test_approve_report_anonymous(self):
        report = DailyReport.objects.create(
            project=self.project,
            reporter=self.user,
            date=datetime.date.today(),
            weather='Sunny',
            work_done='Brick laying',
            progress_percentage=20,
            manpower_count=5,
            status='PENDING'
        )
        response = self.client.post(reverse('approve_report', args=[report.id]), {'status': 'APPROVED'})
        self.assertEqual(response.status_code, 302)

    def test_create_project_anonymous(self):
        response = self.client.post(reverse('create_project'), {'name': 'Anon Project'})
        self.assertEqual(response.status_code, 302)

    def test_submit_vo_anonymous(self):
        response = self.client.post(reverse('submit_vo'), {'project_id': self.project.id})
        self.assertEqual(response.status_code, 302)

    def test_approve_vo_anonymous(self):
        vo = VariationOrder.objects.create(
            project=self.project,
            vo_number='VO-TEST-ANON',
            requested_by=self.user,
            requested_amount=100,
            status='PENDING'
        )
        response = self.client.post(reverse('approve_vo', args=[vo.id]), {'status': 'APPROVED'})
        self.assertEqual(response.status_code, 302)

    def test_submit_hse_incident_anonymous(self):
        response = self.client.post(reverse('submit_hse_incident'), {'project_id': self.project.id})
        self.assertEqual(response.status_code, 302)

    def test_submit_material_request_anonymous(self):
        response = self.client.post(reverse('submit_material_request'), {'project_id': self.project.id})
        self.assertEqual(response.status_code, 302)

    def test_phase_i_reporting_print_and_excel_exports(self):
        self.client.login(username='director', password='password123')
        report_date = datetime.date.today()
        DailyReport.objects.create(
            project=self.project,
            reporter=self.users['siteengineer'],
            date=report_date,
            weather='Sunny',
            work_done='Site work completed',
            progress_percentage=42,
            manpower_count=12,
            status='APPROVED',
        )
        ProgressReport.objects.create(
            project=self.project,
            report_date=report_date,
            report_period='Week 1',
            overall_progress=42,
            civil_progress=42,
            prepared_by=self.users['siteengineer'],
            status='APPROVED',
        )
        FinancialRecord.objects.create(
            project=self.project,
            record_type='EXPENSE',
            reference_number='FIN-RPT-001',
            category='Report Cost',
            description='Reporting cost test',
            amount='150.00',
            transaction_date=report_date,
            status='APPROVED',
            submitted_by=self.users['siteengineer'],
            approved_by=self.users['director'],
        )

        params = {
            'project_id': self.project.id,
            'start_date': report_date.isoformat(),
            'end_date': report_date.isoformat(),
        }
        response = self.client.get(reverse('print_report'), {**params, 'report_type': 'daily'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Daily Report')
        self.assertContains(response, 'Site work completed')

        response = self.client.get(reverse('export_report_excel'), {**params, 'report_type': 'progress'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Progress Report', response.content)
        self.assertIn(b'42', response.content)

        response = self.client.get(reverse('export_report_excel'), {**params, 'report_type': 'financial'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'FIN-RPT-001', response.content)

    def test_submit_bim_clash_anonymous(self):
        response = self.client.post(reverse('submit_bim_clash'), {'project_id': self.project.id})
        self.assertEqual(response.status_code, 302)


class CCMSWorkflowTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.director = User.objects.create_user(username='director', password='password123')
        UserProfile.objects.create(user=self.director, role='HQ_DIRECTOR')
        self.pm = User.objects.create_user(username='projectmanager', password='password123')
        UserProfile.objects.create(user=self.pm, role='PROJECT_MANAGER')
        self.financehq = User.objects.create_user(username='financehq', password='password123')
        UserProfile.objects.create(user=self.financehq, role='FINANCE_HQ')
        self.financesite = User.objects.create_user(username='financesite', password='password123')
        UserProfile.objects.create(user=self.financesite, role='FINANCE_SITE')
        self.engineer = User.objects.create_user(username='siteengineer', password='password123')
        UserProfile.objects.create(user=self.engineer, role='SITE_ENGINEER')
        self.doccontroller = User.objects.create_user(username='doccontroller', password='password123')
        UserProfile.objects.create(user=self.doccontroller, role='DOC_CONTROLLER')
        self.consultant = User.objects.create_user(username='consultant', password='password123')
        UserProfile.objects.create(user=self.consultant, role='CONSULTANT')

        self.project = Project.objects.create(
            name='Workflow Project',
            location='Dili',
            budget=100000.00,
            contract_value=105000.00,
            start_date=datetime.date.today(),
            end_date=datetime.date.today() + datetime.timedelta(days=90),
            status='ACTIVE'
        )
        Schedule.objects.create(
            project=self.project,
            activity_code='A001',
            activity_name='Foundation',
            planned_start=datetime.date.today(),
            planned_finish=datetime.date.today() + datetime.timedelta(days=30),
            status='IN_PROGRESS',
            progress=10,
        )

    def test_daily_report_approval_propagates_workflow(self):
        self.client.login(username='projectmanager', password='password123')
        report = DailyReport.objects.create(
            project=self.project,
            reporter=self.engineer,
            date=datetime.date.today(),
            weather='Sunny',
            work_done='Concrete pour',
            progress_percentage=35,
            manpower_count=20,
            status='PENDING',
        )
        response = self.client.post(reverse('approve_report', args=[report.id]), {'status': 'APPROVED'})
        self.assertEqual(response.status_code, 302)

        report.refresh_from_db()
        self.assertEqual(report.status, 'VERIFIED')
        self.assertFalse(ProgressReport.objects.filter(project=self.project, overall_progress=35).exists())

        approval = Approval.objects.get(module_type='daily_report', reference_id=report.id)
        self.assertEqual(approval.status, 'REVIEWED')

        self.client.login(username='consultant', password='password123')
        response = self.client.post(reverse('process_approval', args=[approval.id]), {
            'status': 'APPROVED',
            'comments': 'Consultant reviewed progress evidence',
        })
        self.assertEqual(response.status_code, 302)
        approval.refresh_from_db()
        self.assertEqual(approval.status, 'REVIEWED')
        self.assertEqual(approval.reviewed_by, self.consultant)

        self.client.login(username='director', password='password123')
        response = self.client.post(reverse('process_approval', args=[approval.id]), {
            'status': 'APPROVED',
            'comments': 'HQ final approval',
        })
        self.assertEqual(response.status_code, 302)

        report.refresh_from_db()
        self.assertEqual(report.status, 'APPROVED')
        self.assertTrue(ProgressReport.objects.filter(project=self.project, overall_progress=35).exists())
        self.assertTrue(Approval.objects.filter(module_type='daily_report', status='APPROVED').exists())
        self.assertTrue(CostSummary.objects.filter(project=self.project, category='Construction Progress').exists())

        sched = Schedule.objects.get(project=self.project, activity_code='A001')
        self.assertGreaterEqual(float(sched.progress), 35)

    def test_vo_submission_creates_approval_and_approval_updates_budget(self):
        self.client.login(username='projectmanager', password='password123')
        response = self.client.post(reverse('submit_vo'), {
            'project_id': self.project.id,
            'requested_amount': '5000',
            'description': 'Extra drainage',
            'justification': 'Design change',
            'time_impact': '3',
        })
        self.assertEqual(response.status_code, 302)
        vo = VariationOrder.objects.first()
        self.assertTrue(Approval.objects.filter(module_type='variation_order', reference_id=vo.id).exists())

        self.client.login(username='director', password='password123')
        old_budget = float(self.project.budget)
        self.client.post(reverse('approve_vo', args=[vo.id]), {'status': 'APPROVED'})
        self.project.refresh_from_db()
        self.assertEqual(float(self.project.budget), old_budget + 5000)
        self.assertTrue(CostSummary.objects.filter(category='Variation Orders').exists())

    def test_invoice_workflow_verify_and_certify(self):
        self.client.login(username='projectmanager', password='password123')
        response = self.client.post(reverse('submit_invoice'), {
            'project_id': self.project.id,
            'amount': '10000',
            'retention': '500',
            'claim_period': 'Term 1',
            'invoice_type': 'PROGRESS',
        })
        self.assertEqual(response.status_code, 302)
        invoice = Invoice.objects.first()
        approval = Approval.objects.get(module_type='invoice', reference_id=invoice.id)

        self.assertTrue(Notification.objects.filter(recipient=self.financesite, related_module='invoice').exists())

        self.client.login(username='financesite', password='password123')
        self.client.post(reverse('process_approval', args=[approval.id]), {'status': 'APPROVED'})
        approval.refresh_from_db()
        invoice.refresh_from_db()
        self.assertEqual(approval.status, 'PENDING')
        self.assertEqual(invoice.status, 'SITE_VERIFIED')

        self.client.login(username='financehq', password='password123')
        self.client.post(reverse('process_approval', args=[approval.id]), {'status': 'APPROVED'})
        approval.refresh_from_db()
        invoice.refresh_from_db()
        self.assertEqual(approval.status, 'REVIEWED')
        self.assertEqual(invoice.status, 'HQ_REVIEWED')

        self.client.login(username='director', password='password123')
        self.client.post(reverse('process_approval', args=[approval.id]), {'status': 'APPROVED', 'deduction': '0'})
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, 'APPROVED')
        self.assertTrue(InterimPaymentCertificate.objects.filter(invoice=invoice).exists())

        self.client.login(username='financehq', password='password123')
        self.client.post(reverse('mark_invoice_paid', args=[invoice.id]), {
            'paid_date': datetime.date.today().isoformat(),
        })
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, 'PAID')

    def test_financial_record_workflow_updates_cashflow(self):
        self.client.login(username='siteengineer', password='password123')
        response = self.client.post(reverse('submit_financial_record'), {
            'project_id': self.project.id,
            'record_type': 'EXPENSE',
            'reference_number': 'EXP-001',
            'category': 'Site Expense',
            'amount': '1250.50',
            'transaction_date': datetime.date.today().isoformat(),
            'description': 'Fuel and minor tools',
        })
        self.assertEqual(response.status_code, 302)
        record = FinancialRecord.objects.get(reference_number='EXP-001')
        approval = Approval.objects.get(module_type='financial_record', reference_id=record.id)
        self.assertEqual(record.status, 'SUBMITTED')
        self.assertEqual(FinancialRecordHistory.objects.filter(financial_record=record).count(), 1)

        self.assertTrue(Notification.objects.filter(recipient=self.financesite, related_module='financial_record').exists())

        self.client.login(username='financesite', password='password123')
        self.client.post(reverse('review_financial_record', args=[record.id]), {'status': 'APPROVED'})
        record.refresh_from_db()
        approval.refresh_from_db()
        self.assertEqual(record.status, 'SITE_VERIFIED')
        self.assertEqual(approval.status, 'PENDING')

        self.client.login(username='financehq', password='password123')
        self.client.post(reverse('review_financial_record', args=[record.id]), {'status': 'APPROVED'})
        record.refresh_from_db()
        approval.refresh_from_db()
        self.assertEqual(record.status, 'HQ_REVIEWED')
        self.assertEqual(approval.status, 'REVIEWED')

        self.client.login(username='director', password='password123')
        self.client.post(reverse('review_financial_record', args=[record.id]), {'status': 'APPROVED'})
        record.refresh_from_db()
        self.assertEqual(record.status, 'APPROVED')
        summary = CostSummary.objects.get(project=self.project, category='Site Expense')
        self.assertEqual(float(summary.actual), 1250.50)

        self.client.login(username='financehq', password='password123')
        self.client.post(reverse('mark_financial_record_paid', args=[record.id]))
        record.refresh_from_db()
        self.assertEqual(record.status, 'PAID')

        response = self.client.get(reverse('export_financial_records'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'EXP-001', response.content)

    def test_phase_g_purchase_request_central_approval(self):
        self.client.login(username='siteengineer', password='password123')
        response = self.client.post(reverse('submit_purchase_request'), {
            'project_id': self.project.id,
            'purchase_number': 'PR-G-001',
            'description': 'Purchase ceiling frame materials',
            'supplier_name': 'Supplier A',
            'amount': '2500',
            'required_date': datetime.date.today().isoformat(),
        })
        self.assertEqual(response.status_code, 302)
        purchase = PurchaseRequest.objects.get(purchase_number='PR-G-001')
        approval = Approval.objects.get(module_type='purchase', reference_id=purchase.id)
        self.assertEqual(approval.current_step, 'REVIEWER')

        self.client.login(username='projectmanager', password='password123')
        self.client.post(reverse('process_approval', args=[approval.id]), {'status': 'APPROVED', 'comments': 'Reviewer ok'})
        approval.refresh_from_db()
        purchase.refresh_from_db()
        self.assertEqual(approval.current_step, 'MANAGER')
        self.assertEqual(purchase.status, 'REVIEWER_REVIEWED')

        self.client.post(reverse('process_approval', args=[approval.id]), {'status': 'APPROVED', 'comments': 'Manager ok'})
        approval.refresh_from_db()
        purchase.refresh_from_db()
        self.assertEqual(approval.current_step, 'CONSULTANT')
        self.assertEqual(purchase.status, 'MANAGER_REVIEWED')

        self.client.login(username='consultant', password='password123')
        self.client.post(reverse('process_approval', args=[approval.id]), {'status': 'APPROVED', 'comments': 'Consultant ok'})
        approval.refresh_from_db()
        self.assertEqual(approval.current_step, 'HQ_APPROVAL')

        self.client.login(username='director', password='password123')
        self.client.post(reverse('process_approval', args=[approval.id]), {'status': 'APPROVED', 'comments': 'HQ approved'})
        approval.refresh_from_db()
        purchase.refresh_from_db()
        self.assertEqual(approval.status, 'APPROVED')
        self.assertEqual(approval.current_step, 'COMPLETED')
        self.assertEqual(purchase.status, 'APPROVED')
        self.assertEqual(ApprovalStepHistory.objects.filter(approval=approval).count(), 4)

    def test_phase_g_progress_central_approval(self):
        progress = ProgressReport.objects.create(
            project=self.project,
            report_date=datetime.date.today(),
            report_period='Week 1',
            overall_progress=12,
            civil_progress=12,
            prepared_by=self.engineer,
            status='SUBMITTED',
        )
        approval = wf.register_progress_submission(progress)

        self.client.login(username='projectmanager', password='password123')
        self.client.post(reverse('process_approval', args=[approval.id]), {'status': 'APPROVED'})
        approval.refresh_from_db()
        progress.refresh_from_db()
        self.assertEqual(approval.current_step, 'MANAGER')
        self.assertEqual(progress.status, 'REVIEWER_REVIEWED')

        self.client.post(reverse('process_approval', args=[approval.id]), {'status': 'APPROVED'})
        approval.refresh_from_db()
        progress.refresh_from_db()
        self.assertEqual(approval.current_step, 'CONSULTANT')
        self.assertEqual(progress.status, 'MANAGER_REVIEWED')

        self.client.login(username='consultant', password='password123')
        self.client.post(reverse('process_approval', args=[approval.id]), {'status': 'APPROVED'})
        approval.refresh_from_db()
        progress.refresh_from_db()
        self.assertEqual(approval.current_step, 'HQ_APPROVAL')
        self.assertEqual(progress.status, 'CONSULTANT_REVIEWED')

        self.client.login(username='director', password='password123')
        self.client.post(reverse('process_approval', args=[approval.id]), {'status': 'APPROVED'})
        approval.refresh_from_db()
        progress.refresh_from_db()
        self.assertEqual(approval.status, 'APPROVED')
        self.assertEqual(progress.status, 'APPROVED')

    def test_document_submission_and_approval(self):
        self.client.login(username='siteengineer', password='password123')
        self.client.post(reverse('submit_document'), {
            'project_id': self.project.id,
            'document_type': 'SHOP_DRAWING',
            'document_number': 'DWG-001',
            'document_title': 'Floor Plan L1',
            'revision': 'B',
            'document_file': SimpleUploadedFile('floor-plan.pdf', b'pdf-content', content_type='application/pdf'),
        })
        doc = Document.objects.get(document_number='DWG-001')
        self.assertEqual(doc.status, 'SUBMITTED')
        self.assertTrue(doc.file)
        self.assertTrue(Approval.objects.filter(module_type='document', reference_id=doc.id).exists())
        self.assertEqual(DocumentRevisionHistory.objects.filter(document=doc).count(), 1)

        self.client.login(username='doccontroller', password='password123')
        self.client.post(reverse('review_document', args=[doc.id]), {
            'status': 'APPROVED',
            'comments': 'DC checked drawing number and file.',
        })
        doc.refresh_from_db()
        self.assertEqual(doc.status, 'DC_REVIEW')
        self.assertEqual(doc.dc_reviewed_by, self.doccontroller)

        self.client.login(username='consultant', password='password123')
        self.client.post(reverse('review_document', args=[doc.id]), {
            'status': 'APPROVED',
            'comments': 'Consultant reviewed technical content.',
        })
        doc.refresh_from_db()
        self.assertEqual(doc.status, 'CONSULTANT_REVIEW')
        self.assertEqual(doc.consultant_reviewed_by, self.consultant)

        self.client.login(username='projectmanager', password='password123')
        self.client.post(reverse('review_document', args=[doc.id]), {
            'status': 'APPROVED',
            'comments': 'Approved for construction.',
        })
        doc.refresh_from_db()
        self.assertEqual(doc.status, 'APPROVED')
        self.assertEqual(doc.approved_by, self.pm)
        self.assertEqual(DocumentRevisionHistory.objects.filter(document=doc).count(), 4)

    def test_document_reject_and_resubmit_revision(self):
        doc = Document.objects.create(
            project=self.project,
            document_type='METHOD_STATEMENT',
            document_number='MS-001',
            document_title='Concrete Method Statement',
            revision='A',
            file=SimpleUploadedFile('method-a.pdf', b'old', content_type='application/pdf'),
            status='SUBMITTED',
            submitted_by=self.engineer,
        )
        Approval.objects.create(
            project=self.project,
            module_type='document',
            reference_id=doc.id,
            document_title='MS-001 - Concrete Method Statement',
            submitted_by=self.engineer,
            status='PENDING',
        )

        self.client.login(username='doccontroller', password='password123')
        self.client.post(reverse('review_document', args=[doc.id]), {
            'status': 'REJECTED',
            'comments': 'Missing attachment index.',
        })
        doc.refresh_from_db()
        self.assertEqual(doc.status, 'REVISION_REQUIRED')
        self.assertIn('Missing attachment index', doc.rejection_reason)

        self.client.login(username='siteengineer', password='password123')
        self.client.post(reverse('submit_document'), {
            'parent_document_id': doc.id,
            'project_id': self.project.id,
            'document_type': doc.document_type,
            'document_number': doc.document_number,
            'document_title': doc.document_title,
            'revision': 'B',
            'document_file': SimpleUploadedFile('method-b.pdf', b'new', content_type='application/pdf'),
        })
        doc.refresh_from_db()
        revision_doc = Document.objects.get(parent_document=doc)
        self.assertEqual(doc.status, 'SUPERSEDED')
        self.assertEqual(revision_doc.status, 'SUBMITTED')
        self.assertEqual(revision_doc.revision, 'B')

    def test_meeting_submission_creates_approval(self):
        self.client.login(username='projectmanager', password='password123')
        self.client.post(reverse('submit_meeting'), {
            'project_id': self.project.id,
            'meeting_title': 'Weekly Site Coordination',
            'meeting_type': 'SITE',
            'minutes': 'Discussed progress and safety.',
            'action_item': 'Submit revised BOQ',
            'responsible_name': 'Cost Engineer',
        })
        meeting = Meeting.objects.first()
        self.assertIsNotNone(meeting)
        self.assertTrue(Approval.objects.filter(module_type='meeting', reference_id=meeting.id).exists())

