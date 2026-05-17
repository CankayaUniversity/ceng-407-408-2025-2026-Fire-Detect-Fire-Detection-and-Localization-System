import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:flamescope/core/auth/auth_service.dart';
import 'package:flamescope/core/router/app_router.dart';
import 'package:flamescope/features/home/widgets/home_header_card.dart';
import 'package:flamescope/features/home/widgets/incident_summary_panel.dart';

class ManagerHomeScreen extends StatelessWidget {
  const ManagerHomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Manager'),
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
          const HomeHeaderCard(
            title: 'Manager Review Desk',
            subtitle: 'Verify alerts, reduce false alarms, escalate real risks',
            icon: Icons.verified_user_outlined,
            accent: Color(0xFFE65100),
          ),
          const SizedBox(height: 16),
          const IncidentSummaryPanel(),
          const SizedBox(height: 18),
          Text(
            'Decision Queue',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
          ),
          const SizedBox(height: 10),
          HomeActionTile(
            icon: Icons.warning_amber_outlined,
            title: 'Incidents',
            subtitle: 'Review detections and confirm or dismiss alarms',
            color: const Color(0xFFD84315),
            onTap: () => context.push(AppRouter.incidentList),
          ),
        ],
      ),
    );
  }
}
