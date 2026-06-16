import 'dart:async';
import 'dart:convert';
import 'dart:ui' show Color;

import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../constants/api_constants.dart';

class FireIncidentEvent {
  final int incidentId;
  final int cameraId;
  final String cameraName;
  final String? cameraLocation;
  final double? confidence;
  final String? snapshotUrl;
  final String? detectedAt;

  const FireIncidentEvent({
    required this.incidentId,
    required this.cameraId,
    required this.cameraName,
    this.cameraLocation,
    this.confidence,
    this.snapshotUrl,
    this.detectedAt,
  });

  factory FireIncidentEvent.fromJson(Map<String, dynamic> json) {
    return FireIncidentEvent(
      incidentId: json['incident_id'] as int,
      cameraId: json['camera_id'] as int? ?? 0,
      cameraName:
          json['camera_name'] as String? ?? 'Camera #${json['camera_id']}',
      cameraLocation: json['camera_location'] as String?,
      confidence: (json['confidence'] as num?)?.toDouble(),
      snapshotUrl: normalizeBackendAssetUrl(json['snapshot_url'] as String?),
      detectedAt:
          json['detected_at'] as String? ?? json['confirmed_at'] as String?,
    );
  }

  bool get isSmokeScenario {
    final haystack =
        '${cameraName.toLowerCase()} ${cameraLocation?.toLowerCase() ?? ''}';
    return haystack.contains('smoke') ||
        haystack.contains('outdoor') ||
        haystack.contains('duman');
  }

  String get detectedTitle =>
      isSmokeScenario ? 'SMOKE DETECTED' : 'FIRE DETECTED';

  String get confirmedTitle =>
      isSmokeScenario ? 'SMOKE RISK CONFIRMED' : 'FIRE CONFIRMED';
}

class NotificationService extends ChangeNotifier {
  static final NotificationService _instance = NotificationService._();
  factory NotificationService() => _instance;
  NotificationService._();

  final FlutterLocalNotificationsPlugin _localNotif =
      FlutterLocalNotificationsPlugin();

  WebSocketChannel? _channel;
  StreamSubscription? _sub;
  String? _token;
  bool _initialized = false;

  final StreamController<FireIncidentEvent> _fireStream =
      StreamController<FireIncidentEvent>.broadcast();
  Stream<FireIncidentEvent> get onFireDetected => _fireStream.stream;

  FireIncidentEvent? _lastEvent;
  FireIncidentEvent? get lastEvent => _lastEvent;
  bool _hasUnread = false;
  bool get hasUnread => _hasUnread;

  Future<void> init() async {
    if (_initialized) return;
    _initialized = true;

    const android = AndroidInitializationSettings('@mipmap/ic_launcher');
    const ios = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
    );
    await _localNotif.initialize(
      const InitializationSettings(android: android, iOS: ios),
    );

