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
      if (mounted) setState(() {
        _incident = IncidentModel.fromJson(r.data as Map<String, dynamic>);
        _loading = false;
      });
    } catch (e) {
      if (mounted) setState(() {
        _error = e is DioException ? (e.response?.statusMessage ?? 'Yüklenemedi') : 'Hata';
        _loading = false;
      });
    }
  }

  Future<void> _confirm() async {
    final auth = context.read<AuthService>();
    if (auth.user?.role != AppRole.admin && auth.user?.role != AppRole.manager) return;
    final dio = createDio(auth);
    try {
      await dio.post('${ApiEndpoints.incidents}/${widget.incidentId}/confirm');
      if (!mounted) return;
      await _load();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Olay başarıyla doğrulandı')),
      );
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Doğrulama gönderilemedi')));
    }
  }

  Future<void> _dismiss() async {
    final auth = context.read<AuthService>();
    if (auth.user?.role != AppRole.admin && auth.user?.role != AppRole.manager) return;
    final dio = createDio(auth);
    try {
      await dio.post('${ApiEndpoints.incidents}/${widget.incidentId}/dismiss');
      if (!mounted) return;
      await _load();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Olay yanlış alarm olarak işaretlendi')),
      );
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Red gönderilemedi')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthService>();
    final canConfirmDismiss = auth.user?.role == AppRole.admin || auth.user?.role == AppRole.manager;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Olay Detayı'),
        leading: IconButton(icon: const Icon(Icons.arrow_back), onPressed: () => context.pop()),
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
                                    _incident!.cameraName ?? 'Kamera #${_incident!.cameraId}',
                                    style: Theme.of(context).textTheme.titleLarge,
                                  ),
                                  const SizedBox(height: 8),
                                  if (_incident!.cameraLocation != null)
                                    _InfoRow(Icons.location_on, _incident!.cameraLocation!),
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
                                      'Güven: ${(_incident!.confidence! * 100).toStringAsFixed(0)}%',
                                    ),
                                  if (_incident!.detectedAt != null)
                                    _InfoRow(Icons.access_time, _formatDate(_incident!.detectedAt!)),
                                ],
                              ),
                            ),
                          ),

                          // ── Onayla / Reddet ────────────────────────────────
                          if (canConfirmDismiss && _incident!.isDetected) ...[
                            const SizedBox(height: 16),
                            Row(
                              children: [
                                Expanded(
                                  child: FilledButton.icon(
                                    style: FilledButton.styleFrom(backgroundColor: Colors.red),
                                    onPressed: _confirm,
                                    icon: const Icon(Icons.local_fire_department),
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
                          if ((auth.user?.role == AppRole.admin || auth.user?.role == AppRole.manager) && _incident!.canStream) ...[
                            const SizedBox(height: 12),
                            OutlinedButton.icon(
                              onPressed: () => context.push(AppRouter.liveStreamPath(cameraId: _incident!.cameraId, incidentId: _incident!.id)),
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
          Icon(icon, size: 16, color: iconColor ?? Theme.of(context).colorScheme.primary),
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
          fit: BoxFit.cover,
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
                Text('Görüntü yüklenemedi', style: TextStyle(color: Colors.grey)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
