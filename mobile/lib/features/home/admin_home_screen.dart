import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:flamescope/core/auth/auth_service.dart';
import 'package:flamescope/core/router/app_router.dart';
import 'package:flamescope/features/home/widgets/home_header_card.dart';
import 'package:flamescope/features/home/widgets/incident_summary_panel.dart';

class AdminHomeScreen extends StatelessWidget {
  const AdminHomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Command Center'),
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
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const _AdminHero(),
          const SizedBox(height: 16),
          const IncidentSummaryPanel(),
          const SizedBox(height: 18),
          Text(
            'Operations',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
          ),
          const SizedBox(height: 10),
          HomeActionTile(
            icon: Icons.people_alt_outlined,
            title: 'User Management',
            subtitle: 'Manage admins, managers, employees and responders',
            color: const Color(0xFF8A4B12),
            onTap: () => context.push(AppRouter.userList),
          ),
          HomeActionTile(
            icon: Icons.videocam_outlined,
            title: 'Cameras',
            subtitle: 'Configure live sources and demo cameras',
            color: const Color(0xFFE65100),
            onTap: () => context.push(AppRouter.cameraList),
          ),
          HomeActionTile(
            icon: Icons.local_fire_department_outlined,
            title: 'Incidents',
            subtitle: 'Review detections, confirmations and false alarms',
            color: const Color(0xFFD32F2F),
            onTap: () => context.push(AppRouter.incidentList),
          ),
        ],
      ),
    );
  }
}

class _AdminHero extends StatelessWidget {
  const _AdminHero();

  @override
  Widget build(BuildContext context) {
    return const HomeHeaderCard(
      title: 'FlameScope Monitoring',
      subtitle: 'Early fire and smoke alerts for connected cameras',
      icon: Icons.local_fire_department,
    );
  }
}
