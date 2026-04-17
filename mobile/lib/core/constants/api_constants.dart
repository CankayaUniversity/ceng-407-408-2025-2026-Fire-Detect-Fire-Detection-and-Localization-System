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

String? normalizeBackendAssetUrl(String? rawUrl) {
  final raw = rawUrl?.trim();
  if (raw == null || raw.isEmpty) return null;

  final apiBase = Uri.parse(kBaseUrl);
  final parsed = Uri.tryParse(raw);

  if (parsed != null && parsed.hasScheme) {
    final isLocalBackendHost =
        parsed.host == 'localhost' || parsed.host == '127.0.0.1';
    if (!kIsWeb && isLocalBackendHost) {
      return parsed
          .replace(
            scheme: apiBase.scheme,
            host: apiBase.host,
            port: apiBase.port,
          )
          .toString();
    }
    return raw;
  }

  final normalizedPath = raw.replaceAll('\\', '/');
  final snapshotsIndex = normalizedPath.toLowerCase().lastIndexOf('snapshots/');
  if (snapshotsIndex >= 0) {
    final suffix = normalizedPath.substring(snapshotsIndex);
    return apiBase.resolve('/$suffix').toString();
  }

  if (normalizedPath.startsWith('/')) {
    return apiBase.resolve(normalizedPath).toString();
  }

  return apiBase.resolve('/$normalizedPath').toString();
}

class ApiEndpoints {
  static const String login = '/auth/login';
  static const String refresh = '/auth/refresh';
  static const String logout = '/auth/logout';
  static const String me = '/me';
  static const String cameras = '/cameras';
  static const String incidents = '/incidents';
  static const String users = '/users';
  static const String notifications = '/notifications';

  static String userDeactivate(int userId) => '/users/$userId/deactivate';
  static String userReactivate(int userId) => '/users/$userId/reactivate';
  static String markNotificationRead(int id) => '/notifications/$id/read';
}
