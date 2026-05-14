import 'package:dio/dio.dart';
import 'package:flamescope/core/auth/auth_service.dart';
import 'package:flamescope/core/constants/api_constants.dart';
import 'package:flamescope/core/router/app_router.dart';
import 'package:flamescope/data/api/notifications_api.dart';
import 'package:flamescope/data/models/notification_model.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

class NotificationListScreen extends StatefulWidget {
  const NotificationListScreen({super.key});

  @override
  State<NotificationListScreen> createState() => _NotificationListScreenState();
}

class _NotificationListScreenState extends State<NotificationListScreen> {
  late NotificationsApi _api;
  List<NotificationModel>? _notifications;
  String? _error;

  @override
  void initState() {
    super.initState();
    final token = context.read<AuthService>().token;
    final dio = Dio(BaseOptions(baseUrl: kBaseUrl));
    if (token != null) dio.options.headers['Authorization'] = 'Bearer $token';
    _api = NotificationsApi(dio);
    _loadNotifications();
  }

  Future<void> _loadNotifications() async {
    try {
      final items = await _api.getMyNotifications();
      setState(() {
        _notifications = items;
        _error = null;
      });
    } catch (e) {
      if (mounted) setState(() => _error = 'Bildirimler yuklenemedi: $e');
    }
  }

  Future<void> _markAsRead(NotificationModel notif) async {
    if (notif.isRead) return;
    try {
      await _api.markAsRead(notif.id);
      _loadNotifications();
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Acil Durum Bildirimleri')),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_error != null) return Center(child: Text(_error!));
    if (_notifications == null) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_notifications!.isEmpty) {
      return const Center(child: Text('Hic bildiriminiz yok.'));
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: _notifications!.length,
      itemBuilder: (context, i) {
        final n = _notifications![i];
        return Card(
          color: n.isRead ? null : Colors.red.shade50,
          child: ListTile(
            leading: Icon(
              n.isRead
                  ? Icons.notifications_none
                  : Icons.notification_important,
              color: n.isRead ? Colors.grey : Colors.red,
            ),
            title: Text(
              n.message,
              style: TextStyle(
                fontWeight: n.isRead ? FontWeight.normal : FontWeight.bold,
              ),
            ),
            subtitle: n.incidentId != null
                ? Text('Olay #${n.incidentId}')
                : const Text('Sistem bildirimi'),
            trailing:
                n.incidentId != null ? const Icon(Icons.chevron_right) : null,
            onTap: () async {
              await _markAsRead(n);
              if (!context.mounted || n.incidentId == null) return;
              context.push(AppRouter.incidentDetailPath(n.incidentId!));
            },
          ),
        );
      },
    );
  }
}
