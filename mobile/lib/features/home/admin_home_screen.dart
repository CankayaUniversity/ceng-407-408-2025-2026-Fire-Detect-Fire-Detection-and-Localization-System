import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:flamescope/core/auth/auth_service.dart';
import 'package:flamescope/core/router/app_router.dart';

class AdminHomeScreen extends StatelessWidget {
  const AdminHomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final user = context.watch<AuthService>().user;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Admin'),
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
          ListTile(
            leading: const Icon(Icons.people_outline),
            title: const Text('Kullanıcı Yönetimi'),
            subtitle: const Text('Kullanıcıları listele ve yeni ekle'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => context.push(AppRouter.userList),
          ),
          if (user != null) ...[
            const SizedBox(height: 8),
            Card(
              child: ListTile(
                leading: const Icon(Icons.person),
                title: Text(user.fullName),
                subtitle: Text(user.email),
              ),
            ),
          ],
          const SizedBox(height: 8),
          ListTile(
            leading: const Icon(Icons.video_library),
            title: const Text('Kameralar'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => context.push(AppRouter.cameraList),
          ),
          ListTile(
            leading: const Icon(Icons.warning_amber),
            title: const Text('Olaylar (Incidents)'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => context.push(AppRouter.incidentList),
          ),
        ],
      ),
    );
  }
}
