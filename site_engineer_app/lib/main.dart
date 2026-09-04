import 'dart:convert';
import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  runApp(const CcmsSiteEngineerApp());
}

const _defaultApiBaseUrl = 'http://192.168.1.37:8000/api';

class CcmsSiteEngineerApp extends StatelessWidget {
  const CcmsSiteEngineerApp({super.key});

  @override
  Widget build(BuildContext context) {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: const Color(0xFF2563EB),
      brightness: Brightness.light,
    );
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'CCMS Site Engineer',
      theme: ThemeData(
        colorScheme: colorScheme,
        scaffoldBackgroundColor: const Color(0xFFF4F7FB),
        appBarTheme: const AppBarTheme(
          centerTitle: false,
          elevation: 0,
          backgroundColor: Color(0xFF0F172A),
          foregroundColor: Colors.white,
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: Colors.white,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
          ),
        ),
        cardTheme: CardThemeData(
          elevation: 0,
          color: Colors.white,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
      home: const BootstrapScreen(),
    );
  }
}

class ApiClient {
  ApiClient({required this.baseUrl, this.accessToken, this.refreshToken});

  String baseUrl;
  String? accessToken;
  String? refreshToken;

  Uri uri(String path, [Map<String, String>? query]) {
    final cleanBase = baseUrl.endsWith('/')
        ? baseUrl.substring(0, baseUrl.length - 1)
        : baseUrl;
    final cleanPath = path.startsWith('/') ? path : '/$path';
    return Uri.parse('$cleanBase$cleanPath').replace(queryParameters: query);
  }

  Map<String, String> get headers => {
    'Accept': 'application/json',
    if (accessToken != null) 'Authorization': 'Bearer $accessToken',
  };

  Future<Map<String, dynamic>> login(String username, String password) async {
    final response = await http.post(
      uri('/token/'),
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: jsonEncode({'username': username, 'password': password}),
    );
    return _decodeResponse(response);
  }

  Future<Map<String, dynamic>> getJson(
    String path, [
    Map<String, String>? query,
  ]) async {
    var response = await http.get(uri(path, query), headers: headers);
    if (_shouldRefresh(response) && await refreshAccessToken()) {
      response = await http.get(uri(path, query), headers: headers);
    }
    return _decodeResponse(response);
  }

  Future<Map<String, dynamic>> postJson(
    String path, [
    Map<String, dynamic>? body,
  ]) async {
    var response = await http.post(
      uri(path),
      headers: {...headers, 'Content-Type': 'application/json'},
      body: jsonEncode(body ?? <String, dynamic>{}),
    );
    if (_shouldRefresh(response) && await refreshAccessToken()) {
      response = await http.post(
        uri(path),
        headers: {...headers, 'Content-Type': 'application/json'},
        body: jsonEncode(body ?? <String, dynamic>{}),
      );
    }
    return _decodeResponse(response);
  }

  Future<Map<String, dynamic>> multipartDailyReport({
    required Map<String, String> fields,
    required List<XFile> photos,
    PlatformFile? supportDocument,
  }) async {
    http.MultipartRequest buildRequest() {
      final request = http.MultipartRequest(
        'POST',
        uri('/mobile/daily-reports/submit/'),
      );
      request.headers.addAll(headers);
      request.fields.addAll(fields);
      return request;
    }

    Future<http.Response> sendRequest() async {
      final request = buildRequest();
      for (final photo in photos) {
        request.files.add(
          await http.MultipartFile.fromPath('photos', photo.path),
        );
      }
      if (supportDocument?.path != null) {
        request.files.add(
          await http.MultipartFile.fromPath(
            'support_document',
            supportDocument!.path!,
            filename: supportDocument.name,
          ),
        );
        request.fields['support_document_name'] = supportDocument.name;
      }
      final streamed = await request.send();
      return http.Response.fromStream(streamed);
    }

    var response = await sendRequest();
    if (_shouldRefresh(response) && await refreshAccessToken()) {
      response = await sendRequest();
    }
    return _decodeResponse(response);
  }

  Future<bool> refreshAccessToken() async {
    final token = refreshToken;
    if (token == null || token.isEmpty) return false;
    final response = await http.post(
      uri('/token/refresh/'),
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: jsonEncode({'refresh': token}),
    );
    if (response.statusCode < 200 || response.statusCode >= 300) {
      return false;
    }
    final data = _decodeResponse(response);
    final newAccess = data['access']?.toString();
    if (newAccess == null || newAccess.isEmpty) return false;
    accessToken = newAccess;
    final newRefresh = data['refresh']?.toString();
    if (newRefresh != null && newRefresh.isNotEmpty) refreshToken = newRefresh;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('accessToken', accessToken!);
    if (refreshToken != null) {
      await prefs.setString('refreshToken', refreshToken!);
    }
    return true;
  }

  bool _shouldRefresh(http.Response response) {
    if (response.statusCode != 401) return false;
    return response.body.contains('token_not_valid') ||
        response.body.contains('Given token not valid') ||
        response.body.contains('Token is invalid');
  }

  Map<String, dynamic> _decodeResponse(http.Response response) {
    final text = response.body;
    final Object? decoded = text.isEmpty
        ? <String, dynamic>{}
        : jsonDecode(text);
    final body = decoded is Map<String, dynamic>
        ? decoded
        : {'results': decoded};
    if (response.statusCode < 200 || response.statusCode >= 300) {
      final detail =
          body['detail'] ??
          body['non_field_errors'] ??
          'Request failed (${response.statusCode})';
      if (response.statusCode == 401 &&
          (body['code'] == 'token_not_valid' ||
              detail.toString().contains('Given token not valid'))) {
        throw AuthExpiredException(
          'Your session has expired. Please login again.',
        );
      }
      throw ApiException(detail.toString());
    }
    return body;
  }
}

class ApiException implements Exception {
  ApiException(this.message);
  final String message;

  @override
  String toString() => message;
}

class AuthExpiredException extends ApiException {
  AuthExpiredException(super.message);
}

class BootstrapScreen extends StatefulWidget {
  const BootstrapScreen({super.key});

  @override
  State<BootstrapScreen> createState() => _BootstrapScreenState();
}

class _BootstrapScreenState extends State<BootstrapScreen> {
  ApiClient? _client;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadSession();
  }

  Future<void> _loadSession() async {
    final prefs = await SharedPreferences.getInstance();
    final baseUrl = prefs.getString('apiBaseUrl') ?? _defaultApiBaseUrl;
    final token = prefs.getString('accessToken');
    final refreshToken = prefs.getString('refreshToken');
    setState(() {
      _client = ApiClient(
        baseUrl: baseUrl,
        accessToken: token,
        refreshToken: refreshToken,
      );
      _loading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_loading || _client == null) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (_client!.accessToken == null) {
      return LoginScreen(
        client: _client!,
        onLoggedIn: (client) => setState(() => _client = client),
      );
    }
    return HomeScreen(
      client: _client!,
      onLogout: () async {
        final prefs = await SharedPreferences.getInstance();
        await prefs.remove('accessToken');
        await prefs.remove('refreshToken');
        setState(() => _client = ApiClient(baseUrl: _client!.baseUrl));
      },
    );
  }
}

class LoginScreen extends StatefulWidget {
  const LoginScreen({
    super.key,
    required this.client,
    required this.onLoggedIn,
  });

  final ApiClient client;
  final ValueChanged<ApiClient> onLoggedIn;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _serverController = TextEditingController(text: _defaultApiBaseUrl);
  final _usernameController = TextEditingController(text: 'DL-EMP-005');
  final _passwordController = TextEditingController();
  bool _loading = false;
  bool _obscure = true;

  @override
  void initState() {
    super.initState();
    _serverController.text = widget.client.baseUrl;
  }

