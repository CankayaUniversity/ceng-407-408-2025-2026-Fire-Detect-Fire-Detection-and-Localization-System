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
    setState(() {
      _loading = true;
      _error = null;
    });
    final auth = context.read<AuthService>();
    final role = auth.user?.role;
    if (role != AppRole.admin) {
      setState(() {
        _loading = false;
        _error = 'Bu sayfaya sadece yönetici (ADMIN) erişebilir.';
      });
      return;
    }
    final dio = createDio(auth);
    try {
      final r = await dio.get(ApiEndpoints.cameras);
      final list = (r.data['cameras'] as List?)?.map((e) => CameraModel.fromJson(e as Map<String, dynamic>)).toList() ?? [];
      if (mounted) setState(() {
        _cameras = list;
        _loading = false;
      });
    } catch (e) {
      if (mounted) setState(() {
        _error = e is DioException ? (e.response?.statusMessage ?? 'Bağlantı hatası') : 'Yüklenemedi';
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Kameralar'),
        leading: IconButton(icon: const Icon(Icons.arrow_back), onPressed: () => context.pop()),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(_error!, textAlign: TextAlign.center),
                      const SizedBox(height: 16),
                      FilledButton(onPressed: _load, child: const Text('Tekrar Dene')),
                    ],
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _load,
                  child: _cameras.isEmpty
                      ? const Center(child: Text('Kamera yok'))
                      : ListView.builder(
                          padding: const EdgeInsets.all(16),
                          itemCount: _cameras.length,
                          itemBuilder: (context, i) {
                            final cam = _cameras[i];
                            final canStream = cam.rtspUrl != null && cam.rtspUrl!.isNotEmpty;
                            return Card(
                              child: ListTile(
                                leading: const Icon(Icons.videocam),
                                title: Text(cam.name),
                                subtitle: Text(cam.location),
                                trailing: canStream
                                    ? IconButton(
                                        icon: const Icon(Icons.play_circle_fill),
                                        onPressed: () => context.push(AppRouter.liveStreamPath(cameraId: cam.id)),
                                      )
                                    : null,
                              ),
                            );
                          },
                        ),
                ),
    );
  }
}
