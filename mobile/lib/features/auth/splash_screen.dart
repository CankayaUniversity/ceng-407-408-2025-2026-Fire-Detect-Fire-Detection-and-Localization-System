import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:flamescope/core/auth/auth_service.dart';
import 'package:flamescope/core/constants/app_constants.dart';
import 'package:flamescope/core/router/app_router.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _checkAuth());
  }

  Future<void> _checkAuth() async {
    await context.read<AuthService>().loadToken();
    if (!mounted) return;
    final auth = context.read<AuthService>();
    if (auth.isLoggedIn && auth.user != null) {
      final role = auth.user!.role;
      switch (role) {
        case AppRole.admin:
          context.go(AppRouter.adminHome);
          break;
        case AppRole.manager:
          context.go(AppRouter.managerHome);
          break;
        case AppRole.employee:
          context.go(AppRouter.employeeHome);
          break;
        case AppRole.fireResponseUnit:
          context.go(AppRouter.fireResponseHome);
          break;
      }
    } else {
      context.go(AppRouter.login);
    }
  }

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.local_fire_department, size: 80, color: Colors.orange),
            SizedBox(height: 24),
            Text('Flame Scope', style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
            SizedBox(height: 16),
            CircularProgressIndicator(),
          ],
        ),
      ),
    );
  }
}
