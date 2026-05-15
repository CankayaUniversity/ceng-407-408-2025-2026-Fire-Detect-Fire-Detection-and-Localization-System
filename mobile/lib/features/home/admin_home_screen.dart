import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:flamescope/core/auth/auth_service.dart';
import 'package:flamescope/core/router/app_router.dart';
import 'package:flamescope/core/notifications/notification_service.dart';
import 'package:flamescope/features/home/widgets/dashboard_home_view.dart';
import 'package:flamescope/features/home/widgets/dashboard_role_label.dart';

class AdminHomeScreen extends StatelessWidget {
  const AdminHomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final user = context.watch<AuthService>().user;
    if (user == null) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    return DashboardHomeView(
      roleTitle: 'Yönetim Paneli',
      userName: user.fullName,
      roleLabel: dashboardRoleLabel(user.role),
      actions: const [
        DashboardActionItem(
          title: 'Kullanıcı Yönetimi',
          subtitle: 'Listele ve yeni kullanıcı ekle',
          icon: Icons.people_alt_outlined,
          route: AppRouter.userList,
          emphasized: true,
        ),
        DashboardActionItem(
          title: 'Kameralar',
          subtitle: 'Kamera akışlarını ve konumları incele',
          icon: Icons.videocam_outlined,
          route: AppRouter.cameraList,
        ),
        DashboardActionItem(
          title: 'Bildirim Geçmişi',
          subtitle: 'Sistemde oluşan son uyarıları incele',
          icon: Icons.notifications_active_outlined,
          route: AppRouter.notificationList,
        ),
      ],
      onAlertTap: (context, event) {
        context.push(AppRouter.incidentDetailPath(event.incidentId));
        context.read<NotificationService>().markRead();
      },
    );
  }
}
