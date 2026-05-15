import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:flamescope/core/auth/auth_service.dart';
import 'package:flamescope/core/notifications/notification_service.dart';
import 'package:flamescope/core/router/app_router.dart';
import 'package:flamescope/core/theme/app_theme.dart';

class DashboardActionItem {
  const DashboardActionItem({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.route,
    this.emphasized = false,
    this.centered = false,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final String route;
  final bool emphasized;
  final bool centered;
}

class DashboardHomeView extends StatelessWidget {
  const DashboardHomeView({
    super.key,
    required this.roleTitle,
    required this.userName,
    required this.roleLabel,
    required this.actions,
    required this.onAlertTap,
    this.showStatusHero = true,
    this.sectionTitle = 'Hızlı Menüler',
    this.description = 'Sistem durumunu izleyin ve kritik işlemlere hızlıca erişin.',
  });

  final String roleTitle;
  final String userName;
  final String roleLabel;
  final List<DashboardActionItem> actions;
  final void Function(BuildContext context, FireIncidentEvent event) onAlertTap;
  final bool showStatusHero;
  final String sectionTitle;
  final String description;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        centerTitle: false,
        titleSpacing: 16,
        title: Align(
          alignment: Alignment.centerLeft,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                userName,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.w800,
                    ),
              ),
              Text(
                roleLabel,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
              ),
            ],
          ),
        ),
        actions: [
          IconButton(
            tooltip: 'Çıkış yap',
            icon: const Icon(Icons.logout),
            onPressed: () async {
              await context.read<AuthService>().logout();
              if (context.mounted) context.go(AppRouter.login);
            },
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 18),
        children: [
          Text(
            roleTitle,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  color: Colors.white,
                ),
          ),
          const SizedBox(height: 6),
          Text(
            description,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
          ),
          if (showStatusHero) ...[
            const SizedBox(height: 16),
            _StatusHeroCard(onAlertTap: onAlertTap),
            const SizedBox(height: 18),
          ] else
            const SizedBox(height: 14),
          Text(
            sectionTitle,
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  color: Colors.white,
                ),
          ),
          const SizedBox(height: 10),
          _DashboardActionGrid(actions: actions),
        ],
      ),
    );
  }
}

class _DashboardActionGrid extends StatelessWidget {
  const _DashboardActionGrid({required this.actions});

  final List<DashboardActionItem> actions;

  @override
  Widget build(BuildContext context) {
    if (actions.length == 1) {
      return _DashboardActionCard(item: actions.first, minHeight: 152);
    }

    if (actions.length == 3 && actions.first.emphasized) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            width: double.infinity,
            child: _DashboardActionCard(
              item: actions.first,
              minHeight: 118,
              centered: true,
            ),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: _DashboardActionCard(
                  item: actions[1],
                  minHeight: 148,
                  centered: true,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _DashboardActionCard(
                  item: actions[2],
                  minHeight: 148,
                  centered: true,
                ),
              ),
            ],
          ),
        ],
      );
    }

    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: actions.length,
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        crossAxisSpacing: 12,
        mainAxisSpacing: 12,
        childAspectRatio: 1.18,
      ),
      itemBuilder: (context, index) {
        final item = actions[index];
        return _DashboardActionCard(item: item);
      },
    );
  }
}

class _StatusHeroCard extends StatefulWidget {
  const _StatusHeroCard({required this.onAlertTap});

  final void Function(BuildContext context, FireIncidentEvent event) onAlertTap;

  @override
  State<_StatusHeroCard> createState() => _StatusHeroCardState();
}

