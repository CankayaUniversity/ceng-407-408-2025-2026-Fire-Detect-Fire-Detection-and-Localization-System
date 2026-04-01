import 'package:flutter/foundation.dart' show kIsWeb;

/// Bilgisayarın LAN IP'si (fiziksel telefon için):
const String kLanIp = '192.168.1.200';

/// Backend API base URL.
/// - Web (Chrome): localhost:8000
/// - Android fiziksel cihaz (aynı Wi-Fi): kLanIp:8000
/// - Android emülatör: 10.0.2.2:8000
String get kBaseUrl => kIsWeb ? 'http://localhost:8000' : 'http://$kLanIp:8000';

/// WebSocket URL (gerçek zamanlı yangın bildirimi)
String get kWsUrl => kIsWeb ? 'ws://localhost:8000/ws' : 'ws://$kLanIp:8000/ws';

class ApiEndpoints {
  static const String login = '/auth/login';
  static const String me = '/me';
  static const String cameras = '/cameras';
  static const String incidents = '/incidents';
  static const String users = '/users';

  static String userDeactivate(int userId) => '/users/$userId/deactivate';
  static String userReactivate(int userId) => '/users/$userId/reactivate';
}
