import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:dio/dio.dart';
import 'package:flamescope/core/api/api_client.dart';
import 'package:flamescope/core/auth/auth_service.dart';
import 'package:flamescope/core/constants/api_constants.dart';
import 'package:flamescope/core/constants/app_constants.dart';
import 'package:flamescope/core/router/app_router.dart';
import 'package:flamescope/core/utils/display_formatters.dart';
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
              ? (e.response?.statusMessage ?? 'Could not load')
              : 'Error';
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
        const SnackBar(content: Text('Incident confirmed successfully')),
      );
    } catch (_) {
      if (mounted)
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Confirmation could not be sent')));
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
        const SnackBar(content: Text('Incident marked as false alarm')),
      );
    } catch (_) {
      if (mounted)
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Dismiss request could not be sent')));
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
      await _load();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            status == 'SAFE'
                ? 'Safety status reported'
                : 'Need-help status reported',
          ),
        ),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Status report could not be sent')),
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
      await _load();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Response status updated')),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Response status could not be sent')),
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
        title: const Text('Incident Detail'),
        leading: IconButton(
            icon: const Icon(Icons.arrow_back), onPressed: () => context.pop()),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text(_error!))
              : _incident == null
                  ? const Center(child: Text('Not found'))
                  : SingleChildScrollView(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          // ── Snapshot fotoğrafı ─────────────────────────────
                          if ((_incident!.snapshotUrl ?? '').isNotEmpty)
                            _SnapshotImage(url: _incident!.snapshotUrl!),

                          const SizedBox(height: 12),

                          // ── Incident information ─────────────────────────────────
                          Card(
                            color: const Color(0xFFFFF3E0),
                            child: Padding(
                              padding: const EdgeInsets.all(16),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    _incident!.cameraName ??
                                        'Camera #${_incident!.cameraId}',
                                    style: Theme.of(context)
                                        .textTheme
                                        .titleLarge
                                        ?.copyWith(
                                          fontWeight: FontWeight.w800,
                                        ),
                                  ),
                                  const SizedBox(height: 8),
                                  if (_incident!.cameraLocation != null)
                                    _InfoRow(Icons.location_on,
                                        _incident!.cameraLocation!),
                                  StatusBadge(status: _incident!.status),
                                  if (_incident!.confidence != null)
                                    _InfoRow(
                                      Icons.percent,
                                      'Risk Score: ${(_incident!.confidence! * 100).toStringAsFixed(0)}%',
                                    ),
                                  const SizedBox(height: 8),
                                  _RiskLevelChip(incident: _incident!),
                                  if (_incident!.detectedAt != null)
                                    _InfoRow(
                                      Icons.access_time,
                                      formatIncidentDate(
                                        _incident!.detectedAt!,
                                      ),
                                    ),
                                ],
                              ),
                            ),
                          ),

                          // ── Confirm / Dismiss ────────────────────────────────
                          const SizedBox(height: 12),
                          _IncidentTimeline(
                            incident: _incident!,
                            formatDate: formatIncidentDate,
                          ),

                          if (canConfirmDismiss &&
                              (_incident!.safetyReports.isNotEmpty ||
                                  _incident!.responseUpdates.isNotEmpty)) ...[
                            const SizedBox(height: 12),
                            _OperationsFeedbackPanel(incident: _incident!),
                          ],

                          if (canConfirmDismiss && _incident!.isDetected) ...[
                            const SizedBox(height: 16),
                            Row(
                              children: [
                                Expanded(
                                  child: FilledButton.icon(
                                    style: FilledButton.styleFrom(
                                        backgroundColor:
                                            const Color(0xFFD84315)),
                                    onPressed: _confirm,
                                    icon:
                                        const Icon(Icons.local_fire_department),
                                    label: const Text('Confirm Alarm'),
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: OutlinedButton.icon(
                                    onPressed: _dismiss,
                                    icon: const Icon(Icons.close),
                                    label: const Text('False Alarm'),
                                  ),
                                ),
                              ],
                            ),
                          ],

                          // ── Live stream ────────────────────────────────────
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
                              label: const Text('Open Live View'),
                            ),
                          ],
                        ],
                      ),
                    ),
    );
  }
}