class _StatusHeroCardState extends State<_StatusHeroCard>
    with SingleTickerProviderStateMixin {
  late final AnimationController _pulseController;
  late final Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    );
    _pulseAnimation = Tween<double>(
      begin: 0.94,
      end: 1.02,
    ).animate(CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut));
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final hasAlarm = context.watch<NotificationService>().lastEvent != null;
    if (hasAlarm) {
      _pulseController.repeat(reverse: true);
    } else {
      _pulseController.stop();
      _pulseController.value = 1;
    }
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final notificationService = context.watch<NotificationService>();
    final event = notificationService.lastEvent;
    final hasAlarm = event != null;

    final backgroundGradient = hasAlarm
        ? const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Color(0xFF5C1712),
              Color(0xFF8A261B),
            ],
          )
        : const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Color(0xFF133520),
              Color(0xFF1F5A30),
            ],
          );

    return AnimatedBuilder(
      animation: _pulseAnimation,
      builder: (context, child) {
        return Transform.scale(
          scale: hasAlarm ? _pulseAnimation.value : 1,
          child: Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: backgroundGradient,
              borderRadius: BorderRadius.circular(24),
              border: Border.all(
                color: hasAlarm
                    ? AppColors.orangeSoft.withValues(alpha: 0.55)
                    : Colors.white.withValues(alpha: 0.10),
              ),
            ),
            child: child,
          ),
        );
      },
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 46,
                height: 46,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(
                  hasAlarm ? Icons.warning_amber_rounded : Icons.verified_user_rounded,
                  color: Colors.white,
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      hasAlarm ? 'AKTİF ALARM' : 'Sistem Durumu',
                      style: theme.textTheme.labelLarge?.copyWith(
                        color: Colors.white.withValues(alpha: 0.90),
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      hasAlarm ? event.cameraName : 'Sistem Aktif ve Güvenli',
                      style: theme.textTheme.headlineSmall?.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Text(
            hasAlarm
                ? '${event.cameraLocation ?? 'Kamera konumu bilinmiyor'}${event.confidence != null ? ' • %${(event.confidence! * 100).toStringAsFixed(0)} güven' : ''}'
                : 'Kritik uyarı görünmüyor. Kameralar ve olay akışları izlenmeye devam ediyor.',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: Colors.white.withValues(alpha: 0.84),
            ),
          ),
          const SizedBox(height: 18),
          Row(
            children: [
              Expanded(
                child: FilledButton(
                  style: FilledButton.styleFrom(
                    backgroundColor: hasAlarm
                        ? AppColors.orangeSoft
                        : Colors.white.withValues(alpha: 0.14),
                    foregroundColor: Colors.white,
                  ),
                  onPressed: hasAlarm
                      ? () => widget.onAlertTap(context, event)
                      : () => context.push(AppRouter.incidentList),
                  child: Text(hasAlarm ? 'Alarmı Aç' : 'Olayları Gör'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _DashboardActionCard extends StatelessWidget {
  const _DashboardActionCard({
    required this.item,
    this.minHeight,
    this.centered,
  });

  final DashboardActionItem item;
  final double? minHeight;
  final bool? centered;

  @override
  Widget build(BuildContext context) {
    final isCentered = centered ?? item.centered;

    return InkWell(
      borderRadius: BorderRadius.circular(22),
      onTap: () => context.push(item.route),
      child: Ink(
        decoration: BoxDecoration(
          color: AppColors.navySurface,
          borderRadius: BorderRadius.circular(22),
          border: Border.all(
            color: Theme.of(context).colorScheme.outlineVariant,
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: ConstrainedBox(
            constraints: BoxConstraints(minHeight: minHeight ?? 0),
            child: Column(
              crossAxisAlignment: isCentered
                  ? CrossAxisAlignment.center
                  : CrossAxisAlignment.start,
              mainAxisAlignment: isCentered
                  ? MainAxisAlignment.center
                  : MainAxisAlignment.start,
              children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: AppColors.orangeContainer,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Icon(
                    item.icon,
                    color: AppColors.orangeSoft,
                    size: 22,
                  ),
                ),
                SizedBox(height: isCentered ? 14 : 18),
                Text(
                  item.title,
                  textAlign: isCentered ? TextAlign.center : TextAlign.start,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.w800,
                      ),
                ),
                const SizedBox(height: 4),
                Text(
                  item.subtitle,
                  textAlign: isCentered ? TextAlign.center : TextAlign.start,
                  maxLines: isCentered ? 2 : 3,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                        height: 1.3,
                      ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