    if (defaultTargetPlatform == TargetPlatform.android) {
      await _localNotif
          .resolvePlatformSpecificImplementation<
              AndroidFlutterLocalNotificationsPlugin>()
          ?.requestNotificationsPermission();
    }
  }

  void connect(String token) {
    if (_token == token && _channel != null) return;
    _token = token;
    _reconnect();
  }

  void _reconnect() {
    _sub?.cancel();
    _channel?.sink.close();

    final uri = Uri.parse('$kWsUrl?token=$_token');
    _channel = WebSocketChannel.connect(uri);

    _sub = _channel!.stream.listen(
      _onMessage,
      onError: (e) {
        debugPrint('[WS] Error: $e - 5s sonra yeniden baglaniliyor');
        Future.delayed(const Duration(seconds: 5), _reconnect);
      },
      onDone: () {
        debugPrint('[WS] Baglanti kapandi - 5s sonra yeniden baglaniliyor');
        Future.delayed(const Duration(seconds: 5), _reconnect);
      },
    );

    debugPrint('[WS] Baglandi: $kWsUrl');
  }

  void _onMessage(dynamic raw) {
    try {
      final data = jsonDecode(raw as String) as Map<String, dynamic>;
      if (data['type'] == 'fire_detected') {
        final event = FireIncidentEvent.fromJson(data);
        _lastEvent = event;
        _hasUnread = true;
        _fireStream.add(event);
        notifyListeners();
        _showDetectedNotification(event);
      } else if (data['type'] == 'fire_confirmed') {
        final event = FireIncidentEvent.fromJson(data);
        _lastEvent = event;
        _hasUnread = true;
        notifyListeners();
        _showConfirmedNotification(
          event,
          data['message'] as String?,
        );
      } else if (data['type'] == 'ops_update') {
        _hasUnread = true;
        notifyListeners();
        _showOpsUpdateNotification(
          title: data['title'] as String? ?? 'Incident Update',
          body: data['message'] as String? ??
              'A new incident update was received.',
          incidentId: data['incident_id'] as int? ?? 0,
        );
      }
    } catch (e) {
      debugPrint('[WS] Mesaj parse hatasi: $e');
    }
  }

  Future<void> _showDetectedNotification(FireIncidentEvent event) async {
    final pct = event.confidence != null
        ? ' (Risk %${(event.confidence! * 100).toStringAsFixed(0)})'
        : '';
    await _showLocalAlert(
      id: event.incidentId,
      channelId: 'fire_alerts',
      channelName: 'Fire Alerts',
      title: '${event.detectedTitle}$pct',
      body:
          '${event.cameraName}${event.cameraLocation != null ? " - ${event.cameraLocation}" : ""}',
    );
  }

  Future<void> _showConfirmedNotification(
    FireIncidentEvent event,
    String? serverMessage,
  ) async {
    final pct = event.confidence != null
        ? ' Risk score: %${(event.confidence! * 100).toStringAsFixed(0)}.'
        : '';
    final body = serverMessage ??
        'Confirmed fire alarm: ${event.cameraName}'
            '${event.cameraLocation != null ? " - ${event.cameraLocation}" : ""}.'
            '$pct Please follow safe exit instructions.';

    await _showLocalAlert(
      id: event.incidentId + 100000,
      channelId: 'confirmed_fire_alerts',
      channelName: 'Confirmed Fire Alarms',
      title: 'EMERGENCY: ${event.confirmedTitle}',
      body: body,
    );
  }

  Future<void> _showOpsUpdateNotification({
    required String title,
    required String body,
    required int incidentId,
  }) async {
    await _showLocalAlert(
      id: incidentId + 200000 + DateTime.now().second,
      channelId: 'incident_updates',
      channelName: 'Incident Updates',
      title: title,
      body: body,
    );
  }

  Future<void> _showLocalAlert({
    required int id,
    required String channelId,
    required String channelName,
    required String title,
    required String body,
  }) async {
    final channel = AndroidNotificationChannel(
      channelId,
      channelName,
      description: 'FlameScope real-time fire alerts',
      importance: Importance.max,
      playSound: true,
      enableVibration: true,
    );
    await _localNotif
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(channel);

    await _localNotif.show(
      id,
      title,
      body,
      NotificationDetails(
        android: AndroidNotificationDetails(
          channel.id,
          channel.name,
          channelDescription: channel.description,
          importance: Importance.max,
          priority: Priority.high,
          color: const Color(0xFFFF3D00),
          styleInformation: BigTextStyleInformation(body),
          largeIcon: const DrawableResourceAndroidBitmap('@mipmap/ic_launcher'),
        ),
        iOS: const DarwinNotificationDetails(
          presentAlert: true,
          presentBadge: true,
          presentSound: true,
        ),
      ),
    );
  }

  Future<void> showPushNotification(String title, String body) async {
    await _showLocalAlert(
      id: DateTime.now().millisecond,
      channelId: 'push_alerts',
      channelName: 'Genel Notificationler',
      title: title,
      body: body,
    );
  }

  void markRead() {
    _hasUnread = false;
    notifyListeners();
  }

  void disconnect() {
    _sub?.cancel();
    _channel?.sink.close();
    _channel = null;
    _token = null;
  }

  @override
  void dispose() {
    disconnect();
    _fireStream.close();
    super.dispose();
  }
}
