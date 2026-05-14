import 'package:flamescope/core/api/api_client.dart';
import 'package:flamescope/core/auth/auth_service.dart';
import 'package:flamescope/core/constants/api_constants.dart';
import 'package:flamescope/core/router/app_router.dart';
import 'package:flamescope/shared/models/incident_model.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

class EmployeeHomeScreen extends StatefulWidget {
  const EmployeeHomeScreen({super.key});

  @override
  State<EmployeeHomeScreen> createState() => _EmployeeHomeScreenState();
}

class _EmployeeHomeScreenState extends State<EmployeeHomeScreen> {
  List<IncidentModel> _active = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadActiveIncidents();
  }

  Future<void> _loadActiveIncidents() async {
    try {
      final dio = createDio(context.read<AuthService>());
      final response = await dio.get(ApiEndpoints.incidents);
      final list = (response.data['incidents'] as List?)
              ?.map((e) => IncidentModel.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [];
      if (!mounted) return;
      setState(() {
        _active = list.where((e) => e.isConfirmed).toList();
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
        title: const Text('Calisan'),
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
        onRefresh: _loadActiveIncidents,
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
            _ActiveEmergencyPanel(active: _active, loading: _loading),
            const SizedBox(height: 16),
            const _SafetyInstructionsCard(),
            const SizedBox(height: 16),
            ListTile(
              leading: const Icon(Icons.notifications_active),
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

class _ActiveEmergencyPanel extends StatelessWidget {
  const _ActiveEmergencyPanel({
    required this.active,
    required this.loading,
  });

  final List<IncidentModel> active;
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

    if (active.isEmpty) {
      return const Card(
        child: ListTile(
          leading: Icon(Icons.check_circle_outline, color: Colors.green),
          title: Text('Aktif acil durum yok'),
          subtitle: Text('Yeni bir onayli alarm geldiginde burada gorunur.'),
        ),
      );
    }

    return Card(
      color: Colors.red.shade50,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Aktif Acil Durumlar',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            for (final incident in active.take(3))
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.warning_amber, color: Colors.red),
                title:
                    Text(incident.cameraName ?? 'Kamera #${incident.cameraId}'),
                subtitle: Text(
                  '${incident.cameraLocation ?? '-'} - ${incident.riskLevelLabel}',
                ),
                trailing: const Icon(Icons.chevron_right),
                onTap: () =>
                    context.push(AppRouter.incidentDetailPath(incident.id)),
              ),
          ],
        ),
      ),
    );
  }
}

class _SafetyInstructionsCard extends StatelessWidget {
  const _SafetyInstructionsCard();

  @override
  Widget build(BuildContext context) {
    const items = [
      'Asansor kullanma.',
      'Duman varsa yere yakin ilerle.',
      'En yakin guvenli cikis yonlendirmesini takip et.',
      'Guvendeysen olay detayindan durumunu bildir.',
    ];

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Tahliye Talimatlari',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            for (final item in items)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 3),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.check, size: 16, color: Colors.green),
                    const SizedBox(width: 8),
                    Expanded(child: Text(item)),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}
