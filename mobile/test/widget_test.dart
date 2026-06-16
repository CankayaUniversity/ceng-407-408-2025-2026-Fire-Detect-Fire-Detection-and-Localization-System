import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'package:flamescope/main.dart';
import 'package:flamescope/core/auth/auth_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() {
    FlutterSecureStorage.setMockInitialValues({});
  });

  testWidgets('FlameScopeApp: splash sonrasi giris ekrani', (WidgetTester tester) async {
    final auth = AuthService();
    await tester.pumpWidget(FlameScopeApp(authService: auth));
    await tester.pump();
    // Splash: async loadToken + redirect
    await tester.pumpAndSettle(const Duration(seconds: 3));

    expect(find.text('Flame Scope'), findsWidgets);
    expect(find.text('Giriş Yap'), findsOneWidget);
  });
}
