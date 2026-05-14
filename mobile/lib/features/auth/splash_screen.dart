import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:flamescope/core/auth/auth_service.dart';
import 'package:flamescope/core/constants/app_constants.dart';
import 'package:flamescope/core/router/app_router.dart';
import 'package:flamescope/core/theme/app_theme.dart';

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
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Scaffold(
      body: Container(
        width: double.infinity,
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              AppColors.deepNavy,
              AppColors.surface,
              AppColors.navy,
            ],
          ),
        ),
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Stack(
                alignment: Alignment.center,
                children: [
                  Container(
                    width: 150,
                    height: 150,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: RadialGradient(
                        colors: [
                          AppColors.orange.withValues(alpha: 0.30),
                          AppColors.orange.withValues(alpha: 0),
                        ],
                      ),
                    ),
                  ),
                  Icon(
                    Icons.local_fire_department,
                    size: 72,
                    color: colorScheme.secondary,
                  ),
                ],
              ),
              const SizedBox(height: 24),
              Text(
                'Flame Scope',
                style: theme.textTheme.headlineSmall?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 10),
              Text(
                'Sistem başlatılıyor',
                style: theme.textTheme.bodyLarge?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 20),
              SizedBox(
                width: 36,
                height: 36,
                child: CircularProgressIndicator(
                  strokeWidth: 3,
                  color: colorScheme.secondary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
