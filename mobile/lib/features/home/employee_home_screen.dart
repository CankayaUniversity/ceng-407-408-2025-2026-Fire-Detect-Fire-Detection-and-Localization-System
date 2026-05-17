import 'package:flamescope/core/api/api_client.dart';
import 'package:flamescope/core/auth/auth_service.dart';
import 'package:flamescope/core/constants/api_constants.dart';
import 'package:flamescope/core/router/app_router.dart';
import 'package:flamescope/features/home/widgets/home_header_card.dart';
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
    return Scaffold(
      appBar: AppBar(
        title: const Text('Safety Center'),
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
            const HomeHeaderCard(
              title: 'Employee Safety',
              subtitle: 'Receive confirmed alarms and report your status',
              icon: Icons.health_and_safety_outlined,
              accent: Color(0xFFEF6C00),
            ),
            const SizedBox(height: 16),
            _ActiveEmergencyPanel(active: _active, loading: _loading),
            const SizedBox(height: 16),
            const _SafetyInstructionsCard(),
            const SizedBox(height: 16),
            HomeActionTile(
              icon: Icons.notifications_active_outlined,
              title: 'Emergency Notifications',
              subtitle: 'Open received alerts and incident messages',
              color: const Color(0xFFD84315),
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
          leading: Icon(Icons.check_circle_outline, color: Color(0xFF2E7D32)),
          title: Text('No active emergency'),
          subtitle: Text('Confirmed alarms will appear here.'),
        ),
      );
    }

    return Card(
      color: const Color(0xFFFFEBEE),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Active Emergencies',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: 8),
            for (final incident in active.take(3))
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(
                  Icons.local_fire_department,
                  color: Color(0xFFC62828),
                ),
                title:
                    Text(incident.cameraName ?? 'Camera #${incident.cameraId}'),
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
      'Do not use elevators.',
      'Stay low if there is smoke.',
      'Follow the nearest safe exit route.',
      'If you are safe, report your status from the incident detail.',
    ];

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Evacuation Instructions',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: 8),
            for (final item in items)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 3),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(
                      Icons.check_circle,
                      size: 16,
                      color: Color(0xFF2E7D32),
                    ),
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
