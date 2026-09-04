import 'package:ccms_site_engineer/main.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  testWidgets('shows the login screen', (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues({});
    await tester.pumpWidget(const CcmsSiteEngineerApp());
    await tester.pump(const Duration(seconds: 1));

    expect(find.text('CCMS Site Engineer'), findsOneWidget);
    expect(find.text('Login'), findsOneWidget);
  });
}
