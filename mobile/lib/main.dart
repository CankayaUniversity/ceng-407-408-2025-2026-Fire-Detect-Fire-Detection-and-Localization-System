import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flamescope/core/auth/auth_service.dart';
import 'package:flamescope/core/router/app_router.dart';
import 'package:flamescope/core/theme/app_theme.dart';

void main() {
  final authService = AuthService()..loadToken();
  runApp(FlameScopeApp(authService: authService));
}

class FlameScopeApp extends StatelessWidget {
  const FlameScopeApp({super.key, required this.authService});
  final AuthService authService;

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider<AuthService>.value(
      value: authService,
      child: MaterialApp.router(
        title: 'Flame Scope',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.light,
        routerConfig: AppRouter.createRouter(authService),
      ),
    );
  }
}