// ── Helper widgets ───────────────────────────────────────────────────────────

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
        title: 'Detected',
        subtitle: incident.detectedAt == null
            ? 'A risky event was generated from camera footage'
            : formatDate(incident.detectedAt!),
        icon: Icons.sensors,
        color: Colors.orange,
        completed: true,
      ),
      _TimelineItem(
        title: incident.isDismissed
            ? 'Marked as false alarm'
            : incident.isConfirmed
                ? 'Decision made'
                : 'Waiting for manager approval',
        subtitle: incident.isDismissed
            ? 'Alarm was moved to DISMISSED status'
            : incident.isConfirmed
                ? 'Alarm was moved to CONFIRMED status'
                : 'Admin/manager can confirm the incident or mark it as false alarm',
        icon: incident.isDismissed
            ? Icons.cancel_outlined
            : incident.isConfirmed
                ? Icons.verified
                : Icons.hourglass_bottom,
        color: incident.isDismissed
            ? Colors.grey
            : incident.isConfirmed
                ? Colors.green
                : Colors.orange,
        completed: incident.isConfirmed || incident.isDismissed,
      ),
      _TimelineItem(
        title: 'Team notified',
        subtitle: incident.confirmedAt == null
            ? 'Employee and fire response unit are notified after confirmation'
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
              'Incident Timeline',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
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

class _OperationsFeedbackPanel extends StatelessWidget {
  const _OperationsFeedbackPanel({required this.incident});

  final IncidentModel incident;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Field Feedback',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            if (incident.safetyReports.isNotEmpty) ...[
              const SizedBox(height: 12),
              Text(
                'Employee Safety',
                style: Theme.of(context).textTheme.labelLarge,
              ),
              const SizedBox(height: 8),
              for (final report in incident.safetyReports)
                _FeedbackRow(
                  icon: report.needsHelp ? Icons.sos : Icons.check_circle,
                  iconColor: report.needsHelp ? Colors.red : Colors.green,
                  title: report.userName,
                  status: report.label,
                  time: report.createdAt,
                ),
            ],
            if (incident.responseUpdates.isNotEmpty) ...[
              const SizedBox(height: 12),
              Text(
                'Fire Response Unit',
                style: Theme.of(context).textTheme.labelLarge,
              ),
              const SizedBox(height: 8),
              for (final update in incident.responseUpdates)
                _FeedbackRow(
                  icon: Icons.local_fire_department,
                  iconColor: Colors.deepOrange,
                  title: update.userName,
                  status: update.label,
                  time: update.createdAt,
                ),
            ],
          ],
        ),
      ),
    );
  }
}

class _FeedbackRow extends StatelessWidget {
  const _FeedbackRow({
    required this.icon,
    required this.iconColor,
    required this.title,
    required this.status,
    required this.time,
  });

  final IconData icon;
  final Color iconColor;
  final String title;
  final String status;
  final DateTime? time;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          CircleAvatar(
            radius: 15,
            backgroundColor: iconColor.withValues(alpha: 0.12),
            child: Icon(icon, size: 16, color: iconColor),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title,
                    style: const TextStyle(fontWeight: FontWeight.w600)),
                Text(
                  time == null
                      ? status
                      : '$status • ${formatIncidentDate(time!)}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
        ],
      ),
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
              'Evacuation Status',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: onSafe,
              icon: const Icon(Icons.check_circle),
              label: const Text('I am safe'),
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: onNeedHelp,
              icon: const Icon(Icons.sos),
              label: const Text('I need help'),
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
              'Response Status',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: onDispatched,
              icon: const Icon(Icons.local_fire_department),
              label: const Text('Dispatched'),
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: onArrived,
              icon: const Icon(Icons.location_on),
              label: const Text('Arrived on scene'),
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: onUnderControl,
              icon: const Icon(Icons.health_and_safety),
              label: const Text('Under control'),
            ),
          ],
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow(this.icon, this.text);
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: [
          Icon(icon, size: 16, color: Theme.of(context).colorScheme.primary),
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
      borderRadius: BorderRadius.circular(8),
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
                Text('Image could not be loaded',
                    style: TextStyle(color: Colors.grey)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