  @override
  void dispose() {
    _serverController.dispose();
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _loading = true);
    try {
      final client = ApiClient(baseUrl: _serverController.text.trim());
      final tokenData = await client.login(
        _usernameController.text.trim(),
        _passwordController.text,
      );
      client.accessToken = tokenData['access']?.toString();
      client.refreshToken = tokenData['refresh']?.toString();
      if (client.accessToken == null) {
        throw ApiException('Token not returned by server.');
      }
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('apiBaseUrl', client.baseUrl);
      await prefs.setString('accessToken', client.accessToken!);
      if (client.refreshToken != null) {
        await prefs.setString('refreshToken', client.refreshToken!);
      }
      widget.onLoggedIn(client);
    } catch (error) {
      if (mounted) _showSnack(context, error.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            const SizedBox(height: 24),
            Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                color: const Color(0xFF2563EB),
                borderRadius: BorderRadius.circular(18),
              ),
              child: const Icon(
                Icons.engineering,
                color: Colors.white,
                size: 38,
              ),
            ),
            const SizedBox(height: 24),
            Text(
              'CCMS Site Engineer',
              style: Theme.of(
                context,
              ).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 8),
            const Text(
              'Submit daily reports, progress photos, and field updates from your phone.',
            ),
            const SizedBox(height: 28),
            Form(
              key: _formKey,
              child: Column(
                children: [
                  TextFormField(
                    controller: _serverController,
                    decoration: const InputDecoration(
                      labelText: 'API Server',
                      prefixIcon: Icon(Icons.link),
                    ),
                    validator: (value) => value == null || value.isEmpty
                        ? 'API server is required'
                        : null,
                  ),
                  const SizedBox(height: 14),
                  TextFormField(
                    controller: _usernameController,
                    decoration: const InputDecoration(
                      labelText: 'Username',
                      prefixIcon: Icon(Icons.person),
                    ),
                    validator: (value) => value == null || value.isEmpty
                        ? 'Username is required'
                        : null,
                  ),
                  const SizedBox(height: 14),
                  TextFormField(
                    controller: _passwordController,
                    obscureText: _obscure,
                    decoration: InputDecoration(
                      labelText: 'Password',
                      prefixIcon: const Icon(Icons.lock),
                      suffixIcon: IconButton(
                        onPressed: () => setState(() => _obscure = !_obscure),
                        icon: Icon(
                          _obscure ? Icons.visibility : Icons.visibility_off,
                        ),
                      ),
                    ),
                    validator: (value) => value == null || value.isEmpty
                        ? 'Password is required'
                        : null,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 22),
            FilledButton.icon(
              onPressed: _loading ? null : _login,
              icon: _loading
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.login),
              label: const Text('Login'),
            ),
          ],
        ),
      ),
    );
  }
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, required this.client, required this.onLogout});

  final ApiClient client;
  final VoidCallback onLogout;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _index = 0;
  Map<String, dynamic>? _me;
  List<dynamic> _projects = [];
  List<dynamic> _reports = [];
  List<dynamic> _roleReports = [];
  List<dynamic> _notifications = [];
  int _unreadNotifications = 0;
  bool _loading = true;

  bool get _canSubmitDailyReport {
    final permissions = _me?['permissions'] as Map<String, dynamic>?;
    return permissions?['can_submit_daily_report'] == true ||
        _me?['role'] == 'SITE_ENGINEER';
  }

  @override
  void initState() {
    super.initState();
    _refreshAll();
  }

  Future<void> _refreshAll() async {
    setState(() => _loading = true);
    try {
      final results = await Future.wait([
        widget.client.getJson('/mobile/me/'),
        widget.client.getJson('/mobile/projects/'),
        widget.client.getJson('/mobile/daily-reports/'),
        widget.client.getJson('/mobile/role-reports/'),
        widget.client.getJson('/mobile/notifications/'),
      ]);
      setState(() {
        _me = results[0];
        _projects = (results[1]['results'] as List?) ?? [];
        _reports = (results[2]['results'] as List?) ?? [];
        _roleReports = (results[3]['results'] as List?) ?? [];
        _notifications = (results[4]['results'] as List?) ?? [];
        _unreadNotifications =
            (results[4]['unread_count'] as num?)?.toInt() ??
            _notifications.where((item) => item['status'] == 'UNREAD').length;
      });
    } on AuthExpiredException catch (error) {
      if (mounted) _showSnack(context, error.message);
      widget.onLogout();
    } catch (error) {
      if (mounted) _showSnack(context, error.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final role = _me?['role']?.toString();
    final roleConfig = _roleConfigFor(role);
    final pages = [
      _RoleWorkspacePage(
        me: _me,
        projects: _projects,
        reports: _reports,
        notifications: _notifications,
        config: roleConfig,
        canSubmitDailyReport: _canSubmitDailyReport,
        onOpenReport: _openReportForm,
        onOpenRoleReport: _openRoleReportForm,
      ),
      _ProjectsPage(
        projects: _projects,
        me: _me,
        canSubmitDailyReport: _canSubmitDailyReport,
        onOpen: _openReportForm,
      ),
      _ReportsPage(dailyReports: _reports, roleReports: _roleReports),
      _NotificationsPage(
        notifications: _notifications,
        onMarkRead: _markNotificationRead,
      ),
    ];
    return Scaffold(
      appBar: AppBar(
        title: Text('CCMS ${roleConfig.title}'),
        actions: [
          IconButton(onPressed: _refreshAll, icon: const Icon(Icons.refresh)),
          PopupMenuButton<String>(
            onSelected: (value) {
              if (value == 'logout') widget.onLogout();
            },
            itemBuilder: (context) => const [
              PopupMenuItem(value: 'logout', child: Text('Logout')),
            ],
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(onRefresh: _refreshAll, child: pages[_index]),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (value) => setState(() => _index = value),
        destinations: [
          NavigationDestination(icon: Icon(roleConfig.icon), label: 'Work'),
          const NavigationDestination(
            icon: Icon(Icons.apartment),
            label: 'Projects',
          ),
          const NavigationDestination(
            icon: Icon(Icons.assignment),
            label: 'Reports',
          ),
          NavigationDestination(
            icon: _unreadNotifications > 0
                ? Badge(
                    label: Text(_unreadNotifications.toString()),
                    child: const Icon(Icons.notifications),
                  )
                : const Icon(Icons.notifications),
            label: 'Alerts',
          ),
        ],
      ),
      floatingActionButton:
          (_index == 0 || _index == 1) &&
              _projects.isNotEmpty &&
              _canSubmitDailyReport
          ? FloatingActionButton.extended(
              onPressed: () => _openReportForm(_projects.first),
              icon: const Icon(Icons.add_a_photo),
              label: const Text('Daily Report'),
            )
          : null,
    );
  }

  Future<void> _openReportForm(dynamic project) async {
    final submitted = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (context) => DailyReportFormScreen(
          client: widget.client,
          project: project as Map<String, dynamic>,
        ),
      ),
    );
    if (submitted == true) _refreshAll();
  }

  Future<void> _openRoleReportForm() async {
    if (_projects.isEmpty) return;
    final submitted = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (context) => RoleReportFormScreen(
          client: widget.client,
          projects: _projects.cast<Map<String, dynamic>>(),
          me: _me,
        ),
      ),
    );
    if (submitted == true) _refreshAll();
  }

  Future<void> _markNotificationRead(Map<String, dynamic> item) async {
    if (item['status'] != 'UNREAD') return;
    final id = item['id'];
    if (id == null) return;
    try {
      final result = await widget.client.postJson(
        '/mobile/notifications/$id/read/',
      );
      setState(() {
        item['status'] = 'READ';
        _unreadNotifications =
            (result['unread_count'] as num?)?.toInt() ??
            _notifications.where((row) => row['status'] == 'UNREAD').length;
      });
    } on AuthExpiredException catch (error) {
      if (mounted) _showSnack(context, error.message);
      widget.onLogout();
    } catch (error) {
      if (mounted) _showSnack(context, error.toString());
    }
  }
}

