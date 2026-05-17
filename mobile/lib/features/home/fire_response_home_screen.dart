import 'package:flamescope/core/api/api_client.dart';
import 'package:flamescope/core/auth/auth_service.dart';
import 'package:flamescope/core/constants/api_constants.dart';
import 'package:flamescope/core/router/app_router.dart';
import 'package:flamescope/features/home/widgets/home_header_card.dart';
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
    return Scaffold(
      appBar: AppBar(
        title: const Text('Fire Response'),
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
            const HomeHeaderCard(
              title: 'Response Operations',
              subtitle: 'Track confirmed emergencies by risk priority',
              icon: Icons.local_fire_department_outlined,
              accent: Color(0xFFC62828),
            ),
            const SizedBox(height: 16),
            _ResponseQueue(incidents: _incidents, loading: _loading),
            const SizedBox(height: 16),
            HomeActionTile(
              icon: Icons.emergency_outlined,
              title: 'Emergency Notifications',
              subtitle: 'Open assigned alerts and response messages',
              color: const Color(0xFFC62828),
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
          leading: Icon(Icons.check_circle_outline, color: Color(0xFF2E7D32)),
          title: Text('No active response required'),
          subtitle: Text('Confirmed fires are listed by risk priority.'),
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
              'Response Queue',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: 8),
            for (final incident in incidents.take(5))
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: Icon(
                  Icons.local_fire_department,
                  color: (incident.confidence ?? 0) >= 0.80
                      ? const Color(0xFFC62828)
                      : const Color(0xFFE65100),
                ),
                title:
                    Text(incident.cameraName ?? 'Camera #${incident.cameraId}'),
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
