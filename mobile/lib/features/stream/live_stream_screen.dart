import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class LiveStreamScreen extends StatelessWidget {
  const LiveStreamScreen({super.key, required this.cameraId, required this.incidentId});
  final int cameraId;
  final int incidentId;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Canlı Yayın'),
        leading: IconButton(icon: const Icon(Icons.arrow_back), onPressed: () => context.pop()),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.videocam_off, size: 64, color: Colors.grey),
            const SizedBox(height: 16),
            Text('Kamera #$cameraId', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            const Text(
              'RTSP stream entegrasyonu için video player eklenecek.\n(Admin/Manager bu ekranı görebilir.)',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.grey),
            ),
          ],
        ),
      ),
    );
  }
}