class _RoleConfig {
  const _RoleConfig({
    required this.title,
    required this.headline,
    required this.description,
    required this.icon,
    required this.color,
    required this.modules,
  });

  final String title;
  final String headline;
  final String description;
  final IconData icon;
  final Color color;
  final List<_RoleModule> modules;
}

class _RoleModule {
  const _RoleModule({
    required this.title,
    required this.subtitle,
    required this.icon,
    this.action,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final String? action;
}

_RoleConfig _roleConfigFor(String? role) {
  switch (role) {
    case 'SITE_ENGINEER':
      return const _RoleConfig(
        title: 'Site Engineer',
        headline: 'Field reporting workspace',
        description:
            'Submit daily progress, actual quantity, manpower total, materials, equipment, documents, and progress photos.',
        icon: Icons.engineering,
        color: Color(0xFF2563EB),
        modules: [
          _RoleModule(
            title: 'New Daily Report',
            subtitle: 'Submit today work progress with at least 4 photos.',
            icon: Icons.add_a_photo,
            action: 'daily_report',
          ),
          _RoleModule(
            title: 'Submitted Reports',
            subtitle:
                'Track pending, verified, rejected, and approved reports.',
            icon: Icons.assignment_turned_in,
          ),
          _RoleModule(
            title: 'Project Resources',
            subtitle:
                'Use assigned work items, material, manpower, and equipment.',
            icon: Icons.inventory_2,
          ),
        ],
      );
    case 'HSE_OFFICER':
      return const _RoleConfig(
        title: 'HSE Officer',
        headline: 'Safety monitoring workspace',
        description:
            'Focus on site safety reports, incidents, unsafe acts, unsafe conditions, and HSE alerts for assigned projects.',
        icon: Icons.health_and_safety,
        color: Color(0xFFDC2626),
        modules: [
          _RoleModule(
            title: 'HSE Reports',
            subtitle: 'Review incident and safety report notifications.',
            icon: Icons.security,
          ),
          _RoleModule(
            title: 'Safety Alerts',
            subtitle: 'Follow critical alerts from assigned projects.',
            icon: Icons.warning_amber,
          ),
          _RoleModule(
            title: 'Assigned Projects',
            subtitle:
                'Monitor only projects where you are assigned as safety officer.',
            icon: Icons.apartment,
          ),
        ],
      );
    case 'QA_QC':
      return const _RoleConfig(
        title: 'QA/QC',
        headline: 'Quality control workspace',
        description:
            'Focus on inspections, material tests, NCR follow-up, and quality-related notifications.',
        icon: Icons.fact_check,
        color: Color(0xFF7C3AED),
        modules: [
          _RoleModule(
            title: 'Inspection Review',
            subtitle:
                'Monitor QA/QC inspection updates from assigned projects.',
            icon: Icons.checklist,
          ),
          _RoleModule(
            title: 'Material Tests',
            subtitle: 'Track test records and quality status.',
            icon: Icons.science,
          ),
          _RoleModule(
            title: 'Quality Alerts',
            subtitle: 'Follow NCR and quality approval notifications.',
            icon: Icons.report_problem,
          ),
        ],
      );
    case 'LOGISTICS':
      return const _RoleConfig(
        title: 'Logistics',
        headline: 'Delivery and movement workspace',
        description:
            'Focus on delivery tracking, material receiving, stock issue, return, and transfer notifications.',
        icon: Icons.local_shipping,
        color: Color(0xFF0891B2),
        modules: [
          _RoleModule(
            title: 'Logistics Records',
            subtitle:
                'Monitor delivery, receiving, issue, return, and transfer activity.',
            icon: Icons.route,
          ),
          _RoleModule(
            title: 'Material Requests',
            subtitle: 'Follow approved requests that need delivery action.',
            icon: Icons.inventory,
          ),
          _RoleModule(
            title: 'Stock Movement',
            subtitle: 'Check movement alerts for assigned projects.',
            icon: Icons.swap_horiz,
          ),
        ],
      );
    case 'STOREKEEPER':
      return const _RoleConfig(
        title: 'Storekeeper',
        headline: 'Inventory workspace',
        description:
            'Focus on stock availability, material issue, receiving, low stock, and inventory alerts.',
        icon: Icons.warehouse,
        color: Color(0xFF0F766E),
        modules: [
          _RoleModule(
            title: 'Inventory & Stock',
            subtitle: 'Monitor material stock for assigned projects.',
            icon: Icons.inventory_2,
          ),
          _RoleModule(
            title: 'Material Requests',
            subtitle: 'Follow material requests and stock issue needs.',
            icon: Icons.assignment,
          ),
          _RoleModule(
            title: 'Low Stock Alerts',
            subtitle: 'Review inventory alerts from the system.',
            icon: Icons.production_quantity_limits,
          ),
        ],
      );
    case 'ADMIN_SITE':
      return const _RoleConfig(
        title: 'Admin Site',
        headline: 'Site administration workspace',
        description:
            'Focus on manpower, attendance, equipment administration, and site records.',
        icon: Icons.groups,
        color: Color(0xFF16A34A),
        modules: [
          _RoleModule(
            title: 'Manpower',
            subtitle: 'Monitor staff and worker data for assigned projects.',
            icon: Icons.badge,
          ),
          _RoleModule(
            title: 'Attendance',
            subtitle: 'Track attendance-related project records.',
            icon: Icons.how_to_reg,
          ),
          _RoleModule(
            title: 'Equipment',
            subtitle: 'Monitor assigned project equipment records.',
            icon: Icons.precision_manufacturing,
          ),
        ],
      );
    case 'DOC_CONTROLLER':
      return const _RoleConfig(
        title: 'Document Controller',
        headline: 'Document control workspace',
        description:
            'Focus on submitted documents, revisions, review status, and document alerts.',
        icon: Icons.folder_copy,
        color: Color(0xFF475569),
        modules: [
          _RoleModule(
            title: 'Document Register',
            subtitle: 'Monitor documents submitted from assigned projects.',
            icon: Icons.folder,
          ),
          _RoleModule(
            title: 'Revision Follow-up',
            subtitle: 'Track revision required and approval status.',
            icon: Icons.history,
          ),
          _RoleModule(
            title: 'Document Alerts',
            subtitle: 'Review document notifications that need action.',
            icon: Icons.mark_email_unread,
          ),
        ],
      );
    case 'COST_ENGINEER':
    case 'FINANCE_SITE':
    case 'FINANCE_HQ':
      return const _RoleConfig(
        title: 'Cost & Finance',
        headline: 'Cost and approval workspace',
        description:
            'Focus on cost control, variation orders, invoices, payment records, and finance approvals.',
        icon: Icons.payments,
        color: Color(0xFFD97706),
        modules: [
          _RoleModule(
            title: 'Cost Control',
            subtitle: 'Monitor budget, actual cost, and variance.',
            icon: Icons.account_balance_wallet,
          ),
          _RoleModule(
            title: 'Approvals',
            subtitle: 'Follow VO, invoice, and payment approval alerts.',
            icon: Icons.approval,
          ),
          _RoleModule(
            title: 'Financial Reports',
            subtitle: 'Review cost-related project report summaries.',
            icon: Icons.query_stats,
          ),
        ],
      );
    case 'PROJECT_MANAGER':
    case 'PROJECT_DIRECTOR':
    case 'HQ_DIRECTOR':
    case 'ADMIN_SYSTEM':
      return const _RoleConfig(
        title: 'Management',
        headline: 'Project control workspace',
        description:
            'Review project progress, pending reports, approvals, cost, material, HSE, QA/QC, and document alerts.',
        icon: Icons.dashboard_customize,
        color: Color(0xFF0F172A),
        modules: [
          _RoleModule(
            title: 'Review Daily Reports',
            subtitle: 'Monitor reports waiting for review or approval.',
            icon: Icons.rate_review,
          ),
          _RoleModule(
            title: 'Approvals',
            subtitle: 'Track approval items across assigned projects.',
            icon: Icons.verified,
          ),
          _RoleModule(
            title: 'Project Monitoring',
            subtitle:
                'Follow progress, cost, material, quality, and safety indicators.',
            icon: Icons.analytics,
          ),
        ],
      );
    default:
      return const _RoleConfig(
        title: 'Workspace',
        headline: 'Assigned work workspace',
        description:
            'Your view is limited to projects and notifications assigned to your account.',
        icon: Icons.work,
        color: Color(0xFF2563EB),
        modules: [
          _RoleModule(
            title: 'Assigned Projects',
            subtitle: 'Open projects assigned to your user.',
            icon: Icons.apartment,
          ),
          _RoleModule(
            title: 'Reports',
            subtitle: 'Review available reports for your project scope.',
            icon: Icons.assignment,
          ),
          _RoleModule(
            title: 'Alerts',
            subtitle: 'Follow notifications from the system.',
            icon: Icons.notifications,
          ),
        ],
      );
  }
}

class _RoleWorkspacePage extends StatelessWidget {
  const _RoleWorkspacePage({
    required this.me,
    required this.projects,
    required this.reports,
    required this.notifications,
    required this.config,
    required this.canSubmitDailyReport,
    required this.onOpenReport,
    required this.onOpenRoleReport,
  });

  final Map<String, dynamic>? me;
  final List<dynamic> projects;
  final List<dynamic> reports;
  final List<dynamic> notifications;
  final _RoleConfig config;
  final bool canSubmitDailyReport;
  final ValueChanged<dynamic> onOpenReport;
  final VoidCallback onOpenRoleReport;

  int get _pendingReportCount =>
      reports.where((report) => report['status'] == 'PENDING').length;

  int get _unreadAlertCount =>
      notifications.where((item) => item['status'] == 'UNREAD').length;

  @override
  Widget build(BuildContext context) {
    final recentProjects = projects.take(3).toList();
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _RoleHeaderCard(me: me, config: config, projectCount: projects.length),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: _MetricTile(
                label: 'Projects',
                value: projects.length.toString(),
                icon: Icons.apartment,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _MetricTile(
                label: 'Reports',
                value: reports.length.toString(),
                icon: Icons.assignment,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _MetricTile(
                label: 'Alerts',
                value: _unreadAlertCount.toString(),
                icon: Icons.notifications,
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        Text(
          'Your Work',
          style: Theme.of(
            context,
          ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
        ),
        const SizedBox(height: 8),
        if (!canSubmitDailyReport) ...[
          _RoleModuleCard(
            module: const _RoleModule(
              title: 'Submit Role Report',
              subtitle:
                  'Create a report for your current role and assigned project.',
              icon: Icons.note_add,
            ),
            color: config.color,
            enabled: projects.isNotEmpty,
            onTap: projects.isNotEmpty ? onOpenRoleReport : null,
          ),
          const SizedBox(height: 8),
        ],
        for (final module in config.modules) ...[
          _RoleModuleCard(
            module: module,
            color: config.color,
            enabled:
                module.action != 'daily_report' ||
                (canSubmitDailyReport && projects.isNotEmpty),
            onTap: module.action == 'daily_report' && projects.isNotEmpty
                ? () => onOpenReport(projects.first)
                : null,
          ),
          const SizedBox(height: 8),
        ],
        const SizedBox(height: 8),
        Text(
          'Current Scope',
          style: Theme.of(
            context,
          ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800),
        ),
        const SizedBox(height: 8),
        if (recentProjects.isEmpty)
          const _EmptyState(
            icon: Icons.apartment,
            text: 'No assigned projects found.',
          )
        else
          for (final project in recentProjects)
            Card(
              child: ListTile(
                leading: Icon(Icons.business, color: config.color),
                title: Text(
                  project['name']?.toString() ?? 'Project',
                  style: const TextStyle(fontWeight: FontWeight.w800),
                ),
                subtitle: Text(
                  '${project['project_code'] ?? '-'}  -  ${project['location'] ?? ''}',
                ),
                trailing: Text(project['status']?.toString() ?? ''),
                onTap: canSubmitDailyReport
                    ? () => onOpenReport(project)
                    : null,
              ),
            ),
        if (_pendingReportCount > 0) ...[
          const SizedBox(height: 8),
          _InfoBanner(
            icon: Icons.pending_actions,
            text: '$_pendingReportCount report waiting for next action.',
          ),
        ],
      ],
    );
  }
}

class _RoleHeaderCard extends StatelessWidget {
  const _RoleHeaderCard({
    required this.me,
    required this.config,
    required this.projectCount,
  });

  final Map<String, dynamic>? me;
  final _RoleConfig config;
  final int projectCount;

  @override
  Widget build(BuildContext context) {
    return Card(
      color: config.color,
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(config.icon, color: Colors.white, size: 36),
            const SizedBox(height: 14),
            Text(
              config.headline,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 22,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              config.description,
              style: const TextStyle(color: Color(0xFFE2E8F0), height: 1.35),
            ),
            const SizedBox(height: 12),
            Text(
              '${me?['role_display'] ?? config.title}  -  $projectCount projects',
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _MetricTile extends StatelessWidget {
  const _MetricTile({
    required this.label,
    required this.value,
    required this.icon,
  });

  final String label;
  final String value;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: Theme.of(context).colorScheme.primary),
            const SizedBox(height: 8),
            Text(
              value,
              style: Theme.of(
                context,
              ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w900),
            ),
            Text(label, style: Theme.of(context).textTheme.bodySmall),
          ],
        ),
      ),
    );
  }
}

class _RoleModuleCard extends StatelessWidget {
  const _RoleModuleCard({
    required this.module,
    required this.color,
    required this.enabled,
    this.onTap,
  });

  final _RoleModule module;
  final Color color;
  final bool enabled;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final muted = !enabled;
    return Card(
      child: ListTile(
        contentPadding: const EdgeInsets.all(16),
        leading: CircleAvatar(
          backgroundColor: color.withValues(alpha: muted ? 0.08 : 0.14),
          foregroundColor: muted ? Colors.grey : color,
          child: Icon(module.icon),
        ),
        title: Text(
          module.title,
          style: TextStyle(
            fontWeight: FontWeight.w800,
            color: muted ? Colors.grey : null,
          ),
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 4),
          child: Text(module.subtitle),
        ),
        trailing: onTap == null
            ? const Icon(Icons.info_outline)
            : const Icon(Icons.chevron_right),
        onTap: enabled ? onTap : null,
      ),
    );
  }
}

