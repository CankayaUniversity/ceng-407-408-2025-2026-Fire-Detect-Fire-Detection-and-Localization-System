import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:dio/dio.dart';

import 'package:flamescope/core/api/api_client.dart';
import 'package:flamescope/core/auth/auth_service.dart';
import 'package:flamescope/core/constants/api_constants.dart';
import 'package:flamescope/core/stream/hls_player.dart';
import 'package:flamescope/shared/models/camera_model.dart';

class LiveStreamScreen extends StatefulWidget {
  const LiveStreamScreen({
    super.key,
    required this.cameraId,
    required this.incidentId,
  });
  final int cameraId;
  final int incidentId;

  @override
  State<LiveStreamScreen> createState() => _LiveStreamScreenState();
}

class _LiveStreamScreenState extends State<LiveStreamScreen> {
  CameraModel? _camera;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _fetchCamera();
  }

  Future<void> _fetchCamera() async {
    setState(() { _loading = true; _error = null; });
    final auth = context.read<AuthService>();
    try {
      final r = await createDio(auth).get(
        '${ApiEndpoints.cameras}/${widget.cameraId}',
      );
      if (mounted) {
        setState(() {
          _camera = CameraModel.fromJson(r.data as Map<String, dynamic>);
          _loading = false;
        });
      }
    } on DioException catch (e) {
      // 404 ya da auth hatası — sadece cameraId ile devam et
      if (mounted) setState(() { _loading = false; });
    } catch (e) {
      if (mounted) setState(() { _error = e.toString(); _loading = false; });
    }
  }

  String? get _rtspUrl => _camera?.rtspUrl;

  String get _hlsUrl {
    final rtsp = _rtspUrl;
    if (rtsp == null || rtsp.isEmpty) return '';
    return rtspToHls(rtsp);
  }

  @override
  Widget build(BuildContext context) {
    final title = _camera?.name ?? 'Kamera #${widget.cameraId}';

    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: Text(title),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        actions: [
          if (_rtspUrl != null)
            IconButton(
              icon: const Icon(Icons.refresh),
              tooltip: 'Yenile',
              onPressed: _fetchCamera,
            ),
        ],
      ),
      body: _loading
          ? const Center(
              child: CircularProgressIndicator(color: Colors.white),
            )
          : _error != null
              ? _ErrorView(message: _error!, onRetry: _fetchCamera)
              : _rtspUrl == null || _rtspUrl!.isEmpty
                  ? const _NoStreamView()
                  : _StreamView(
                      rtspUrl: _rtspUrl!,
                      hlsUrl: _hlsUrl,
                      cameraName: _camera?.name ?? '',
                      location: _camera?.location ?? '',
                    ),
    );
  }
}

// ── Alt widget'lar ─────────────────────────────────────────────

class _StreamView extends StatelessWidget {
  const _StreamView({
    required this.rtspUrl,
    required this.hlsUrl,
    required this.cameraName,
    required this.location,
  });
  final String rtspUrl;
  final String hlsUrl;
  final String cameraName;
  final String location;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // ── Video alanı ────────────────────────────────────────
        Expanded(
          child: HlsPlayerWidget(rtspUrl: rtspUrl),
        ),
        // ── Alt bilgi şeridi ───────────────────────────────────
        Container(
          color: Colors.black,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          child: Row(
            children: [
              const Icon(Icons.circle, color: Colors.red, size: 10),
              const SizedBox(width: 6),
              const Text(
                'CANLI',
                style: TextStyle(
                  color: Colors.red,
                  fontWeight: FontWeight.bold,
                  fontSize: 12,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  location.isNotEmpty ? location : cameraName,
                  style: const TextStyle(color: Colors.white70, fontSize: 12),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              // HLS URL kopyala butonu
              GestureDetector(
                onTap: () {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text('HLS: $hlsUrl'),
                      action: SnackBarAction(
                        label: 'Tamam',
                        onPressed: () {},
                      ),
                    ),
                  );
                },
                child: const Tooltip(
                  message: 'HLS URL\'yi göster',
                  child: Icon(Icons.info_outline, color: Colors.white38, size: 18),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _NoStreamView extends StatelessWidget {
  const _NoStreamView();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.videocam_off, color: Colors.white38, size: 64),
          SizedBox(height: 16),
          Text(
            'Bu kamera için RTSP URL tanımlı değil.\nKameralar ekranından URL ekleyin.',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.white54),
          ),
        ],
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.message, required this.onRetry});
  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.error_outline, color: Colors.red, size: 48),
          const SizedBox(height: 12),
          Text(message,
              style: const TextStyle(color: Colors.white70),
              textAlign: TextAlign.center),
          const SizedBox(height: 16),
          FilledButton(onPressed: onRetry, child: const Text('Tekrar Dene')),
        ],
      ),
    );
  }
}
