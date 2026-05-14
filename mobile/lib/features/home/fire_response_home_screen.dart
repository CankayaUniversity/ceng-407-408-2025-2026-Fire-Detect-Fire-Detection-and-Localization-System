import 'package:flamescope/core/api/api_client.dart';
import 'package:flamescope/core/auth/auth_service.dart';
import 'package:flamescope/core/constants/api_constants.dart';
import 'package:flamescope/core/router/app_router.dart';
import 'package:flamescope/shared/models/incident_model.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

class FireResponseHomeScreen extends StatefulWidget {
  const FireResponseHomeScreen({super.key});

  @override
  State<FireResponseHomeScreen> createState() => _FireResponseHomeScreenState();
}

class _FireResponseHomeScreenState extends State<FireResponseHomeScreen> {
  List<IncidentModel> _incidents = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final dio = createDio(context.read<AuthService>());
      final response = await dio.get(ApiEndpoints.incidents);
      final list = (response.data['incidents'] as List?)
              ?.map((e) => IncidentModel.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [];
      list.sort((a, b) => (b.confidence ?? 0).compareTo(a.confidence ?? 0));
      if (!mounted) return;
      setState(() {
        _incidents = list.where((e) => e.isConfirmed).toList();
        _loading = false;
      });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = context.watch<AuthService>().user;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Yangin Mudahale'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () async {
              await context.read<AuthService>().logout();
              if (context.mounted) context.go(AppRouter.login);
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (user != null)
              Card(
                child: ListTile(
                  leading: const Icon(Icons.person),
                  title: Text(user.fullName),
                  subtitle: Text(user.email),
                ),
              ),
            const SizedBox(height: 16),
            _ResponseQueue(incidents: _incidents, loading: _loading),
            const SizedBox(height: 16),
            ListTile(
              leading: const Icon(Icons.emergency),
              title: const Text('Acil Durum Bildirimleri'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => context.push(AppRouter.notificationList),
            ),
          ],
        ),
      ),
    );
  }
}

class _ResponseQueue extends StatelessWidget {
  const _ResponseQueue({
    required this.incidents,
    required this.loading,
  });

  final List<IncidentModel> incidents;
  final bool loading;

  @override
  Widget build(BuildContext context) {
    if (loading) {
      return const Card(
        child: Padding(
          padding: EdgeInsets.all(16),
          child: Center(child: CircularProgressIndicator()),
        ),
      );
    }

    if (incidents.isEmpty) {
      return const Card(
        child: ListTile(
          leading: Icon(Icons.check_circle_outline, color: Colors.green),
          title: Text('Aktif mudahale gerektiren olay yok'),
          subtitle:
              Text('Onaylanan yanginlar risk onceligine gore listelenir.'),
        ),
      );
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Mudahale Kuyrugu',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            for (final incident in incidents.take(5))
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: Icon(
                  Icons.local_fire_department,
                  color: (incident.confidence ?? 0) >= 0.80
                      ? Colors.red
                      : Colors.orange,
                ),
                title:
                    Text(incident.cameraName ?? 'Kamera #${incident.cameraId}'),
                subtitle: Text(
                  '${incident.cameraLocation ?? '-'} - ${incident.riskLevelLabel}',
                ),
                trailing: Text(
                  incident.confidence == null
                      ? '-'
                      : '%${(incident.confidence! * 100).round()}',
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                onTap: () =>
                    context.push(AppRouter.incidentDetailPath(incident.id)),
              ),
          ],
        ),
      ),
    );
  }
}