class _InfoBanner extends StatelessWidget {
  const _InfoBanner({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Card(
      color: const Color(0xFFEFF6FF),
      child: ListTile(
        leading: Icon(icon, color: const Color(0xFF2563EB)),
        title: Text(text, style: const TextStyle(fontWeight: FontWeight.w700)),
      ),
    );
  }
}

class _ProjectsPage extends StatelessWidget {
  const _ProjectsPage({
    required this.projects,
    required this.me,
    required this.canSubmitDailyReport,
    required this.onOpen,
  });

  final List<dynamic> projects;
  final Map<String, dynamic>? me;
  final bool canSubmitDailyReport;
  final ValueChanged<dynamic> onOpen;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _SummaryCard(me: me, projectCount: projects.length),
        const SizedBox(height: 12),
        Text(
          'Assigned Projects',
          style: Theme.of(
            context,
          ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
        ),
        if (!canSubmitDailyReport) ...[
          const SizedBox(height: 6),
          Text(
            'Daily report submission is limited to Site Engineer accounts.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
        const SizedBox(height: 8),
        if (projects.isEmpty)
          const _EmptyState(
            icon: Icons.apartment,
            text: 'No assigned projects found.',
          )
        else
          for (final project in projects)
            Card(
              child: ListTile(
                contentPadding: const EdgeInsets.all(16),
                title: Text(
                  project['name']?.toString() ?? 'Project',
                  style: const TextStyle(fontWeight: FontWeight.w800),
                ),
                subtitle: Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Text(
                    '${project['project_code'] ?? '-'}\n${project['location'] ?? ''}',
                  ),
                ),
                isThreeLine: true,
                trailing: Icon(
                  canSubmitDailyReport
                      ? Icons.chevron_right
                      : Icons.visibility_outlined,
                ),
                onTap: canSubmitDailyReport ? () => onOpen(project) : null,
              ),
            ),
      ],
    );
  }
}

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({required this.me, required this.projectCount});

  final Map<String, dynamic>? me;
  final int projectCount;

  @override
  Widget build(BuildContext context) {
    return Card(
      color: const Color(0xFF0F172A),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(Icons.engineering, color: Colors.white, size: 34),
            const SizedBox(height: 12),
            Text(
              me == null ? 'Welcome' : 'Welcome, ${me!['username']}',
              style: const TextStyle(
                color: Colors.white,
                fontSize: 22,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              '${me?['role_display'] ?? 'Site Engineer'}  -  $projectCount projects',
              style: const TextStyle(color: Color(0xFFCBD5E1)),
            ),
          ],
        ),
      ),
    );
  }
}

