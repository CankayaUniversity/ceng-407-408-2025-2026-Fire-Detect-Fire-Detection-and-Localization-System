import 'package:flutter/foundation.dart' show kIsWeb;

/// Backend host for local/LAN development.
/// Physical phones can pass --dart-define=FLAMESCOPE_API_HOST=<LAN_IP>.
const String kLanIp = String.fromEnvironment(
  'FLAMESCOPE_API_HOST',
  defaultValue: '10.0.2.2',
);

/// Full backend URL override for cloud deployments.
/// Example: --dart-define=FLAMESCOPE_API_BASE_URL=https://flamescope.onrender.com
const String _apiBaseUrlOverride = String.fromEnvironment(
  'FLAMESCOPE_API_BASE_URL',
  defaultValue: '',
);

String _trimTrailingSlash(String value) {
  var result = value.trim();
  while (result.endsWith('/')) {
    result = result.substring(0, result.length - 1);
  }
  return result;
}

/// Backend API base URL.
/// - Web local: localhost:8000
/// - Android emulator local: 10.0.2.2:8000
/// - Cloud/demo: pass FLAMESCOPE_API_BASE_URL
String get kBaseUrl {
  final override = _trimTrailingSlash(_apiBaseUrlOverride);
  if (override.isNotEmpty) return override;
  return kIsWeb ? 'http://localhost:8000' : 'http://$kLanIp:8000';
}

/// WebSocket URL for real-time fire notifications.
String get kWsUrl {
  final apiBase = Uri.parse(kBaseUrl);
  return Uri(
    scheme: apiBase.scheme == 'https' ? 'wss' : 'ws',
    host: apiBase.host,
    port: apiBase.hasPort ? apiBase.port : null,
    path: '/ws',
  ).toString();
}

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
  static const String incidentSummary = '/incidents/analytics/summary';
  static const String users = '/users';
  static const String notifications = '/notifications';

  static String userDeactivate(int userId) => '/users/$userId/deactivate';
  static String userReactivate(int userId) => '/users/$userId/reactivate';
  static String markNotificationRead(int id) => '/notifications/$id/read';
  static String incidentSafetyReport(int id) => '/incidents/$id/safety-report';
  static String incidentResponseUpdate(int id) =>
      '/incidents/$id/response-update';
  static String restartLobbyDemo(int cameraId) =>
      '/cameras/$cameraId/demo/restart-lobby';
  static String restartOutdoorDemo(int cameraId) =>
      '/cameras/$cameraId/demo/restart-outdoor';
}
