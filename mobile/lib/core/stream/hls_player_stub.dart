import 'package:flutter/widgets.dart';

String rtspToHls(String rtspUrl) {
  try {
    final clean = rtspUrl.replaceAll('"', '').trim();
    final uri = Uri.parse(clean);
    return 'http://${uri.host}:8888${uri.path.isEmpty ? '/stream' : uri.path}';
  } catch (_) {
    return rtspUrl;
  }
}

class HlsPlayerWidget extends StatelessWidget {
  const HlsPlayerWidget({super.key, required this.rtspUrl});
  final String rtspUrl;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Text(
        'Canlı yayın bu platformda desteklenmiyor.\nHLS: ${rtspToHls(rtspUrl)}',
        textAlign: TextAlign.center,
      ),
    );
  }
}