class _ReportsPage extends StatelessWidget {
  const _ReportsPage({required this.dailyReports, required this.roleReports});

  final List<dynamic> dailyReports;
  final List<dynamic> roleReports;

  @override
  Widget build(BuildContext context) {
    if (dailyReports.isEmpty && roleReports.isEmpty) {
      return ListView(
        children: [
          _EmptyState(
            icon: Icons.assignment_outlined,
            text: 'No daily reports submitted yet.',
          ),
        ],
      );
    }
    final rows = [
      for (final report in dailyReports) {'kind': 'daily', 'data': report},
      for (final report in roleReports) {'kind': 'role', 'data': report},
    ];
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: rows.length,
      itemBuilder: (context, index) {
        final row = rows[index];
        final kind = row['kind'] as String;
        final report = row['data'] as Map<String, dynamic>;
        final project = report['project'] as Map<String, dynamic>? ?? {};
        return Card(
          child: ListTile(
            contentPadding: const EdgeInsets.all(16),
            leading: Icon(
              kind == 'daily' ? Icons.assignment : Icons.note_alt,
              color: Theme.of(context).colorScheme.primary,
            ),
            title: Text(
              kind == 'daily'
                  ? project['name']?.toString() ?? 'Project'
                  : report['title']?.toString() ?? 'Role Report',
              style: const TextStyle(fontWeight: FontWeight.w800),
            ),
            subtitle: Text(
              kind == 'daily'
                  ? '${report['date']}  -  ${report['progress_percentage']}%  -  ${report['photo_count']} photos'
                  : '${project['name'] ?? 'Project'}  -  ${report['report_type'] ?? '-'}\n${report['report_date'] ?? ''}  -  ${report['priority'] ?? 'MEDIUM'}',
            ),
            isThreeLine: kind != 'daily',
            trailing: _StatusPill(status: report['status']?.toString() ?? '-'),
          ),
        );
      },
    );
  }
}

class _NotificationsPage extends StatelessWidget {
  const _NotificationsPage({
    required this.notifications,
    required this.onMarkRead,
  });

  final List<dynamic> notifications;
  final ValueChanged<Map<String, dynamic>> onMarkRead;

  @override
  Widget build(BuildContext context) {
    if (notifications.isEmpty) {
      return ListView(
        children: [
          _EmptyState(
            icon: Icons.notifications_none,
            text: 'No notifications.',
          ),
        ],
      );
    }
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: notifications.length,
      itemBuilder: (context, index) {
        final item = notifications[index] as Map<String, dynamic>;
        return Card(
          child: ListTile(
            contentPadding: const EdgeInsets.all(16),
            leading: Icon(
              item['status'] == 'UNREAD'
                  ? Icons.notifications_active
                  : Icons.notifications_none,
              color: item['status'] == 'UNREAD'
                  ? Theme.of(context).colorScheme.primary
                  : null,
            ),
            title: Text(
              item['title']?.toString() ?? 'Notification',
              style: const TextStyle(fontWeight: FontWeight.w800),
            ),
            subtitle: Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(
                '${item['message']?.toString() ?? ''}\n${item['type'] ?? 'INFO'}'
                '${item['related_module'] == null ? '' : ' - ${item['related_module']}'}',
              ),
            ),
            trailing: item['status'] == 'UNREAD'
                ? const Icon(Icons.mark_email_read_outlined)
                : const Icon(Icons.check_circle_outline),
            onTap: () => onMarkRead(item),
          ),
        );
      },
    );
  }
}

class RoleReportFormScreen extends StatefulWidget {
  const RoleReportFormScreen({
    super.key,
    required this.client,
    required this.projects,
    required this.me,
  });

  final ApiClient client;
  final List<Map<String, dynamic>> projects;
  final Map<String, dynamic>? me;

  @override
  State<RoleReportFormScreen> createState() => _RoleReportFormScreenState();
}

class _RoleReportFormScreenState extends State<RoleReportFormScreen> {
  final _formKey = GlobalKey<FormState>();
  final _titleController = TextEditingController();
  final _locationController = TextEditingController();
  final _descriptionController = TextEditingController();
  DateTime _reportDate = DateTime.now();
  int? _projectId;
  String _priority = 'MEDIUM';
  String? _reportType;
  bool _submitting = false;

  @override
  void initState() {
    super.initState();
    _projectId = widget.projects.isEmpty
        ? null
        : widget.projects.first['id'] as int?;
    final types = _reportTypesForRole(widget.me?['role']?.toString());
    _reportType = types.first;
  }

