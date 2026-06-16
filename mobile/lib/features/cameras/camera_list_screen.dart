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

  String _streamUrlForIp(String ip) => 'rtsp://$ip:8554/webcam';

  String _cameraIpFromStreamUrl(String? url) {
    if (url == null || url.trim().isEmpty) return '';
    final uri = Uri.tryParse(url.trim());
    return uri?.host ?? '';
  }

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
    if (auth.user?.role != AppRole.admin) {
      setState(() {
        _loading = false;
        _error = 'Only admins can access this page.';
      });
      return;
    }
    try {
      final r = await createDio(auth).get(ApiEndpoints.cameras);
      final list = (r.data['cameras'] as List?)
              ?.map((e) => CameraModel.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [];
      if (mounted)
        setState(() {
          _cameras = list;
          _loading = false;
        });
    } catch (e) {
      if (mounted)
        setState(() {
          _error = e is DioException
              ? (e.message ?? 'Connection error')
              : 'Could not load';
          _loading = false;
        });
    }
  }

  // ── Add Camera dialog ──────────────────────────────────────
  Future<void> _showAddDialog() async {
    final nameCtrl = TextEditingController();
    final locationCtrl = TextEditingController();
    final rtspCtrl = TextEditingController();
    String? error;
    String? validationMessage;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setS) => AlertDialog(
          title: const Row(
            children: [
              Icon(Icons.videocam_outlined, color: Colors.deepOrange),
              SizedBox(width: 8),
              Text('Add Camera'),
            ],
          ),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  'Register a camera source for the detector service.',
                  style: Theme.of(ctx).textTheme.bodySmall?.copyWith(
                        color: Colors.grey.shade700,
                      ),
                ),
                const SizedBox(height: 14),
                TextField(
                  controller: nameCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Camera Name',
                    hintText: 'Office Entrance Camera',
                    prefixIcon: Icon(Icons.label_outline),
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: locationCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Location',
                    hintText: 'Office / Storage',
                    prefixIcon: Icon(Icons.location_on_outlined),
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                _IpShortcut(
                  onIpSelected: (ip) {
                    rtspCtrl.text = _streamUrlForIp(ip);
                    setS(() {
                      validationMessage = 'Stream source looks valid.';
                      error = null;
                    });
                  },
                ),
                if (validationMessage != null) ...[
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      const Icon(Icons.check_circle,
                          color: Colors.green, size: 16),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          validationMessage!,
                          style: const TextStyle(
                              color: Colors.green, fontSize: 12),
                        ),
                      ),
                    ],
                  ),
                ],
                if (error != null) ...[
                  const SizedBox(height: 8),
                  Text(error!,
                      style: const TextStyle(color: Colors.red, fontSize: 12)),
                ],
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () {
                if (nameCtrl.text.trim().isEmpty ||
                    locationCtrl.text.trim().isEmpty ||
                    rtspCtrl.text.trim().isEmpty) {
                  setS(() =>
                      error = 'Fill in all fields and validate the camera IP');
                  return;
                }
                Navigator.pop(ctx, true);
              },
              child: const Text('Add'),
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
            content: Text(
                'Camera added. Detector will connect automatically within 30 seconds.'),
            backgroundColor: Colors.green,
          ),
        );
        _load();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: ${e is DioException ? e.message : e}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _deleteCamera(CameraModel cam) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete Camera'),
        content: Text(
          'Delete ${cam.name}? Related incidents and notifications for this camera will also be removed.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          FilledButton.icon(
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.pop(ctx, true),
            icon: const Icon(Icons.delete_outline),
            label: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed != true || !mounted) return;

    final auth = context.read<AuthService>();
    try {
      await createDio(auth).delete('${ApiEndpoints.cameras}/${cam.id}');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Camera deleted.'),
            backgroundColor: Colors.green,
          ),
        );
        _load();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e'), backgroundColor: Colors.red),
        );
      }
    }
  }

  // Stream source update dialog
  Future<void> _showEditRtspDialog(CameraModel cam) async {
    final rtspCtrl = TextEditingController(
        text: cam.rtspUrl ?? 'rtsp://192.168.1.35:8554/webcam');
    String? validationMessage;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setS) => AlertDialog(
          title: Text('${cam.name} - Update Stream Source'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'Enter the camera IP address. The stream source is generated automatically.',
                style: Theme.of(ctx).textTheme.bodySmall?.copyWith(
                      color: Colors.grey.shade700,
                    ),
              ),
              const SizedBox(height: 12),
              _IpShortcut(
                initialIp: _cameraIpFromStreamUrl(cam.rtspUrl),
                onIpSelected: (ip) {
                  rtspCtrl.text = _streamUrlForIp(ip);
                  setS(() {
                    validationMessage = 'Stream source looks valid.';
                  });
                },
              ),
              if (validationMessage != null) ...[
                const SizedBox(height: 8),
                Row(
                  children: [
                    const Icon(Icons.check_circle,
                        color: Colors.green, size: 16),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        validationMessage!,
                        style:
                            const TextStyle(color: Colors.green, fontSize: 12),
                      ),
                    ),
                  ],
                ),
              ],
            ],
          ),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: const Text('Cancel')),
            FilledButton(
                onPressed: () => Navigator.pop(ctx, true),
                child: const Text('Save')),
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
            content: Text(
                'Stream source updated. Detector will connect automatically.'),
            backgroundColor: Colors.green,
          ),
        );
        _load();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e'), backgroundColor: Colors.red),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isAdmin = context.watch<AuthService>().user?.role == AppRole.admin;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Cameras'),
        leading: IconButton(
            icon: const Icon(Icons.arrow_back), onPressed: () => context.pop()),
      ),
      floatingActionButton: isAdmin
          ? FloatingActionButton.extended(
              onPressed: _showAddDialog,
              icon: const Icon(Icons.add),
              label: const Text('Add Camera'),
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
                      const Icon(Icons.error_outline,
                          size: 48, color: Colors.red),
                      const SizedBox(height: 12),
                      Text(_error!, textAlign: TextAlign.center),
                      const SizedBox(height: 16),
                      FilledButton(
                          onPressed: _load, child: const Text('Retry')),
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
                              const Icon(Icons.videocam_off,
                                  size: 64, color: Colors.grey),
                              const SizedBox(height: 12),
                              const Text('No cameras yet'),
                              const SizedBox(height: 16),
                              if (isAdmin)
                                FilledButton.icon(
                                  onPressed: _showAddDialog,
                                  icon: const Icon(Icons.add),
                                  label: const Text('Add First Camera'),
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
                                  child: const Icon(Icons.videocam,
                                      color: Colors.deepOrange),
                                ),
                                title: Text(cam.name,
                                    style: const TextStyle(
                                        fontWeight: FontWeight.bold)),
                                subtitle: Text(cam.location),
                                isThreeLine: false,
                                trailing: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    if (cam.rtspUrl != null)
                                      IconButton(
                                        icon: const Icon(Icons.play_circle_fill,
                                            color: Colors.deepOrange),
                                        tooltip: 'Watch live',
                                        onPressed: () => context.push(
                                            AppRouter.liveStreamPath(
                                                cameraId: cam.id)),
                                      ),
                                    if (isAdmin)
                                      IconButton(
                                        icon: const Icon(Icons.edit_outlined),
                                        tooltip: 'Update Stream Source',
                                        onPressed: () =>
                                            _showEditRtspDialog(cam),
                                      ),
                                    if (isAdmin)
                                      IconButton(
                                        icon: const Icon(Icons.delete_outline),
                                        color: Colors.red,
                                        tooltip: 'Delete Camera',
                                        onPressed: () => _deleteCamera(cam),
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
  final String initialIp;
  const _IpShortcut({
    required this.onIpSelected,
    this.initialIp = '',
  });

  @override
  State<_IpShortcut> createState() => _IpShortcutState();
}

class _IpShortcutState extends State<_IpShortcut> {
  final _ctrl = TextEditingController();

  @override
  void initState() {
    super.initState();
    _ctrl.text = widget.initialIp;
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: TextField(
            controller: _ctrl,
            keyboardType: TextInputType.url,
            decoration: const InputDecoration(
              labelText: 'Camera IP',
              hintText: '192.168.1.29',
              helperText: 'Use dots between IP parts.',
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
          child: const Text('Validate Stream'),
        ),
      ],
    );
  }
}
