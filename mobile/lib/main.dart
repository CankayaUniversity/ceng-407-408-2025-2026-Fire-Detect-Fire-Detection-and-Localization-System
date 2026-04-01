import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flamescope/core/auth/auth_service.dart';
import 'package:flamescope/core/notifications/notification_service.dart';
import 'package:flamescope/core/router/app_router.dart';
import 'package:flamescope/core/theme/app_theme.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Bildirimleri başlat
  await NotificationService().init();

  final authService = AuthService()..loadToken();

  runApp(FlameScopeApp(authService: authService));
}

class FlameScopeApp extends StatelessWidget {
  const FlameScopeApp({super.key, required this.authService});
  final AuthService authService;

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<AuthService>.value(value: authService),
        ChangeNotifierProvider<NotificationService>.value(
          value: NotificationService(),
        ),
      ],
      child: _AppWithFireAlert(authService: authService),
    );
  }
}

class _AppWithFireAlert extends StatefulWidget {
  const _AppWithFireAlert({required this.authService});
  final AuthService authService;

  @override
  State<_AppWithFireAlert> createState() => _AppWithFireAlertState();
}

class _AppWithFireAlertState extends State<_AppWithFireAlert> {
  @override
  void initState() {
    super.initState();
    // Auth değişimini dinle → login olunca WS bağlan
    widget.authService.addListener(_onAuthChanged);
  }

  void _onAuthChanged() {
    final token = widget.authService.token;
    if (token != null && token.isNotEmpty) {
      NotificationService().connect(token);
    } else {
      NotificationService().disconnect();
    }
  }

  @override
  void dispose() {
    widget.authService.removeListener(_onAuthChanged);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Flame Scope',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      routerConfig: AppRouter.createRouter(widget.authService),
      builder: (context, child) {
        // Tüm sayfaların üstüne yangın uyarı banner'ı yerleştir
        return Stack(
          children: [
            child ?? const SizedBox.shrink(),
            const _FireAlertBanner(),
          ],
        );
      },
    );
  }
}

/// Yangın tespit edildiğinde ekranın üstünde görünen kırmızı banner.
class _FireAlertBanner extends StatefulWidget {
  const _FireAlertBanner();

  @override
  State<_FireAlertBanner> createState() => _FireAlertBannerState();
}

class _FireAlertBannerState extends State<_FireAlertBanner>
    with SingleTickerProviderStateMixin {
  late final AnimationController _anim;
  FireIncidentEvent? _current;

  @override
  void initState() {
    super.initState();
    _anim = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 400),
    );
    NotificationService().onFireDetected.listen(_onFire);
  }

  void _onFire(FireIncidentEvent event) {
    setState(() => _current = event);
    _anim.forward(from: 0);
    // 8 saniye sonra otomatik kapat
    Future.delayed(const Duration(seconds: 8), () {
      if (mounted) _anim.reverse();
    });
  }

  @override
  void dispose() {
    _anim.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_current == null) return const SizedBox.shrink();
    final pct = _current!.confidence != null
        ? ' • %${(_current!.confidence! * 100).toStringAsFixed(0)}'
        : '';
    return Positioned(
      top: 0,
      left: 0,
      right: 0,
      child: SlideTransition(
        position: Tween<Offset>(
          begin: const Offset(0, -1),
          end: Offset.zero,
        ).animate(CurvedAnimation(parent: _anim, curve: Curves.easeOut)),
        child: SafeArea(
          child: GestureDetector(
            onTap: () => _anim.reverse(),
            child: Container(
              margin: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.red.shade700,
                borderRadius: BorderRadius.circular(12),
                boxShadow: const [
                  BoxShadow(
                    color: Colors.black26,
                    blurRadius: 8,
                    offset: Offset(0, 4),
                  ),
                ],
              ),
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 12,
                ),
                child: Row(
                  children: [
                    const Icon(Icons.local_fire_department,
                        color: Colors.white, size: 32),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'YANGIN TESPİT EDİLDİ$pct',
                            style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.bold,
                              fontSize: 15,
                            ),
                          ),
                          Text(
                            '${_current!.cameraName}'
                            '${_current!.cameraLocation != null ? " • ${_current!.cameraLocation}" : ""}',
                            style: const TextStyle(
                              color: Colors.white70,
                              fontSize: 13,
                            ),
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close, color: Colors.white),
                      onPressed: () => _anim.reverse(),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
