import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:dio/dio.dart';
import 'package:flamescope/core/api/api_client.dart';
import 'package:flamescope/core/auth/auth_service.dart';
import 'package:flamescope/core/constants/api_constants.dart';
import 'package:flamescope/core/constants/app_constants.dart';
import 'package:flamescope/core/router/app_router.dart';
import 'package:flamescope/shared/models/incident_model.dart';

class IncidentDetailScreen extends StatefulWidget {
  const IncidentDetailScreen({super.key, required this.incidentId});
  final int incidentId;

  @override
  State<IncidentDetailScreen> createState() => _IncidentDetailScreenState();
}

class _IncidentDetailScreenState extends State<IncidentDetailScreen> {
  IncidentModel? _incident;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    final auth = context.read<AuthService>();
    final dio = createDio(auth);
    try {
      final r = await dio.get('${ApiEndpoints.incidents}/${widget.incidentId}');
      if (mounted)
        setState(() {
          _incident = IncidentModel.fromJson(r.data as Map<String, dynamic>);
          _loading = false;
        });
    } catch (e) {
      if (mounted)
        setState(() {
          _error = e is DioException
              ? (e.response?.statusMessage ?? 'Yüklenemedi')
              : 'Hata';
          _loading = false;
        });
    }
  }

  Future<void> _confirm() async {
    final auth = context.read<AuthService>();
    if (auth.user?.role != AppRole.admin && auth.user?.role != AppRole.manager)
      return;
    final dio = createDio(auth);
    try {
      await dio.post('${ApiEndpoints.incidents}/${widget.incidentId}/confirm');
      if (!mounted) return;
      await _load();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Olay başarıyla doğrulandı')),
      );
    } catch (_) {
      if (mounted)
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Doğrulama gönderilemedi')));
    }
  }

  Future<void> _dismiss() async {
    final auth = context.read<AuthService>();
    if (auth.user?.role != AppRole.admin && auth.user?.role != AppRole.manager)
      return;
    final dio = createDio(auth);
    try {
      await dio.post('${ApiEndpoints.incidents}/${widget.incidentId}/dismiss');
      if (!mounted) return;
      await _load();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Olay yanlış alarm olarak işaretlendi')),
      );
    } catch (_) {
      if (mounted)
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: Text('Red gönderilemedi')));
    }
  }

  Future<void> _submitSafetyStatus(String status) async {
    final dio = createDio(context.read<AuthService>());
    try {
      await dio.post(
        ApiEndpoints.incidentSafetyReport(widget.incidentId),
        data: {'status': status},
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            status == 'SAFE'
                ? 'Guvenli durum bildirildi'
                : 'Yardim ihtiyaci bildirildi',
          ),
        ),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Durum bildirimi gonderilemedi')),
      );
    }
  }

  Future<void> _submitResponseStatus(String status) async {
    final dio = createDio(context.read<AuthService>());
    try {
      await dio.post(
        ApiEndpoints.incidentResponseUpdate(widget.incidentId),
        data: {'status': status},
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Mudahale durumu guncellendi')),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Mudahale durumu gonderilemedi')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthService>();
    final canConfirmDismiss =
        auth.user?.role == AppRole.admin || auth.user?.role == AppRole.manager;
    final isEmployee = auth.user?.role == AppRole.employee;
    final isFireResponse = auth.user?.role == AppRole.fireResponseUnit;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Olay Detayı'),
        leading: IconButton(
            icon: const Icon(Icons.arrow_back), onPressed: () => context.pop()),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text(_error!))
              : _incident == null
                  ? const Center(child: Text('Bulunamadı'))
                  : SingleChildScrollView(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          // ── Snapshot fotoğrafı ─────────────────────────────
                          if ((_incident!.snapshotUrl ?? '').isNotEmpty)
                            _SnapshotImage(url: _incident!.snapshotUrl!),

                          const SizedBox(height: 12),

                          // ── Olay bilgileri ─────────────────────────────────
                          Card(
                            child: Padding(
                              padding: const EdgeInsets.all(16),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    _incident!.cameraName ??
                                        'Kamera #${_incident!.cameraId}',
                                    style:
                                        Theme.of(context).textTheme.titleLarge,
                                  ),
                                  const SizedBox(height: 8),
                                  if (_incident!.cameraLocation != null)
                                    _InfoRow(Icons.location_on,
                                        _incident!.cameraLocation!),
                                  _InfoRow(
                                    Icons.circle,
                                    _incident!.status,
                                    iconColor: _incident!.isConfirmed
                                        ? Colors.green
                                        : _incident!.isDetected
                                            ? Colors.orange
                                            : Colors.grey,
                                  ),
                                  if (_incident!.confidence != null)
                                    _InfoRow(
                                      Icons.percent,
                                      'Risk Skoru: ${(_incident!.confidence! * 100).toStringAsFixed(0)}%',
                                    ),
                                  const SizedBox(height: 8),
                                  _RiskLevelChip(incident: _incident!),
                                  if (_incident!.detectedAt != null)
                                    _InfoRow(Icons.access_time,
                                        _formatDate(_incident!.detectedAt!)),
                                ],
                              ),
                            ),
                          ),

                          // ── Onayla / Reddet ────────────────────────────────
                          const SizedBox(height: 12),
                          _IncidentTimeline(
                            incident: _incident!,
                            formatDate: _formatDate,
                          ),

                          if (canConfirmDismiss && _incident!.isDetected) ...[
                            const SizedBox(height: 16),
                            Row(
                              children: [
                                Expanded(
                                  child: FilledButton.icon(
                                    style: FilledButton.styleFrom(
                                        backgroundColor: Colors.red),
                                    onPressed: _confirm,
                                    icon:
                                        const Icon(Icons.local_fire_department),
                                    label: const Text('Yangın — Onayla'),
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: OutlinedButton.icon(
                                    onPressed: _dismiss,
                                    icon: const Icon(Icons.close),
                                    label: const Text('Yanlış Alarm'),
                                  ),
                                ),
                              ],
                            ),
                          ],

                          // ── Canlı yayın ────────────────────────────────────
                          if (isEmployee && _incident!.isConfirmed) ...[
                            const SizedBox(height: 16),
                            _EmployeeSafetyActions(
                              onSafe: () => _submitSafetyStatus('SAFE'),
                              onNeedHelp: () =>
                                  _submitSafetyStatus('NEED_HELP'),
                            ),
                          ],

                          if (isFireResponse && _incident!.isConfirmed) ...[
                            const SizedBox(height: 16),
                            _FireResponseActions(
                              onDispatched: () =>
                                  _submitResponseStatus('DISPATCHED'),
                              onArrived: () => _submitResponseStatus('ARRIVED'),
                              onUnderControl: () =>
                                  _submitResponseStatus('UNDER_CONTROL'),
                            ),
                          ],

                          if ((auth.user?.role == AppRole.admin ||
                                  auth.user?.role == AppRole.manager) &&
                              _incident!.canStream) ...[
                            const SizedBox(height: 12),
                            OutlinedButton.icon(
                              onPressed: () => context.push(
                                  AppRouter.liveStreamPath(
                                      cameraId: _incident!.cameraId,
                                      incidentId: _incident!.id)),
                              icon: const Icon(Icons.videocam),
                              label: const Text('Canlı Yayına Geç'),
                            ),
                          ],
                        ],
                      ),
                    ),
    );
  }

  String _formatDate(DateTime d) {
    return '${d.day}.${d.month}.${d.year} ${d.hour}:${d.minute.toString().padLeft(2, '0')}';
  }
}

