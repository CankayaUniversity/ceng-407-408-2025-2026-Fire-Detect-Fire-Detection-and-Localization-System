import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:flamescope/core/auth/auth_service.dart';
import 'package:flamescope/core/constants/app_constants.dart';
import 'package:flamescope/features/auth/login_screen.dart';
import 'package:flamescope/features/auth/splash_screen.dart';
import 'package:flamescope/features/home/admin_home_screen.dart';
import 'package:flamescope/features/home/manager_home_screen.dart';
import 'package:flamescope/features/home/employee_home_screen.dart';
import 'package:flamescope/features/home/fire_response_home_screen.dart';
import 'package:flamescope/features/incidents/incident_list_screen.dart';
import 'package:flamescope/features/incidents/incident_detail_screen.dart';
import 'package:flamescope/features/cameras/camera_list_screen.dart';
import 'package:flamescope/features/users/user_list_screen.dart';
import 'package:flamescope/features/users/user_create_screen.dart';
import 'package:flamescope/features/stream/live_stream_screen.dart';
import 'package:flamescope/features/emergency/emergency_alert_screen.dart';

class AppRouter {
  static const String splash = '/';
  static const String login = '/login';
  static const String adminHome = '/admin';
  static const String managerHome = '/manager';
  static const String employeeHome = '/employee';
  static const String fireResponseHome = '/fire-response';
  static const String incidentList = '/incidents';
  static const String incidentDetail = '/incidents/:id';
  static const String cameraList = '/cameras';
  static const String userList = '/users';
  static const String userCreate = '/users/create';
  static const String liveStream = '/stream';
  static const String emergencyAlert = '/emergency';

  static String incidentDetailPath(int id) => '/incidents/$id';
  static String liveStreamPath({int? cameraId, int? incidentId}) {
    final q = <String>[];
    if (cameraId != null && cameraId > 0) q.add('cameraId=$cameraId');
    if (incidentId != null && incidentId > 0) q.add('incidentId=$incidentId');
    return '/stream${q.isEmpty ? '' : '?${q.join('&')}'}';
  }

  static GoRouter createRouter(AuthService authService) {
    return GoRouter(
      initialLocation: splash,
      refreshListenable: authService,
      redirect: (context, state) {
        final onSplash = state.matchedLocation == splash;
        final onLogin = state.matchedLocation == login;

        if (onSplash) return null;
        if (!authService.isLoggedIn) return onLogin ? null : login;
        if (onLogin) return _homeForRole(authService.user?.role);
        return null;
      },
      routes: [
      GoRoute(path: splash, builder: (_, __) => const SplashScreen()),
      GoRoute(path: login, builder: (_, __) => const LoginScreen()),
      GoRoute(path: adminHome, builder: (_, __) => const AdminHomeScreen()),
      GoRoute(path: managerHome, builder: (_, __) => const ManagerHomeScreen()),
      GoRoute(path: employeeHome, builder: (_, __) => const EmployeeHomeScreen()),
      GoRoute(path: fireResponseHome, builder: (_, __) => const FireResponseHomeScreen()),
      GoRoute(path: incidentList, builder: (_, __) => const IncidentListScreen()),
      GoRoute(
        path: '/incidents/:id',
        builder: (c, state) {
          final id = int.tryParse(state.pathParameters['id'] ?? '') ?? 0;
          return IncidentDetailScreen(incidentId: id);
        },
      ),
      GoRoute(path: cameraList, builder: (_, __) => const CameraListScreen()),
      GoRoute(path: userList, builder: (_, __) => const UserListScreen()),
      GoRoute(path: userCreate, builder: (_, __) => const UserCreateScreen()),
      GoRoute(
        path: liveStream,
        builder: (c, state) {
          final cameraId = int.tryParse(state.uri.queryParameters['cameraId'] ?? '') ?? 0;
          final incidentId = int.tryParse(state.uri.queryParameters['incidentId'] ?? '') ?? 0;
          return LiveStreamScreen(cameraId: cameraId, incidentId: incidentId);
        },
      ),
      GoRoute(path: emergencyAlert, builder: (_, __) => const EmergencyAlertScreen()),
    ],
    );
  }

  static String _homeForRole(AppRole? role) {
    switch (role) {
      case AppRole.admin:
        return adminHome;
      case AppRole.manager:
        return managerHome;
      case AppRole.fireResponseUnit:
        return fireResponseHome;
      case AppRole.employee:
      default:
        return employeeHome;
    }
  }
}
