import 'package:flutter/foundation.dart' show kIsWeb;

/// Backend API base URL. Web: localhost:8000, Android emulator: 10.0.2.2:8000, fiziksel cihaz: bilgisayar IP.
String get kBaseUrl => kIsWeb ? 'http://localhost:8000' : 'http://10.0.2.2:8000';

class ApiEndpoints {
  static const String login = '/auth/login';
  static const String me = '/me';
  static const String cameras = '/cameras';
  static const String incidents = '/incidents';
  static const String users = '/users';

  static String userDeactivate(int userId) => '/users/$userId/deactivate';
  static String userReactivate(int userId) => '/users/$userId/reactivate';
}