// ── Yardımcı widget'lar ──────────────────────────────────────────────────────

class _RiskLevelChip extends StatelessWidget {
  const _RiskLevelChip({required this.incident});

  final IncidentModel incident;

  @override
  Widget build(BuildContext context) {
    final color = switch (incident.riskLevel) {
      'CRITICAL' => Colors.red,
      'HIGH' => Colors.deepOrange,
      'MEDIUM' => Colors.orange,
      'LOW' => Colors.green,
      _ => Colors.grey,
    };

    return Align(
      alignment: Alignment.centerLeft,
      child: Chip(
        avatar: Icon(Icons.shield, color: color, size: 18),
        label: Text(incident.riskLevelLabel),
        side: BorderSide(color: color.withValues(alpha: 0.45)),
        backgroundColor: color.withValues(alpha: 0.08),
      ),
    );
  }
}

class _IncidentTimeline extends StatelessWidget {
  const _IncidentTimeline({
    required this.incident,
    required this.formatDate,
  });

  final IncidentModel incident;
  final String Function(DateTime date) formatDate;

  @override
  Widget build(BuildContext context) {
    final items = <_TimelineItem>[
      _TimelineItem(
        title: 'Tespit edildi',
        subtitle: incident.detectedAt == null
            ? 'Kamera goruntusunden riskli olay uretildi'
            : formatDate(incident.detectedAt!),
        icon: Icons.sensors,
        color: Colors.orange,
        completed: true,
      ),
      _TimelineItem(
        title: incident.isConfirmed
            ? 'Karar verildi'
            : 'Yonetici onayi bekleniyor',
        subtitle: incident.isConfirmed
            ? 'Alarm CONFIRMED durumuna alindi'
            : 'Admin/manager olayi onaylayabilir veya yanlis alarm isaretleyebilir',
        icon: incident.isConfirmed ? Icons.verified : Icons.hourglass_bottom,
        color: incident.isConfirmed ? Colors.green : Colors.orange,
        completed: incident.isConfirmed,
      ),
      _TimelineItem(
        title: 'Calisanlara bildirildi',
        subtitle: incident.confirmedAt == null
            ? 'Onay sonrasi employee ve fire response unit bilgilendirilir'
            : formatDate(incident.confirmedAt!),
        icon: Icons.campaign,
        color: Colors.red,
        completed: incident.isConfirmed,
      ),
    ];

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Olay Zaman Cizelgesi',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 12),
            for (var i = 0; i < items.length; i++)
              _TimelineRow(
                item: items[i],
                isLast: i == items.length - 1,
              ),
          ],
        ),
      ),
    );
  }
}

