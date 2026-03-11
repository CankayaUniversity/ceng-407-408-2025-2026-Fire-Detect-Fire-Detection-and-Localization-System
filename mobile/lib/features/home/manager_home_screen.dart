import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:flamescope/core/auth/auth_service.dart';
import 'package:flamescope/core/router/app_router.dart';

class ManagerHomeScreen extends StatelessWidget {
  const ManagerHomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final user = context.watch<AuthService>().user;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Yönetici'),
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
          if (user != null)
            Card(
              child: ListTile(
                leading: const Icon(Icons.person),
                title: Text(user.fullName),
                subtitle: Text(user.email),
              ),
            ),
          const SizedBox(height: 16),
          ListTile(
            leading: const Icon(Icons.warning_amber),
            title: const Text('Olaylar (Incidents)'),
            subtitle: const Text('Doğrula / Reddet'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => context.push(AppRouter.incidentList),
          ),
        ],
      ),
    );
  }
}
