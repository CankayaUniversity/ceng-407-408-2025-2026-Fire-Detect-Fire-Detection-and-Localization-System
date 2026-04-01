import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:dio/dio.dart';
import 'package:flamescope/core/api/api_client.dart';
import 'package:flamescope/core/auth/auth_service.dart';
import 'package:flamescope/core/constants/app_constants.dart';
import 'package:flamescope/core/constants/api_constants.dart';
import 'package:flamescope/core/router/app_router.dart';
import 'package:flamescope/shared/models/camera_model.dart';

class CameraListScreen extends StatefulWidget {
  const CameraListScreen({super.key});

  @override
  State<CameraListScreen> createState() => _CameraListScreenState();
}

class _CameraListScreenState extends State<CameraListScreen> {
  List<CameraModel> _cameras = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    final auth = context.read<AuthService>();
    if (auth.user?.role != AppRole.admin) {
      setState(() { _loading = false; _error = 'Sadece yönetici erişebilir.'; });
      return;
    }
    try {
      final r = await createDio(auth).get(ApiEndpoints.cameras);
      final list = (r.data['cameras'] as List?)
              ?.map((e) => CameraModel.fromJson(e as Map<String, dynamic>))
              .toList() ?? [];
      if (mounted) setState(() { _cameras = list; _loading = false; });
    } catch (e) {
      if (mounted) setState(() {
        _error = e is DioException ? (e.message ?? 'Bağlantı hatası') : 'Yüklenemedi';
        _loading = false;
      });
    }
  }

  // ── Kamera Ekle dialog ──────────────────────────────────────
  Future<void> _showAddDialog() async {
    final nameCtrl = TextEditingController();
    final locationCtrl = TextEditingController();
    final rtspCtrl = TextEditingController(text: 'rtsp://192.168.1.34:8554/stream');
    String? error;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setS) => AlertDialog(
          title: const Row(
            children: [
              Icon(Icons.videocam_outlined, color: Colors.deepOrange),
              SizedBox(width: 8),
              Text('Kamera Ekle'),
            ],
          ),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: nameCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Kamera Adı',
                    hintText: 'Arkadas Webcam',
                    prefixIcon: Icon(Icons.label_outline),
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: locationCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Konum',
                    hintText: 'Ofis / Depo',
                    prefixIcon: Icon(Icons.location_on_outlined),
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: rtspCtrl,
                  decoration: const InputDecoration(
                    labelText: 'RTSP URL',
                    hintText: 'rtsp://192.168.1.X:8554/stream',
                    prefixIcon: Icon(Icons.link),
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 6),
                // Hızlı IP girişi
              _IpShortcut(
                onIpSelected: (ip) {
                  rtspCtrl.text = 'rtsp://$ip:8554/stream';
                  setS(() {});
                },
              ),
                if (error != null) ...[
                  const SizedBox(height: 8),
                  Text(error!, style: const TextStyle(color: Colors.red, fontSize: 12)),
                ],
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('İptal'),
            ),
            FilledButton(
              onPressed: () {
                if (nameCtrl.text.trim().isEmpty ||
                    locationCtrl.text.trim().isEmpty ||
                    rtspCtrl.text.trim().isEmpty) {
                  setS(() => error = 'Tüm alanları doldurun');
                  return;
                }
                Navigator.pop(ctx, true);
              },
              child: const Text('Ekle'),
            ),
          ],
        ),
      ),
    );

    if (confirmed != true || !mounted) return;

    final auth = context.read<AuthService>();
    try {
      // Tırnak ve boşlukları temizle
      final rtsp = rtspCtrl.text.trim().replaceAll('"', '').replaceAll("'", '');
      await createDio(auth).post(ApiEndpoints.cameras, data: {
        'name': nameCtrl.text.trim(),
        'location': locationCtrl.text.trim(),
        'rtsp_url': rtsp,
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Kamera eklendi! Detector 30 saniyede otomatik bağlanır.'),
            backgroundColor: Colors.green,
          ),
        );
        _load();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Hata: ${e is DioException ? e.message : e}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  // ── RTSP URL güncelle dialog ────────────────────────────────
  Future<void> _showEditRtspDialog(CameraModel cam) async {
    final rtspCtrl = TextEditingController(text: cam.rtspUrl ?? 'rtsp://192.168.1.34:8554/stream');

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setS) => AlertDialog(
          title: Text('${cam.name} — RTSP Güncelle'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: rtspCtrl,
                decoration: const InputDecoration(
                  labelText: 'Yeni RTSP URL',
                    hintText: 'rtsp://192.168.1.X:8554/stream',
                    prefixIcon: Icon(Icons.link),
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 8),
                _IpShortcut(
                  onIpSelected: (ip) {
                    rtspCtrl.text = 'rtsp://$ip:8554/stream';
                    setS(() {});
                  },
                ),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('İptal')),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Kaydet')),
          ],
        ),
      ),
    );

    if (confirmed != true || !mounted) return;

    final auth = context.read<AuthService>();
    try {
      final rtsp = rtspCtrl.text.trim().replaceAll('"', '').replaceAll("'", '');
      await createDio(auth).patch(
        '${ApiEndpoints.cameras}/${cam.id}',
        data: {'rtsp_url': rtsp},
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('RTSP URL güncellendi! Detector otomatik bağlanır.'),
            backgroundColor: Colors.green,
          ),
        );
        _load();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Hata: $e'), backgroundColor: Colors.red),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isAdmin = context.watch<AuthService>().user?.role == AppRole.admin;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Kameralar'),
        leading: IconButton(icon: const Icon(Icons.arrow_back), onPressed: () => context.pop()),
      ),
      floatingActionButton: isAdmin
          ? FloatingActionButton.extended(
              onPressed: _showAddDialog,
              icon: const Icon(Icons.add),
              label: const Text('Kamera Ekle'),
              backgroundColor: Colors.deepOrange,
            )
          : null,
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.error_outline, size: 48, color: Colors.red),
                      const SizedBox(height: 12),
                      Text(_error!, textAlign: TextAlign.center),
                      const SizedBox(height: 16),
                      FilledButton(onPressed: _load, child: const Text('Tekrar Dene')),
                    ],
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _load,
                  child: _cameras.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const Icon(Icons.videocam_off, size: 64, color: Colors.grey),
                              const SizedBox(height: 12),
                              const Text('Henüz kamera yok'),
                              const SizedBox(height: 16),
                              if (isAdmin)
                                FilledButton.icon(
                                  onPressed: _showAddDialog,
                                  icon: const Icon(Icons.add),
                                  label: const Text('İlk Kamerayı Ekle'),
                                ),
                            ],
                          ),
                        )
                      : ListView.builder(
                          padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
                          itemCount: _cameras.length,
                          itemBuilder: (context, i) {
                            final cam = _cameras[i];
                            return Card(
                              margin: const EdgeInsets.only(bottom: 8),
                              child: ListTile(
                                leading: CircleAvatar(
                                  backgroundColor: Colors.deepOrange.shade50,
                                  child: const Icon(Icons.videocam, color: Colors.deepOrange),
                                ),
                                title: Text(cam.name,
                                    style: const TextStyle(fontWeight: FontWeight.bold)),
                                subtitle: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(cam.location),
                                    if (cam.rtspUrl != null)
                                      Text(
                                        cam.rtspUrl!,
                                        style: TextStyle(
                                          fontSize: 11,
                                          color: Colors.grey.shade600,
                                          fontFamily: 'monospace',
                                        ),
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                  ],
                                ),
                                isThreeLine: cam.rtspUrl != null,
                                trailing: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    if (cam.rtspUrl != null)
                                      IconButton(
                                        icon: const Icon(Icons.play_circle_fill,
                                            color: Colors.deepOrange),
                                        tooltip: 'Canlı izle',
                                        onPressed: () => context.push(
                                            AppRouter.liveStreamPath(cameraId: cam.id)),
                                      ),
                                    if (isAdmin)
                                      IconButton(
                                        icon: const Icon(Icons.edit_outlined),
                                        tooltip: 'RTSP güncelle',
                                        onPressed: () => _showEditRtspDialog(cam),
                                      ),
                                  ],
                                ),
                              ),
                            );
                          },
                        ),
                ),
    );
  }
}

/// Hızlı IP seçimi widgeti — yaygın subnet'leri gösterir.
class _IpShortcut extends StatefulWidget {
  final void Function(String ip) onIpSelected;
  const _IpShortcut({required this.onIpSelected});

  @override
  State<_IpShortcut> createState() => _IpShortcutState();
}

class _IpShortcutState extends State<_IpShortcut> {
  final _ctrl = TextEditingController();

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: TextField(
            controller: _ctrl,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(
              labelText: 'Arkadaşın IP\'si',
              hintText: '192.168.1.X',
              isDense: true,
              border: OutlineInputBorder(),
              prefixIcon: Icon(Icons.wifi, size: 18),
            ),
          ),
        ),
        const SizedBox(width: 8),
        FilledButton.tonal(
          onPressed: () {
            final ip = _ctrl.text.trim();
            if (ip.isNotEmpty) widget.onIpSelected(ip);
          },
          child: const Text('Uygula'),
        ),
      ],
    );
  }
}
