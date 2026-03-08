import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:flamescope/core/auth/auth_service.dart';
import 'package:flamescope/core/router/app_router.dart';

class EmployeeHomeScreen extends StatelessWidget {
  const EmployeeHomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final user = context.watch<AuthService>().user;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Çalışan'),
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
            leading: const Icon(Icons.notifications_active),
            title: const Text('Acil Durum Bildirimleri'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => context.push(AppRouter.emergencyAlert),
          ),
        ],
      ),
    );
  }
}
