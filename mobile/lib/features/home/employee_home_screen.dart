import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flamescope/core/auth/auth_service.dart';
import 'package:flamescope/core/router/app_router.dart';
import 'package:flamescope/features/home/widgets/dashboard_home_view.dart';
import 'package:flamescope/features/home/widgets/dashboard_role_label.dart';

class EmployeeHomeScreen extends StatelessWidget {
  const EmployeeHomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final user = context.watch<AuthService>().user;
    if (user == null) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    return DashboardHomeView(
      roleTitle: 'Personel Paneli',
      userName: user.fullName,
      roleLabel: dashboardRoleLabel(user.role),
      showStatusHero: false,
      sectionTitle: 'Acil Durum Bildirimleri',
      description: 'Bu bölümde yalnızca aktif acil durum yönlendirmelerine erişebilirsiniz.',
      actions: const [
        DashboardActionItem(
          title: 'Acil Durum Bildirimleri',
          subtitle: 'Doğrulanmış yangın uyarılarını ve yönlendirmeleri aç',
          icon: Icons.emergency_outlined,
          route: AppRouter.emergencyAlert,
          centered: true,
        ),
      ],
      onAlertTap: (_, __) {},
    );
  }
}
