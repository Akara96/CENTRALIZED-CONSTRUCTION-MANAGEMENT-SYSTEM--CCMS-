import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import (
    UserProfile, Company, Project, ProjectTeam, ProgressReport,
    DailyReport, ProgressPhoto, SiteActivity, WorkItem, CostSummary,
    VariationOrder, Invoice, Schedule, QAQCInspection, HSEReport,
    Meeting, MeetingAction, Document, Approval, RiskRegister,
    MaterialTest, MaterialRequest, BIMModel, BIMClash, InterimPaymentCertificate
)

class Command(BaseCommand):
    help = 'Seeds the database with full rich CCMS data (Users, Projects, WorkItems, Financials, Schedule, HSE, QAQC)'

    def handle(self, *args, **kwargs):
        self.stdout.write('Clearing existing CCMS database records...')
        
        # Clear in correct order due to foreign keys
        Approval.objects.all().delete()
        Document.objects.all().delete()
        MeetingAction.objects.all().delete()
        Meeting.objects.all().delete()
        HSEReport.objects.all().delete()
        QAQCInspection.objects.all().delete()
        Schedule.objects.all().delete()
        
        # Clear new models
        BIMClash.objects.all().delete()
        BIMModel.objects.all().delete()
        MaterialRequest.objects.all().delete()
        MaterialTest.objects.all().delete()
        InterimPaymentCertificate.objects.all().delete()
        
        Invoice.objects.all().delete()
        VariationOrder.objects.all().delete()
        CostSummary.objects.all().delete()
        WorkItem.objects.all().delete()
        SiteActivity.objects.all().delete()
        ProgressPhoto.objects.all().delete()
        DailyReport.objects.all().delete()
        ProgressReport.objects.all().delete()
        ProjectTeam.objects.all().delete()
        RiskRegister.objects.all().delete()
        Project.objects.all().delete()
        Company.objects.all().delete()
        
        self.stdout.write('Seeding database with realistic Timor-Leste CCMS data...')
        
        # 1. Create Companies
        c_klien, _ = Company.objects.get_or_create(
            company_name='Ministry of Public Works (MOP)',
            company_type='CLIENT',
            address='Dili, Timor-Leste',
            phone='+670 331 1234',
            email='info@mop.gov.tl'
        )
        c_kontraktor, _ = Company.objects.get_or_create(
            company_name='Timor Jaya Construction Lda',
            company_type='CONTRACTOR',
            address='Fatuhada, Dili',
            phone='+670 7723 4567',
            email='contact@timorjaya.tl'
        )
        c_konsultan, _ = Company.objects.get_or_create(
            company_name='East Timor Infrastructure Consultants',
            company_type='CONSULTANT',
            address='Colmera, Dili',
            phone='+670 7734 5678',
            email='hello@etic.tl'
        )
        
        # 2. Create Users & Profiles
        users_data = [
            ('director', 'director@ccms.com', 'HQ_DIRECTOR', 'CCMSdirector123!', 'HQ Director Central'),
            ('projectmanager', 'pm@ccms.com', 'PROJECT_MANAGER', 'CCMSmanager123!', 'Senior Project Manager'),
            ('siteengineer', 'engineer@ccms.com', 'SITE_ENGINEER', 'CCMSengineer123!', 'Resident Site Engineer'),
            ('costengineer', 'cost@ccms.com', 'COST_ENGINEER', 'CCMScost123!', 'Quantity Surveyor / Cost'),
            ('qaqc', 'qaqc@ccms.com', 'QA_QC', 'CCMSqaqc123!', 'QA/QC inspector'),
            ('hse', 'hse@ccms.com', 'HSE_OFFICER', 'CCMShse123!', 'Safety Officer'),
        ]
        
        created_users = {}
        for username, email, role, password, position in users_data:
            user, created = User.objects.get_or_create(username=username, email=email)
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(f'Created user: {username}')
            
            # Profile
            profile, p_created = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.position = position
            profile.phone = '+670 7700 0000'
            profile.save()
            created_users[role] = user

        # 3. Create Projects
        projects_data = [
            {
                'name': 'Dili Office Tower',
                'location': 'Katedral, Dili',
                'client_name': 'Ministry of Public Works',
                'company': c_kontraktor,
                'project_code': 'PRJ-2026-DOT',
                'status': 'ACTIVE',
                'contract_value': 15000000.00,
                'budget': 14200000.00,
                'start_date': datetime.date(2026, 1, 1),
                'end_date': datetime.date(2027, 12, 31)
            },
            {
                'name': 'Baucau Regional Hospital Expansion',
                'location': 'Baucau Vila',
                'client_name': 'Ministry of Health',
                'company': c_kontraktor,
                'project_code': 'PRJ-2026-BRH',
                'status': 'ACTIVE',
                'contract_value': 8500000.00,
                'budget': 8000000.00,
                'start_date': datetime.date(2026, 2, 15),
                'end_date': datetime.date(2027, 6, 30)
            },
            {
                'name': 'Liquica - Tibar Coastal Highway',
                'location': 'Tibar - Liquica Road',
                'client_name': 'Ministry of Public Works',
                'company': c_kontraktor,
                'project_code': 'PRJ-2026-LTH',
                'status': 'PLANNING',
                'contract_value': 24000000.00,
                'budget': 22500000.00,
                'start_date': datetime.date(2026, 8, 1),
                'end_date': datetime.date(2028, 12, 31)
            }
        ]

        created_projects = []
        for proj_info in projects_data:
            proj = Project.objects.create(**proj_info)
            self.stdout.write(f"Created project: {proj.name}")
            created_projects.append(proj)

        p_dili = created_projects[0]
        p_baucau = created_projects[1]
        
        # Seed Project Teams
        for p in created_projects:
            for role, usr in created_users.items():
                ProjectTeam.objects.create(
                    project=p,
                    user=usr,
                    role_in_project=usr.profile.position,
                    joined_date=datetime.date(2026, 1, 1)
                )

        # 4. Create Work Items (BOQ items) for Dili Office Tower
        items_data = [
            ('1.1', 'Preparation & Mobilization Works', 'Preparation', 1.0, 150000, 150000, 1.0, 100),
            ('2.1', 'Excavation & Substructure Works', 'Structure', 4500.0, 45.0, 202500, 4500.0, 100),
            ('2.2', 'Beton Structure Kolon (Andar 1-3)', 'Structure', 1200.0, 350.0, 420000, 1200.0, 100),
            ('2.3', 'Beton Structure Plat Lantai (Andar 4)', 'Structure', 850.0, 320.0, 272000, 425.0, 50),
            ('3.1', 'Pemasangan Dinding Bata Hebel', 'Arsitektur', 8200.0, 25.0, 205000, 1640.0, 20),
            ('4.1', 'Instalasi Jalur Kabel Elektrikal Utama', 'MEP', 1.0, 380000, 380000, 0.35, 35),
        ]
        for code, name, cat, qty, rate, amt, act_qty, prog in items_data:
            WorkItem.objects.create(
                project=p_dili,
                item_code=code,
                item_name=name,
                category=cat,
                boq_quantity=qty,
                unit_rate=rate,
                boq_amount=amt,
                actual_quantity=act_qty,
                actual_amount=float(act_qty) * rate,
                progress_percent=prog
            )

        # 5. Create Cost Summaries (Cost Control)
        cost_cats = [
            ('Civil / Structural Works', 5000000, 4200000, 4300000, 4900000),
            ('Architectural & Finishing Works', 4000000, 850000, 1200000, 3950000),
            ('MEP & Lift Works', 3500000, 680000, 950000, 3450000),
            ('Manajemen Proyek & Overhead', 1700000, 720000, 750000, 1680000),
        ]
        for cat, bud, act, comm, fore in cost_cats:
            CostSummary.objects.create(
                project=p_dili,
                category=cat,
                budget=bud,
                actual=act,
                committed=comm,
                forecast=fore,
                report_date=datetime.date(2026, 6, 8)
            )

        # 6. Seed Schedule (S-Curve & Gantt)
        schedules_dili = [
            ('A001', 'Foundation & Ground Tank Works', '2026-01-05', '2026-02-28', '2026-01-05', '2026-03-05', 100, 'COMPLETED'),
            ('A002', 'Structure Kolom & Plat Lantai 1-3', '2026-03-01', '2026-05-15', '2026-03-05', '2026-05-20', 100, 'COMPLETED'),
            ('A003', 'Structure Kolom & Plat Lantai 4-6', '2026-05-16', '2026-08-30', '2026-05-22', None, 45, 'IN_PROGRESS'),
            ('A004', 'Dinding Bata & Plasteran Interior', '2026-06-01', '2026-10-15', '2026-06-03', None, 15, 'IN_PROGRESS'),
            ('A005', 'Instalasi MEP & HVAC Lantai 1-3', '2026-06-15', '2026-11-30', None, None, 0, 'NOT_STARTED'),
        ]
        for code, name, plan_s, plan_f, act_s, act_f, prog, stat in schedules_dili:
            Schedule.objects.create(
                project=p_dili,
                activity_code=code,
                activity_name=name,
                planned_start=datetime.datetime.strptime(plan_s, '%Y-%m-%d').date(),
                planned_finish=datetime.datetime.strptime(plan_f, '%Y-%m-%d').date(),
                actual_start=datetime.datetime.strptime(act_s, '%Y-%m-%d').date() if act_s else None,
                actual_finish=datetime.datetime.strptime(act_f, '%Y-%m-%d').date() if act_f else None,
                duration_planned=(datetime.datetime.strptime(plan_f, '%Y-%m-%d').date() - datetime.datetime.strptime(plan_s, '%Y-%m-%d').date()).days,
                progress=prog,
                status=stat
            )

        # 7. Seed Variation Orders (VO)
        VariationOrder.objects.create(
            project=p_dili,
            vo_number='VO-DOT-001',
            description='Additional elevator shear wall thickness per QA/QC instruction',
            requested_by=created_users['PROJECT_MANAGER'],
            request_date=datetime.date(2026, 5, 10),
            requested_amount=120000.00,
            approved_amount=120000.00,
            time_impact=10,
            justification='Keamanan seismik gedung perkantoran di daerah rawan gempa.',
            status='APPROVED',
            approved_by=created_users['HQ_DIRECTOR'],
            approved_date=datetime.date(2026, 5, 20)
        )
        VariationOrder.objects.create(
            project=p_dili,
            vo_number='VO-DOT-002',
            description='Peralihan merek AC VRV Central dari Daikin ke Mitsubishi Heavy Industries',
            requested_by=created_users['PROJECT_MANAGER'],
            request_date=datetime.date(2026, 6, 2),
            requested_amount=85000.00,
            approved_amount=0.00,
            time_impact=5,
            justification='Ketersediaan stock Daikin mengalami delay 4 bulan dari supplier.',
            status='PENDING'
        )

        # 8. Seed Invoices (Payment Claims)
        Invoice.objects.create(
            project=p_dili,
            invoice_number='INV-DOT-2601',
            invoice_type='ADVANCE',
            claim_period='Uang Muka Kerja 15%',
            amount=2250000.00,
            retention=0.00,
            net_amount=2250000.00,
            status='PAID',
            due_date=datetime.date(2026, 2, 1),
            paid_date=datetime.date(2026, 1, 28)
        )
        Invoice.objects.create(
            project=p_dili,
            invoice_number='INV-DOT-2602',
            invoice_type='PROGRESS',
            claim_period='Termijn I - Progres 25%',
            amount=3750000.00,
            retention=187500.00,
            net_amount=3562500.00,
            status='VERIFIED',
            due_date=datetime.date(2026, 6, 30),
            submitted_by=created_users['PROJECT_MANAGER']
        )

        # 9. Create Sample Daily Reports
        reports = [
            {
                'project': p_dili,
                'reporter': created_users['SITE_ENGINEER'],
                'date': datetime.date(2026, 6, 1),
                'weather': 'Sunny',
                'work_done': 'Pengecoran kolom beton K-350 struktur lantai 4 zona B.',
                'issues': 'Tidak ada kendala material.',
                'progress_percentage': 26,
                'manpower_count': 55,
                'equipment_used': '1 Mobile Crane, 2 Concrete Pump Truck, 3 Vibrator',
                'materials_used': '45 m3 ReadyMix K-350, 4.2 ton Besi Deform D19',
                'status': 'APPROVED',
            },
            {
                'project': p_dili,
                'reporter': created_users['SITE_ENGINEER'],
                'date': datetime.date(2026, 6, 5),
                'weather': 'Sunny',
                'work_done': 'Pembesian plat lantai 4 zona C dan pemasangan perancah scaffolding.',
                'issues': 'Keterlambatan pengiriman kawat bendrat 2 jam.',
                'progress_percentage': 28,
                'manpower_count': 62,
                'equipment_used': '1 Mobile Crane, 1 Tower Crane',
                'materials_used': '80 lembar Plywood 18mm, 150 kg Kawat Ikat',
                'status': 'APPROVED',
            },
            {
                'project': p_dili,
                'reporter': created_users['SITE_ENGINEER'],
                'date': datetime.date(2026, 6, 8),
                'weather': 'Light Rain',
                'work_done': 'Instalasi pipa sparing kabel elektrikal dan pipa drainase di plat lantai 4.',
                'issues': 'Heavy rain from 13:00 to 15:30 delayed concrete beam casting.',
                'progress_percentage': 29,
                'manpower_count': 42,
                'equipment_used': '1 Tower Crane',
                'materials_used': '120 m Pipa PVC Conduit, 12 pcs Junction Box',
                'status': 'PENDING',
            },
            {
                'project': p_baucau,
                'reporter': created_users['SITE_ENGINEER'],
                'date': datetime.date(2026, 6, 8),
                'weather': 'Sunny',
                'work_done': 'Pemasangan dinding bata merah lantai 2 dan instalasi kusen jendela.',
                'issues': 'Fluktuasi suplai listrik dari EDTL, generator stand-by digunakan.',
                'progress_percentage': 18,
                'manpower_count': 32,
                'equipment_used': '1 Excavator mini, 1 Generator Set 100 KVA',
                'materials_used': '3500 pcs Bata Merah, 60 sak Semen Gresik',
                'status': 'APPROVED',
            }
        ]

        for rep_info in reports:
            rep = DailyReport.objects.create(
                project=rep_info['project'],
                reporter=rep_info['reporter'],
                date=rep_info['date'],
                weather=rep_info['weather'],
                work_done=rep_info['work_done'],
                issues=rep_info['issues'],
                progress_percentage=rep_info['progress_percentage'],
                manpower_count=rep_info['manpower_count'],
                equipment_used=rep_info['equipment_used'],
                materials_used=rep_info['materials_used'],
                status=rep_info['status']
            )
            ProgressPhoto.objects.create(
                daily_report=rep,
                image_url=f"/static/core/images/mock_progress_{rep_info['progress_percentage']}.jpg",
                caption=f"Work Progress {rep.project.name} {rep.progress_percentage}%"
            )

        # 10. Seed QA/QC Inspections
        QAQCInspection.objects.create(
            project=p_dili,
            inspector=created_users['QA_QC'],
            inspection_type='Tes Kuat Tekan Beton',
            location='Kolom Lantai 3',
            item='Slump test & Concrete Cube 28 Days',
            standard_reference='ASTM C39 / SNI 1974:2011',
            result_value='36.5 MPa (Target K-350/29.0 MPa)',
            status='PASS',
            remarks='Hasil uji laboratorium universitas terakreditasi melampaui batas desain minimum.',
            inspection_date=datetime.date(2026, 5, 25)
        )
        QAQCInspection.objects.create(
            project=p_dili,
            inspector=created_users['QA_QC'],
            inspection_type='Pemeriksaan Kelurusan Kolom',
            location='Kolom As A-4 Lantai 4',
            item='Verticality / Plumbness Test',
            standard_reference='BS 8110 Vertical Tolerance',
            result_value='Deviasi 12mm (Maksimum toleransi 10mm)',
            status='FAIL',
            remarks='Perlu perbaikan bekisting vertikal sebelum pengecoran berikutnya.',
            inspection_date=datetime.date(2026, 6, 6),
            corrective_action='Pemasangan support pipa strutting tambahan untuk meluruskan kolom vertikal.'
        )

        # 11. Seed HSE Reports
        HSEReport.objects.create(
            project=p_dili,
            reporter=created_users['HSE_OFFICER'],
            report_type='DAILY',
            severity='LOW',
            description='Safety Induction dilakukan kepada 12 pekerja sub-kontraktor baru elektrikal. Toolbox meeting harian membahas kerja di ketinggian.',
            location='Gedung Utama Ground Floor',
            persons_involved=12,
            action_taken='Pemberian helm standard baru dan safety harness.',
            report_date=datetime.date(2026, 6, 8)
        )
        HSEReport.objects.create(
            project=p_dili,
            reporter=created_users['HSE_OFFICER'],
            report_type='NEAR_MISS',
            severity='MEDIUM',
            description='Scaffolding bergeser 15cm karena tanah di dasar lunak akibat rembesan air hujan. Hampir menjatuhkan material batu bata.',
            location='Sisi Luar Zona Utara Lantai 3',
            persons_involved=2,
            action_taken='Area dipasangi safety line. Pondasi landasan scaffolding dipasang papan tebal dan distabilkan ulang.',
            report_date=datetime.date(2026, 6, 7)
        )

        # 12. Seed Risk Register
        RiskRegister.objects.create(
            project=p_dili,
            risk_code='RSK-DOT-01',
            risk_description='Keterlambatan pengiriman material import utama lift escalator dan curtain wall kaca.',
            category='Supply Chain',
            probability='HIGH',
            impact='HIGH',
            risk_level='CRITICAL',
            mitigation_plan='Melakukan pre-order 6 bulan lebih awal dari pabrikan di China dan menggunakan jalur laut ekspres kontainer prioritas.',
            status='mitigated',
            identified_date=datetime.date(2026, 2, 1)
        )
        RiskRegister.objects.create(
            project=p_dili,
            risk_code='RSK-DOT-02',
            risk_description='Curah hujan di atas rata-rata bulanan (La Nina) mengganggu pekerjaan struktur beton luar.',
            category='Weather / Force Majeure',
            probability='MEDIUM',
            impact='HIGH',
            risk_level='HIGH',
            mitigation_plan='Menyiapkan terpal pelindung beton cor berukuran besar (curtain tent) dan pompa submersible siaga di basement galian.',
            status='mitigated',
            identified_date=datetime.date(2026, 3, 10)
        )

        # 13. Seed Document Control
        Document.objects.create(
            project=p_dili,
            document_type='Shop Drawing',
            document_number='SD-DOT-ARC-302',
            document_title='Denah & Detail Partisi Toilet Andar 2-5',
            revision='Rev B',
            category='Arsitektural',
            status='APPROVED',
            submitted_by=created_users['PROJECT_MANAGER'],
            approved_by=created_users['HQ_DIRECTOR']
        )
        Document.objects.create(
            project=p_dili,
            document_type='Method Statement',
            document_number='MS-DOT-STR-015',
            document_title='Prosedur Metoda Pengecoran Balok Bentang Lebar Lantai 4',
            revision='Rev A',
            category='Structureal',
            status='SUBMITTED',
            submitted_by=created_users['PROJECT_MANAGER']
        )

        # 14. Seed Material Tests & Requests (Phase F)
        MaterialTest.objects.create(
            project=p_dili,
            material_name='Semen Portland Type I',
            test_type='Uji Kuat Tekan & Konsistensi',
            sample_location='Batching Plant Dili',
            test_date=datetime.date(2026, 5, 20),
            lab_name='Lab MOP Timor-Leste',
            result_value='380 kg/cm2 (Target 350 kg/cm2)',
            standard_value='ASTM C150 / SNI 15-2049-2004',
            status='PASS',
            remarks='Material semen memenuhi standar mutu kelayakan konstruksi.'
        )
        MaterialTest.objects.create(
            project=p_dili,
            material_name='Besi Baja Beton D22',
            test_type='Uji Tarik (Tensile Test)',
            sample_location='Main Steel Warehouse',
            test_date=datetime.date(2026, 6, 1),
            lab_name='Dili Public Works Laboratory',
            result_value='Kuat leleh 420 MPa (Target >400 MPa)',
            standard_value='ASTM A615 / SNI 2052:2017',
            status='PASS',
            remarks='Hasil uji tarik baja memenuhi spesifikasi teknis.'
        )

        MaterialRequest.objects.create(
            project=p_dili,
            material_name='Beton ReadyMix K-350',
            quantity=120.00,
            unit='m3',
            requested_by=created_users['SITE_ENGINEER'],
            required_date=datetime.date(2026, 6, 12),
            status='APPROVED',
            remarks='Diperlukan untuk pengecoran plat lantai 4 zona A.'
        )
        MaterialRequest.objects.create(
            project=p_dili,
            material_name='Pipa PVC Conduit 20mm',
            quantity=450.00,
            unit='batang',
            requested_by=created_users['SITE_ENGINEER'],
            required_date=datetime.date(2026, 6, 15),
            status='SUBMITTED',
            remarks='Second floor interior electrical installation work.'
        )

        # 15. Seed BIM Models & Clash Detections (Roadmap BIM Integration)
        m_struct = BIMModel.objects.create(
            project=p_dili,
            model_name='Dili Tower Structural Model',
            discipline='STRUCT',
            lod_level='LOD 350',
            version='v2.1',
            file_path='/static/core/bim/dot_struct_v2.1.ifc',
            status='APPROVED',
            reviewed_by=created_users['HQ_DIRECTOR']
        )
        m_mep = BIMModel.objects.create(
            project=p_dili,
            model_name='Dili Tower Plumbing & HVAC Model',
            discipline='MEP',
            lod_level='LOD 300',
            version='v1.4',
            file_path='/static/core/bim/dot_mep_v1.4.ifc',
            status='REVIEW',
            reviewed_by=created_users['PROJECT_MANAGER']
        )

        BIMClash.objects.create(
            project=p_dili,
            bim_model=m_mep,
            clash_type='HARD',
            description='Pipa air kotor dia. 4 inch menabrak balok struktur utama lantai 3 zona B.',
            discipline_a='MEP (Plumbing)',
            discipline_b='STRUCT (Beam)',
            severity='HIGH',
            status='OPEN',
            detected_date=datetime.date(2026, 6, 3)
        )
        BIMClash.objects.create(
            project=p_dili,
            bim_model=m_mep,
            clash_type='SOFT',
            description='Clearance ducting AC ke tray kabel elektrikal kurang dari 150mm di koridor lantai 2.',
            discipline_a='MEP (HVAC)',
            discipline_b='MEP (Electrical)',
            severity='MEDIUM',
            status='RESOLVED',
            detected_date=datetime.date(2026, 6, 4),
            resolved_date=datetime.date(2026, 6, 8)
        )

        # 16. Seed Interim Payment Certificates (IPC / Termin)
        # Fetching first invoice to associate with IPC
        inv = Invoice.objects.filter(project=p_dili).first()
        InterimPaymentCertificate.objects.create(
            project=p_dili,
            invoice=inv,
            ipc_number='IPC-DOT-2601-CERT',
            claimed_amount=2250000.00,
            verified_amount=2250000.00,
            deduction=0.00,
            certified_amount=2250000.00,
            remarks='Sertifikat pembayaran Uang Muka Kerja 15% telah diverifikasi penuh oleh Konsultan.',
            status='CERTIFIED',
            certified_by=created_users['HQ_DIRECTOR'],
            certified_date=datetime.date(2026, 1, 25)
        )

        self.stdout.write(self.style.SUCCESS('Rich CCMS database successfully seeded with Material, BIM, and IPC modules!'))