  @override
  void dispose() {
    _titleController.dispose();
    _locationController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  String _dateText(DateTime value) {
    final month = value.month.toString().padLeft(2, '0');
    final day = value.day.toString().padLeft(2, '0');
    return '${value.year}-$month-$day';
  }

  List<String> _reportTypesForRole(String? role) {
    switch (role) {
      case 'HSE_OFFICER':
        return const ['HSE Daily', 'Incident', 'Near Miss', 'Unsafe Condition'];
      case 'QA_QC':
        return const ['QA/QC Inspection', 'Material Test', 'NCR Follow-up'];
      case 'LOGISTICS':
        return const ['Delivery Update', 'Receiving Report', 'Stock Movement'];
      case 'STOREKEEPER':
        return const ['Inventory Report', 'Low Stock', 'Material Issue'];
      case 'ADMIN_SITE':
        return const ['Manpower Report', 'Attendance Report', 'Site Admin'];
      case 'DOC_CONTROLLER':
        return const [
          'Document Report',
          'Revision Follow-up',
          'Submission Log',
        ];
      case 'COST_ENGINEER':
      case 'FINANCE_SITE':
      case 'FINANCE_HQ':
        return const ['Cost Report', 'Payment Report', 'Invoice Follow-up'];
      case 'PROJECT_MANAGER':
      case 'PROJECT_DIRECTOR':
      case 'HQ_DIRECTOR':
      case 'ADMIN_SYSTEM':
        return const ['Management Report', 'Approval Note', 'Project Issue'];
      case 'SUPERVISOR':
        return const ['Supervisor Report', 'Field Issue', 'Work Update'];
      case 'CONSULTANT':
        return const [
          'Consultant Review',
          'Technical Note',
          'Approval Comment',
        ];
      default:
        return const ['General Report', 'Issue Report', 'Work Update'];
    }
  }

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _reportDate,
      firstDate: DateTime(2020),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (picked != null) setState(() => _reportDate = picked);
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_projectId == null) {
      _showSnack(context, 'Project is required.');
      return;
    }
    setState(() => _submitting = true);
    try {
      await widget.client.postJson('/mobile/role-reports/submit/', {
        'project_id': _projectId,
        'report_type': _reportType,
        'title': _titleController.text.trim(),
        'description': _descriptionController.text.trim(),
        'location': _locationController.text.trim(),
        'priority': _priority,
        'report_date': _dateText(_reportDate),
      });
      if (!mounted) return;
      _showSnack(context, 'Role report submitted.');
      Navigator.of(context).pop(true);
    } catch (error) {
      if (mounted) _showSnack(context, error.toString());
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final reportTypes = _reportTypesForRole(widget.me?['role']?.toString());
    return Scaffold(
      appBar: AppBar(title: const Text('New Role Report')),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            _SectionTitle(
              title: widget.me?['role_display']?.toString() ?? 'Role Report',
              subtitle: 'Submit a report for your assigned project and role.',
            ),
            DropdownButtonFormField<int>(
              initialValue: _projectId,
              isExpanded: true,
              decoration: const InputDecoration(
                labelText: 'Project *',
                prefixIcon: Icon(Icons.apartment),
              ),
              items: [
                for (final project in widget.projects)
                  DropdownMenuItem<int>(
                    value: project['id'] as int?,
                    child: Text(
                      project['name']?.toString() ?? 'Project',
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
              ],
              validator: (value) =>
                  value == null ? 'Project is required' : null,
              onChanged: (value) => setState(() => _projectId = value),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: _reportType,
              isExpanded: true,
              decoration: const InputDecoration(
                labelText: 'Report Type *',
                prefixIcon: Icon(Icons.category),
              ),
              items: [
                for (final type in reportTypes)
                  DropdownMenuItem(value: type, child: Text(type)),
              ],
              validator: (value) => value == null || value.isEmpty
                  ? 'Report type is required'
                  : null,
              onChanged: (value) => setState(() => _reportType = value),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: _pickDate,
              icon: const Icon(Icons.calendar_month),
              label: Text(_dateText(_reportDate)),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: _priority,
              decoration: const InputDecoration(
                labelText: 'Priority *',
                prefixIcon: Icon(Icons.flag),
              ),
              items: const [
                DropdownMenuItem(value: 'LOW', child: Text('Low')),
                DropdownMenuItem(value: 'MEDIUM', child: Text('Medium')),
                DropdownMenuItem(value: 'HIGH', child: Text('High')),
                DropdownMenuItem(value: 'CRITICAL', child: Text('Critical')),
              ],
              onChanged: (value) =>
                  setState(() => _priority = value ?? 'MEDIUM'),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _titleController,
              decoration: const InputDecoration(
                labelText: 'Title *',
                prefixIcon: Icon(Icons.title),
              ),
              validator: (value) => value == null || value.trim().isEmpty
                  ? 'Title is required'
                  : null,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _locationController,
              decoration: const InputDecoration(
                labelText: 'Location',
                prefixIcon: Icon(Icons.place),
              ),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _descriptionController,
              minLines: 5,
              maxLines: 9,
              decoration: const InputDecoration(
                labelText: 'Report Detail *',
                alignLabelWithHint: true,
              ),
              validator: (value) => value == null || value.trim().isEmpty
                  ? 'Report detail is required'
                  : null,
            ),
            const SizedBox(height: 22),
            FilledButton.icon(
              onPressed: _submitting ? null : _submit,
              icon: _submitting
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.send),
              label: const Text('Submit Report'),
            ),
          ],
        ),
      ),
    );
  }
}

class DailyReportFormScreen extends StatefulWidget {
  const DailyReportFormScreen({
    super.key,
    required this.client,
    required this.project,
  });

  final ApiClient client;
  final Map<String, dynamic> project;

  @override
  State<DailyReportFormScreen> createState() => _DailyReportFormScreenState();
}

class _DailyReportFormScreenState extends State<DailyReportFormScreen> {
  final _formKey = GlobalKey<FormState>();
  final _workController = TextEditingController();
  final _issuesController = TextEditingController();
  final _progressController = TextEditingController(text: '0');
  final _manpowerController = TextEditingController(text: '0');
  final _actualQuantityController = TextEditingController();
  final _picker = ImagePicker();

  bool _loading = true;
  bool _submitting = false;
  DateTime _reportDate = DateTime.now();
  String _weather = 'Sunny';
  List<dynamic> _workItems = [];
  List<dynamic> _materials = [];
  List<dynamic> _manpower = [];
  List<dynamic> _equipment = [];
  String? _selectedCategory;
  int? _selectedWorkItemId;
  PlatformFile? _supportDocument;
  final List<XFile> _photos = [];
  final List<_MaterialReportRow> _materialRows = List.generate(
    1,
    (_) => _MaterialReportRow(),
  );
  final List<_EquipmentReportRow> _equipmentRows = List.generate(
    3,
    (_) => _EquipmentReportRow(),
  );

  @override
  void initState() {
    super.initState();
    _loadResources();
  }

  @override
  void dispose() {
    _workController.dispose();
    _issuesController.dispose();
    _progressController.dispose();
    _manpowerController.dispose();
    _actualQuantityController.dispose();
    for (final row in _materialRows) {
      row.dispose();
    }
    for (final row in _equipmentRows) {
      row.dispose();
    }
    super.dispose();
  }

  Future<void> _loadResources() async {
    try {
      final data = await widget.client.getJson(
        '/mobile/projects/${widget.project['id']}/resources/',
      );
      setState(() {
        _workItems = (data['work_items'] as List?) ?? [];
        _materials = (data['materials'] as List?) ?? [];
        _manpower = (data['manpower'] as List?) ?? [];
        _equipment = (data['equipment'] as List?) ?? [];
        if (_workItems.isNotEmpty) {
          _selectedCategory = _categoryOf(_workItems.first);
          _selectedWorkItemId = _workItems.first['id'] as int?;
        }
      });
    } catch (error) {
      if (mounted) _showSnack(context, error.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _pickPhoto(ImageSource source) async {
    final photo = await _picker.pickImage(
      source: source,
      imageQuality: 72,
      maxWidth: 1600,
    );
    if (photo == null) return;
    setState(() {
      _photos.add(photo);
    });
  }

  Future<void> _pickDocument() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: [
        'pdf',
        'doc',
        'docx',
        'xls',
        'xlsx',
        'csv',
        'txt',
        'jpg',
        'jpeg',
        'png',
      ],
    );
    final file = result?.files.single;
    if (file == null) return;
    setState(() => _supportDocument = file);
  }

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _reportDate,
      firstDate: DateTime(2020),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (picked != null) setState(() => _reportDate = picked);
  }

  String _dateText(DateTime value) {
    final month = value.month.toString().padLeft(2, '0');
    final day = value.day.toString().padLeft(2, '0');
    return '${value.year}-$month-$day';
  }

  String _categoryOf(dynamic item) {
    final category = item['category']?.toString().trim();
    return category == null || category.isEmpty ? 'General' : category;
  }

