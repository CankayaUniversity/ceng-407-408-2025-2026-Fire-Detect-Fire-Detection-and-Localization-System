import 'dart:async';
import 'dart:convert';
import 'dart:ui' show Color;

import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../constants/api_constants.dart';

/// Yangın olayı verisi — WebSocket'ten parse edilir.
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
      cameraId: json['camera_id'] as int,
      cameraName: json['camera_name'] as String? ?? 'Kamera #${json['camera_id']}',
      cameraLocation: json['camera_location'] as String?,
      confidence: (json['confidence'] as num?)?.toDouble(),
      snapshotUrl: normalizeBackendAssetUrl(json['snapshot_url'] as String?),
      detectedAt: json['detected_at'] as String?,
    );
  }
}

/// WebSocket bağlantısını yönetir ve yangın olaylarını yayınlar.
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

  // Dışarıdan dinlenebilen yangın olayı akışı
  final StreamController<FireIncidentEvent> _fireStream =
      StreamController<FireIncidentEvent>.broadcast();
  Stream<FireIncidentEvent> get onFireDetected => _fireStream.stream;

  // Son olay (UI badge için)
  FireIncidentEvent? _lastEvent;
  FireIncidentEvent? get lastEvent => _lastEvent;
  bool _hasUnread = false;
  bool get hasUnread => _hasUnread;

  /// Uygulama başlangıcında bir kez çağrılır.
  Future<void> init() async {
    if (_initialized) return;
    _initialized = true;

    // Android & iOS local notification init
    const android = AndroidInitializationSettings('@mipmap/ic_launcher');
    const ios = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
    );
    await _localNotif.initialize(
      const InitializationSettings(android: android, iOS: ios),
    );

    // Android 13+ için bildirim izni
    if (defaultTargetPlatform == TargetPlatform.android) {
      await _localNotif
          .resolvePlatformSpecificImplementation<
              AndroidFlutterLocalNotificationsPlugin>()
          ?.requestNotificationsPermission();
    }
  }

  /// JWT token ile WebSocket'e bağlan.
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
        debugPrint('[WS] Hata: $e — 5s sonra yeniden bağlanıyor');
        Future.delayed(const Duration(seconds: 5), _reconnect);
      },
      onDone: () {
        debugPrint('[WS] Bağlantı kapandı — 5s sonra yeniden bağlanıyor');
        Future.delayed(const Duration(seconds: 5), _reconnect);
      },
    );

    debugPrint('[WS] Bağlandı: $kWsUrl');
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
        _showLocalNotification(event);
      } else if (data['type'] == 'fire_confirmed') {
        // FCM natively handles this on Mobile. To prevent double notifications,
        // we strictly limit this WebSocket fallback to Web and Desktop emulators.
        if (kIsWeb ||
            (defaultTargetPlatform != TargetPlatform.android &&
             defaultTargetPlatform != TargetPlatform.iOS)) {
          showPushNotification(
            '🚨 YANGIN ONAYLANDI',
            data['message'] as String? ?? 'Acil durum! Yangın alarmı onaylandı.',
          );
        }
      }
    } catch (e) {
      debugPrint('[WS] Mesaj parse hatası: $e');
    }
  }

  Future<void> _showLocalNotification(FireIncidentEvent event) async {
    final pct = event.confidence != null
        ? ' (%${(event.confidence! * 100).toStringAsFixed(0)})'
        : '';
    const channel = AndroidNotificationChannel(
      'fire_alerts',
      'Yangın Uyarıları',
      description: 'Yangın tespit bildirimler',
      importance: Importance.max,
      playSound: true,
      enableVibration: true,
    );
    await _localNotif
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(channel);

    await _localNotif.show(
      event.incidentId,
      '🔥 YANGIN TESPİT EDİLDİ$pct',
      '${event.cameraName}${event.cameraLocation != null ? " • ${event.cameraLocation}" : ""}',
      NotificationDetails(
        android: AndroidNotificationDetails(
          channel.id,
          channel.name,
          channelDescription: channel.description,
          importance: Importance.max,
          priority: Priority.high,
          color: const Color(0xFFFF3D00),
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
    const channel = AndroidNotificationChannel(
      'push_alerts',
      'Genel Bildirimler',
      description: 'Sistem push bildirimleri',
      importance: Importance.max,
      playSound: true,
      enableVibration: true,
    );
    await _localNotif
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(channel);

    await _localNotif.show(
      DateTime.now().millisecond,
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
