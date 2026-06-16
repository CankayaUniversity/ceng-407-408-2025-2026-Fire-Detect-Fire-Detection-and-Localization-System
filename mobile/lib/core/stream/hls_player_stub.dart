import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';

String rtspToHls(String rtspUrl) {
  try {
    final clean = rtspUrl.replaceAll('"', '').trim();
    final uri = Uri.parse(clean);
    final path = uri.path.isEmpty ? '/webcam' : uri.path;
    return 'http://${uri.host}:8888$path/index.m3u8';
  } catch (_) {
    return rtspUrl;
  }
}

class HlsPlayerWidget extends StatefulWidget {
  const HlsPlayerWidget({super.key, required this.rtspUrl});
  final String rtspUrl;

  @override
  State<HlsPlayerWidget> createState() => _HlsPlayerWidgetState();
}

class _HlsPlayerWidgetState extends State<HlsPlayerWidget> {
  VideoPlayerController? _controller;
  String? _error;

  @override
  void initState() {
    super.initState();
    _openStream();
  }

  @override
  void didUpdateWidget(covariant HlsPlayerWidget oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.rtspUrl != widget.rtspUrl) {
      _openStream();
    }
  }

  Future<void> _openStream() async {
    final old = _controller;
    _controller = null;
    await old?.dispose();

    final hlsUrl = rtspToHls(widget.rtspUrl);
    final controller = VideoPlayerController.networkUrl(Uri.parse(hlsUrl));

    setState(() {
      _controller = controller;
      _error = null;
    });

    try {
      await controller.initialize();
      await controller.setLooping(true);
      await controller.play();
      if (mounted) setState(() {});
    } catch (e) {
      if (mounted) {
        setState(() => _error = 'Stream could not be opened: $hlsUrl');
      }
      await controller.dispose();
      if (mounted && identical(_controller, controller)) {
        _controller = null;
      }
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = _controller;

    if (_error != null) {
      return _MessageView(
        icon: Icons.videocam_off_outlined,
        message: _error!,
        onRetry: _openStream,
      );
    }

    if (controller == null || !controller.value.isInitialized) {
      return const Center(
        child: CircularProgressIndicator(color: Colors.white),
      );
    }

    return Center(
      child: AspectRatio(
        aspectRatio: controller.value.aspectRatio,
        child: VideoPlayer(controller),
      ),
    );
  }
}

class _MessageView extends StatelessWidget {
  const _MessageView({
    required this.icon,
    required this.message,
    required this.onRetry,
  });

  final IconData icon;
  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: Colors.white54, size: 48),
            const SizedBox(height: 12),
            Text(
              message,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.white70),
            ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: onRetry,
              child: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }
}