class _TimelineItem {
  const _TimelineItem({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.color,
    required this.completed,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final Color color;
  final bool completed;
}

class _TimelineRow extends StatelessWidget {
  const _TimelineRow({
    required this.item,
    required this.isLast,
  });

  final _TimelineItem item;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    final color = item.completed ? item.color : Colors.grey;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Column(
          children: [
            CircleAvatar(
              radius: 16,
              backgroundColor: color.withValues(alpha: 0.14),
              child: Icon(item.icon, size: 17, color: color),
            ),
            if (!isLast)
              Container(
                width: 2,
                height: 34,
                color: color.withValues(alpha: 0.25),
              ),
          ],
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Padding(
            padding: EdgeInsets.only(bottom: isLast ? 0 : 14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.title,
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 2),
                Text(
                  item.subtitle,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _EmployeeSafetyActions extends StatelessWidget {
  const _EmployeeSafetyActions({
    required this.onSafe,
    required this.onNeedHelp,
  });

  final VoidCallback onSafe;
  final VoidCallback onNeedHelp;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Tahliye Durumu',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: onSafe,
              icon: const Icon(Icons.check_circle),
              label: const Text('Guvendeyim'),
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: onNeedHelp,
              icon: const Icon(Icons.sos),
              label: const Text('Yardima ihtiyacim var'),
            ),
          ],
        ),
      ),
    );
  }
}

class _FireResponseActions extends StatelessWidget {
  const _FireResponseActions({
    required this.onDispatched,
    required this.onArrived,
    required this.onUnderControl,
  });

  final VoidCallback onDispatched;
  final VoidCallback onArrived;
  final VoidCallback onUnderControl;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Mudahale Durumu',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: onDispatched,
              icon: const Icon(Icons.local_fire_department),
              label: const Text('Yola cikildi'),
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: onArrived,
              icon: const Icon(Icons.location_on),
              label: const Text('Olay yerine ulasildi'),
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: onUnderControl,
              icon: const Icon(Icons.health_and_safety),
              label: const Text('Kontrol altina alindi'),
            ),
          ],
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow(this.icon, this.text, {this.iconColor});
  final IconData icon;
  final String text;
  final Color? iconColor;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: [
          Icon(icon,
              size: 16,
              color: iconColor ?? Theme.of(context).colorScheme.primary),
          const SizedBox(width: 6),
          Expanded(child: Text(text)),
        ],
      ),
    );
  }
}

class _SnapshotImage extends StatelessWidget {
  const _SnapshotImage({required this.url});
  final String url;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(12),
      child: AspectRatio(
        aspectRatio: 16 / 9,
        child: Image.network(
          url,
          fit: BoxFit.contain,
          loadingBuilder: (_, child, progress) => progress == null
              ? child
              : Container(
                  color: Colors.grey[200],
                  child: const Center(child: CircularProgressIndicator()),
                ),
          errorBuilder: (_, __, ___) => Container(
            color: Colors.grey[200],
            child: const Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.broken_image, size: 48, color: Colors.grey),
                SizedBox(height: 8),
                Text('Görüntü yüklenemedi',
                    style: TextStyle(color: Colors.grey)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