  List<String> get _categories {
    final seen = <String>{};
    for (final item in _workItems) {
      seen.add(_categoryOf(item));
    }
    return seen.toList()..sort();
  }

  List<dynamic> get _filteredWorkItems {
    if (_selectedCategory == null) return _workItems;
    return _workItems
        .where((item) => _categoryOf(item) == _selectedCategory)
        .toList();
  }

  List<Map<String, dynamic>> _materialPayload() {
    return _materialRows
        .where((row) => row.materialId != null)
        .map(
          (row) => {
            'id': row.materialId,
            'quantity': row.quantityController.text.trim(),
            'notes': row.notesController.text.trim(),
          },
        )
        .toList();
  }

  List<Map<String, dynamic>> _equipmentPayload() {
    return _equipmentRows
        .where((row) => row.equipmentId != null)
        .map(
          (row) => {
            'id': row.equipmentId,
            'hours': row.hoursController.text.trim(),
            'operator_id': row.operatorId,
            'notes': row.notesController.text.trim(),
          },
        )
        .toList();
  }

  void _addMaterialRow() {
    setState(() => _materialRows.add(_MaterialReportRow()));
  }

  void _removeMaterialRow(int index) {
    if (_materialRows.length <= 1) return;
    final row = _materialRows.removeAt(index);
    row.dispose();
    setState(() {});
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_photos.length < 4) {
      _showSnack(context, 'At least 4 progress photos are required.');
      return;
    }
    setState(() => _submitting = true);
    try {
      await widget.client.multipartDailyReport(
        fields: {
          'project_id': widget.project['id'].toString(),
          'date': _dateText(_reportDate),
          'weather': _weather,
          'work_done': _workController.text.trim(),
          'issues': _issuesController.text.trim(),
          'progress_percentage': _progressController.text.trim(),
          'manpower_count': _manpowerController.text.trim(),
          'materials_used': '',
          'equipment_used': '',
          'material_items_json': jsonEncode(_materialPayload()),
          'equipment_items_json': jsonEncode(_equipmentPayload()),
          if (_selectedWorkItemId != null)
            'work_item_id': _selectedWorkItemId.toString(),
          if (_actualQuantityController.text.trim().isNotEmpty)
            'actual_quantity': _actualQuantityController.text.trim(),
        },
        photos: _photos,
        supportDocument: _supportDocument,
      );
      if (!mounted) return;
      _showSnack(context, 'Daily report submitted.');
      Navigator.of(context).pop(true);
    } catch (error) {
      _showSnack(context, error.toString());
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final categories = _categories;
    final workItems = _filteredWorkItems;
    return Scaffold(
      appBar: AppBar(title: const Text('New Daily Report')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : Form(
              key: _formKey,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  Card(
                    child: ListTile(
                      title: Text(
                        widget.project['name']?.toString() ?? 'Project',
                        style: const TextStyle(fontWeight: FontWeight.w800),
                      ),
                      subtitle: Text(
                        widget.project['project_code']?.toString() ?? '',
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  _SectionTitle(
                    title: 'Report Date *',
                    subtitle: 'Same daily report date used in web.',
                  ),
                  OutlinedButton.icon(
                    onPressed: _pickDate,
                    icon: const Icon(Icons.calendar_month),
                    label: Text(_dateText(_reportDate)),
                  ),
                  const SizedBox(height: 12),
                  if (categories.isNotEmpty) ...[
                    DropdownButtonFormField<String>(
                      initialValue: _selectedCategory,
                      isExpanded: true,
                      decoration: const InputDecoration(
                        labelText: 'Work Category *',
                        prefixIcon: Icon(Icons.category),
                      ),
                      items: [
                        for (final category in categories)
                          DropdownMenuItem(
                            value: category,
                            child: Text(
                              category,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                      ],
                      onChanged: (value) {
                        final nextItems = _workItems
                            .where((item) => _categoryOf(item) == value)
                            .toList();
                        setState(() {
                          _selectedCategory = value;
                          _selectedWorkItemId = nextItems.isEmpty
                              ? null
                              : nextItems.first['id'] as int?;
                        });
                      },
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<int>(
                      initialValue: _selectedWorkItemId,
                      isExpanded: true,
                      decoration: const InputDecoration(
                        labelText: 'Work Item *',
                        prefixIcon: Icon(Icons.checklist),
                      ),
                      items: [
                        for (final item in workItems)
                          DropdownMenuItem<int>(
                            value: item['id'] as int?,
                            child: Text(
                              '${item['item_code'] ?? '-'} - ${item['item_name']} (BOQ ${item['boq_quantity'] ?? 0} ${item['unit'] ?? ''})',
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                      ],
                      validator: (value) =>
                          value == null ? 'Work item is required' : null,
                      onChanged: (value) =>
                          setState(() => _selectedWorkItemId = value),
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _actualQuantityController,
                      keyboardType: const TextInputType.numberWithOptions(
                        decimal: true,
                      ),
                      decoration: const InputDecoration(
                        labelText: 'Actual Quantity *',
                        prefixIcon: Icon(Icons.straighten),
                      ),
                      validator: (value) =>
                          value == null || value.trim().isEmpty
                          ? 'Actual quantity is required'
                          : null,
                    ),
                    const SizedBox(height: 12),
                  ],
                  _SectionTitle(
                    title: 'Weather Site *',
                    subtitle: 'Select the site weather condition.',
                  ),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      _WeatherChip(
                        label: 'Sunny',
                        icon: Icons.wb_sunny,
                        selected: _weather == 'Sunny',
                        onSelected: () => setState(() => _weather = 'Sunny'),
                      ),
                      _WeatherChip(
                        label: 'Cloudy',
                        icon: Icons.cloud,
                        selected: _weather == 'Cloudy',
                        onSelected: () => setState(() => _weather = 'Cloudy'),
                      ),
                      _WeatherChip(
                        label: 'Rainy',
                        icon: Icons.water_drop,
                        selected: _weather == 'Rainy',
                        onSelected: () => setState(() => _weather = 'Rainy'),
                      ),
                      _WeatherChip(
                        label: 'Storm',
                        icon: Icons.thunderstorm,
                        selected: _weather == 'Storm',
                        onSelected: () => setState(() => _weather = 'Storm'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _workController,
                    minLines: 4,
                    maxLines: 8,
                    decoration: const InputDecoration(
                      labelText: 'Work Done Today *',
                      alignLabelWithHint: true,
                    ),
                    validator: (value) => value == null || value.trim().isEmpty
                        ? 'Work done is required'
                        : null,
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: TextFormField(
                          controller: _progressController,
                          keyboardType: TextInputType.number,
                          decoration: const InputDecoration(
                            labelText: 'Progress %',
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: TextFormField(
                          controller: _manpowerController,
                          keyboardType: TextInputType.number,
                          decoration: const InputDecoration(
                            labelText: 'Total Staff Site *',
                          ),
                          validator: (value) => value == null || value.isEmpty
                              ? 'Total staff is required'
                              : null,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _issuesController,
                    minLines: 2,
                    maxLines: 5,
                    decoration: const InputDecoration(
                      labelText: 'Issues / Obstacles',
                      alignLabelWithHint: true,
                    ),
                  ),
                  const SizedBox(height: 16),
                  _SectionTitle(
                    title: 'Material Usage',
                    subtitle: 'Select from project material master.',
                  ),
                  for (
                    var index = 0;
                    index < _materialRows.length;
                    index++
                  ) ...[
                    _MaterialUsageFields(
                      row: _materialRows[index],
                      materials: _materials,
                      index: index + 1,
                      onChanged: () => setState(() {}),
                      onRemove: _materialRows.length > 1
                          ? () => _removeMaterialRow(index)
                          : null,
                    ),
                    const SizedBox(height: 10),
                  ],
                  Align(
                    alignment: Alignment.centerLeft,
                    child: OutlinedButton.icon(
                      onPressed: _addMaterialRow,
                      icon: const Icon(Icons.add),
                      label: const Text('Add Material'),
                    ),
                  ),
                  const SizedBox(height: 6),
                  _SectionTitle(
                    title: 'Equipment Usage',
                    subtitle: 'Select active or rented equipment in project.',
                  ),
                  for (
                    var index = 0;
                    index < _equipmentRows.length;
                    index++
                  ) ...[
                    _EquipmentUsageFields(
                      row: _equipmentRows[index],
                      equipment: _equipment,
                      manpower: _manpower,
                      index: index + 1,
                      onChanged: () => setState(() {}),
                    ),
                    const SizedBox(height: 10),
                  ],
                  const SizedBox(height: 6),
                  Text(
                    'Document and Progress Photos',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 8),
                  OutlinedButton.icon(
                    onPressed: _pickDocument,
                    icon: const Icon(Icons.attach_file),
                    label: Text(_supportDocument?.name ?? 'Document optional'),
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 10,
                    runSpacing: 10,
                    children: [
                      for (var index = 0; index < _photos.length; index++)
                        Stack(
                          children: [
                            ClipRRect(
                              borderRadius: BorderRadius.circular(12),
                              child: Image.file(
                                File(_photos[index].path),
                                width: 78,
                                height: 78,
                                fit: BoxFit.cover,
                              ),
                            ),
                            Positioned(
                              top: 2,
                              right: 2,
                              child: InkWell(
                                onTap: () =>
                                    setState(() => _photos.removeAt(index)),
                                child: Container(
                                  decoration: const BoxDecoration(
                                    color: Colors.black54,
                                    shape: BoxShape.circle,
                                  ),
                                  padding: const EdgeInsets.all(3),
                                  child: const Icon(
                                    Icons.close,
                                    color: Colors.white,
                                    size: 14,
                                  ),
                                ),
                              ),
                            ),
                          ],
                        ),
                      OutlinedButton.icon(
                        onPressed: () => _pickPhoto(ImageSource.camera),
                        icon: const Icon(Icons.camera_alt),
                        label: Text(
                          _photos.length < 4
                              ? 'Camera (${_photos.length}/4)'
                              : 'Camera',
                        ),
                      ),
                      OutlinedButton.icon(
                        onPressed: () => _pickPhoto(ImageSource.gallery),
                        icon: const Icon(Icons.photo_library),
                        label: Text(
                          _photos.length < 4
                              ? 'Gallery (${_photos.length}/4)'
                              : 'Gallery',
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 22),
                  FilledButton.icon(
                    onPressed: _submitting ? null : _submit,
                    icon: _submitting
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.send),
                    label: const Text('Submit Report'),
                  ),
                  const SizedBox(height: 32),
                ],
              ),
            ),
    );
  }
}

class _MaterialReportRow {
  int? materialId;
  final quantityController = TextEditingController();
  final notesController = TextEditingController();

  void dispose() {
    quantityController.dispose();
    notesController.dispose();
  }
}

class _EquipmentReportRow {
  int? equipmentId;
  int? operatorId;
  final hoursController = TextEditingController();
  final notesController = TextEditingController();

  void dispose() {
    hoursController.dispose();
    notesController.dispose();
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.title, required this.subtitle});

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: Theme.of(
              context,
            ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 2),
          Text(
            subtitle,
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: const Color(0xFF64748B)),
          ),
        ],
      ),
    );
  }
}

class _WeatherChip extends StatelessWidget {
  const _WeatherChip({
    required this.label,
    required this.icon,
    required this.selected,
    required this.onSelected,
  });

  final String label;
  final IconData icon;
  final bool selected;
  final VoidCallback onSelected;

  @override
  Widget build(BuildContext context) {
    return ChoiceChip(
      avatar: Icon(icon, size: 18),
      label: Text(label),
      selected: selected,
      onSelected: (_) => onSelected(),
    );
  }
}

class _MaterialUsageFields extends StatelessWidget {
  const _MaterialUsageFields({
    required this.row,
    required this.materials,
    required this.index,
    required this.onChanged,
    this.onRemove,
  });

  final _MaterialReportRow row;
  final List<dynamic> materials;
  final int index;
  final VoidCallback onChanged;
  final VoidCallback? onRemove;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Material $index',
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
                if (onRemove != null)
                  IconButton(
                    tooltip: 'Remove material',
                    onPressed: onRemove,
                    icon: const Icon(Icons.delete_outline),
                  ),
              ],
            ),
            DropdownButtonFormField<int>(
              initialValue: row.materialId,
              isExpanded: true,
              decoration: const InputDecoration(labelText: 'Material'),
              items: [
                for (final material in materials)
                  DropdownMenuItem<int>(
                    value: material['id'] as int?,
                    child: Text(
                      '${material['item_code'] ?? '-'} - ${material['name']} (${material['unit'] ?? ''})',
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
              ],
              onChanged: (value) {
                row.materialId = value;
                onChanged();
              },
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    controller: row.quantityController,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    decoration: const InputDecoration(labelText: 'Qty'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  flex: 2,
                  child: TextFormField(
                    controller: row.notesController,
                    decoration: const InputDecoration(
                      labelText: 'Notes/location',
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _EquipmentUsageFields extends StatelessWidget {
  const _EquipmentUsageFields({
    required this.row,
    required this.equipment,
    required this.manpower,
    required this.index,
    required this.onChanged,
  });

  final _EquipmentReportRow row;
  final List<dynamic> equipment;
  final List<dynamic> manpower;
  final int index;
  final VoidCallback onChanged;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            DropdownButtonFormField<int>(
              initialValue: row.equipmentId,
              isExpanded: true,
              decoration: InputDecoration(labelText: 'Equipment $index'),
              items: [
                for (final item in equipment)
                  DropdownMenuItem<int>(
                    value: item['id'] as int?,
                    child: Text(
                      '${item['equipment_code'] ?? '-'} - ${item['name']}',
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
              ],
              onChanged: (value) {
                row.equipmentId = value;
                onChanged();
              },
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    controller: row.hoursController,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    decoration: const InputDecoration(labelText: 'Hours'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  flex: 2,
                  child: DropdownButtonFormField<int>(
                    initialValue: row.operatorId,
                    isExpanded: true,
                    decoration: const InputDecoration(labelText: 'Operator'),
                    items: [
                      for (final person in manpower)
                        DropdownMenuItem<int>(
                          value: person['id'] as int?,
                          child: Text(
                            person['name']?.toString() ?? 'Operator',
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                    ],
                    onChanged: (value) {
                      row.operatorId = value;
                      onChanged();
                    },
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            TextFormField(
              controller: row.notesController,
              decoration: const InputDecoration(labelText: 'Activity/notes'),
            ),
          ],
        ),
      ),
    );
  }
}

class _StatusPill extends StatelessWidget {
  const _StatusPill({required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final color = switch (status) {
      'APPROVED' => Colors.green,
      'VERIFIED' => Colors.blue,
      'REJECTED' => Colors.red,
      _ => Colors.orange,
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: .12),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        status,
        style: TextStyle(
          color: color.shade700,
          fontWeight: FontWeight.w800,
          fontSize: 12,
        ),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(32),
      child: Column(
        children: [
          Icon(icon, size: 48, color: Colors.black38),
          const SizedBox(height: 12),
          Text(
            text,
            textAlign: TextAlign.center,
            style: const TextStyle(color: Colors.black54),
          ),
        ],
      ),
    );
  }
}

void _showSnack(BuildContext context, String message) {
  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
}
